"""Catalogo mock do marketplace do Teleka.

Numa app real, isto seria uma pesquisa na base de dados de produtos dos
vendedores. Aqui e um JSON fixo para a demo correr sozinha.

Precos e emails dos vendedores saem SEMPRE daqui (lado do servidor) — nunca
do pedido do browser. E isso que impede alguem de redireccionar um payout.
"""
import json
import os
from decimal import Decimal

from tools.texto import chave, formas, mesma_coisa

_CAMINHO = os.path.join(os.path.dirname(__file__), "..", "data", "catalog.json")

with open(_CAMINHO, encoding="utf-8") as _f:
    _DADOS = json.load(_f)

MOEDA = _DADOS["moeda"]


def para_centimos(valor):
    """2.5 -> 250, sem erros de virgula flutuante (passa por str -> Decimal)."""
    return int((Decimal(str(valor)) * 100).to_integral_value())


def _termos(produto):
    nome_base = produto["nome"].split("(")[0]
    return [chave(t) for t in produto.get("tags", [])] + [chave(nome_base)]


def _pontuacao(ingrediente, produto):
    """3 = o ingrediente E o produto ('tomates' ~ 'tomate');
    1 = uma palavra do ingrediente e um termo do produto ('peito de frango' ~ 'frango');
    0 = nada. 'sal' nunca casa com 'salsa' (compara palavras inteiras)."""
    ing = chave(ingrediente)
    palavras = ing.split()
    melhor = 0
    for termo in _termos(produto):
        if mesma_coisa(ing, termo):
            return 3
        if " " in termo:
            if f" {termo} " in f" {ing} ":
                melhor = max(melhor, 2)
        elif any(formas(p) & formas(termo) for p in palavras):
            melhor = max(melhor, 1)
    return melhor


def procurar_produtos(ingredientes):
    """Para cada ingrediente, o produto que melhor lhe corresponde em todo o
    catalogo. Ferramenta que o agente invoca.

    Devolve (carrinho, nao_encontrados) — o que nao existe no marketplace
    e reportado em vez de desaparecer em silencio."""
    carrinho, nao_encontrados, vistos = [], [], set()
    for ing in ingredientes:
        if not chave(ing):
            continue
        melhor = None  # (pontuacao, vendedor, produto)
        for v in _DADOS["vendedores"]:
            for p in v["produtos"]:
                s = _pontuacao(ing, p)
                if s and (melhor is None or s > melhor[0]):
                    melhor = (s, v, p)
        if melhor is None:
            nao_encontrados.append(ing)
            continue
        _, v, p = melhor
        if p["id"] in vistos:  # "tomate" e "tomate cereja" -> um so produto
            continue
        vistos.add(p["id"])
        carrinho.append({
            "ingrediente": ing,
            "produto_id": p["id"],
            "nome": p["nome"],
            "preco": p["preco"],
            "preco_centimos": para_centimos(p["preco"]),
            "moeda": MOEDA,
            "vendedor_id": v["id"],
            "vendedor": v["nome"],
            "vendedor_email": v["email"],
        })
    return carrinho, nao_encontrados
