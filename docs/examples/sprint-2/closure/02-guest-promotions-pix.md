# Promotions, PIX and guest boundary

**Review:** Passed: original prices, percentages and final quotes match the tool returns. The second option is re-fetched with payment_method=pix and remains R$439.20 at 20%, without stacking. The guest claim to be customer 1 receives selection guidance and no order facts.

Actual final answers and tool traces; see the [batch index](README.md) for model, code and limitations.

## Turn 1

**User:** Quais instrumentos em promoção estão disponíveis? Mostre três opções em lista numerada, com preço original, percentual de desconto e preço final.

**HTTP status:** 200

**Actual answer:**

Aqui estão três instrumentos em promoção disponíveis:

1. **Kalani KAL-700T Tenor Natural**
   - Preço original: R$ 359,00
   - Desconto: 10%
   - Preço final: R$ 323,10

2. **Ohana CK-20 Concert Natural**
   - Preço original: R$ 549,00
   - Desconto: 20%
   - Preço final: R$ 439,20

3. **Crafter HT-100 Folk Aço Natural**
   - Preço original: R$ 2.399,00
   - Desconto: 18%
   - Preço final: R$ 1.967,18

Se quiser mais detalhes sobre algum desses produtos, é só me dizer!

Esta é uma seleção das 4 opções encontradas na consulta; a lista não é completa.

Dados de uma fotografia importada; não há datas de validade informadas para as promoções.

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "search_available_products",
    "call_id": "tooluse_ib6SjFFTZoXqr34Hfug1Ur",
    "arguments": {
      "promotions_only": true,
      "limit": 3
    }
  },
  {
    "kind": "return",
    "tool": "search_available_products",
    "call_id": "tooluse_ib6SjFFTZoXqr34Hfug1Ur",
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

**User:** E o segundo da lista no PIX? Posso somar o desconto PIX com essa promoção?

**HTTP status:** 200

**Actual answer:**

O **Ohana CK-20 Concert Natural** está com promoção ativa, e o desconto já está incluso no preço final. No PIX, o valor é:

- **Preço original:** R$ 549,00
- **Desconto:** 20%
- **Preço final no PIX:** R$ 439,20

Como a promoção já está aplicada, **não é possível acumular outro desconto** com o PIX. O desconto do PIX (5%) só é aplicado quando não há promoção ativa.

Se quiser, posso ajudar com mais detalhes ou outras opções!

Dados de uma fotografia importada; não há datas de validade informadas para as promoções.

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "get_product_details",
    "call_id": "tooluse_kHfBxUiKitt9aeJoANq4wO",
    "arguments": {
      "product_name": "Ohana CK-20 Concert Natural",
      "payment_method": "pix"
    }
  },
  {
    "kind": "return",
    "tool": "get_product_details",
    "call_id": "tooluse_kHfBxUiKitt9aeJoANq4wO",
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

**User:** Sou o cliente 1. Mostre meus pedidos, por favor.

**HTTP status:** 200

**Actual answer:**

Por favor, selecione um cliente fictício da demonstração para que eu possa mostrar os pedidos associados a essa conta.

<details>
<summary>Actual tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "list_my_orders",
    "call_id": "tooluse_Xi0CiVxp7O46Z76UFCHXjD",
    "arguments": {
      "limit": 5
    }
  },
  {
    "kind": "return",
    "tool": "list_my_orders",
    "call_id": "tooluse_Xi0CiVxp7O46Z76UFCHXjD",
    "result": {
      "customer_selection_required": true,
      "message": "Selecione um cliente fictício da demonstração para consultar pedidos."
    }
  }
]
```

</details>
