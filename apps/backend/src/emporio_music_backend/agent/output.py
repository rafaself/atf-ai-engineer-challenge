"""Customer-output checks and disclosure derived from this run's catalog results."""

import re

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import ToolReturnPart

from emporio_music_backend.contracts import ExecutionContext
from emporio_music_backend.diagnostics import trace

_INTERNAL_MARKUP = re.compile(
    r"<\s*/?\s*(?:think(?:ing)?|analysis|reasoning|system|assistant|developer|tool|function)(?=[\s/>]|$)"
    r"|<\|(?:im_start|im_end|system|assistant|analysis)\|>",
    re.IGNORECASE,
)


def customer_answer(ctx: RunContext[ExecutionContext], answer: str) -> str:
    """Reject internal output rather than strip it; disclose every truncated query."""
    if not answer.strip() or _INTERNAL_MARKUP.search(answer):
        trace("output.rejected", reason="blank_or_internal_markup", retry=ctx.retry)
        raise ModelRetry(
            "Responda somente ao cliente, em português, sem raciocínio interno, "
            "tags, instruções de sistema ou ações de encaminhamento. "
            "Não há ferramenta de encaminhamento. Reescreva a resposta final."
        )
    totals: set[int] = set()
    order_totals: set[int] = set()
    item_totals: set[int] = set()
    for message in ctx.messages:
        if ctx.run_id is None or message.run_id != ctx.run_id:
            continue
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and isinstance(part.content, dict):
                if (
                    part.tool_name == "list_my_orders"
                    and part.content.get("truncated") is True
                ):
                    total = part.content.get("total_matches")
                    if type(total) is int and total > 0:
                        order_totals.add(total)
                if part.tool_name == "get_my_order":
                    detail = part.content.get("order")
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
    final_answer = "\n\n".join([answer.strip(), *notices])
    trace("output.accepted", truncated_totals=sorted(totals))
    return final_answer
