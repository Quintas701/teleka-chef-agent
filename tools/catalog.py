"""Catalogo mock do marketplace do Teleka.

Numa app real, isto seria uma pesquisa na base de dados de produtos dos
vendedores. Aqui e um JSON fixo para a demo correr sozinha.
"""
import json
import os

_CAMINHO = os.path.join(os.path.dirname(__file__), "..", "data", "catalog.json")

with open(_CAMINHO, encoding="utf-8") as _f:
    _DADOS = json.load(_f)

MOEDA = _DADOS["moeda"]


def _indice_email():
    return {v["id"]: v["email"] for v in _DADOS["vendedores"]}


def procurar_produtos(ingredientes):
    """Dada uma lista de ingredientes, devolve o melhor produto correspondente
    de cada vendedor (um por ingrediente). Ferramenta que o agente invoca."""
    emails = _indice_email()
    resultados = []
    vistos = set()
    for ing in ingredientes:
        ing_l = ing.lower().strip()
        if not ing_l:
            continue
        for v in _DADOS["vendedores"]:
            achou = None
            for p in v["produtos"]:
                if ing_l in p["nome"].lower() or any(ing_l == t or ing_l in t for t in p.get("tags", [])):
                    achou = p
                    break
            if achou and achou["id"] not in vistos:
                vistos.add(achou["id"])
                resultados.append({
                    "ingrediente": ing,
                    "produto_id": achou["id"],
                    "nome": achou["nome"],
                    "preco": achou["preco"],
                    "moeda": MOEDA,
                    "vendedor_id": v["id"],
                    "vendedor": v["nome"],
                    "vendedor_email": emails[v["id"]],
                })
                break
    return resultados
