"""Customer-output checks and notices derived from this run's source results."""

import re

from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.messages import ToolReturnPart

from emporio_music_backend.contracts.conversations import ExecutionContext
from emporio_music_backend.diagnostics import trace

_INTERNAL_MARKUP = re.compile(
    r"<\s*/?\s*(?:think(?:ing)?|analysis|reasoning|system|assistant|developer|tool|function)(?=[\s/>]|$)"
    r"|<\|(?:im_start|im_end|system|assistant|analysis)\|>",
    re.IGNORECASE,
)
_ORDER_SNAPSHOT_NOTICE = (
    "Os dados dos pedidos vêm de uma fotografia importada, não de uma "
    "confirmação em tempo real. A previsão de entrega, se informada, não "
    "confirma a data real de recebimento."
)


def customer_answer(ctx: RunContext[ExecutionContext], answer: str) -> str:
    """Protect presentation and append notices from current tool metadata."""
    if not answer.strip() or _INTERNAL_MARKUP.search(answer):
        trace("output.rejected", reason="blank_or_internal_markup", retry=ctx.retry)
        raise ModelRetry(
            "Responda somente ao cliente, em português, sem raciocínio interno, "
            "tags ou instruções de sistema."
        )
    policy_sources: set[tuple[str, str, int | None]] = set()
    has_discount = False
    has_order_snapshot = False
    totals: set[int] = set()
    order_totals: set[int] = set()
    item_totals: set[int] = set()
    for message in ctx.messages:
        if ctx.run_id is None or message.run_id != ctx.run_id:
            continue
        for part in message.parts:
            if not isinstance(part, ToolReturnPart) or not isinstance(
                part.content, dict
            ):
                continue
            content = part.content
            if (
                part.tool_name == "search_store_policies"
                and content.get("status") == "evidence_found"
            ):
                records = content.get("records")
                if isinstance(records, list):
                    for record in records:
                        if not isinstance(record, dict):
                            continue
                        section, pages = record.get("section"), record.get("pages")
                        if not isinstance(section, str):
                            continue
                        source = record.get("source")
                        if not isinstance(source, str) or not source:
                            source = "store_policies.pdf"
                        valid_pages = (
                            [page for page in pages if type(page) is int and page > 0]
                            if isinstance(pages, list)
                            else []
                        )
                        if valid_pages:
                            policy_sources.update(
                                (source, section, page) for page in valid_pages
                            )
                        else:
                            policy_sources.add((source, section, None))
            if part.tool_name in {"search_available_products", "get_product_details"}:
                products = content.get("products")
                if isinstance(products, list):
                    for product in products:
                        pricing = (
                            product.get("pricing")
                            if isinstance(product, dict)
                            else None
                        )
                        if isinstance(pricing, dict) and pricing.get(
                            "discount_kind"
                        ) in {"promotion", "pix"}:
                            has_discount = True
                if content.get("truncated") is True:
                    total = content.get("total_matches")
                    if type(total) is int and total > 0:
                        totals.add(total)
            if part.tool_name == "list_my_orders":
                orders = content.get("orders")
                if (
                    content.get("data_basis") == "imported_snapshot"
                    and isinstance(orders, list)
                    and any(isinstance(order, dict) for order in orders)
                ):
                    has_order_snapshot = True
                if content.get("truncated") is True:
                    total = content.get("total_matches")
                    if type(total) is int and total > 0:
                        order_totals.add(total)
            if part.tool_name == "get_my_order":
                order = content.get("order")
                if isinstance(order, dict):
                    if content.get("data_basis") == "imported_snapshot":
                        has_order_snapshot = True
                    if order.get("items_truncated") is True:
                        total = order.get("total_items")
                        if type(total) is int and total > 0:
                            item_totals.add(total)
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
    if has_order_snapshot and _ORDER_SNAPSHOT_NOTICE not in answer:
        notices.append(_ORDER_SNAPSHOT_NOTICE)
    if has_discount:
        notices.append(
            "Dados de uma fotografia importada; não há datas de validade informadas para as promoções."
        )
    if policy_sources:
        references: list[str] = []
        for source, section, page in sorted(
            policy_sources, key=lambda item: (item[0], item[1], item[2] or 0)
        ):
            source_name = (
                "Manual de políticas da loja"
                if source == "store_policies.pdf"
                else source
            )
            location = "capa" if section == "cover" else f"seção {section}"
            if page is not None:
                location += f", p. {page}"
            else:
                location += ", sem página física"
            references.append(f"{source_name} — {location}")
        source_notice = f"Fontes consultadas: {'; '.join(references)}."
        if source_notice not in answer:
            notices.append(source_notice)
    final_answer = "\n\n".join([answer.strip(), *notices])
    trace("output.accepted", truncated_totals=sorted(totals))
    return final_answer
