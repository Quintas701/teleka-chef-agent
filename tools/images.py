"""Imagem do prato — gratuita, gerada do lado do cliente.

Construimos um URL do Pollinations (geracao gratuita, sem chave) e a UI
carrega-o directamente num <img>. Se falhar, a UI mostra um emoji de prato.
Assim o backend nao precisa de rede nem de guardar ficheiros para a demo.
"""
import urllib.parse

POLLINATIONS = "https://image.pollinations.ai/prompt/"


def url_imagem(descricao, ingredientes_txt=""):
    prompt = (
        f"{descricao}, made with {ingredientes_txt}. "
        "Professional food photography, appetizing, natural light, top-down, rustic table."
    )
    return POLLINATIONS + urllib.parse.quote(prompt) + "?width=512&height=512&nologo=true"
