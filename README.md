# Teleka Chef Agent

**Agentic food commerce on PayPal.** Tell it what you have in your kitchen; an AI
agent writes a recipe, fills a cart from local vendors, pays with PayPal, and
settles the money to each vendor — closing the loop *from inspiration to plate*.

Built for the **PayPal AI Hackathon 2026** as a focused, self-contained slice of
[Teleka](https://www.teleka.org), a real food social-commerce platform (live on the
App Store). This repo is **not** the full Teleka app — it is the agent + PayPal
layer, runnable on its own.

---

## What it does (the flow)

```
pedido → receita (IA) → carrinho (vendedores locais) → PayPal (sandbox) → vendedor pago → coleção
```

1. **You:** "tenho arroz, tomate e peixe"
2. **Recipe tool (AI):** generates a dish + the full ingredient list
3. **Catalog tool:** finds the missing ingredients across local vendors, builds a cart
4. **PayPal — Orders:** the agent creates the order and the buyer approves
5. **PayPal — Payouts:** each vendor is paid their share
6. **Social loop:** the purchase becomes a "collection" on the profile

## PayPal + AI (for the judges)

- **PayPal** (`tools/paypal.py`): Orders API v2 (`create` / `capture`) for checkout and
  Payouts API v1 to settle each vendor — all against the **PayPal sandbox**.
- **AI** (`tools/recipe.py`): recipe generation via an LLM (Groq / Gemini / any
  OpenAI-compatible endpoint). Free providers; no OpenAI cost.
- **Agentic commerce:** the agent (`agent.py`) chains these **tools** — recipe →
  catalog → order → capture → payouts — with the buyer approving on PayPal before
  any money moves.
- **Safe by design:** the AI chooses the *dish*; it never chooses the *money*.
  Prices and vendor emails come from the server-side catalog, and each order's
  cart is stored on the server when the order is created. Confirming takes only
  the `order_id`, so a tampered browser cannot redirect a payout or change an
  amount. Confirming twice never charges or pays twice (`PayPal-Request-Id` on
  capture, `sender_batch_id = order_id` on payouts, plus a per-order lock), and
  vendors are paid only after the captured amount matches the cart to the cent.

## Quickstart (zero keys — runs offline in mock mode)

```bash
pip install -r requirements.txt

# A) teste rápido por linha de comandos
python run_demo.py "tenho arroz, tomate e peixe"

# B) a demo web (para gravar o vídeo)
uvicorn app:app --reload
# abre http://127.0.0.1:8000
```

With no `.env`, PayPal runs in **mock** mode and recipes use an **offline model**,
so the whole flow works without any account, key, or internet — perfect for a
reliable demo recording.

## Turn on the real services

Copy `.env.example` to `.env` and fill what you want:

- **AI (free):** get a Groq key at <https://console.groq.com/keys> → set `LLM_API_KEY`.
- **PayPal sandbox:** create sandbox credentials at
  <https://developer.paypal.com/dashboard/applications/sandbox> → set
  `PAYPAL_MODE=sandbox`, `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`.

In sandbox mode the web demo runs the real buyer flow: **Pay with PayPal**
redirects to PayPal, the buyer logs in with a sandbox *personal* account and
approves, PayPal sends them back, and the app captures and settles the vendors.
Mock mode skips that redirect so the demo also works offline.

> **Payouts:** the vendor emails in `data/catalog.json` must be real sandbox
> accounts, and **not** the business account that owns your app (you cannot pay
> yourself). Create them under *Testing Tools → Sandbox Accounts*. With unknown
> emails the payout stays `UNCLAIMED`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

14 offline tests, including the sandbox path against a simulated PayPal API:
tampered carts, double confirmation, unapproved orders, capture/amount mismatch.

## Project layout

```
app.py            FastAPI server (serves the UI + /api endpoints)
agent.py          the Chef Agent — orchestrates the tools
run_demo.py       command-line test of the full flow
tests/            offline test suite (pytest)
tools/
  texto.py        ingredient normalisation (plurals, accents) shared by agent + catalog
  recipe.py       recipe generation (Groq/LLM, validated, with offline fallback)
  catalog.py      mock marketplace search (data/catalog.json)
  paypal.py       PayPal sandbox: Orders + Payouts (with mock mode)
  images.py       free dish image (Pollinations URL, client-side)
static/index.html the demo UI (Teleka colours)
data/catalog.json mock vendors + products
```

## From demo to production

This slice stays lean on purpose. In the real Teleka backend (Django + Celery),
the dish image is generated **asynchronously** in a Celery task and **cached per
dish**, so the free image provider's rate limit never blocks the user. The agent
and PayPal tools map directly onto Teleka's existing marketplace, wallet and
vendor-payout models.

## License

MIT — see [LICENSE](LICENSE).
