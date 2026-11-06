"""Teste do fluxo completo por linha de comandos (sem servidor web).

    python run_demo.py "tenho arroz, tomate e peixe"

Corre em modo mock por omissao, por isso funciona sem chaves nem internet.
"""
import json
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import agent


def main():
    pedido = sys.argv[1] if len(sys.argv) > 1 else "tenho arroz, tomate e peixe"
    print(f"\n>>> Pedido: {pedido}\n")

    r = agent.processar(pedido)
    print(f"PayPal em modo: {r['paypal_modo']}")
    print(f"\nReceita [{r['receita']['motor']}]: {r['receita']['titulo']}")
    print(f"  {r['receita']['descricao']}")
    for i, passo in enumerate(r["receita"]["passos"], 1):
        print(f"   {i}. {passo}")

    print(f"\nFaltam comprar: {', '.join(r['faltam']) or '(nada)'}")
    print("Carrinho:")
    for p in r["carrinho"]:
        print(f"   - {p['nome']:28} {p['preco']:>5.2f} {p['moeda']}  ({p['vendedor']})")
    print(f"   TOTAL: {r['total']:.2f} {r['moeda']}")

    if not r["order"]:
        print("\n(Carrinho vazio — nada a pagar.)")
        return
    print(f"\nOrder PayPal: {r['order']['id']}  [{r['order']['status']}]")

    print("\n--- utilizador aprova e paga ---")
    c = agent.confirmar(r["order"]["id"], r["carrinho"])
    print(f"Captura: {c['captura']['id']}  [{c['captura']['status']}]")
    for po in c["payouts"]:
        print(f"Payout -> {po['vendedor']:30} {po['valor']} {po['moeda']}  "
              f"[{po['status']}] ({po['batch_id']})")
    print(f"\n{c['mensagem']}")
    print("\nOK — fluxo completo.\n")


if __name__ == "__main__":
    main()
