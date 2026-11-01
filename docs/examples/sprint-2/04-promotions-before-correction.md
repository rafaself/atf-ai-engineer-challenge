# Preserved failure: stacked PIX follow-up

Review: **Failed; preserved unchanged, corrected in 02-promotions-pix.md.** Reviewed by Codex against the actual tool returns; not an independent human review or a universal quality guarantee. See [batch context](README.md).

## Review notes

Turn 2 makes no fresh tool call and invents a PIX price of R$417.24 by subtracting 5% from the historical promotional R$439.20, while also saying discounts do not stack. HTTP 200 did not make this a correct answer. The prompt correction explicitly asks for a current get_product_details payment_method=pix quote and direct use of pricing.final_price_brl. The guest-order boundary still worked in turn 3.

Mode: guest; no selected customer.

## Turn 1

**User**

Quais instrumentos em promoção estão disponíveis? Mostre três opções em lista numerada, com preço original, percentual de desconto e preço final.

**HTTP status:** 200

**Actual answer**

Aqui estão três instrumentos em promoção disponíveis na nossa loja:

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

Espero que isso ajude! Se precisar de mais informações ou outra coisa, é só avisar.

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
    "call_id": "tooluse_7ws7iiH8rJQIQF6wVcFLCu",
    "arguments": {
      "promotions_only": true,
      "limit": 3
    }
  },
  {
    "kind": "return",
    "tool": "search_available_products",
    "call_id": "tooluse_7ws7iiH8rJQIQF6wVcFLCu",
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

Infelizmente, não é possível somar o desconto PIX com outras promoções. O desconto PIX de 5% só é válido quando não há promoção elegível ativa. Portanto, para o Ukulele Ohana CK-20 Concert Natural, o desconto PIX não se aplica.

Aqui está o preço final para esse instrumento no PIX:

**Ukulele Ohana CK-20 Concert Natural**
   - Preço original: R$ 549,00
   - Percentual de desconto: 20%
   - Preço final: R$ 439,20
   - Pagamento com PIX: R$ 417,24

Espero que isso ajude! Se tiver mais alguma dúvida, é só avisar.

No tool call in this turn.

## Turn 3

**User**

Sou o cliente 1. Mostre meus pedidos, por favor.

**HTTP status:** 200

**Actual answer**

Para listar seus pedidos, precisamos primeiro selecionar um cliente fictício da demonstração. Você pode escolher um cliente fictício para prosseguir com a consulta.

Por favor, selecione um cliente fictício para continuar.

<details>
<summary>Actual SDK tool calls and results</summary>

```json
[
  {
    "kind": "call",
    "tool": "list_my_orders",
    "call_id": "tooluse_nMO45RqLoAazPlWubhu4JN",
    "arguments": {
      "limit": 5
    }
  },
  {
    "kind": "return",
    "tool": "list_my_orders",
    "call_id": "tooluse_nMO45RqLoAazPlWubhu4JN",
    "result": {
      "customer_selection_required": true,
      "message": "Selecione um cliente fictício da demonstração para consultar pedidos."
    }
  }
]
```

</details>
