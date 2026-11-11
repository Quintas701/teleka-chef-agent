"""Geracao de receitas.

Com LLM_API_KEY (Groq/Gemini/OpenAI-compativel) gera a receita por IA.
Sem chave, usa uma receita-modelo determinista para a demo correr offline.
Devolve sempre: {titulo, descricao, passos: [...], ingredientes_necessarios: [...]}.
"""
import json
import os
import re

import requests

_STAPLES = ["cebola", "alho", "azeite", "sal"]


def _tem_llm():
    return bool(os.getenv("LLM_API_KEY"))


def _extrair_json(texto):
    """Le JSON mesmo que o modelo o embrulhe em texto ou cercas ```."""
    try:
        return json.loads(texto)
    except Exception:
        pass
    m = re.search(r"\{.*\}", texto, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError("resposta da IA nao e JSON")


def _gerar_llm(have_list):
    # HTTP directo ao endpoint compativel-OpenAI (Groq/Gemini). Usamos requests
    # em vez do SDK openai para evitar conflitos de dependencias (ex.: Anaconda,
    # onde o SDK v3 dava "TypeError: process() takes no keyword arguments").
    base = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    modelo = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
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
    r = requests.post(
        base + "/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": modelo,
            "messages": [
                {"role": "system", "content": "Respondes sempre com JSON valido, sem texto a mais."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.6,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
        },
        timeout=20,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    conteudo = r.json()["choices"][0]["message"]["content"]
    dados = _validar(_extrair_json(conteudo))
    dados["motor"] = f"IA ({modelo})"
    return dados


def _lista_de_texto(valor):
    if not isinstance(valor, list):
        return []
    return [str(x).strip() for x in valor if isinstance(x, (str, int, float)) and str(x).strip()]


def _validar(dados):
    """O LLM e uma fonte nao confiavel: confirma a forma antes de a usar.
    Uma lista que chegue como string seria iterada letra a letra e o carrinho
    encheria de 'a', 'r', 'r'... — melhor recusar e cair no modelo offline."""
    if not isinstance(dados, dict):
        raise ValueError("resposta nao e um objecto JSON")
    ingredientes = [i.lower() for i in _lista_de_texto(dados.get("ingredientes_necessarios"))]
    passos = _lista_de_texto(dados.get("passos"))
    if not ingredientes or not passos:
        raise ValueError("faltam ingredientes_necessarios ou passos")
    titulo = dados.get("titulo")
    descricao = dados.get("descricao")
    return {
        "titulo": str(titulo).strip()[:120] if titulo else "Prato do dia",
        "descricao": str(descricao).strip()[:300] if descricao else "",
        "passos": passos[:8],
        "ingredientes_necessarios": list(dict.fromkeys(ingredientes))[:20],
    }


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
        except Exception as e:  # rede/chave/modelo/JSON invalido — cai no modelo offline
            print(f"[recipe] LLM falhou ({type(e).__name__}: {e}); uso a receita-modelo.")
    return _gerar_canned(have_list)
