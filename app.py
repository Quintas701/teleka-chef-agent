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

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

import agent
from tools.recipe import _tem_llm
from tools.paypal import estado as paypal_estado

app = FastAPI(title="Teleka Chef Agent")
BASE = os.path.dirname(os.path.abspath(__file__))


class PedidoIn(BaseModel):
    pedido: str


class ConfirmarIn(BaseModel):
    order_id: str
    carrinho: list


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE, "static", "index.html"))


@app.get("/api/estado")
def estado():
    return {
        "paypal": paypal_estado(),
        "ia": "configurada" if _tem_llm() else "modelo offline",
    }


@app.post("/api/gerar")
def gerar(inp: PedidoIn):
    return agent.processar(inp.pedido)


@app.post("/api/confirmar")
def confirmar(inp: ConfirmarIn):
    return agent.confirmar(inp.order_id, inp.carrinho)
