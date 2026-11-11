"""Testes do fluxo completo. Correm offline: mock, ou a API PayPal simulada.

    pip install -r requirements-dev.txt
    pytest
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

import agent  # noqa: E402
import app as servidor  # noqa: E402
from tools import paypal, recipe  # noqa: E402
from tools.catalog import procurar_produtos  # noqa: E402
from tools.texto import mesma_coisa  # noqa: E402


@pytest.fixture(autouse=True)
def _ambiente_limpo(monkeypatch):
    for k in ("LLM_API_KEY", "PAYPAL_MODE", "PAYPAL_CLIENT_ID", "PAYPAL_CLIENT_SECRET"):
        monkeypatch.delenv(k, raising=False)
    paypal._token_cache.update(valor=None, expira=0.0)
    agent._ORDERS.clear()


@pytest.fixture
def cliente():
    return TestClient(servidor.app)


# ---------- texto / catalogo ----------
def test_plural_e_acentos_sao_o_mesmo_ingrediente():
    assert mesma_coisa("Tomates", "tomate")
    assert mesma_coisa("limões", "limao")
    assert mesma_coisa("ovos", "ovo")
    assert not mesma_coisa("sal", "salsa")


def test_parser_separa_com_e_ignora_verbos():
    assert agent._parse_ingredientes("Tenho arroz, tomates e peixe") == ["arroz", "tomates", "peixe"]
    assert agent._parse_ingredientes("frango com batata") == ["frango", "batata"]
    assert agent._parse_ingredientes("azeite de oliva") == ["azeite de oliva"]


def test_catalogo_casa_palavras_e_reporta_o_que_falta():
    carrinho, falta = procurar_produtos(["peito de frango", "limões", "salsa", "trufa"])
    ids = [p["produto_id"] for p in carrinho]
    assert ids == ["p13", "p11", "p21"]  # 'salsa' e salsa (p21), nunca sal (p5)
    assert falta == ["trufa"]
    assert all(p["bairro"] and p["nome_en"] for p in carrinho)


def test_nao_cobra_o_que_o_utilizador_ja_tem():
    r = agent.processar("tenho tomates, cebolas, alho, azeite e sal")
    assert all(p["produto_id"] not in ("p10", "p2") for p in r["carrinho"])
    assert r["order"] is None and r["total"] == 0


# ---------- LLM: saida invalida cai no modelo offline ----------
def test_llm_com_lista_como_string_e_recusado():
    with pytest.raises(ValueError):
        recipe._validar({"titulo": "x", "passos": ["a"], "ingredientes_necessarios": "arroz"})


def test_llm_falha_cai_no_offline(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "x")
    monkeypatch.setattr(recipe, "_gerar_llm", lambda h, l: (_ for _ in ()).throw(RuntimeError("rede")))
    assert recipe.gerar_receita(["arroz"])["motor"] == "offline recipe book"
    assert recipe.gerar_receita(["arroz"], lang="pt")["motor"] == "livro de receitas offline"


# ---------- pratos reais, nunca inventados ----------
@pytest.mark.parametrize("tenho, lang, prato", [
    (["frango", "batatas"], "pt", "Frango frito com batata frita"),
    (["chicken", "potatoes"], "en", "Fried chicken with French fries"),
    (["frango", "batata"], "en", "Fried chicken with French fries"),  # PT escrito, EN pedido
    (["arroz", "tomate", "peixe"], "pt", "Arroz de peixe"),
    (["fuba", "peixe"], "pt", "Funge com calulu de peixe"),
    (["ovos", "batatas"], "pt", "Tortilha de batata"),
    (["ovos", "farinha", "leite"], "en", "Fluffy pancakes"),
    (["esparguete", "tomates"], "pt", "Esparguete com molho de tomate"),
    (["frango"], "pt", "Frango grelhado com gindungo"),
])
def test_livro_escolhe_o_prato_classico(tenho, lang, prato):
    assert recipe._gerar_canned(tenho, lang)["titulo"] == prato


def test_livro_usa_as_palavras_do_utilizador_e_compra_oleo_para_fritar():
    r = agent.processar("tenho frango e batatas", lang="pt")
    assert r["receita"]["ingredientes_necessarios"][:2] == ["frango", "batatas"]
    ids = [p["produto_id"] for p in r["carrinho"]]
    assert "p31" in ids and "p4" not in ids  # oleo vegetal, nao azeite
    assert not {"p13", "p6"} & set(ids)      # nao volta a vender frango nem batata


def test_sem_prato_no_livro_o_titulo_e_honesto():
    assert recipe._gerar_canned(["beringela", "queijo"], "pt")["titulo"] == "Refogado de beringela e queijo"


def test_prompt_da_ia_impoe_o_prato_classico(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "x")
    visto = {}

    def falso(url, headers=None, json=None, timeout=None):
        visto.update(json)
        conteudo = '{"titulo": "Frango frito com batata frita", "passos": ["a"], "ingredientes_necessarios": ["frango"]}'
        return type("R", (), {"status_code": 200, "text": "",
                              "json": lambda self: {"choices": [{"message": {"content": conteudo}}]}})()
    monkeypatch.setattr(recipe.requests, "post", falso)
    r = recipe.gerar_receita(["frango", "batatas"], lang="pt")
    pedido = visto["messages"][1]["content"]
    assert "OBRIGATORIAMENTE: 'Frango frito com batata frita'" in pedido
    assert "tratando o utilizador por tu" in pedido
    assert visto["reasoning_effort"] == "low" and r["motor"].startswith("AI")


def test_despensa_entre_linguas_nao_compra_duas_vezes(monkeypatch):
    # o utilizador escreve "arroz", a IA responde "rice": e o MESMO produto
    monkeypatch.setattr(recipe, "_tem_llm", lambda: False)
    monkeypatch.setattr(agent, "gerar_receita", lambda have, lang="en": {
        "titulo": "Rice", "descricao": "", "passos": ["cook"], "motor": "x",
        "ingredientes_necessarios": ["rice", "tomato", "water"]})
    r = agent.processar("tenho arroz")
    ids = [p["produto_id"] for p in r["carrinho"]]
    assert "p1" not in ids and ids == ["p10"]
    pantry = next(t for t in r["trace"] if t["tool"] == "check_pantry")["data"]
    assert pantry["have"] == ["rice"] and pantry["skipped"] == ["water"]  # agua nao se compra


def test_trace_regista_cada_ferramenta_e_lingua():
    r = agent.processar("I have rice, tomato and fish", lang="en")
    assert [t["tool"] for t in r["trace"]] == [
        "parse_request", "generate_recipe", "check_pantry", "search_marketplace", "create_paypal_order"]
    assert all(isinstance(t["ms"], int) for t in r["trace"])
    assert r["receita"]["titulo"] == "Portuguese fish rice (arroz de peixe)"
    c = agent.confirmar(r["order"]["id"])
    assert [t["tool"] for t in c["trace"]] == ["capture_payment", "verify_amount", "pay_vendors"]
    assert c["trace"][1]["data"]["match"] is True
    pt = agent.processar("tenho arroz", lang="pt")
    assert pt["lang"] == "pt" and pt["receita"]["titulo"] == "Arroz de tomate"


# ---------- fluxo mock pela API HTTP ----------
def test_fluxo_mock_completo(cliente):
    r = cliente.post("/api/gerar", json={"pedido": "tenho arroz, tomate e peixe"}).json()
    assert r["receita"]["titulo"] == "Portuguese fish rice (arroz de peixe)"
    assert r["total"] == 7.6 and r["order"]["mock"]
    c = cliente.post("/api/confirmar", json={"order_id": r["order"]["id"]}).json()
    assert c["captura"]["status"] == "COMPLETED"
    assert sum(float(p["valor"]) for p in c["payouts"]) == pytest.approx(7.6)


def test_cliente_nao_consegue_redireccionar_payouts(cliente):
    r = cliente.post("/api/gerar", json={"pedido": "tenho arroz"}).json()
    adulterado = [dict(p, vendedor_email="atacante@evil.example", preco=9999) for p in r["carrinho"]]
    c = cliente.post("/api/confirmar",
                     json={"order_id": r["order"]["id"], "carrinho": adulterado}).json()
    emails = {p["destinatario"] for p in c["payouts"]}
    assert "atacante@evil.example" not in emails
    assert sum(float(p["valor"]) for p in c["payouts"]) == pytest.approx(r["total"])


def test_confirmar_duas_vezes_nao_paga_duas_vezes(cliente, monkeypatch):
    chamadas = []
    original = paypal.pagar_vendedores
    monkeypatch.setattr(agent, "pagar_vendedores",
                        lambda *a, **k: chamadas.append(1) or original(*a, **k))
    oid = cliente.post("/api/gerar", json={"pedido": "arroz"}).json()["order"]["id"]
    c1 = cliente.post("/api/confirmar", json={"order_id": oid}).json()
    c2 = cliente.post("/api/confirmar", json={"order_id": oid}).json()
    assert len(chamadas) == 1 and c1 == c2


def test_order_desconhecida_e_404_e_mock_forjado_nao_paga(cliente):
    r = cliente.post("/api/confirmar", json={"order_id": "MOCK-ORDER-FORJADA"})
    assert r.status_code == 404 and "erro" in r.json()


def test_pedido_vazio_ou_enorme_e_recusado(cliente):
    assert cliente.post("/api/gerar", json={"pedido": ""}).status_code == 422
    assert cliente.post("/api/gerar", json={"pedido": "x" * 501}).status_code == 422
    assert cliente.post("/api/gerar", json={"pedido": "e e e"}).status_code == 400
    assert cliente.post("/api/gerar", json={"pedido": "arroz", "lang": "xx"}).status_code == 422


def test_pagina_e_logo_servidos(cliente):
    assert "TELEKA" in cliente.get("/").text
    assert cliente.get("/logo.svg").headers["content-type"].startswith("image/svg")


# ---------- sandbox com a API PayPal simulada ----------
class _Resp:
    def __init__(self, status, corpo):
        self.status_code, self._c, self.ok, self.text = status, corpo, status < 400, str(corpo)

    def json(self):
        return self._c


class _PayPalFalso:
    def __init__(self, valor_capturado=None, aprovado=True):
        self.pedidos, self.valor_capturado, self.aprovado = [], valor_capturado, aprovado

    def __call__(self, url, headers=None, json=None, data=None, timeout=None):
        self.pedidos.append((url, headers, json))
        if url.endswith("/oauth2/token"):
            return _Resp(200, {"access_token": "T", "expires_in": 3600})
        if url.endswith("/v2/checkout/orders"):
            self.total = json["purchase_units"][0]["amount"]["value"]
            return _Resp(201, {"id": "ORD1", "status": "PAYER_ACTION_REQUIRED",
                               "links": [{"rel": "payer-action", "href": "https://pp/aprovar"}]})
        if url.endswith("/capture"):
            if not self.aprovado:
                return _Resp(422, {"name": "UNPROCESSABLE_ENTITY", "debug_id": "D1",
                                   "details": [{"issue": "ORDER_NOT_APPROVED",
                                                "description": "Payer has not yet approved"}]})
            v = self.valor_capturado or self.total
            return _Resp(201, {"id": "ORD1", "status": "COMPLETED", "purchase_units": [{
                "payments": {"captures": [{"id": "CAP1", "status": "COMPLETED",
                                           "amount": {"value": v, "currency_code": "USD"}}]}}]})
        if url.endswith("/payments/payouts"):
            return _Resp(201, {"batch_header": {"payout_batch_id": "B1", "batch_status": "PENDING"}})
        raise AssertionError(url)


@pytest.fixture
def sandbox(monkeypatch):
    monkeypatch.setenv("PAYPAL_MODE", "sandbox")
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "id")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "s")

    def instalar(**kw):
        falso = _PayPalFalso(**kw)
        monkeypatch.setattr(paypal.requests, "post", falso)
        return falso
    return instalar


def test_sandbox_fluxo_com_aprovacao(cliente, sandbox):
    pp = sandbox()
    r = cliente.post("/api/gerar", json={"pedido": "tenho arroz, tomate e peixe"}).json()
    assert r["order"]["approve_url"] == "https://pp/aprovar"
    ctx = pp.pedidos[-1][2]["payment_source"]["paypal"]["experience_context"]
    assert ctx["return_url"].endswith("/?paypal=aprovado")

    c = cliente.post("/api/confirmar", json={"order_id": "ORD1"}).json()
    assert c["captura"]["valor"] == "7.60"
    lote = pp.pedidos[-1][2]
    assert lote["sender_batch_header"]["sender_batch_id"] == "ORD1"  # idempotente na PayPal
    assert pp.pedidos[-2][1]["PayPal-Request-Id"] == "capturar-ORD1"
    tokens = [u for u, *_ in pp.pedidos if u.endswith("/oauth2/token")]
    assert len(tokens) == 1  # token reutilizado


def test_sandbox_nao_aprovado_da_erro_legivel_e_nao_paga(cliente, sandbox):
    pp = sandbox(aprovado=False)
    cliente.post("/api/gerar", json={"pedido": "arroz"})
    r = cliente.post("/api/confirmar", json={"order_id": "ORD1"})
    assert r.status_code == 422 and "ORDER_NOT_APPROVED" in r.json()["erro"]
    assert not any(u.endswith("/payouts") for u, *_ in pp.pedidos)


def test_sandbox_valor_capturado_diferente_suspende_payouts(cliente, sandbox):
    pp = sandbox(valor_capturado="0.01")
    cliente.post("/api/gerar", json={"pedido": "arroz"})
    r = cliente.post("/api/confirmar", json={"order_id": "ORD1"})
    assert r.status_code == 409
    assert not any(u.endswith("/payouts") for u, *_ in pp.pedidos)
