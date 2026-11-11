"""Servidor da demo Teleka Chef Agent (FastAPI).

    uvicorn app:app --reload
    # abre http://127.0.0.1:8000
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import agent
from tools.recipe import _tem_llm
from tools.paypal import ErroPayPal, aviso_configuracao, estado as paypal_estado

app = FastAPI(title="Teleka Chef Agent")
BASE = os.path.dirname(os.path.abspath(__file__))

if aviso_configuracao():
    print(f"[aviso] {aviso_configuracao()}")


class PedidoIn(BaseModel):
    pedido: str = Field(min_length=1, max_length=500)
    lang: str = Field(default="en", pattern="^(en|pt)$")


class ConfirmarIn(BaseModel):
    # So o id. O carrinho (precos, vendedores, emails) vive no servidor.
    order_id: str = Field(min_length=1, max_length=64)


@app.exception_handler(agent.ErroAgente)
def _erro_agente(_req, e: agent.ErroAgente):
    return JSONResponse(status_code=e.status, content={"erro": str(e)})


@app.exception_handler(ErroPayPal)
def _erro_paypal(_req, e: ErroPayPal):
    return JSONResponse(status_code=e.status,
                        content={"erro": str(e), "codigo": e.codigo, "debug_id": e.debug_id})


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


@app.get("/logo.svg")
def logo():
    return FileResponse(os.path.join(BASE, "static", "logo.svg"), media_type="image/svg+xml")


@app.get("/api/estado")
def estado():
    return {
        "paypal": paypal_estado(),
        "paypal_aviso": aviso_configuracao(),
        "ia": "configurada" if _tem_llm() else "modelo offline",
        "ia_modelo": os.getenv("LLM_MODEL", "openai/gpt-oss-120b") if _tem_llm() else None,
    }


@app.post("/api/gerar")
def gerar(inp: PedidoIn, request: Request):
    # A PayPal devolve o comprador a esta pagina com ?token=<order_id> depois de aprovar.
    base = str(request.base_url).rstrip("/")
    return agent.processar(inp.pedido, return_url=f"{base}/?paypal=aprovado",
                           cancel_url=f"{base}/?paypal=cancelado", lang=inp.lang)


@app.post("/api/confirmar")
def confirmar(inp: ConfirmarIn):
    return agent.confirmar(inp.order_id)
