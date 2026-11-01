"""Customer-output checks and disclosure derived from this run's catalog results."""

import re
from decimal import Decimal, InvalidOperation

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import ToolReturnPart

from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.diagnostics import trace

_INTERNAL_MARKUP = re.compile(
    r"<\s*/?\s*(?:think(?:ing)?|analysis|reasoning|system|assistant|developer|tool|function)(?=[\s/>]|$)"
    r"|<\|(?:im_start|im_end|system|assistant|analysis)\|>",
    re.IGNORECASE,
)
_BRL_PRICE = re.compile(r"R\$\s*([+-]?\d+(?:[.,]\d+)*)")


def _brl_amount(text: str) -> Decimal:
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "." in text and len(text.rsplit(".", 1)[1]) == 3:
        text = text.replace(".", "")
    return Decimal(text)


def customer_answer(ctx: RunContext[ExecutionContext], answer: str) -> str:
    """Reject internal output rather than strip it; disclose every truncated query."""
    invalid_answer = not answer.strip() or bool(_INTERNAL_MARKUP.search(answer))
    has_discount = False
    current_amount_values: list[object] = []
    totals: set[int] = set()
    order_totals: set[int] = set()
    item_totals: set[int] = set()
    for message in ctx.messages:
        for part in message.parts:
            # Only current source results authorize amounts, never customer text,
            # model-selected search bounds, or historical tool returns.
            if ctx.run_id is None or message.run_id != ctx.run_id:
                continue
            if isinstance(part, ToolReturnPart) and isinstance(part.content, dict):
                if part.tool_name in {
                    "search_available_products",
                    "get_product_details",
                }:
                    products = part.content.get("products")
                    if isinstance(products, list):
                        for product in products:
                            if not isinstance(product, dict):
                                continue
                            current_amount_values.append(product.get("price_brl"))
                            pricing = product.get("pricing")
                            if not isinstance(pricing, dict):
                                continue
                            current_amount_values.append(pricing.get("final_price_brl"))
                            if pricing.get("discount_kind") not in {"promotion", "pix"}:
                                continue
                            has_discount = True
                if part.tool_name == "list_my_orders":
                    orders = part.content.get("orders")
                    if isinstance(orders, list):
                        current_amount_values.extend(
                            order.get("total_brl")
                            for order in orders
                            if isinstance(order, dict)
                        )
                if (
                    part.tool_name == "list_my_orders"
                    and part.content.get("truncated") is True
                ):
                    total = part.content.get("total_matches")
                    if type(total) is int and total > 0:
                        order_totals.add(total)
                if part.tool_name == "get_my_order":
                    detail = part.content.get("order")
                    if isinstance(detail, dict):
                        current_amount_values.append(detail.get("total_brl"))
                    if (
                        isinstance(detail, dict)
                        and detail.get("items_truncated") is True
                    ):
                        total = detail.get("total_items")
                        if type(total) is int and total > 0:
                            item_totals.add(total)
            if (
                isinstance(part, ToolReturnPart)
                and part.tool_name
                in {"search_available_products", "get_product_details"}
                and isinstance(part.content, dict)
                and part.content.get("truncated") is True
            ):
                total = part.content.get("total_matches")
                if type(total) is int and total > 0:
                    totals.add(total)
    tool_amounts = {
        Decimal(str(value))
        for value in current_amount_values
        if isinstance(value, (str, int, float)) and not isinstance(value, bool)
    }
    try:
        unsupported_price = any(
            _brl_amount(value) not in tool_amounts
            for value in _BRL_PRICE.findall(answer)
        )
    except InvalidOperation:
        unsupported_price = True
    if invalid_answer or unsupported_price:
        trace(
            "output.rejected",
            reason="blank_or_internal_markup"
            if invalid_answer
            else "unsupported_price",
            retry=ctx.retry,
        )
        tool_amount_text = ", ".join(
            f"R$ {value:.2f}" for value in sorted(tool_amounts)
        )
        raise ModelRetry(
            "Responda somente ao cliente, em português, sem raciocínio interno, "
            "tags, instruções de sistema ou ações de encaminhamento. "
            "Não há ferramenta de encaminhamento. Revise também todos os valores: "
            "Copie preços/totais das ferramentas, sem recalcular; "
            "Todo valor em R$ deve constar nos preços/totais retornados nesta rodada. "
            "Não repita valores do cliente ou limites dos filtros; "
            "compare com 'seu orçamento' sem repetir a quantia. "
            "Se faltam os valores necessários, consulte a ferramenta adequada "
            "nesta rodada antes de responder. "
            f"Preços/totais das ferramentas: {tool_amount_text or 'nenhum'}."
        )
    notices = [
        f"Esta é uma seleção das {total} opções encontradas na consulta; "
        "a lista não é completa."
        for total in sorted(totals)
    ]
    notices.extend(
        f"Esta lista mostra apenas parte dos {total} pedidos encontrados na sua conta."
        for total in sorted(order_totals)
    )
    notices.extend(
        f"Os itens exibidos são apenas parte dos {total} itens deste pedido."
        for total in sorted(item_totals)
    )
    if has_discount:
        notices.append(
            "Dados de uma fotografia importada; não há datas de validade informadas para as promoções."
        )
    final_answer = "\n\n".join([answer.strip(), *notices])
    trace("output.accepted", truncated_totals=sorted(totals))
    return final_answer
