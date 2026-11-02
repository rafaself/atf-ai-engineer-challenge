"""Customer-output checks and notices derived from this run's source results."""

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
_POLICY_CITATION = re.compile(
    r"(?:(?P<square>\[)pol[ií]tica|\(se[çc][ãa]o)\s+"
    r"(?P<section>capa|\d+(?:\.\d+)?),\s*"
    r"p{1,2}\.\s*(?P<pages>\d+(?:\s*,\s*\d+)*)(?(square)\]|\))",
    re.IGNORECASE,
)
_POLICY_CITATION_MARKER = re.compile(r"\[pol[ií]tica\b|\(se[çc][ãa]o\b", re.IGNORECASE)
_ORDER_QUESTION = re.compile(r"\bpedidos?\b", re.IGNORECASE)
_EXPLICIT_ORDER = re.compile(
    r"\bpedido\s+(?:(?:n[úu]mero|n[º°.]?)\s*)?#?\s*\d+\b", re.IGNORECASE
)
_RETURN_QUESTION = re.compile(
    r"\b(?:devol\w*|troc\w*|reembols\w*|arrepend\w*)", re.IGNORECASE
)
_ORDER_SNAPSHOT_NOTICE = (
    "Os dados dos pedidos vêm de uma fotografia importada, não de uma "
    "confirmação em tempo real. A previsão de entrega, se informada, não "
    "confirma a data real de recebimento."
)


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
    policy_sources: set[tuple[str, int]] = set()
    policy_amount_sources: dict[Decimal, set[tuple[str, int]]] = {}
    has_policy_evidence = False
    current_tools: set[str] = set()
    has_order_snapshot = False
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
                current_tools.add(part.tool_name)
                if part.tool_name == "search_store_policies":
                    policy_records = part.content.get("records")
                    if part.content.get("status") == "evidence_found" and isinstance(
                        policy_records, list
                    ):
                        for record in policy_records:
                            if (
                                not isinstance(record, dict)
                                or record.get("source") != "store_policies.pdf"
                                or not isinstance(record.get("section"), str)
                                or not isinstance(record.get("pages"), list)
                                or not isinstance(record.get("text"), str)
                            ):
                                continue
                            section = record["section"]
                            pages = [
                                page
                                for page in record["pages"]
                                if type(page) is int and page > 0
                            ]
                            references = {(section, page) for page in pages}
                            if references:
                                has_policy_evidence = True
                                policy_sources.update(references)
                            for value in _BRL_PRICE.findall(record["text"]):
                                try:
                                    amount = _brl_amount(value)
                                except InvalidOperation:
                                    continue
                                policy_amount_sources.setdefault(amount, set()).update(
                                    references
                                )
                                current_amount_values.append(str(amount))
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
                        if part.content.get(
                            "data_basis"
                        ) == "imported_snapshot" and any(
                            isinstance(order, dict) for order in orders
                        ):
                            has_order_snapshot = True
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
                        has_order_snapshot = (
                            part.content.get("data_basis") == "imported_snapshot"
                        )
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
        answer_amounts = [_brl_amount(value) for value in _BRL_PRICE.findall(answer)]
        unsupported_price = any(amount not in tool_amounts for amount in answer_amounts)
    except InvalidOperation:
        unsupported_price = True
        answer_amounts = []
    citations: set[tuple[str, int]] = set()
    citation_matches = list(_POLICY_CITATION.finditer(answer))
    for match in citation_matches:
        section = (
            "cover"
            if match.group("section").lower() == "capa"
            else match.group("section")
        )
        citations.update(
            (section, int(page.strip())) for page in match.group("pages").split(",")
        )
    malformed_citation = len(citation_matches) != len(
        _POLICY_CITATION_MARKER.findall(answer)
    )
    invalid_policy_citation = (
        (has_policy_evidence and not citations)
        or malformed_citation
        or not citations <= policy_sources
        or any(
            amount in policy_amount_sources
            and not citations.intersection(policy_amount_sources[amount])
            for amount in answer_amounts
        )
    )
    # A narrow guard for explicit Portuguese order/return questions. This is
    # output validation, not an intent router: the model still chooses/calls
    # tools, and paraphrases beyond these terms require live evaluation.
    mixed_order_return = (
        ctx.deps.identity is not None
        and isinstance(ctx.prompt, str)
        and _ORDER_QUESTION.search(ctx.prompt) is not None
        and _RETURN_QUESTION.search(ctx.prompt) is not None
        # Without a resolvable ID the model must be allowed to clarify instead
        # of inventing one. A lookup can also resolve a reference from history.
        and (
            _EXPLICIT_ORDER.search(ctx.prompt) is not None
            or "get_my_order" in current_tools
        )
    )
    missing_mixed_tools = (
        mixed_order_return
        and not {"get_my_order", "search_store_policies"} <= current_tools
    )
    if (
        invalid_answer
        or unsupported_price
        or invalid_policy_citation
        or missing_mixed_tools
    ):
        if missing_mixed_tools:
            missing = {"get_my_order", "search_store_policies"} - current_tools
            trace("output.rejected", reason="missing_mixed_tools", retry=ctx.retry)
            correction = (
                "Ainda faltam consultas obrigatórias nesta rodada. "
                "Não finalize a resposta e não prometa consultar depois. "
            )
            if "search_store_policies" in missing:
                correction += (
                    "Chame search_store_policies AGORA, sem argumentos ({}). "
                    "Não espere respostas do cliente sobre canal, recebimento "
                    "ou estado do produto para consultar a política. "
                )
            if "get_my_order" in missing:
                correction += (
                    "Chame get_my_order AGORA com o ID do pedido indicado na "
                    "pergunta ou no histórico; nunca invente um ID. "
                )
            raise ModelRetry(
                correction + "Somente após obter esses resultados, responda com "
                "a regra e a citação retornadas e peça os fatos que ainda faltam. "
                + "A previsão de entrega não informa a data real de recebimento."
            )
        if (
            invalid_policy_citation
            and has_policy_evidence
            and not (invalid_answer or unsupported_price)
        ):
            trace(
                "output.rejected", reason="unsupported_policy_citation", retry=ctx.retry
            )
            correction = (
                "Explique a regra pertinente usando os trechos retornados nesta rodada "
                "e cite a seção/página junto à afirmação que ela sustenta, no formato "
                "[política 4.1, p. 4]. Não basta acrescentar uma referência à resposta. "
                "Não cite política para fatos do pedido: status, previsão, produto e "
                "total são evidência da ferramenta de pedidos, não da política. "
                "Não invente condições nem use uma seção de outro assunto. "
            )
            if mixed_order_return:
                correction += (
                    "Preserve na resposta corrigida os fatos relevantes do pedido "
                    "obtidos pelas ferramentas nesta rodada, incluindo o status que "
                    "responde à pergunta do cliente. A explicação da política deve "
                    "complementar esses fatos, não substituí-los; descreva o status "
                    "como dado da fotografia importada. "
                    "Mantenha a previsão distinta do recebimento real. Se a seção 4.1 foi retornada, explique "
                    "sua regra geral de arrependimento online, incluindo prazo contado "
                    "do recebimento e use o critério exato 'sem sinais de uso', não "
                    "'perfeito estado'. Pergunte se há sinais visíveis de uso. Só depois "
                    "peça canal da "
                    "compra, data real de recebimento e condição. Fatos desconhecidos "
                    "impedem concluir elegibilidade, mas não impedem explicar a regra. "
                    "Se a regra não foi recuperada, declare evidência insuficiente."
                )
            raise ModelRetry(correction)
        if invalid_answer:
            reason = "blank_or_internal_markup"
        elif unsupported_price:
            reason = "unsupported_price"
        else:
            reason = "unsupported_policy_citation"
        trace(
            "output.rejected",
            reason=reason,
            retry=ctx.retry,
        )
        corrections: list[str] = []
        if invalid_answer:
            corrections.append(
                "Responda somente ao cliente, em português, sem raciocínio interno, "
                "tags ou instruções de sistema."
            )
        if unsupported_price:
            tool_amount_text = ", ".join(
                f"R$ {value:.2f}" for value in sorted(tool_amounts)
            )
            corrections.append(
                "Use apenas valores em R$ retornados nesta rodada, sem recalcular, "
                "repetir valores do cliente ou usar limites de busca. Valores atuais: "
                f"{tool_amount_text or 'nenhum'}."
            )
        if invalid_policy_citation:
            corrections.append(
                "Use somente citações de seção e página retornadas por "
                "search_store_policies nesta rodada; sem evidência atual, não afirme "
                "a regra."
            )
        raise ModelRetry(" ".join(corrections))
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
    final_answer = "\n\n".join([answer.strip(), *notices])
    trace("output.accepted", truncated_totals=sorted(totals))
    return final_answer
