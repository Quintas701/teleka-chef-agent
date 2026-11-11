"""Recipe generation / Geracao de receitas.

Com LLM_API_KEY (Groq/Gemini/OpenAI-compativel) gera a receita por IA.
Sem chave, usa uma receita-modelo determinista para a demo correr offline.
Devolve sempre: {titulo, descricao, passos: [...], ingredientes_necessarios: [...]}.
"""
import json
import os
import re

import requests

from tools.livro import PRATOS
from tools.texto import mesma_coisa

_STAPLES = {"pt": ["cebola", "alho", "azeite", "sal"],
            "en": ["onion", "garlic", "olive oil", "salt"]}
_IDIOMA = {"pt": "portugues europeu", "en": "English"}
_MOTOR_OFFLINE = {"pt": "livro de receitas offline", "en": "offline recipe book"}


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
    prato = _prato_do_livro(have_list)
    if prato is not None:
        # a combinacao tem um prato classico obvio: e esse que se cozinha
        escolha = (f"O prato e OBRIGATORIAMENTE: '{prato[lang]['titulo']}'. "
                   "Escreve a receita desse prato.\n")
    else:
        escolha = ""
    prompt = (
        "Es um chef de cozinha caseira. O utilizador TEM em casa: "
        f"{have}.\n"
        "Propoe UM prato REAL e CONHECIDO — uma receita classica que uma pessoa "
        "reconheceria pelo nome e cozinharia de facto em casa — que use esses "
        "ingredientes como protagonistas. Escolhe a combinacao mais obvia e "
        "tradicional; nada de pratos inventados, fusoes estranhas nem nomes "
        "genericos como 'salteado do chef'.\n"
        "Exemplos: frango + batata -> 'Frango frito com batata frita'; "
        "arroz + peixe -> 'Arroz de peixe'; ovo + batata -> 'Tortilha de batata'; "
        "fuba + peixe -> 'Funge com calulu de peixe'; massa + tomate -> "
        "'Esparguete com molho de tomate'.\n"
        + escolha +
        "Se algum ingrediente do utilizador nao combinar com o prato, deixa-o de fora "
        "em vez de forcar.\n"
        f"Escreve titulo, descricao e passos em {_IDIOMA[lang]}"
        + (" (portugues de Portugal, tratando o utilizador por tu: 'tempera', "
           "'junta', 'frita' — nunca 'tempere', 'adicione')" if lang == "pt" else "")
        + ". Os passos sao "
        "instrucoes reais e concretas, com quantidades, tempos e temperaturas "
        "quando importa (ex.: 'Frita em oleo a 170 C durante 12 min').\n"
        "Responde APENAS em JSON valido com as chaves: "
        '"titulo" (nome do prato), "descricao" (1 frase apetitosa), '
        '"passos" (lista de 4 a 6 strings) e '
        '"ingredientes_necessarios" (lista COMPLETA de ingredientes do prato, '
        "em minusculas e no singular, incluindo os que o utilizador ja tem; "
        "para esses, repete EXACTAMENTE as palavras do utilizador; os restantes "
        f"em {_IDIOMA[lang]}, nomes simples de mercearia, sem quantidades; "
        "nao incluas agua)."
    )
    corpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Respondes sempre com JSON valido, sem texto a mais."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }
    if "gpt-oss" in modelo:
        # o raciocinio do gpt-oss gasta tokens antes da resposta: sem isto o JSON
        # chegava cortado ao fim de ~900 tokens e caia no livro offline
        corpo["reasoning_effort"] = "low"
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


def _tem(ingrediente, have_list):
    from tools.catalog import mesmo_produto
    return next((h for h in have_list
                 if mesma_coisa(ingrediente, h) or mesmo_produto(ingrediente, h)), None)


def _prato_do_livro(have_list):
    """O prato classico que aproveita mais ingredientes principais do utilizador."""
    melhor = None
    for prato in PRATOS:
        if all(_tem(p, have_list) for p in prato["principais"]):
            if melhor is None or len(prato["principais"]) > len(melhor["principais"]):
                melhor = prato
    return melhor


def _gerar_canned(have_list, lang="en"):
    """Sem IA: escolhe um prato REAL do livro (tools/livro.py) — o que aproveita
    mais ingredientes principais do utilizador. Frango + batata -> frango frito
    com batata frita. Nunca inventa um prato."""
    melhor = _prato_do_livro(have_list)
    if melhor is not None:
        v = melhor[lang]
        # o que o utilizador ja tem aparece com as palavras dele
        ingredientes = [_tem(i, have_list) or i for i in v["ingredientes"]]
        return {
            "titulo": v["titulo"],
            "descricao": v["descricao"],
            "passos": list(v["passos"]),
            "ingredientes_necessarios": list(dict.fromkeys(i.lower() for i in ingredientes)),
            "motor": _MOTOR_OFFLINE[lang],
        }

    # nenhum prato do livro serve: um refogado simples, honesto no nome
    staples = _STAPLES[lang]
    necessarios = list(dict.fromkeys([h.lower().strip() for h in have_list] + staples))
    e = " e " if lang == "pt" else " and "
    juntos = (", ".join(have_list[:-1]) + e + have_list[-1]) if len(have_list) > 1 else have_list[0]
    if lang == "pt":
        return {
            "titulo": f"Refogado de {juntos}",
            "descricao": f"Um refogado caseiro e simples com {juntos}.",
            "passos": ["Pica a cebola e o alho e refoga em azeite durante 5 min.",
                       f"Junta {juntos} cortado em pedaços pequenos e tempera com sal.",
                       "Tapa e cozinha em lume brando 15–20 min, mexendo de vez em quando.",
                       "Prova, retifica o sal e serve quente."],
            "ingredientes_necessarios": necessarios,
            "motor": _MOTOR_OFFLINE[lang],
        }
    return {
        "titulo": f"Simple {juntos} stir-fry",
        "descricao": f"A simple home-style stir-fry with {juntos}.",
        "passos": ["Chop the onion and garlic and sauté in olive oil for 5 min.",
                   f"Add {juntos}, cut into small pieces, and season with salt.",
                   "Cover and cook on low heat 15–20 min, stirring now and then.",
                   "Taste, adjust the salt and serve hot."],
        "ingredientes_necessarios": necessarios,
        "motor": _MOTOR_OFFLINE[lang],
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
