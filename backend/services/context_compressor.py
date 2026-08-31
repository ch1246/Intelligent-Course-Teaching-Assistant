"""
Context Compressor — Token counting & budget-aware message compression.

Ensures the assembled context (system prompt + retrieval docs + memory +
history + user message) stays within the configured max_context_tokens budget.

Compression priority (first to keep, last to drop):
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
        ``"truncate"`` (current implementation) or ``"summarize"`` (future).

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
    while len(history) > 2:
        history.pop(0)
        test = [system_msg] + history
        if count_messages_tokens(test) <= budget:
            logger.info(
                "Context compressed: dropped %d history messages → %d messages, %d tokens",
                len(messages) - len(test), len(test), count_messages_tokens(test),
            )
            return test

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

def _truncate_to_token_budget(text: str, max_tokens: int, method: str) -> str:
    """Truncate *text* to *max_tokens*, trying natural break points."""
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
