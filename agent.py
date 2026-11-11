"""The Teleka Chef Agent.

Chains the tools (recipe -> pantry check -> marketplace -> PayPal) to close the
loop "from inspiration to plate": the user says what they have, the AI writes
the recipe, the agent fills a cart from local vendors, creates the PayPal
order and, once the buyer approves, captures it and settles every vendor.

Every tool call is recorded in a trace (tool, structured data, duration) that
the UI shows as "Agent activity" — nothing is hidden behind the curtain.

Deliberate split of responsibilities:
- the AI decides the DISH and its ingredients;
- the MONEY is never decided by the LLM or by the browser. Prices and vendor
  emails come from the server-side catalog, and each order's cart is stored
  here when the order is created. Confirmation takes only the order_id —
  nothing in the client's request can change who gets paid or how much.
"""
import re
import threading
import time
from contextlib import contextmanager

from tools.recipe import gerar_receita
from tools.catalog import procurar_produtos, mesmo_produto, MOEDA
from tools.paypal import (criar_order, capturar_order, pagar_vendedores, ErroPayPal,
                          estado as paypal_estado)
from tools.images import url_imagem
from tools.texto import mesma_coisa

MAX_INGREDIENTES = 20
LINGUAS = ("en", "pt")

# Things nobody buys from a vendor: never put them in the cart.
_DA_TORNEIRA = ("agua", "water", "agua da torneira", "tap water", "gelo", "ice")

_MSG = {
    "sem_ingredientes": {
        "pt": "Nao encontrei ingredientes no pedido. Ex.: 'tenho arroz, tomate e peixe'.",
        "en": "I couldn't find any ingredients. Try: 'I have rice, tomato and fish'."},
    "order_desconhecida": {
        "pt": "Order desconhecida (ou o servidor reiniciou). Gera o carrinho de novo.",
        "en": "Unknown order (or the server restarted). Please build the cart again."},
    "nao_concluido": {
        "pt": "Pagamento nao concluido (estado PayPal: {s}). Nenhum vendedor foi pago.",
        "en": "Payment not completed (PayPal status: {s}). No vendor was paid."},
    "valor_difere": {
        "pt": "Valor capturado ({c}) difere do carrinho ({e}). Payouts suspensos.",
        "en": "Captured amount ({c}) does not match the cart ({e}). Payouts on hold."},
    "payout_falhou": {
        "pt": "Pagamento capturado ({id}), mas a liquidacao aos vendedores falhou: {erro}",
        "en": "Payment captured ({id}), but settling the vendors failed: {erro}"},
    "concluido": {
        "pt": "Pagamento concluido e vendedores pagos. A tua compra virou uma colecao "
              "no teu perfil Teleka — inspira o proximo utilizador e o ciclo recomeca.",
        "en": "Paid, and every vendor settled. Your purchase becomes a collection on your "
              "Teleka profile — it inspires the next cook, and the loop starts again."},
}


def _t(chave, lang, **kw):
    return _MSG[chave][lang if lang in LINGUAS else "en"].format(**kw)


class ErroAgente(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


class _Rastro:
    """Records each tool call: {tool, data, ms}. The UI renders it."""

    def __init__(self):
        self.passos = []

    @contextmanager
    def passo(self, ferramenta):
        reg = {"tool": ferramenta, "data": {}}
        t0 = time.perf_counter()
        try:
            yield reg["data"]
        finally:
            reg["ms"] = round((time.perf_counter() - t0) * 1000)
            self.passos.append(reg)


# ---------- order state (in memory: enough for the demo) ----------
# order_id -> {"carrinho", "total_centimos", "moeda", "mock", "titulo", "lang",
#              "lock", "resultado"}
_ORDERS = {}
_ORDERS_LOCK = threading.Lock()


def _parse_ingredientes(texto):
    # "tenho arroz, tomate e peixe" / "I have rice, tomato and fish" -> 3 items
    texto = re.sub(r"(?i)\b(tenho|tengo|i have|i've got|i got|os|as|uns|umas|um|uma|"
                   r"tambem|também|some|the|a|an)\b", " ", texto)
    # "com"/"with" split ("frango com batata" = 2 items); "de"/"of" do not ("azeite de oliva")
    partes = re.split(r"(?i),|;|\n|\be\b|\by\b|\band\b|\bcom\b|\bwith\b|/|\+|&", texto)
    vistos = []
    for p in partes:
        p = re.sub(r"\s+", " ", p).strip(" .!?:").lower()
        if p and not any(mesma_coisa(p, v) for v in vistos):
            vistos.append(p)
    return vistos[:MAX_INGREDIENTES]


def processar(pedido_texto, return_url=None, cancel_url=None, lang="en"):
    """Step 1: from the request to a cart + a PayPal order awaiting approval."""
    lang = lang if lang in LINGUAS else "en"
    rastro = _Rastro()

    with rastro.passo("parse_request") as d:
        have = _parse_ingredientes(pedido_texto)
        d["ingredients"] = have
    if not have:
        raise ErroAgente(_t("sem_ingredientes", lang))

    with rastro.passo("generate_recipe") as d:
        receita = gerar_receita(have, lang=lang)
        d.update(engine=receita["motor"], title=receita["titulo"],
                 ingredients=len(receita["ingredientes_necessarios"]))

    # "tomatoes" (what you have) == "tomato" (what the recipe needs):
    # without this the user would pay for what is already in the kitchen.
    with rastro.passo("check_pantry") as d:
        faltam, ja_tens, torneira = [], [], []
        for i in receita["ingredientes_necessarios"]:
            if any(mesma_coisa(i, h) or mesmo_produto(i, h) for h in have):
                ja_tens.append(i)
            elif any(mesma_coisa(i, x) for x in _DA_TORNEIRA):
                torneira.append(i)
            else:
                faltam.append(i)
        d.update(have=ja_tens, missing=faltam, skipped=torneira)

    with rastro.passo("search_marketplace") as d:
        carrinho, nao_encontrados = procurar_produtos(faltam)
        total_centimos = sum(p["preco_centimos"] for p in carrinho)
        d.update(found=len(carrinho), vendors=sorted({p["vendedor"] for p in carrinho}),
                 not_found=nao_encontrados, total=f"{total_centimos / 100:.2f} {MOEDA}")

    order = None
    if carrinho:
        with rastro.passo("create_paypal_order") as d:
            order = criar_order(total_centimos, descricao=receita["titulo"], moeda=MOEDA,
                                return_url=return_url, cancel_url=cancel_url)
            d.update(order_id=order["id"], status=order["status"],
                     amount=f"{order['valor']} {MOEDA}", mode=paypal_estado())
        with _ORDERS_LOCK:
            _ORDERS[order["id"]] = {
                "carrinho": carrinho, "total_centimos": total_centimos, "moeda": MOEDA,
                "mock": order["mock"], "titulo": receita["titulo"], "lang": lang,
                "lock": threading.Lock(), "resultado": None,
            }

    return {
        "ingredientes_que_tens": have,
        "receita": receita,
        "imagem_url": url_imagem(receita["titulo"], ", ".join(have)),
        "faltam": faltam,
        "nao_encontrados": nao_encontrados,
        "carrinho": carrinho,
        "total": total_centimos / 100,
        "moeda": MOEDA,
        "order": order,
        "paypal_modo": paypal_estado(),
        "lang": lang,
        "trace": rastro.passos,
    }


def _valor_em_centimos(texto):
    inteiro, _, frac = str(texto).partition(".")
    return int(inteiro) * 100 + int((frac + "00")[:2])


def confirmar(order_id, lang=None):
    """Step 2: the buyer approved -> capture the payment and settle each vendor.

    Idempotent: confirming the same order twice returns the same result
    without charging or paying again."""
    with _ORDERS_LOCK:
        reg = _ORDERS.get(order_id)
    if reg is None:
        raise ErroAgente(_t("order_desconhecida", lang or "en"), 404)
    lang = reg["lang"]

    with reg["lock"]:  # two simultaneous clicks: the 2nd waits and gets the same result
        if reg["resultado"] is not None:
            return reg["resultado"]
        rastro = _Rastro()

        with rastro.passo("capture_payment") as d:
            captura = capturar_order(order_id, mock=reg["mock"])
            d.update(capture_id=captura["id"], status=captura["status"])
        if captura["status"] != "COMPLETED":
            raise ErroAgente(_t("nao_concluido", lang, s=captura["status"]), 402)

        esperado = f"{reg['total_centimos'] / 100:.2f} {reg['moeda']}"
        with rastro.passo("verify_amount") as d:
            if reg["mock"]:
                capturado, ok = esperado, True
            else:
                capturado = f"{captura['valor']} {captura['moeda']}"
                ok = (captura["moeda"] == reg["moeda"]
                      and _valor_em_centimos(captura["valor"]) == reg["total_centimos"])
            d.update(expected=esperado, captured=capturado, match=ok)
        if not ok:
            raise ErroAgente(_t("valor_difere", lang, c=capturado, e=esperado), 409)

        # group by vendor; in integer cents the payouts add up to the exact total
        por_vendedor = {}
        for p in reg["carrinho"]:
            item = por_vendedor.setdefault(p["vendedor_id"], {
                "email": p["vendedor_email"], "vendedor": p["vendedor"], "centimos": 0})
            item["centimos"] += p["preco_centimos"]

        with rastro.passo("pay_vendors") as d:
            try:
                payouts = pagar_vendedores(list(por_vendedor.values()), sender_batch_id=order_id,
                                           moeda=reg["moeda"], nota="Teleka sale",
                                           mock=reg["mock"])
            except ErroPayPal as e:
                # the buyer HAS paid: don't hide that behind a generic error
                raise ErroPayPal(_t("payout_falhou", lang, id=captura["id"], erro=e),
                                 status=e.status, codigo=e.codigo, debug_id=e.debug_id) from e
            d.update(vendors=len(payouts), batch_id=payouts[0]["batch_id"] if payouts else None,
                     status=payouts[0]["status"] if payouts else None, total=esperado)

        reg["resultado"] = {
            "captura": captura,
            "payouts": payouts,
            "titulo": reg["titulo"],
            "mensagem": _t("concluido", lang),
            "trace": rastro.passos,
        }
        return reg["resultado"]
