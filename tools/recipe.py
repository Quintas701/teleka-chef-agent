"""Geracao de receitas.

Com LLM_API_KEY (Groq/Gemini/OpenAI-compativel) gera a receita por IA.
Sem chave, usa uma receita-modelo determinista para a demo correr offline.
Devolve sempre: {titulo, descricao, passos: [...], ingredientes_necessarios: [...]}.
"""
import json
import os

_STAPLES = ["cebola", "alho", "azeite", "sal"]


def _tem_llm():
    return bool(os.getenv("LLM_API_KEY"))


def _gerar_llm(have_list):
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
    )
    modelo = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
    have = ", ".join(have_list)
    prompt = (
        "Es um chef. O utilizador TEM estes ingredientes: "
        f"{have}. "
        "Sugere UM prato simples. Responde APENAS em JSON valido com as chaves: "
        '"titulo" (string), "descricao" (1 frase apetitosa), '
        '"passos" (lista de 3 a 5 strings curtas) e '
        '"ingredientes_necessarios" (lista COMPLETA de ingredientes do prato, '
        "em minusculas e no singular, incluindo os que o utilizador ja tem)."
    )
    resp = client.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": "Respondes sempre com JSON valido, sem texto a mais."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    dados = json.loads(resp.choices[0].message.content)
    # normaliza
    dados["ingredientes_necessarios"] = [str(i).lower().strip() for i in dados.get("ingredientes_necessarios", [])]
    dados["passos"] = [str(p) for p in dados.get("passos", [])]
    dados.setdefault("titulo", "Prato do dia")
    dados.setdefault("descricao", "")
    dados["motor"] = f"IA ({modelo})"
    return dados


def _gerar_canned(have_list):
    """Receita-modelo sem IA — garante que a demo corre sem chaves."""
    principal = have_list[0] if have_list else "legumes"
    titulo = f"{principal.capitalize()} salteado do chef"
    necessarios = list(dict.fromkeys([h.lower().strip() for h in have_list] + _STAPLES))
    passos = [
        "Pica a cebola e o alho e leva ao lume com o azeite.",
        f"Junta {', '.join(have_list) if have_list else 'os ingredientes'} e tempera com sal.",
        "Deixa cozinhar em lume brando ate ganhar cor.",
        "Serve quente e bom apetite.",
    ]
    return {
        "titulo": titulo,
        "descricao": f"Um prato simples e reconfortante com {', '.join(have_list) or 'o que tens em casa'}.",
        "passos": passos,
        "ingredientes_necessarios": necessarios,
        "motor": "modelo (offline)",
    }


def gerar_receita(have_list):
    """Ferramenta que o agente invoca: ingredientes que o utilizador TEM -> receita."""
    if _tem_llm():
        try:
            return _gerar_llm(have_list)
        except Exception as e:  # rede/chave/modelo — cai no modelo offline
            print(f"[recipe] LLM falhou ({e}); uso a receita-modelo.")
    return _gerar_canned(have_list)
