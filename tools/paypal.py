"""Integracao PayPal (sandbox) com modo mock.

- Modo real: define PAYPAL_CLIENT_ID e PAYPAL_CLIENT_SECRET (sandbox) e
  PAYPAL_MODE=sandbox. Usa a API REST v2 (Orders) e v1 (Payouts).
- Modo mock (por omissao, ou sem credenciais): devolve respostas simuladas,
  para a demo correr sem conta PayPal e sem rede. O codigo real fica visivel
  para os juizes.

Estas sao as "ferramentas" de pagamento que o agente invoca.
"""
import base64
import os
import uuid

import requests

API_BASE = "https://api-m.sandbox.paypal.com"


def _modo_mock():
    if os.getenv("PAYPAL_MODE", "mock").lower() == "mock":
        return True
    return not (os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"))


def _token():
    cid = os.getenv("PAYPAL_CLIENT_ID")
    secret = os.getenv("PAYPAL_CLIENT_SECRET")
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        f"{API_BASE}/v1/oauth2/token",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def criar_order(total, descricao="", moeda="USD"):
    """Cria uma Order de pagamento. Ferramenta do agente."""
    valor = f"{float(total):.2f}"
    if _modo_mock():
        return {
            "id": "MOCK-ORDER-" + uuid.uuid4().hex[:10].upper(),
            "status": "CREATED",
            "valor": valor, "moeda": moeda,
            "approve_url": "https://www.sandbox.paypal.com/checkoutnow?token=MOCK",
            "mock": True,
        }
    token = _token()
    r = requests.post(
        f"{API_BASE}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {"currency_code": moeda, "value": valor},
                "description": descricao[:127],
            }],
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    approve = next((l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), None)
    return {"id": data["id"], "status": data["status"], "valor": valor, "moeda": moeda,
            "approve_url": approve, "mock": False}


def capturar_order(order_id, moeda="USD"):
    """Captura (cobra) uma Order aprovada. Ferramenta do agente.

    Nota: no fluxo real, a Order tem de ser aprovada pelo comprador (approve_url)
    antes da captura. Para a demo sem redireccionamento, usa o modo mock.
    """
    if _modo_mock() or str(order_id).startswith("MOCK"):
        return {"id": order_id, "status": "COMPLETED", "mock": True}
    token = _token()
    r = requests.post(
        f"{API_BASE}/v2/checkout/orders/{order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {"id": data.get("id", order_id), "status": data.get("status", "COMPLETED"), "mock": False}


def pagar_vendedor(valor, email_vendedor, moeda="USD", nota="Pagamento Teleka"):
    """Paga um vendedor via Payouts. Ferramenta do agente (liquidacao)."""
    v = f"{float(valor):.2f}"
    if _modo_mock():
        return {"batch_id": "MOCK-PAYOUT-" + uuid.uuid4().hex[:10].upper(),
                "status": "SUCCESS", "valor": v, "moeda": moeda,
                "destinatario": email_vendedor, "mock": True}
    token = _token()
    r = requests.post(
        f"{API_BASE}/v1/payments/payouts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "sender_batch_header": {"sender_batch_id": uuid.uuid4().hex, "email_subject": nota},
            "items": [{
                "recipient_type": "EMAIL",
                "amount": {"value": v, "currency": moeda},
                "receiver": email_vendedor,
                "note": nota,
            }],
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    return {"batch_id": data["batch_header"]["payout_batch_id"],
            "status": data["batch_header"]["batch_status"],
            "valor": v, "moeda": moeda, "destinatario": email_vendedor, "mock": False}


def estado():
    return "mock" if _modo_mock() else "sandbox"
