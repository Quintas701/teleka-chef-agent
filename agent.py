"""O Teleka Chef Agent.

Orquestra as ferramentas (receita -> catalogo -> PayPal) para fechar o ciclo
"da inspiracao ao prato": o utilizador diz o que tem, o agente gera a receita,
monta o carrinho com produtos de vendedores locais, cria o pagamento PayPal e,
na confirmacao, captura e paga o vendedor.

Com um modelo que suporta tool-calling (via LLM_API_KEY) o proprio LLM invoca
as ferramentas (modo "agentico"). Sem isso, a orquestracao e determinista.
Ambos usam EXACTAMENTE as mesmas ferramentas.
"""
import os
import re

from tools.recipe import gerar_receita
from tools.catalog import procurar_produtos, MOEDA
from tools.paypal import criar_order, capturar_order, pagar_vendedor, estado as paypal_estado
from tools.images import url_imagem


def _parse_ingredientes(texto):
    # aceita "tenho arroz, tomate e peixe" -> ["arroz", "tomate", "peixe"]
    texto = re.sub(r"(?i)\b(tenho|tengo|i have|com|com os|os|as)\b", " ", texto)
    partes = re.split(r",|;|\be\b|\band\b|/|\+", texto)
    return [p.strip().lower() for p in partes if p.strip()]


def processar(pedido_texto):
    """Passo 1: do pedido ao carrinho + Order criada (a aguardar confirmacao)."""
    have = _parse_ingredientes(pedido_texto)
    receita = gerar_receita(have)

    have_set = {h.lower() for h in have}
    faltam = [i for i in receita["ingredientes_necessarios"] if i.lower() not in have_set]
    if not faltam:  # ja tem tudo? compra na mesma os staples para a demo ter carrinho
        faltam = [i for i in receita["ingredientes_necessarios"]]

    carrinho = procurar_produtos(faltam)
    total = round(sum(p["preco"] for p in carrinho), 2)

    order = criar_order(total, descricao=receita["titulo"], moeda=MOEDA) if carrinho else None

    return {
        "ingredientes_que_tens": have,
        "receita": receita,
        "imagem_url": url_imagem(receita["titulo"], ", ".join(have)),
        "faltam": faltam,
        "carrinho": carrinho,
        "total": total,
        "moeda": MOEDA,
        "order": order,
        "paypal_modo": paypal_estado(),
    }


def confirmar(order_id, carrinho):
    """Passo 2: o utilizador aprova -> captura o pagamento e paga cada vendedor."""
    captura = capturar_order(order_id, moeda=MOEDA)

    # agrupa o carrinho por vendedor e paga a cada um o seu subtotal
    por_vendedor = {}
    for p in carrinho:
        chave = (p["vendedor_id"], p["vendedor"], p["vendedor_email"])
        por_vendedor.setdefault(chave, 0.0)
        por_vendedor[chave] += float(p["preco"])

    payouts = []
    for (vid, nome, email), subtotal in por_vendedor.items():
        res = pagar_vendedor(round(subtotal, 2), email, moeda=MOEDA, nota=f"Venda Teleka — {nome}")
        res["vendedor"] = nome
        payouts.append(res)

    return {
        "captura": captura,
        "payouts": payouts,
        "mensagem": "Pagamento concluido. A tua compra virou uma colecao no teu perfil — "
                    "inspira o proximo utilizador e o ciclo recomeca.",
    }
