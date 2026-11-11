"""O Teleka Chef Agent.

Orquestra as ferramentas (receita -> catalogo -> PayPal) para fechar o ciclo
"da inspiracao ao prato": o utilizador diz o que tem, a IA gera a receita, o
agente monta o carrinho com produtos de vendedores locais, cria o pagamento
PayPal e, na confirmacao, captura e liquida cada vendedor.

Divisao de responsabilidades (deliberada):
- a IA decide o PRATO e os ingredientes;
- o DINHEIRO nunca e decidido pelo LLM nem pelo browser. Precos e emails dos
  vendedores saem do catalogo do servidor, e o carrinho de cada order fica
  guardado aqui no momento em que a order e criada. A confirmacao so recebe o
  order_id — nao ha nada no pedido do cliente que mude quem recebe ou quanto.
"""
import re
import threading

from tools.recipe import gerar_receita
from tools.catalog import procurar_produtos, MOEDA
from tools.paypal import (criar_order, capturar_order, pagar_vendedores, ErroPayPal,
                          estado as paypal_estado)
from tools.images import url_imagem
from tools.texto import mesma_coisa

MAX_INGREDIENTES = 20


class ErroAgente(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.status = status


# ---------- estado das orders (em memoria: chega para a demo) ----------
# order_id -> {"carrinho", "total_centimos", "moeda", "mock", "titulo",
#              "lock", "resultado"}
_ORDERS = {}
_ORDERS_LOCK = threading.Lock()


def _parse_ingredientes(texto):
    # aceita "tenho arroz, tomate e peixe" -> ["arroz", "tomate", "peixe"]
    texto = re.sub(r"(?i)\b(tenho|tengo|i have|os|as|uns|umas|um|uma|tambem|também)\b",
                   " ", texto)
    # "com" separa ("frango com batata" = 2 ingredientes); "de" nao ("azeite de oliva")
    partes = re.split(r"(?i),|;|\n|\be\b|\by\b|\band\b|\bcom\b|\bwith\b|/|\+", texto)
    vistos = []
    for p in partes:
        p = re.sub(r"\s+", " ", p).strip(" .!?").lower()
        if p and not any(mesma_coisa(p, v) for v in vistos):
            vistos.append(p)
    return vistos[:MAX_INGREDIENTES]


def processar(pedido_texto, return_url=None, cancel_url=None):
    """Passo 1: do pedido ao carrinho + Order criada (a aguardar confirmacao)."""
    have = _parse_ingredientes(pedido_texto)
    if not have:
        raise ErroAgente("Nao encontrei ingredientes no pedido. Ex.: 'tenho arroz, tomate e peixe'.")
    receita = gerar_receita(have)

    # "tomates" (o que tens) e "tomate" (o que a receita pede) sao a mesma coisa:
    # sem isto, o utilizador pagaria pelo que ja tem em casa.
    faltam = [i for i in receita["ingredientes_necessarios"]
              if not any(mesma_coisa(i, h) for h in have)]

    carrinho, nao_encontrados = procurar_produtos(faltam)
    total_centimos = sum(p["preco_centimos"] for p in carrinho)

    order = None
    if carrinho:
        order = criar_order(total_centimos, descricao=receita["titulo"], moeda=MOEDA,
                            return_url=return_url, cancel_url=cancel_url)
        with _ORDERS_LOCK:
            _ORDERS[order["id"]] = {
                "carrinho": carrinho, "total_centimos": total_centimos, "moeda": MOEDA,
                "mock": order["mock"], "titulo": receita["titulo"],
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
    }


def _valor_em_centimos(texto):
    inteiro, _, frac = str(texto).partition(".")
    return int(inteiro) * 100 + int((frac + "00")[:2])


def confirmar(order_id):
    """Passo 2: o comprador aprovou -> captura o pagamento e paga cada vendedor.

    Idempotente: confirmar a mesma order duas vezes devolve o mesmo resultado
    sem voltar a cobrar nem a pagar."""
    with _ORDERS_LOCK:
        reg = _ORDERS.get(order_id)
    if reg is None:
        raise ErroAgente("Order desconhecida (ou o servidor reiniciou). Gera o carrinho de novo.", 404)

    with reg["lock"]:  # dois cliques simultaneos: o segundo espera e recebe o mesmo resultado
        if reg["resultado"] is not None:
            return reg["resultado"]

        captura = capturar_order(order_id, mock=reg["mock"])
        if captura["status"] != "COMPLETED":
            raise ErroAgente(f"Pagamento nao concluido (estado PayPal: {captura['status']}). "
                             "Nenhum vendedor foi pago.", 402)
        if not reg["mock"]:
            if (captura["moeda"] != reg["moeda"]
                    or _valor_em_centimos(captura["valor"]) != reg["total_centimos"]):
                raise ErroAgente(
                    f"Valor capturado ({captura['valor']} {captura['moeda']}) difere do carrinho "
                    f"({reg['total_centimos'] / 100:.2f} {reg['moeda']}). Payouts suspensos.", 409)

        # agrupa por vendedor; em centimos inteiros, a soma dos payouts == total exacto
        por_vendedor = {}
        for p in reg["carrinho"]:
            item = por_vendedor.setdefault(p["vendedor_id"], {
                "email": p["vendedor_email"], "vendedor": p["vendedor"], "centimos": 0})
            item["centimos"] += p["preco_centimos"]

        try:
            payouts = pagar_vendedores(list(por_vendedor.values()), sender_batch_id=order_id,
                                       moeda=reg["moeda"], nota="Venda Teleka", mock=reg["mock"])
        except ErroPayPal as e:
            # o cliente JA pagou: nao esconder isso atras de um erro generico
            raise ErroPayPal(f"Pagamento capturado ({captura['id']}), mas a liquidacao aos "
                             f"vendedores falhou: {e}", status=e.status, codigo=e.codigo,
                             debug_id=e.debug_id) from e

        reg["resultado"] = {
            "captura": captura,
            "payouts": payouts,
            "mensagem": "Pagamento concluido. A tua compra virou uma colecao no teu perfil — "
                        "inspira o proximo utilizador e o ciclo recomeca.",
        }
        return reg["resultado"]
