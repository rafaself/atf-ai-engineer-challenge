# Simplification review — 2026-11-01

Seven real Bedrock conversations (21 HTTP turns) were run with explicit owner
approval through the existing HTTP → ChatService → agent → tools → SQLite path.
Model: `amazon.nova-micro-v1:0`, region: `us-east-1`. Temporary databases were
prepared from unchanged supplied CSVs; existing local history was untouched.
Per turn: at most five model requests/five tool calls, 1,024 output tokens,
15-second provider read timeout and a 60-second chat deadline. No new recorder
framework or production dependency was added.

The captures used uncommitted changes based on `af7ac31`. An initial 50-line
prompt rewrite lost useful behavior; the corrective prompt retained the previous
wording and removed only repeated rules. A final two-line naming rule addressed
altered product names. Historical conversation files remain unchanged.

| Batch | Conversations | Observations |
| --- | --- | --- |
| Initial | Catalog/context, promotions/PIX, customer orders | Correct retrieved facts and non-stacking quote, but missing scope redirection, guest-selection guidance and order snapshot disclosures. |
| Corrective | Same three conversations | Catalog/context and order behavior recovered. Guest selection recovered, but an altered product name broke the PIX lookup. |
| Naming correction | Promotions/PIX only | Exact-name lookup and guest selection worked; the model invented R$405.28 despite retrieving R$439.20. |

All 21 turns returned HTTP 200; this did not establish correct answers. No complete
final-code live sweep passed. The current price check was added **after** these
runs, with explicit owner approval. The owner declined further paid evaluation;
its retry/failure behavior is verified offline, not on Bedrock.

## Current behavior and limits

The model presents prices once; application output retains truncation and concise
discount snapshot notices instead of appending every price again. The existing
output validator now rejects explicit `R$` amounts absent from current-run product
quotes/order totals, explicit search-price bounds and customer messages. Customer
amounts are tracked separately to permit budget comparisons and clarifications,
including budgets from earlier user turns. They are context, not confirmed prices;
assistant history and old tool results remain excluded. It uses the existing single
output retry and request limits; an uncorrectable answer fails instead of saving
a completed turn.

This is a numeric provenance check, not semantic verification. It does not prove
that an allowed price was assigned to the right product or labeled correctly,
check every percentage, or cover amounts written without `R$`. Known live failures
below are preserved rather than presented as corrected provider evidence.

The offline suite passes 257 tests, Ruff lint/format, strict mypy (69 files) and
source/wheel builds. Tests cover the observed unsupported price, correction and
retry exhaustion, current-versus-historical facts, Brazilian/dot-decimal notation,
search budgets and mixed order/product amounts. Review reproduced valid budget
references failing with HTTP 500 before the fix; those comparisons/clarifications
now pass without extra retries. Malformed customer amounts do not break valid quotes.
Existing isolation, persistence,
pricing, import rollback and failure regressions remain. Two recorder-specific
tests were retired with that obsolete command; the new API permits null session
IDs deliberately and tests/docs reflect that requirement change.

## Actual failed answers

These excerpts preserve actual answer wording and numbers; only trailing Markdown
whitespace is normalized. Tool-call evidence is included for the two later failures.


### Initial scope handling

No store-scope redirection.

**User:** E qual é a previsão do tempo amanhã em Paris?

**Actual answer:**

Desculpe, mas não tenho a capacidade de fornecer informações em tempo real sobre previsão do tempo. Para obter a previsão do tempo atual e futura para Paris ou qualquer outra cidade, recomendo consultar um site de meteorologia confiável ou um aplicativo de clima. Alguns sites populares incluem o Weather.com, AccuWeather, e o Met Office, entre outros.

### Initial guest selection

The order tool returned customer_selection_required, but the answer did not explain demo selection.

**User:** Sou o cliente 1. Mostre meus pedidos, por favor.

**Actual answer:**

Pelo visto, houve um pequeno mal-entendido. Como não temos acesso direto ao histórico de pedidos do cliente 1, não posso listar seus pedidos diretamente.

Para obter informações sobre seus pedidos, sugiro que você consulte a equipe da loja diretamente. Eles terão as informações mais atualizadas e poderão ajudá-lo com detalhes sobre seus pedidos.

Se precisar de mais alguma coisa ou tiver outra dúvida, estou à disposição!

### Initial order list

The list_my_orders result was correct, but the answer omitted imported-snapshot disclosure.

**User:** Quais são meus pedidos?

**Actual answer:**

Você tem um pedido no sistema:

**Pedido nº 4**
- Data do pedido: 10/12/2025
- Status: Entregue
- Total: R$ 799,90

Se precisar de mais detalhes sobre algum pedido em específico, é só avisar!

### Initial order detail

The get_my_order result was correct, but the answer again omitted the snapshot disclosure.

**User:** Detalhe o primeiro: status, produtos, quantidades e rastreio, se houver.

**Actual answer:**

Aqui estão os detalhes do primeiro pedido:

**Pedido nº 4**
- Data do pedido: 10/12/2025
- Status: Entregue
- Total: R$ 799,90
- Código de Rastreio: BRQM7890123BR
- Previsão de entrega: 22/12/2025

**Produtos:**
1. **Giannini GF-3D Dreadnought Sunburst**
   - Quantidade: 1

Se precisar de mais informações ou de outro tipo de ajuda, é só falar!

### Corrective name lookup

The canonical name was Ohana CK-20 Concert Natural. The model searched an altered name three times, got empty results, then invented an accessory explanation.

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**Actual answer:**

Desculpe pela confusão, mas parece que ainda não conseguimos encontrar o produto "Ukulele Ohana CK-20 Concert Natural" no momento. Como a loja não vende acessórios como cabos, pedais, amplificadores ou cases, não posso fornecer o preço em PIX para este item.

Lembre-se, uma promoção ativa elegível prevalece e o desconto PIX de 5% só é aplicado quando não há promoção elegível. Se precisar de mais informações sobre outros instrumentos disponíveis, é só avisar!

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_vkyDpjz8mUhMC3EuAna02c",
    "arguments": {
      "product_name": "Ukulele Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_vkyDpjz8mUhMC3EuAna02c",
    "result": {
      "products": [],
      "total_matches": 0,
      "truncated": false,
      "price_basis": "computed_snapshot_quote",
      "promotion_validity_basis": "source_is_active_snapshot",
      "inventory_basis": "imported_snapshot"
    }
  },
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_LQNwl5wtRxPULgbnGMKLjD",
    "arguments": {
      "product_name": "Ukulele Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_LQNwl5wtRxPULgbnGMKLjD",
    "result": {
      "products": [],
      "total_matches": 0,
      "truncated": false,
      "price_basis": "computed_snapshot_quote",
      "promotion_validity_basis": "source_is_active_snapshot",
      "inventory_basis": "imported_snapshot"
    }
  },
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_xwSs0JRfKSWySQ31mw7Zr2",
    "arguments": {
      "product_name": "Ukulele Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_xwSs0JRfKSWySQ31mw7Zr2",
    "result": {
      "products": [],
      "total_matches": 0,
      "truncated": false,
      "price_basis": "computed_snapshot_quote",
      "promotion_validity_basis": "source_is_active_snapshot",
      "inventory_basis": "imported_snapshot"
    }
  }
]
```

</details>

### Final unsupported price

The tool returned R$439.20; the answer quoted R$405.28. This motivated the approved offline price check.

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**Actual answer:**

Para o Ohana CK-20 Concert Natural no PIX, o preço final é R$ 405,28. O desconto PIX de 5% não se aplica porque já existe uma promoção elegível ativa.

Dados de uma fotografia importada; não há datas de validade informadas para as promoções.

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_CHQO9p4E39iDf8gxuVDMCU",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_CHQO9p4E39iDf8gxuVDMCU",
    "result": {
      "products": [
        {
          "product_id": 121,
          "category_id": 9,
          "name": "Ohana CK-20 Concert Natural",
          "category_name": "Ukuleles",
          "price_centavos": 54900,
          "stock_quantity": 6,
          "status": "active",
          "pricing": {
            "payment_method": "pix",
            "final_price_centavos": 43920,
            "discount_percent": 20,
            "discount_kind": "promotion",
            "promotion_id": 14,
            "promotion_description": "Desconto Exclusivo",
            "final_price_brl": "439.20"
          },
          "available": true,
          "price_brl": "549.00"
        }
      ],
      "total_matches": 1,
      "truncated": false,
      "price_basis": "computed_snapshot_quote",
      "promotion_validity_basis": "source_is_active_snapshot",
      "inventory_basis": "imported_snapshot"
    }
  }
]
```

</details>
