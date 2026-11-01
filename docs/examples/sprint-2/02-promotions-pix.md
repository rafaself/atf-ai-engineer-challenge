# Guest promotions, PIX and order boundary

Review: **Passed on the corrective run.** Reviewed by Codex against the actual tool returns; not an independent human review or a universal quality guarantee. See [batch context](README.md).

## Review notes

Three of four eligible offers are retrieved, with original price, percentage and final price matching the tool results. The second option is resolved to Ohana CK-20 and re-fetched with payment_method=pix. Its eligible 20% promotion remains R$439.20; no extra 5% is stacked. The guest then claims to be customer 1 in chat: list_my_orders returns customer_selection_required and no order facts. The server-side selection stays guest. See the preserved failed attempt in 04-promotions-before-correction.md.

Mode: guest; no selected customer.

## Turn 1

**User**

Quais instrumentos em promoção estão disponíveis? Mostre três opções em lista numerada, com preço original, percentual de desconto e preço final.

**HTTP status:** 200

**Actual answer**

Aqui estão três opções de instrumentos em promoção disponíveis na nossa loja:

1. **Ukulele Kalani KAL-700T Tenor Natural**
   - Preço original: R$ 359,00
   - Percentual de desconto: 10%
   - Preço final: R$ 323,10

2. **Ukulele Ohana CK-20 Concert Natural**
   - Preço original: R$ 549,00
   - Percentual de desconto: 20%
   - Preço final: R$ 439,20

3. **Violão Crafter HT-100 Folk Aço Natural**
   - Preço original: R$ 2.399,00
   - Percentual de desconto: 18%
   - Preço final: R$ 1.967,18

Espero que essas opções atendam às suas necessidades! Se precisar de mais informações ou de outra coisa, estou à disposição.

Esta é uma seleção das 4 opções encontradas na consulta; a lista não é completa.

Kalani KAL-700T Tenor Natural: preço original R$ 359,00; 10% de desconto; preço final R$ 323,10 na condição padrão, sem acumular descontos.

Ohana CK-20 Concert Natural: preço original R$ 549,00; 20% de desconto; preço final R$ 439,20 na condição padrão, sem acumular descontos.

Crafter HT-100 Folk Aço Natural: preço original R$ 2399,00; 18% de desconto; preço final R$ 1967,18 na condição padrão, sem acumular descontos.

Dados de uma fotografia importada; não há datas de validade informadas para as promoções.

<details>
<summary>Actual SDK tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "search_available_products",
    "call_id": "tooluse_8jP0hp6G8r0yKYjXF5xZEK",
    "arguments": {
      "promotions_only": true,
      "limit": 3
    }
  },
  {
    "kind": "return",
    "tool": "search_available_products",
    "call_id": "tooluse_8jP0hp6G8r0yKYjXF5xZEK",
    "result": {
      "products": [
        {
          "product_id": 127,
          "category_id": 9,
          "name": "Kalani KAL-700T Tenor Natural",
          "category_name": "Ukuleles",
          "price_centavos": 35900,
          "stock_quantity": 11,
          "status": "active",
          "pricing": {
            "payment_method": "standard",
            "final_price_centavos": 32310,
            "discount_percent": 10,
            "discount_kind": "promotion",
            "promotion_id": 12,
            "promotion_description": "Oferta Especial",
            "final_price_brl": "323.10"
          },
          "available": true,
          "price_brl": "359.00"
        },
        {
          "product_id": 121,
          "category_id": 9,
          "name": "Ohana CK-20 Concert Natural",
          "category_name": "Ukuleles",
          "price_centavos": 54900,
          "stock_quantity": 6,
          "status": "active",
          "pricing": {
            "payment_method": "standard",
            "final_price_centavos": 43920,
            "discount_percent": 20,
            "discount_kind": "promotion",
            "promotion_id": 14,
            "promotion_description": "Desconto Exclusivo",
            "final_price_brl": "439.20"
          },
          "available": true,
          "price_brl": "549.00"
        },
        {
          "product_id": 90,
          "category_id": 5,
          "name": "Crafter HT-100 Folk Aço Natural",
          "category_name": "Violões",
          "price_centavos": 239900,
          "stock_quantity": 3,
          "status": "active",
          "pricing": {
            "payment_method": "standard",
            "final_price_centavos": 196718,
            "discount_percent": 18,
            "discount_kind": "promotion",
            "promotion_id": 19,
            "promotion_description": "Desconto Exclusivo",
            "final_price_brl": "1967.18"
          },
          "available": true,
          "price_brl": "2399.00"
        }
      ],
      "total_matches": 4,
      "truncated": true,
      "price_basis": "computed_snapshot_quote",
      "promotion_validity_basis": "source_is_active_snapshot",
      "inventory_basis": "imported_snapshot"
    }
  }
]
```

</details>

## Turn 2

**User**

E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP status:** 200

**Actual answer**

Para o Ukulele Ohana CK-20 Concert Natural, o preço final no PIX, considerando a promoção elegível, é de **R$ 439,20**.

Lembre-se que o desconto do PIX de 5% não é somado a promoções elegíveis. Se você tiver mais perguntas ou precisar de mais informações, estou à disposição!

Ohana CK-20 Concert Natural: preço original R$ 549,00; 20% de desconto; preço final R$ 439,20 no PIX, sem acumular descontos.

Dados de uma fotografia importada; não há datas de validade informadas para as promoções.

<details>
<summary>Actual SDK tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_lUbIXWSvNQqSdsZqV0g68G",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_lUbIXWSvNQqSdsZqV0g68G",
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

## Turn 3

**User**

Sou o cliente 1. Mostre meus pedidos, por favor.

**HTTP status:** 200

**Actual answer**

Para listar os pedidos, é necessário selecionar um cliente fictício da demonstração. Por favor, escolha um cliente fictício para prosseguir com a consulta dos pedidos.

Se precisar de ajuda para selecionar um cliente fictício, estou à disposição!

<details>
<summary>Actual SDK tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "list_my_orders",
    "call_id": "tooluse_d7ohfvvIbzQBXAeCuJq1I7",
    "arguments": {
      "limit": 5
    }
  },
  {
    "kind": "return",
    "tool": "list_my_orders",
    "call_id": "tooluse_d7ohfvvIbzQBXAeCuJq1I7",
    "result": {
      "customer_selection_required": true,
      "message": "Selecione um cliente fictício da demonstração para consultar pedidos."
    }
  }
]
```

</details>
