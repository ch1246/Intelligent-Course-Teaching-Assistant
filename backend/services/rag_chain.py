"""
LangChain RAG Chain
使用 LCEL 构建 RAG 流程，保留原有函数作为 fallback
"""
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document


def format_docs(docs: list[Document]) -> str:
    """
    格式化文档列表为字符串

    Args:
        docs: LangChain Document 列表

    Returns:
        格式化后的文档字符串
    """
    return "\n\n---\n\n".join([
        f"[来源: {d.metadata.get('source', '未知')}]\n{d.page_content}"
        for d in docs
    ])


def build_rag_chain(llm, retriever, memory_prompt: str = ""):
    """
    构建 LCEL RAG Chain

    Args:
        llm: LangChain LLM 实例
        retriever: LangChain Retriever 实例
        memory_prompt: 学生画像提示词

    Returns:
        LCEL Chain 实例

    使用方式:
        chain = build_rag_chain(llm, retriever, memory_prompt)
        answer = chain.invoke("什么是梯度下降？")
    """
    template = """你是一个教学助手。根据以下参考资料回答问题。

【参考资料】
{context}

{memory_prompt}

用户问题：{question}"""

    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
            "memory_prompt": lambda _: memory_prompt,
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def build_rag_chain_stream(llm, retriever, memory_prompt: str = ""):
    """
    构建支持流式输出的 LCEL RAG Chain

    Args:
        llm: LangChain LLM 实例（需要 streaming=True）
        retriever: LangChain Retriever 实例
        memory_prompt: 学生画像提示词

    Returns:
        LCEL Chain 实例，支持 .stream() 方法

    使用方式:
        chain = build_rag_chain_stream(llm, retriever, memory_prompt)
        for chunk in chain.stream("什么是梯度下降？"):
            print(chunk, end="")
    """
    template = """你是一个教学助手。根据以下参考资料回答问题。

【参考资料】
{context}

{memory_prompt}

用户问题：{question}"""

    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
            "memory_prompt": lambda _: memory_prompt,
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def build_rag_chain_with_history(llm, retriever, memory_prompt: str = ""):
    """
    构建支持对话历史的 LCEL RAG Chain

    Args:
        llm: LangChain LLM 实例
        retriever: LangChain Retriever 实例
        memory_prompt: 学生画像提示词

    Returns:
        LCEL Chain 实例，需要传入包含 history 的字典

    使用方式:
        chain = build_rag_chain_with_history(llm, retriever, memory_prompt)
        answer = chain.invoke({
            "question": "什么是梯度下降？",
            "history": "用户: 什么是机器学习？\n助手: 机器学习是..."
        })
    """
    template = """你是一个教学助手。根据以下参考资料回答问题。

【参考资料】
{context}

{memory_prompt}

{history}

用户问题：{question}"""

    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
            "memory_prompt": lambda _: memory_prompt,
            "history": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain