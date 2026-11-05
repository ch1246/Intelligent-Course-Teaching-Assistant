"""
Context Compressor — Token counting & budget-aware message compression.

Ensures the assembled context (system prompt + retrieval docs + memory +
history + user message) stays within the configured max_context_tokens budget.

Compatibility note: the summary below was aspirational; the implementation actually
drops in the order listed under "Actual drop order".

Actual drop order (what the code does):
  1. 最旧的历史消息（保留最后 1 轮）；``summarize`` 模式下先把它们压成抽取式摘要
  2. 从 System Prompt 的**尾部**截断（模板里尾部通常是检索文档 → 再往前是学生画像）
  3. 当前用户消息（保底：只有当剩余预算 > 50 token 时才截）
  4. 核选项：system 截到预算一半 + 只保留最后一条消息

Reference priority (first to keep, last to drop):
  1. System prompt skeleton (core instruction at the top)
  2. Current user message
  3. Student profile (memory_prompt)
  4. Retrieval documents (trimmed from bottom = least relevant)
  5. History messages (oldest first)
"""
import re
import logging

logger = logging.getLogger(__name__)

# ── Tokenizer (lazy init) ──────────────────────────────────────
_tiktoken_enc = None


def _get_tokenizer():
    """Return tiktoken encoding or None (use fallback estimation)."""
    global _tiktoken_enc
    if _tiktoken_enc is not None:
        return _tiktoken_enc
    try:
        import tiktoken
        _tiktoken_enc = tiktoken.get_encoding("cl100k_base")
        return _tiktoken_enc
    except Exception:
        _tiktoken_enc = False
    return None


# ── Token counting ─────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """Count tokens with tiktoken (precise) or fallback estimation (safe overcount).

    Fallback uses character-class estimation tuned for Chinese+English mix:
      - CJK / fullwidth: ~1.5 tokens/char
      - ASCII / other:   ~0.3 tokens/char
    """
    enc = _get_tokenizer()
    if enc:
        return len(enc.encode(text))

    cjk = len(re.findall(
        r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]',
        text,
    ))
    other = len(text) - cjk
    return max(1, int(cjk * 1.5 + other * 0.3))


def count_messages_tokens(messages: list[dict]) -> int:
    """Total tokens for an OpenAI-style messages list (content + overhead)."""
    total = 0
    for msg in messages:
        total += count_tokens(msg.get("content", ""))
    # OpenAI chat overhead: ~4 tokens/message framing + 3 request priming
    total += len(messages) * 4 + 3
    return total


# ── Compression ────────────────────────────────────────────────

def compress_messages(
    messages: list[dict],
    max_tokens: int,
    compression_method: str = "truncate",
) -> list[dict]:
    """Compress messages to fit within *max_tokens* budget.

    Parameters
    ----------
    messages : list[dict]
        Expected structure:  [system_msg, ...history..., user_msg]
    max_tokens : int
        Hard token cap for the entire messages array.
    compression_method : str
        ``"truncate"`` —— 直接丢弃最旧历史 / 从尾部硬截断（默认）；
        ``"summarize"`` —— 丢弃前先把被丢的历史压成一段**抽取式**摘要（每条保留首句），
        系统提示词也改成"整句装填"而不是切断句子。注意：抽取式摘要不调用 LLM，
        因此零成本、可离线；若要做生成式摘要需另接模型。

    Returns
    -------
    list[dict]
        Compressed messages (may be same object if no compression needed).
    """
    if not messages or max_tokens <= 0:
        return messages

    budget = max(1, max_tokens)
    total = count_messages_tokens(messages)

    if total <= budget:
        return messages  # already fits

    orig_total = total
    system_msg = messages[0]
    history = list(messages[1:])  # copy so we can mutate

    # ── Step 1: drop oldest history messages (keep last 2 = 1 turn) ──
    # summarize 模式：丢弃之前先把要丢的历史压成一段抽取式摘要保留下来
    if compression_method == "summarize" and len(history) > 2:
        kept = history[-2:]
        dropped = history[:-2]
        digest = _summarize_messages(dropped, max(48, budget // 8))
        if digest:
            digest_msg = {
                "role": "system",
                "content": f"【历史对话摘要（抽取式压缩，未调用 LLM）】\n{digest}",
            }
            candidate = [system_msg, digest_msg] + kept
            if count_messages_tokens(candidate) <= budget:
                logger.info(
                    "Context compressed(summarize): %d 条历史 → 摘要 %d tokens，总计 %d tokens",
                    len(dropped), count_tokens(digest), count_messages_tokens(candidate),
                )
                return candidate
        history = kept

    # ── Step 1b: 从最旧的历史开始丢，直到塞进预算 ──
    # 每条消息的 token 只分词一次，之后增量扣减。旧实现每丢一条就对剩余
    # 全量重新分词，长会话是 O(n²)：30 轮对话要重复分词几百次。
    # 计数口径与 count_messages_tokens 保持一致：每条 content + 4 帧开销，请求级 +3。
    system_cost = count_tokens(system_msg.get("content", "")) + 4
    per_msg = [count_tokens(m.get("content", "")) + 4 for m in history]
    history_cost = sum(per_msg)
    request_overhead = 3

    dropped_n = 0
    while len(history) > 2:
        history_cost -= per_msg.pop(0)
        history.pop(0)
        dropped_n += 1
        total_now = system_cost + history_cost + request_overhead
        if total_now <= budget:
            logger.info(
                "Context compressed: dropped %d history messages → %d messages, %d tokens",
                dropped_n, len(history) + 1, total_now,
            )
            return [system_msg] + history

    # ── Step 2: truncate system prompt (tail = least-relevant docs) ──
    system_content = system_msg.get("content", "")
    system_tokens = count_tokens(system_content)

    overhead_msg = {"role": "system", "content": ""}
    base_tokens = count_messages_tokens([overhead_msg] + history)
    target = budget - base_tokens

    if target > 0 and system_tokens > target:
        truncated = _truncate_to_token_budget(system_content, target, compression_method)
        result = [{"role": "system", "content": truncated}] + history
        logger.info(
            "Context compressed: system prompt %d→%d tokens  (total %d→%d)",
            system_tokens, count_tokens(truncated),
            orig_total, count_messages_tokens(result),
        )
        return result

    # ── Step 3: last resort — truncate user message ──
    if history:
        last_msg = history[-1]
        overhead_without_last = count_messages_tokens([system_msg] + history[:-1])
        remaining = budget - overhead_without_last
        if remaining > 50:
            truncated = _truncate_to_token_budget(
                last_msg.get("content", ""), remaining, compression_method,
            )
            result = [system_msg] + history[:-1] + [
                {"role": last_msg["role"], "content": truncated}
            ]
            logger.warning("Context compression: user message truncated")
            return result

    # ── Step 4: nuclear option — minimal viable context ──
    result = [
        {"role": "system", "content": _truncate_to_token_budget(
            system_content, budget // 2, compression_method,
        )},
        history[-1] if history else {"role": "user", "content": ""},
    ]
    logger.warning("Context severely compressed to skeleton")
    return result


# ── Internal helpers ───────────────────────────────────────────

def _summarize_messages(messages: list[dict], max_tokens: int, max_items: int = 8) -> str:
    """把将被丢弃的历史压成一段抽取式摘要（每条按配额取首句，不调用 LLM）。

    只摘要**最近** max_items 条被丢弃的消息（越靠近当前轮越相关），更早的直接省略
    并注明条数，这样摘要本身也能稳定控制在上限内。
    """
    if not messages:
        return ""

    recent = messages[-max_items:]
    omitted = len(messages) - len(recent)
    per_item = max(10, (max_tokens - 12) // max(1, len(recent)) - 2)

    lines: list[str] = []
    if omitted > 0:
        lines.append(f"（更早的 {omitted} 条历史已省略）")
    for msg in recent:
        role = "学生" if msg.get("role") == "user" else "助手"
        content = re.sub(r"\s+", " ", (msg.get("content") or "")).strip()
        if not content:
            continue
        head = _truncate_to_token_budget(content, per_item, "truncate")
        suffix = "…" if len(head) < len(content) else ""
        lines.append(f"{role}：{head}{suffix}")

    if len(lines) <= (1 if omitted > 0 else 0):
        return ""
    return _truncate_to_token_budget("\n".join(lines), max_tokens, "truncate")


def _pack_sentences(text: str, max_tokens: int) -> str:
    """按整句贪心装填，尽量不把句子切断（summarize 模式用）。"""
    sentences = [s for s in re.split(r"(?<=[。！？!?；;\n])", text) if s.strip()]
    kept: list[str] = []
    used = 0
    for sentence in sentences:
        tokens = count_tokens(sentence)
        if used + tokens > max_tokens:
            break
        kept.append(sentence)
        used += tokens
    if not kept:
        return ""
    return "".join(kept).strip()


def _truncate_to_token_budget(text: str, max_tokens: int, method: str = "truncate") -> str:
    """Truncate *text* to *max_tokens*.

    ``summarize`` 模式优先按整句装填（保住句子完整性），装不下再退回硬截断。
    """
    if count_tokens(text) <= max_tokens:
        return text

    if method == "summarize":
        packed = _pack_sentences(text, max_tokens)
        if packed:
            return packed

    enc = _get_tokenizer()

    if enc:
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated = enc.decode(tokens[:max_tokens])
    else:
        cjk = len(re.findall(
            r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef]',
            text,
        ))
        other = len(text) - cjk
        ratio = 1.5 if cjk > other else 0.3
        est_chars = int(max_tokens / ratio) if ratio > 0 else len(text)
        if est_chars >= len(text):
            return text
        truncated = text[:est_chars]

    truncated = _snap_to_boundary(truncated)
    return truncated.strip()


def _snap_to_boundary(text: str) -> str:
    """Rewind to the last natural boundary (para / line / sentence)."""
    if not text:
        return text

    last_para = text.rfind("\n\n")
    if last_para > len(text) * 0.5:
        return text[:last_para]

    last_nl = text.rfind("\n")
    if last_nl > len(text) * 0.7:
        return text[:last_nl]

    for punct in ("。", "！", "？", ". ", "! ", "? ", "\n"):
        pos = text.rfind(punct)
        if pos > len(text) * 0.6:
            return text[:pos + len(punct)]

    return text
