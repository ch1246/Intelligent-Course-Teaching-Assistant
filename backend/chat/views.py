import json
import logging
import asyncio
import threading
import re
import time as _time
from datetime import timedelta

from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view
from asgiref.sync import sync_to_async
from .models import ChatSession, ChatMessage, UserMemory
from .serializers import (
    ChatSessionSerializer, ChatCreateSerializer, ChatCompletionSerializer,
    ChatMessageSerializer,
)
from accounts.views import make_response
from courses.models import Course
from settings_app.models import AgentAPIConfig
from services.rag_service import (
    chat_stream_structured,
    collection_name_for_course,
    distance_to_similarity,
    expand_queries,
    lexical_rerank,
    search_similar,
)
from services.context_compressor import compress_messages
from services.rag_chain import render_system_prompt

# LangChain 主链路：依赖缺失时置 None，调用处降级为手写实现
# （search_similar / chat_stream_structured），保证应用仍可启动。
try:
    from services.langchain_vectorstore import search_with_scores
except Exception:  # pragma: no cover - langchain 依赖缺失时降级
    search_with_scores = None
try:
    from services.langchain_llm import get_llm_with_params
except Exception:  # pragma: no cover - langchain 依赖缺失时降级
    get_llm_with_params = None
from harness.models import TraceLog
from dashboard.models import LearningRecord

logger = logging.getLogger(__name__)


# ── Sessions (unchanged) ──────────────────────────────

@api_view(["GET", "POST"])
def sessions(request, course_id):
    if request.method == "GET":
        qs = ChatSession.objects.filter(user=request.user, course_id=course_id).order_by("-updated_at")
        return make_response(data=ChatSessionSerializer(qs, many=True).data)
    ser = ChatCreateSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)
    try:
        course = Course.objects.get(pk=ser.validated_data["course_id"])
    except Course.DoesNotExist:
        return make_response(code=404, message="课程不存在", http_status=404)
    session = ChatSession.objects.create(
        title=ser.validated_data.get("title", "新对话"),
        user=request.user, course=course,
        skill=ser.validated_data["skill"],
    )
    return make_response(data=ChatSessionSerializer(session).data)


@api_view(["GET", "DELETE"])
def session_detail(request, course_id, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id, user=request.user, course_id=course_id)
    except ChatSession.DoesNotExist:
        return make_response(code=404, message="会话不存在", http_status=404)
    if request.method == "GET":
        return make_response(data=ChatSessionSerializer(session).data)
    else:
        session.delete()
        return make_response(message="删除成功")


@api_view(["GET"])
def session_messages(request, course_id, session_id):
    try:
        session = ChatSession.objects.get(pk=session_id, user=request.user, course_id=course_id)
    except ChatSession.DoesNotExist:
        return make_response(code=404, message="会话不存在", http_status=404)
    msgs = session.messages.all()
    return make_response(data=ChatMessageSerializer(msgs, many=True).data)


# ── User Memory ───────────────────────────────────────

TOPIC_STOP_WORDS = {
    "的", "是", "了", "在", "和", "也", "就", "都", "而", "及", "与",
    "着", "或", "一个", "没有", "我们", "你们", "他们", "这个", "那个",
    "什么", "怎么", "如何", "为什么", "哪些", "可以", "需要", "应该",
    "请", "帮", "给", "让", "用", "对", "从", "到", "中", "上", "下",
    "有", "会", "能", "要", "想", "做", "说", "看", "知道", "了解",
    "解释", "讲", "详细", "简单", "大概", "一下", "谢谢", "请问",
    "还", "不", "很", "比较", "非常", "更", "最", "别",
}


def _extract_topics(text: str, max_topics: int = 5) -> list[str]:
    """Simple keyword-based topic extraction from a question."""
    words = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]+", text.lower())
    candidates = {}
    for w in words:
        if w in TOPIC_STOP_WORDS or len(w) < 2:
            continue
        candidates[w] = candidates.get(w, 0) + 1
    sorted_candidates = sorted(candidates.items(), key=lambda x: -x[1])
    topics = [t[0] for t in sorted_candidates[:max_topics]]
    abbreviations = re.findall(r"\b[A-Z]{2,6}\b", text)
    for abbr in abbreviations:
        if abbr not in topics:
            topics.append(abbr)
    return topics[:max_topics]


def _get_user_memories(user, course) -> list[dict]:
    """Get recent memory records for this user+course."""
    records = UserMemory.objects.filter(user=user, course=course).order_by("-last_asked_at")[:30]
    return [
        {"topic": r.topic, "mastery": r.mastery, "question_count": r.question_count}
        for r in records
    ]


def _build_memory_prompt(memories: list[dict]) -> str:
    """Build a student profile section for the system prompt."""
    if not memories:
        return ""

    weak = [(m["topic"], m["mastery"], m["question_count"]) for m in memories if m["mastery"] < 0.5]
    medium = [(m["topic"], m["mastery"], m["question_count"]) for m in memories if 0.5 <= m["mastery"] < 0.75]
    strong = [(m["topic"], m["mastery"], m["question_count"]) for m in memories if m["mastery"] >= 0.75]

    lines = ["\n\n【学生画像 — 本课程学习记录】"]
    if weak:
        items = "、".join([f"{t}(掌握度{int(m*100)}%, 提问{c}次)" for t, m, c in weak[:8]])
        lines.append(f"- ⚠️ 薄弱知识点：{items}")
        lines.append("  对这些知识点请放慢节奏，多举例，确认学生理解后再继续")
    if medium:
        items = "、".join([t for t, _, _ in medium[:5]])
        lines.append(f"- 📖 学习中：{items}")
    if strong:
        items = "、".join([t for t, _, _ in strong[:5]])
        lines.append(f"- ✅ 已掌握：{items}")
        lines.append("  对这些知识点可快速带过，不必展开")

    return "\n".join(lines)


# ── 学生画像掌握度更新规则 ─────────────────────────────
# 可观测的证据只有两条：同一知识点的**重复提问**，以及**两次提问的间隔**。
#   · 短时间内反复问同一个点 → 说明上次没讲懂，是负向证据 → 衰减
#   · 隔了较久再问同一个点 → 更接近「复习/回忆」，是正向证据 → 小幅提升
# 旧实现只有衰减项，掌握度会单调漂到下限 0.1，画像长期失真。
REASK_DECAY_WINDOW = timedelta(hours=24)  # 24 小时内重复提问视为「还没懂」
MASTERY_REASK_DECAY = 0.88                # 相对衰减 12%
MASTERY_FLOOR = 0.1
MASTERY_CEIL = 0.95
MASTERY_REVIEW_BOOST = 0.06               # 每次间隔式复习吃掉剩余差距的 6%


def _update_memory(user, course, question: str, response: str):
    """Update user memory after each Q&A turn.

    规则见上方常量说明。回答为空（生成失败/中断）时不做任何调整 —— 没学到
    不等于没掌握；掌握度的主动修正走 memory_bulk_update API（教师/前端手动）。
    """
    if not (response or "").strip():
        return
    topics = _extract_topics(question)
    if not topics:
        return

    now = timezone.now()
    for topic in topics:
        obj, created = UserMemory.objects.get_or_create(
            user=user, course=course, topic=topic,
            defaults={"mastery": 0.5, "question_count": 1},
        )
        if created:
            continue

        obj.question_count += 1
        gap = now - obj.last_asked_at if obj.last_asked_at else REASK_DECAY_WINDOW
        if gap < REASK_DECAY_WINDOW:
            # 还没懂：相对衰减，且有下限，不会归零
            obj.mastery = max(MASTERY_FLOOR, obj.mastery * MASTERY_REASK_DECAY)
        else:
            # 间隔式复习：向 1 收敛但永远够不到，避免刷成 100%
            obj.mastery = min(MASTERY_CEIL, obj.mastery + MASTERY_REVIEW_BOOST * (1 - obj.mastery))

        obj.last_asked_at = now
        obj.save(update_fields=["question_count", "mastery", "last_asked_at"])


def _record_learning_time(user, course, seconds: int):
    """Accumulate real conversation duration (seconds) into today's learning record."""
    if seconds <= 0:
        return
    today = timezone.now().date()
    record, _ = LearningRecord.objects.get_or_create(
        user=user, course=course, date=today,
        defaults={"duration_seconds": 0},
    )
    record.duration_seconds += seconds
    record.save(update_fields=["duration_seconds"])


# ── Memory API ────────────────────────────────────────

@api_view(["GET"])
def user_memory(request, course_id):
    """Get user knowledge map for a course."""
    memories = UserMemory.objects.filter(user=request.user, course_id=course_id).order_by("mastery")
    return make_response(data={
        "memories": [
            {"id": m.id, "topic": m.topic, "mastery": round(m.mastery, 2),
             "question_count": m.question_count, "last_asked_at": str(m.last_asked_at),
             "notes": m.notes}
            for m in memories
        ],
        "summary": {
            "weak_count": memories.filter(mastery__lt=0.5).count(),
            "medium_count": memories.filter(mastery__gte=0.5, mastery__lt=0.75).count(),
            "strong_count": memories.filter(mastery__gte=0.75).count(),
            "total_topics": memories.count(),
        }
    })


@api_view(["DELETE"])
def delete_memory(request, course_id, memory_id):
    """Delete a single memory record."""
    try:
        m = UserMemory.objects.get(pk=memory_id, user=request.user, course_id=course_id)
    except UserMemory.DoesNotExist:
        return make_response(code=404, message="记录不存在", http_status=404)
    m.delete()
    return make_response(message="已删除")


@api_view(["POST"])
def memory_bulk_update(request, course_id):
    """Bulk update mastery for multiple topics."""
    data = request.data
    if not isinstance(data, list):
        return make_response(code=400, message="请求体应为列表", http_status=400)
    updated = 0
    for item in data:
        topic = item.get("topic")
        mastery = item.get("mastery")
        if topic and mastery is not None:
            UserMemory.objects.filter(user=request.user, course_id=course_id, topic=topic).update(
                mastery=max(0.0, min(1.0, float(mastery)))
            )
            updated += 1
    return make_response(data={"updated": updated})


# ── Helpers ───────────────────────────────────────────

def _get_agent_config():
    config = AgentAPIConfig.objects.filter(is_active=True, is_default=True).first()
    if not config:
        config = AgentAPIConfig.objects.filter(is_active=True).first()
    return config


# 系统提示词装配已迁至 services.rag_chain（render_system_prompt /
# build_system_prompt_legacy / build_system_prompt_from_template），
# 生产链路与 LCEL 链共用同一套提示词，改提示词只改 rag_chain.py。


def _resolve_pipeline(skill: str):
    """Resolve RAG pipeline from DB config.

    Returns ``(prompt_template, context_strategy, agent_config, pipeline)``。
    第 4 项是真正命中的 RAGPipeline（走默认管道时有值，走回退时为 None），
    用于把 TraceLog 记录关联到管道 —— 此前 4 处 TraceLog 写入都没传 pipeline，
    链路追踪里这个外键恒为 NULL，页面上永远看不到是哪条管道跑的。
    """
    # 1. Try default pipeline
    from harness.models import RAGPipeline
    pipeline = RAGPipeline.objects.filter(
        is_active=True, is_default=True,
        prompt_template__skill=skill,
    ).select_related("prompt_template", "context_strategy", "agent_config").first()

    if pipeline:
        return pipeline.prompt_template, pipeline.context_strategy, pipeline.agent_config, pipeline

    # 2. Fall back to AgentAPIConfig associations
    config = _get_agent_config()
    if config:
        template = config.prompt_template
        strategy = config.context_strategy
        if template and template.skill == skill:
            return template, strategy, config, None

    # 3. Fall back to any default template for this skill
    from prompt_engine.models import PromptTemplate
    from context_engine.models import ContextStrategy
    template = PromptTemplate.objects.filter(skill=skill, is_active=True, is_default=True).first()
    strategy = ContextStrategy.objects.filter(is_active=True, is_default=True).first()
    return template, strategy, _get_agent_config(), None


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ── Chat Completion ───────────────────────────────────

@api_view(["POST"])
def chat_completions(request, course_id):
    ser = ChatCompletionSerializer(data=request.data)
    if not ser.is_valid():
        return make_response(code=400, message=str(ser.errors), http_status=400)

    d = ser.validated_data
    session_id = d["session_id"]
    user_message = d["message"]

    try:
        session = ChatSession.objects.get(pk=session_id, user=request.user, course_id=course_id)
    except ChatSession.DoesNotExist:
        return make_response(code=404, message="会话不存在", http_status=404)

    # skill 以会话为准；仅当请求显式指定时才覆盖（serializer 中 skill 已改为可选，
    # 不再默认成 "qa" 造成与 session.skill 漂移）
    skill = d.get("skill") or session.skill

    course = session.course
    user = request.user
    ChatMessage.objects.create(session=session, role="user", content=user_message)

    config = _get_agent_config()
    if not config:
        return make_response(code=500, message="请先在管理中心配置 Agent API", http_status=500)

    model = config.default_model or (config.model_list[0] if config.model_list else "gpt-3.5-turbo")

    # ── Resolve pipeline from DB ───────────────────────
    prompt_template, context_strategy, _pipeline_config, trace_pipeline = _resolve_pipeline(skill)

    # Use strategy defaults or hardcoded fallbacks
    top_k = context_strategy.top_k if context_strategy else 5
    sim_threshold = context_strategy.similarity_threshold if context_strategy else 0.0
    include_memory = context_strategy.include_memory if context_strategy else True
    include_history = context_strategy.include_history if context_strategy else True
    history_turns = context_strategy.history_turns if context_strategy else 10
    # 这两个开关此前是「UI 上能配、代码零引用」，现在真正接进检索链路
    rerank_enabled = bool(context_strategy.rerank_enabled) if context_strategy else False
    enable_query_rewrite = bool(context_strategy.enable_query_rewrite) if context_strategy else False

    # ── Load user memories ─────────────────────────────
    memories = _get_user_memories(user, course) if include_memory else []
    memory_prompt = _build_memory_prompt(memories) if include_memory else ""
    memory_summary = None
    if memories:
        weak = [m for m in memories if m["mastery"] < 0.5]
        strong = [m for m in memories if m["mastery"] >= 0.75]
        memory_summary = f"已记录 {len(memories)} 个知识点，薄弱 {len(weak)} 个，已掌握 {len(strong)} 个"

    def sync_gen():
        full_response = ""
        sources_list = []
        queue = []

        def run_in_thread():
            loop = asyncio.new_event_loop()
            try:
                async def collect():
                    trace_session = session  # captured from outer scope
                    trace_pipeline_obj = trace_pipeline  # 命中的管道，用于关联 TraceLog
                    turn_start = _time.time()
                    try:
                        # ── Phase 1: 检索 ──────────────────
                        t0 = _time.time()
                        queue.append({"_ctrl": "status", "phase": "searching",
                                       "message": "🔍 正在检索课程资料..."})

                        # 检索式：开启查询改写时用「原问题 + 核心词版 + 英文术语」多路召回
                        queries = expand_queries(user_message) if enable_query_rewrite else [user_message]
                        collection_name = collection_name_for_course(course.id)
                        context_docs = []
                        langchain_ok = True
                        for q in queries:
                            try:
                                if search_with_scores is None:
                                    raise RuntimeError("LangChain 检索不可用（langchain 依赖缺失）")
                                found = search_with_scores(collection_name, q, top_k=top_k)
                            except Exception as e:
                                if langchain_ok:
                                    logger.warning(f"LangChain scored search failed, falling back: {e}")
                                    langchain_ok = False
                                try:
                                    found = search_similar(collection_name, q, n_results=top_k)
                                except Exception as e2:
                                    logger.warning(f"RAG search also failed: {e2}")
                                    found = []
                            for d in found:
                                # Chroma 的 space=l2 返回「平方 L2 距离」，换算成真实余弦相似度
                                d["similarity"] = round(distance_to_similarity(d.get("distance")), 4)
                                d["query"] = q
                            context_docs.extend(found)

                        # 多查询结果合并：按内容去重，保留相似度最高的那条
                        if len(queries) > 1 and context_docs:
                            deduped = {}
                            for d in context_docs:
                                key = (d.get("content") or "")[:200]
                                if key not in deduped or d["similarity"] > deduped[key]["similarity"]:
                                    deduped[key] = d
                            context_docs = list(deduped.values())

                        # 相似度阈值过滤：similarity 现在是真实余弦相似度，阈值终于生效
                        if sim_threshold > 0 and context_docs:
                            context_docs = [d for d in context_docs if d["similarity"] >= sim_threshold]

                        # 排序取 top_k；开启重排时用「向量相似度 + 字面重合度」融合排序
                        context_docs.sort(key=lambda d: d.get("similarity", 0.0), reverse=True)
                        context_docs = context_docs[:top_k]
                        if rerank_enabled and len(context_docs) > 1:
                            context_docs = lexical_rerank(user_message, context_docs)

                        t_retrieve = (_time.time() - t0) * 1000
                        await sync_to_async(TraceLog.objects.create)(
                            session=trace_session, pipeline=trace_pipeline_obj, phase="retrieve",
                            duration_ms=round(t_retrieve, 1),
                            detail={"top_k": top_k, "threshold": sim_threshold,
                                    "found": len(context_docs), "query": user_message[:200],
                                    "queries": queries, "rerank": rerank_enabled,
                                    "avg_similarity": round(
                                        sum(d.get("similarity", 0.0) for d in context_docs)
                                        / len(context_docs), 4
                                    ) if context_docs else 0.0},
                        )

                        if context_docs:
                            sources_list.extend([
                                d.get("metadata", {}).get("source", f"资料片段 {i+1}")
                                for i, d in enumerate(context_docs)
                            ])
                            queue.append({"_ctrl": "status", "phase": "found",
                                           "message": f"📚 已检索到 {len(context_docs)} 个相关片段",
                                           "retrievalCount": len(context_docs),
                                           "retrievals": [{
                                               "source": d.get("metadata", {}).get("source", "未知来源"),
                                               "preview": d["content"][:120] + "..." if len(d["content"]) > 120 else d["content"],
                                               "relevance": f"{max(0, min(100, int(d.get('similarity', 0.0) * 100)))}%",
                                           } for d in context_docs]})
                        else:
                            queue.append({"_ctrl": "status", "phase": "no_docs",
                                           "message": "⚠️ 未找到相关课程资料，将基于通用知识回答"})

                        # ── Phase 2: 组装提示词 ────────────
                        t0 = _time.time()
                        if memory_summary:
                            queue.append({"_ctrl": "status", "phase": "memory",
                                           "message": f"🧠 已加载学生画像：{memory_summary}",
                                           "memorySummary": memory_summary,
                                           "memoryDetail": [{"topic": m["topic"], "mastery": m["mastery"]} for m in memories[:10]]})

                        queue.append({"_ctrl": "status", "phase": "analyzing",
                                       "message": "🔄 正在综合分析资料与学生画像..."})

                        # ── Build system prompt（装配逻辑在 services.rag_chain）──
                        system_prompt = render_system_prompt(
                            prompt_template.content if prompt_template else None,
                            skill, course.name, context_docs,
                            memory_prompt, user_message,
                            # 后台配置的「全局 System Prompt」，所有技能共用的前置规范
                            global_preamble=_pipeline_config.system_prompt if _pipeline_config else "",
                        )

                        # Build messages array
                        messages = [{"role": "system", "content": system_prompt}]
                        if include_history:
                            history_msgs = await sync_to_async(
                                lambda: list(session.messages.order_by("-created_at")[:history_turns * 2])
                            )()
                            for msg in reversed(history_msgs):
                                messages.append({"role": msg.role, "content": msg.content})
                        else:
                            messages.append({"role": "user", "content": user_message})

                        # ── Compress context to fit token budget ──
                        max_ctx = context_strategy.max_context_tokens if context_strategy else 3000
                        cm = context_strategy.compression_method if context_strategy else "truncate"
                        messages = compress_messages(messages, max_ctx, cm)

                        t_build = (_time.time() - t0) * 1000
                        await sync_to_async(TraceLog.objects.create)(
                            session=trace_session, pipeline=trace_pipeline_obj, phase="build_prompt",
                            duration_ms=round(t_build, 1),
                            detail={"template_id": prompt_template.id if prompt_template else None,
                                    "template_name": prompt_template.name if prompt_template else "legacy",
                                    "docs_count": len(context_docs),
                                    "memory_enabled": include_memory,
                                    "prompt_length": len(system_prompt)},
                        )

                        # ── Phase 3: 思考 ──────────────────
                        pipeline_name = prompt_template.name if prompt_template else "默认"
                        thinking_info = {
                            "systemPrompt": system_prompt[:500],  # 增大预览长度
                            "fullSystemPrompt": system_prompt,     # 完整 prompt
                            "retrievalInfo": f"检索到 {len(context_docs)} 个片段 (top_k={top_k}, 检索式={len(queries)}, 重排={'开' if rerank_enabled else '关'})",
                            "model": model,
                            "pipeline": pipeline_name,
                        }
                        if memory_summary:
                            thinking_info["memorySummary"] = memory_summary
                            thinking_info["memoryPrompt"] = memory_prompt[:400]

                        queue.append({"_ctrl": "thinking_start", **thinking_info})

                        queue.append({"_ctrl": "status", "phase": "generating",
                                       "message": f"✍️ AI 正在生成回答（模型: {model}）..."})

                        # ── Phase 4: 生成 ──────────────────
                        t0 = _time.time()
                        first_content = True
                        ai_response_text = ""

                        # LangChain LLM 流式生成（fallback 到原实现）
                        _use_langchain_llm = True
                        try:
                            if get_llm_with_params is None:
                                raise RuntimeError("LangChain LLM 不可用（langchain 依赖缺失）")
                            llm = get_llm_with_params(
                                base_url=config.base_url.rstrip("/"),
                                api_key=config.get_api_key(),
                                model=model,
                            )
                            async for chunk in llm.astream(messages):
                                content = chunk.content
                                if content:
                                    if first_content:
                                        queue.append({"_ctrl": "answer_start"})
                                        first_content = False
                                    ai_response_text += content
                                    queue.append({"type": "content", "content": content})
                        except Exception as e:
                            logger.warning(f"LangChain LLM failed, falling back: {e}")
                            _use_langchain_llm = False

                        if not _use_langchain_llm:
                            async for event in chat_stream_structured(
                                messages=messages, base_url=config.base_url,
                                api_key=config.get_api_key(), model=model,
                            ):
                                if event["type"] == "content":
                                    if first_content:
                                        queue.append({"_ctrl": "answer_start"})
                                        first_content = False
                                    ai_response_text += event["content"]
                                    queue.append(event)

                        t_generate = (_time.time() - t0) * 1000
                        await sync_to_async(TraceLog.objects.create)(
                            session=trace_session, pipeline=trace_pipeline_obj, phase="generate",
                            duration_ms=round(t_generate, 1),
                            detail={"model": model, "response_length": len(ai_response_text)},
                        )

                        # ── Phase 5: 更新记忆 ──────────────
                        t0 = _time.time()
                        await sync_to_async(_update_memory)(user, course, user_message, ai_response_text)
                        t_memory = (_time.time() - t0) * 1000
                        await sync_to_async(TraceLog.objects.create)(
                            session=trace_session, pipeline=trace_pipeline_obj, phase="memory",
                            duration_ms=round(t_memory, 1),
                            detail={"topics": _extract_topics(user_message)},
                        )
                        queue.append({"_ctrl": "status", "phase": "memory_updated",
                                       "message": "✅ 已更新学习记忆"})

                        queue.append({"_ctrl": "done", "sources": "\n".join(sources_list) if sources_list else ""})

                    except Exception as e:
                        queue.append({"_ctrl": "error", "message": str(e)})
                    finally:
                        # 按真实对话耗时（秒）自动累加学习时长
                        elapsed = max(1, round(_time.time() - turn_start))
                        try:
                            await sync_to_async(_record_learning_time)(user, course, elapsed)
                        except Exception:
                            logger.warning("Failed to record learning time", exc_info=True)

                loop.run_until_complete(collect())
            finally:
                loop.close()

        t = threading.Thread(target=run_in_thread)
        t.start()

        answer_started = False
        answer_saved = False
        pos = 0
        while t.is_alive() or pos < len(queue):
            while pos < len(queue):
                item = queue[pos]
                pos += 1

                ctrl = item.get("_ctrl")
                if ctrl == "status":
                    yield _sse_event({"type": "status", **{k: v for k, v in item.items() if k != "_ctrl"}})
                elif ctrl == "thinking_start":
                    yield _sse_event({"type": "thinking_start", **{k: v for k, v in item.items() if k != "_ctrl"}})
                elif ctrl == "answer_start":
                    answer_started = True
                elif ctrl == "done":
                    full_response = full_response.strip()
                    ChatMessage.objects.create(
                        session=session, role="assistant",
                        content=full_response,
                        sources=item.get("sources", ""),
                    )
                    answer_saved = True
                    yield _sse_event({"type": "done", "sources": item.get("sources", "")})
                elif ctrl == "error":
                    yield _sse_event({"type": "error", "message": item["message"]})
                    t = None
                    break
                else:
                    chunk = item.get("content", "")
                    full_response += chunk
                    yield _sse_event({"type": "content", "content": chunk})

            if t is None:
                break
            _time.sleep(0.03)

        # 兜底：仅当 done 事件没走到（中断/异常）时保存半截回答。
        # 旧实现用 get_or_create(session, role) 匹配任意历史 assistant 消息，
        # 导致中断时的半截回答永远存不进去 —— 这里用 answer_saved 标记精确判断。
        if not answer_saved and full_response.strip():
            ChatMessage.objects.create(
                session=session, role="assistant",
                content=full_response.strip(),
                sources="\n".join(sources_list),
            )

    response = StreamingHttpResponse(sync_gen(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
