"""Recipe generation / Geracao de receitas.

Com LLM_API_KEY (Groq/Gemini/OpenAI-compativel) gera a receita por IA.
Sem chave, usa uma receita-modelo determinista para a demo correr offline.
Devolve sempre: {titulo, descricao, passos: [...], ingredientes_necessarios: [...]}.
"""
import json
import os
import re

import requests

_STAPLES = {"pt": ["cebola", "alho", "azeite", "sal"],
            "en": ["onion", "garlic", "olive oil", "salt"]}
_IDIOMA = {"pt": "portugues europeu", "en": "English"}


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


def _gerar_llm(have_list, lang="en"):
    # HTTP directo ao endpoint compativel-OpenAI (Groq/Gemini), sem o SDK openai:
    # no Anaconda o SDK v3 dava "TypeError: process() takes no keyword arguments".
    base = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
    modelo = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    have = ", ".join(have_list)
    prompt = (
        "Es um chef. O utilizador TEM estes ingredientes: "
        f"{have}. "
        "Sugere UM prato simples e saboroso que os aproveite. "
        f"Escreve titulo, descricao e passos em {_IDIOMA[lang]}. "
        "Responde APENAS em JSON valido com as chaves: "
        '"titulo" (string), "descricao" (1 frase apetitosa), '
        '"passos" (lista de 3 a 5 strings curtas) e '
        '"ingredientes_necessarios" (lista COMPLETA de ingredientes do prato, '
        "em minusculas e no singular, incluindo os que o utilizador ja tem; "
        "para esses, repete EXACTAMENTE as palavras do utilizador; os restantes "
        f"em {_IDIOMA[lang]}, nomes simples de mercearia, sem quantidades)."
    )
    corpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Respondes sempre com JSON valido, sem texto a mais."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
    }
    cab = {"Authorization": f"Bearer {os.getenv('LLM_API_KEY')}",
           "Content-Type": "application/json"}
    r = requests.post(base + "/chat/completions", headers=cab, json=corpo, timeout=20)
    if r.status_code == 400 and "json_validate_failed" in r.text:
        # o modo JSON estrito da Groq recusa de vez em quando uma resposta valida
        # do gpt-oss; uma segunda tentativa sem ele, lida por _extrair_json, resolve
        corpo.pop("response_format")
        r = requests.post(base + "/chat/completions", headers=cab, json=corpo, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
    conteudo = r.json()["choices"][0]["message"]["content"]
    dados = _validar(_extrair_json(conteudo))
    dados["motor"] = f"AI · {modelo}"
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


def _gerar_canned(have_list, lang="en"):
    """Template recipe without AI — the demo runs with no keys at all."""
    staples = _STAPLES[lang]
    necessarios = list(dict.fromkeys([h.lower().strip() for h in have_list] + staples))
    juntos = ", ".join(have_list)
    principal = (have_list[0] if have_list else "").capitalize()
    if lang == "pt":
        return {
            "titulo": f"{principal or 'Legumes'} salteado do chef",
            "descricao": f"Um prato simples e reconfortante com {juntos or 'o que tens em casa'}.",
            "passos": ["Pica a cebola e o alho e leva ao lume com o azeite.",
                       f"Junta {juntos or 'os ingredientes'} e tempera com sal.",
                       "Deixa cozinhar em lume brando ate ganhar cor.",
                       "Serve quente e bom apetite."],
            "ingredientes_necessarios": necessarios,
            "motor": "modelo offline",
        }
    return {
        "titulo": f"Chef's {principal or 'vegetable'} sauté",
        "descricao": f"A simple, comforting dish with {juntos or 'what you have at home'}.",
        "passos": ["Chop the onion and garlic and sweat them in olive oil.",
                   f"Add {juntos or 'the ingredients'} and season with salt.",
                   "Cook over low heat until golden.",
                   "Serve hot. Enjoy!"],
        "ingredientes_necessarios": necessarios,
        "motor": "offline template",
    }


def gerar_receita(have_list, lang="en"):
    """Agent tool: ingredients the user HAS -> recipe (in the chosen language)."""
    lang = lang if lang in _STAPLES else "en"
    if _tem_llm():
        try:
            return _gerar_llm(have_list, lang)
        except Exception as e:  # network/key/model/invalid JSON — fall back to offline
            print(f"[recipe] LLM failed ({type(e).__name__}: {e}); using the template.")
    return _gerar_canned(have_list, lang)
