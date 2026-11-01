# Preserved closing-evaluation failures

These are actual failed HTTP turns, not passing examples. Model/batch context and code references are in the [index](README.md). Internal reasoning drafts and credentials are excluded.

## Micro baseline: 02-guest-promotions-pix

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP:** 500 · **Actual response:** `{"detail": "Conversation failed"}`

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_gcZDCeQFhpfc0RqGnonpxH",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_gcZDCeQFhpfc0RqGnonpxH",
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

## Micro baseline: 02-promotions-replay

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP:** 500 · **Actual response:** `{"detail": "Conversation failed"}`

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_ey0r77wpneQRgQBB1SgZ0y",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_ey0r77wpneQRgQBB1SgZ0y",
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

## Micro combined correction: 02-guest-promotions-pix

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP:** 500 · **Actual response:** `{"detail": "Conversation failed"}`

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_Mf3DuxoOx0wjkorTvNN5mP",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_Mf3DuxoOx0wjkorTvNN5mP",
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

## Lite comparison: 02-guest-promotions-pix

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP:** 500 · **Actual response:** `{"detail": "Conversation failed"}`

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_IyBksPUVEtA463LX1EQUyD",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_IyBksPUVEtA463LX1EQUyD",
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

## Lite comparison: 02-promotion-diagnostic

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP:** 500 · **Actual response:** `{"detail": "Conversation failed"}`

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_8pjwOnhkMnouPd7pGNep1Y",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_8pjwOnhkMnouPd7pGNep1Y",
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

## Qwen before missing-facts feedback: 01-guest-catalog-context

**User:** E o segundo da sua lista, qual é o preço e o estoque agora?

**HTTP:** 500 · **Actual response:** `{"detail": "Conversation failed"}`

<details>
<summary>Actual tool calls and results</summary>

```json
[]
```

</details>

## Lite category failure despite HTTP 200

The request asked for violões. The search omitted category; the answer mislabeled returned ukuleles as violões.

**User:** Então mostre três violões disponíveis até R$ 1.000, em lista numerada, com preço e estoque.

**Actual answer:**

Aqui estão três violões disponíveis até R$ 1.000,00:

1. **Shelby SU-21S Soprano Sunburst**
   - Preço: R$ 159,90
   - Estoque: 8

2. **Kalani KAL-300S Soprano Natural**
   - Preço: R$ 179,90
   - Estoque: 12

3. **Kala KA-15S Soprano Mogno**
   - Preço: R$ 199,90
   - Estoque: 15

Todos os modelos estão dentro do seu orçamento e têm estoque disponível. 🎸

Esta é uma seleção das 23 opções encontradas na consulta; a lista não é completa.

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "search_available_products",
    "call_id": "tooluse_c7TVxvrV7fQDAHLcJJZdi8",
    "arguments": {
      "min_price_brl": 0,
      "max_price_brl": 1000,
      "limit": 3
    }
  },
  {
    "kind": "return",
    "tool": "search_available_products",
    "call_id": "tooluse_c7TVxvrV7fQDAHLcJJZdi8",
    "result": {
      "products": [
        {
          "product_id": 119,
          "category_id": 9,
          "name": "Shelby SU-21S Soprano Sunburst",
          "category_name": "Ukuleles",
          "price_centavos": 15990,
          "stock_quantity": 8,
          "status": "active",
          "pricing": {
            "payment_method": "standard",
            "final_price_centavos": 15990,
            "discount_percent": 0,
            "discount_kind": "none",
            "promotion_id": null,
            "promotion_description": null,
            "final_price_brl": "159.90"
          },
          "available": true,
          "price_brl": "159.90"
        },
        {
          "product_id": 118,
          "category_id": 9,
          "name": "Kalani KAL-300S Soprano Natural",
          "category_name": "Ukuleles",
          "price_centavos": 17990,
          "stock_quantity": 12,
          "status": "active",
          "pricing": {
            "payment_method": "standard",
            "final_price_centavos": 17990,
            "discount_percent": 0,
            "discount_kind": "none",
            "promotion_id": null,
            "promotion_description": null,
            "final_price_brl": "179.90"
          },
          "available": true,
          "price_brl": "179.90"
        },
        {
          "product_id": 116,
          "category_id": 9,
          "name": "Kala KA-15S Soprano Mogno",
          "category_name": "Ukuleles",
          "price_centavos": 19990,
          "stock_quantity": 15,
          "status": "active",
          "pricing": {
            "payment_method": "standard",
            "final_price_centavos": 19990,
            "discount_percent": 0,
            "discount_kind": "none",
            "promotion_id": null,
            "promotion_description": null,
            "final_price_brl": "199.90"
          },
          "available": true,
          "price_brl": "199.90"
        }
      ],
      "total_matches": 23,
      "truncated": true,
      "price_basis": "computed_snapshot_quote",
      "promotion_validity_basis": "source_is_active_snapshot",
      "inventory_basis": "imported_snapshot"
    }
  }
]
```

</details>
