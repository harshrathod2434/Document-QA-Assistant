"""Grounded question answering and full-library summarisation."""

from typing import Any, Dict, Iterable, List

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import OPENAI_API_KEY, OPENAI_LLM_MODEL, QA_SYSTEM_PROMPT, TOP_K_RESULTS
from embedding import load_vector_store


SUMMARY_PROMPT = """You are an expert document analyst. Summarise all of the supplied source material, not merely the most relevant excerpts.

Requirements:
- Follow the user's requested format and level of detail.
- Cover the central purpose, major findings, important evidence, decisions, risks, and action items when present.
- Preserve important numbers, names, qualifications, and disagreements.
- Organise the answer with useful Markdown headings and concise bullet points.
- Do not invent facts or use outside knowledge.
- Cite source labels such as [filename, page 3] throughout the response.

User request: {question}

Source material:
{context}

Complete grounded summary:"""

SYNTHESIS_PROMPT = """Combine the section summaries below into one coherent, non-repetitive answer to the user's request.

Retain every important fact, number, qualification, decision, risk, and source citation. Use clear Markdown headings and concise bullets. Do not add outside information.

User request: {question}

Section summaries:
{context}

Final complete summary:"""


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=OPENAI_LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        temperature=0.2,
    )


def _labelled_context(documents: Iterable[Document]) -> str:
    sections = []
    for document in documents:
        metadata = document.metadata
        location = ""
        if metadata.get("page") is not None:
            location = f", page {metadata['page']}"
        elif metadata.get("slide") is not None:
            location = f", slide {metadata['slide']}"
        sections.append(
            f"[Source: {metadata.get('source', 'Unknown')}{location}]\n{document.page_content}"
        )
    return "\n\n".join(sections)


def _sources(documents: Iterable[Document]) -> List[dict]:
    sources: List[dict] = []
    seen = set()
    for document in documents:
        metadata = document.metadata
        key = (metadata.get("source", "Unknown"), metadata.get("page", metadata.get("slide", 0)))
        if key in seen:
            continue
        seen.add(key)
        source = {
            "file": metadata.get("source", "Unknown"),
            "type": metadata.get("file_type", "unknown"),
            "snippet": document.page_content[:240] + ("..." if len(document.page_content) > 240 else ""),
        }
        if "page" in metadata:
            source["page"] = metadata["page"]
        if "slide" in metadata:
            source["slide"] = metadata["slide"]
        sources.append(source)
    return sources


def _all_documents(vector_store) -> List[Document]:
    payload = vector_store.get(include=["documents", "metadatas"])
    texts = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []
    return [
        Document(page_content=text, metadata=(metadatas[index] or {}))
        for index, text in enumerate(texts)
        if text
    ]


def _batches(documents: List[Document], character_limit: int = 36000) -> List[List[Document]]:
    batches: List[List[Document]] = []
    current: List[Document] = []
    current_size = 0
    for document in documents:
        size = len(document.page_content)
        if current and current_size + size > character_limit:
            batches.append(current)
            current = []
            current_size = 0
        current.append(document)
        current_size += size
    if current:
        batches.append(current)
    return batches


def summarize_documents(question: str) -> Dict[str, Any]:
    """Summarise the full indexed library using map-reduce for large inputs."""
    try:
        vector_store = load_vector_store()
        if vector_store is None:
            raise ValueError("No document database found. Please upload and process documents first.")
        documents = _all_documents(vector_store)
        if not documents:
            raise ValueError("No readable document content was found.")

        llm = get_llm()
        summary_chain = ChatPromptTemplate.from_template(SUMMARY_PROMPT) | llm
        partials = []
        for batch in _batches(documents):
            response = summary_chain.invoke({"context": _labelled_context(batch), "question": question})
            partials.append(response.content)

        if len(partials) == 1:
            answer = partials[0]
        else:
            synthesis_chain = ChatPromptTemplate.from_template(SYNTHESIS_PROMPT) | llm
            answer = synthesis_chain.invoke({
                "context": "\n\n--- SECTION SUMMARY ---\n\n".join(partials),
                "question": question,
            }).content
        return {"answer": answer, "sources": _sources(documents)}
    except ValueError as error:
        return {"answer": str(error), "sources": []}
    except Exception as error:
        return {"answer": f"An error occurred while summarising the documents: {error}", "sources": []}


def ask_question(question: str) -> Dict[str, Any]:
    """Answer a focused question using semantic retrieval."""
    try:
        vector_store = load_vector_store()
        if vector_store is None:
            raise ValueError("No document database found. Please upload and process documents first.")

        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOP_K_RESULTS},
        )
        documents = retriever.invoke(question)
        context = _labelled_context(documents)
        chain = ChatPromptTemplate.from_template(QA_SYSTEM_PROMPT) | get_llm()
        response = chain.invoke({"context": context, "question": question})
        return {"answer": response.content, "sources": _sources(documents)}
    except ValueError as error:
        return {"answer": str(error), "sources": []}
    except Exception as error:
        return {"answer": f"An error occurred while processing your question: {error}", "sources": []}
