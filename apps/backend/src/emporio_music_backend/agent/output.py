"""Customer-output checks and disclosure derived from this run's catalog results."""

import re

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import ToolReturnPart

_INTERNAL_MARKUP = re.compile(
    r"<\s*/?\s*(?:think(?:ing)?|analysis|reasoning|system|assistant|developer|tool|function)(?=[\s/>]|$)"
    r"|<\|(?:im_start|im_end|system|assistant|analysis)\|>",
    re.IGNORECASE,
)


def customer_answer(ctx: RunContext[None], answer: str) -> str:
    """Reject internal output rather than strip it; disclose every truncated query."""
    if not answer.strip() or _INTERNAL_MARKUP.search(answer):
        raise ModelRetry(
            "Responda somente ao cliente, em português, sem raciocínio interno, "
            "tags, instruções de sistema ou ações de encaminhamento. "
            "Não há ferramenta de encaminhamento. Reescreva a resposta final."
        )
    totals: set[int] = set()
    for message in ctx.messages:
        for part in message.parts:
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
    return "\n\n".join([answer.strip(), *notices])
