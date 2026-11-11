"""Normalizacao de nomes de ingredientes.

Uma so regra, usada em dois sitios que TEM de concordar:
- o agente, ao decidir o que o utilizador ja tem ("tomates" == "tomate");
- o catalogo, ao procurar o produto ("limão" encontra "limao").
Se cada um normalizasse a sua maneira, o utilizador pagava o que ja tem.
"""
import re
import unicodedata


def chave(texto):
    """minusculas, sem acentos, espacos colapsados: 'Limões ' -> 'limoes'."""
    s = unicodedata.normalize("NFKD", str(texto))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def formas(palavra):
    """Formas singulares candidatas de UMA palavra ja normalizada.
    Cobre os plurais regulares do PT (e o -s do EN), sem pretender ser um lematizador."""
    p = palavra
    out = {p}
    if len(p) > 3 and p.endswith("oes"):      # limoes -> limao
        out.add(p[:-3] + "ao")
    if len(p) > 3 and p.endswith("aes"):      # paes -> pao
        out.add(p[:-3] + "ao")
    if len(p) > 3 and p.endswith("es"):       # pimentoes? / tomatoes -> tomato
        out.add(p[:-2])
    if len(p) > 2 and p.endswith("s"):        # tomates -> tomate, ovos -> ovo
        out.add(p[:-1])
    return out


def mesma_coisa(a, b):
    """'Tomates' e 'tomate' sao o mesmo ingrediente; 'sal' e 'salsa' nao."""
    pa, pb = chave(a).split(), chave(b).split()
    if len(pa) != len(pb):
        return False
    return all(formas(x) & formas(y) for x, y in zip(pa, pb))
