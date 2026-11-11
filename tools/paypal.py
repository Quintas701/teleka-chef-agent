"""Integracao PayPal (sandbox) com modo mock.

- Modo real: PAYPAL_MODE=sandbox + PAYPAL_CLIENT_ID + PAYPAL_CLIENT_SECRET.
  Usa a API REST v2 (Orders) e v1 (Payouts).
- Modo mock (por omissao, ou sem credenciais): respostas simuladas, para a demo
  correr sem conta PayPal e sem rede. O codigo real fica visivel para os juizes.

Idempotencia: a PayPal deduplica pelo cabecalho PayPal-Request-Id (Orders) e
pelo sender_batch_id (Payouts). Derivamos ambos do order_id, por isso um
duplo clique ou um retry de rede NUNCA cobra nem paga duas vezes.

Estas sao as "ferramentas" de pagamento que o agente invoca.
"""
import base64
import os
import threading
import time
import uuid

import requests

API_BASE = "https://api-m.sandbox.paypal.com"
TIMEOUT = 30


class ErroPayPal(Exception):
    """Falha da API PayPal, com a mensagem e o debug_id que a PayPal devolve."""

    def __init__(self, mensagem, status=502, codigo=None, debug_id=None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.debug_id = debug_id


def _modo_mock():
    if os.getenv("PAYPAL_MODE", "mock").lower() != "sandbox":
        return True
    return not (os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"))


def estado():
    return "mock" if _modo_mock() else "sandbox"


def aviso_configuracao():
    """Explica porque estamos em mock quando o utilizador pediu sandbox."""
    if os.getenv("PAYPAL_MODE", "mock").lower() == "sandbox" and _modo_mock():
        return "PAYPAL_MODE=sandbox mas faltam PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET — a usar mock."
    return None


# ---------- token OAuth (cacheado ate perto de expirar) ----------
_token_cache = {"valor": None, "expira": 0.0}
_token_lock = threading.Lock()


def _token():
    with _token_lock:
        if _token_cache["valor"] and time.time() < _token_cache["expira"]:
            return _token_cache["valor"]
        cid = os.getenv("PAYPAL_CLIENT_ID")
        secret = os.getenv("PAYPAL_CLIENT_SECRET")
        auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
        r = requests.post(
            f"{API_BASE}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
            timeout=TIMEOUT,
        )
        _verificar(r, "autenticacao")
        dados = r.json()
        _token_cache["valor"] = dados["access_token"]
        _token_cache["expira"] = time.time() + int(dados.get("expires_in", 300)) - 60
        return _token_cache["valor"]


def _verificar(r, operacao):
    if r.ok:
        return
    try:
        corpo = r.json()
    except ValueError:
        corpo = {}
    detalhes = corpo.get("details") or [{}]
    codigo = detalhes[0].get("issue") or corpo.get("name") or corpo.get("error")
    msg = (detalhes[0].get("description") or corpo.get("message")
           or corpo.get("error_description") or r.text[:200])
    raise ErroPayPal(f"PayPal ({operacao}): {codigo or r.status_code} — {msg}",
                     status=422 if r.status_code == 422 else 502,
                     codigo=codigo, debug_id=corpo.get("debug_id"))


def _post(caminho, operacao, json=None, request_id=None):
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}
    if request_id:
        headers["PayPal-Request-Id"] = request_id
    try:
        r = requests.post(f"{API_BASE}{caminho}", headers=headers, json=json, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise ErroPayPal(f"PayPal ({operacao}): sem ligacao — {e}") from e
    _verificar(r, operacao)
    return r.json()


def _valor(centimos):
    return f"{centimos // 100}.{centimos % 100:02d}"


# ---------- Orders v2 ----------
def criar_order(total_centimos, descricao="", moeda="USD", return_url=None, cancel_url=None):
    """Cria uma Order de pagamento. Ferramenta do agente.
    Em sandbox devolve approve_url: o comprador TEM de aprovar la antes da captura."""
    valor = _valor(total_centimos)
    if _modo_mock():
        return {"id": "MOCK-ORDER-" + uuid.uuid4().hex[:10].upper(), "status": "CREATED",
                "valor": valor, "moeda": moeda, "approve_url": None, "mock": True}

    unidade = {"amount": {"currency_code": moeda, "value": valor},
               "description": (descricao or "Compra Teleka")[:127]}
    corpo = {"intent": "CAPTURE", "purchase_units": [unidade]}
    if return_url:
        corpo["payment_source"] = {"paypal": {"experience_context": {
            "return_url": return_url,
            "cancel_url": cancel_url or return_url,
            "user_action": "PAY_NOW",
            "shipping_preference": "NO_SHIPPING",
            "brand_name": "Teleka",
        }}}
    data = _post("/v2/checkout/orders", "criar order", json=corpo)
    approve = next((l["href"] for l in data.get("links", [])
                    if l.get("rel") in ("payer-action", "approve")), None)
    return {"id": data["id"], "status": data["status"], "valor": valor, "moeda": moeda,
            "approve_url": approve, "mock": False}


def capturar_order(order_id, mock):
    """Captura (cobra) uma Order aprovada. Ferramenta do agente.
    Devolve o estado E o valor efectivamente capturado, para o agente confirmar
    que bate com o carrinho antes de pagar a alguem."""
    if mock:
        return {"id": order_id, "status": "COMPLETED", "valor": None, "moeda": None, "mock": True}
    data = _post(f"/v2/checkout/orders/{order_id}/capture", "capturar",
                 request_id=f"capturar-{order_id}")
    cap = {}
    for pu in data.get("purchase_units", []):
        caps = pu.get("payments", {}).get("captures", [])
        if caps:
            cap = caps[0]
            break
    amount = cap.get("amount", {})
    return {"id": cap.get("id", data.get("id", order_id)),
            "status": cap.get("status", data.get("status")),
            "valor": amount.get("value"), "moeda": amount.get("currency_code"),
            "mock": False}


# ---------- Payouts v1 ----------
def pagar_vendedores(itens, sender_batch_id, moeda="USD", nota="Venda Teleka", mock=False):
    """Paga varios vendedores num UNICO lote Payouts. Ferramenta do agente.

    itens: [{"email", "centimos", "vendedor"}]. sender_batch_id deve ser estavel
    (o order_id): a PayPal recusa um segundo lote com o mesmo id."""
    if mock:
        batch = "MOCK-PAYOUT-" + uuid.uuid4().hex[:10].upper()
        estado_lote = "SUCCESS"
    else:
        data = _post("/v1/payments/payouts", "payouts", json={
            "sender_batch_header": {"sender_batch_id": sender_batch_id[:127],
                                    "email_subject": nota},
            "items": [{
                "recipient_type": "EMAIL",
                "amount": {"value": _valor(i["centimos"]), "currency": moeda},
                "receiver": i["email"],
                "note": f"{nota} — {i['vendedor']}"[:4000],
                "sender_item_id": f"{sender_batch_id}-{n}"[:63],
            } for n, i in enumerate(itens)],
        })
        batch = data["batch_header"]["payout_batch_id"]
        estado_lote = data["batch_header"]["batch_status"]
    return [{"batch_id": batch, "status": estado_lote, "valor": _valor(i["centimos"]),
             "moeda": moeda, "destinatario": i["email"], "vendedor": i["vendedor"],
             "mock": mock} for i in itens]
