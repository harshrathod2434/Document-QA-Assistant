"""
Retrieval module: handles question answering by retrieving relevant
document chunks and generating answers using OpenAI GPT-4o-mini.
Uses modern LCEL (LangChain Expression Language) chains.
"""

from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from config import OPENAI_API_KEY, OPENAI_LLM_MODEL, TOP_K_RESULTS, QA_SYSTEM_PROMPT
from embedding import load_vector_store


def get_llm() -> ChatOpenAI:
    """Create and return the OpenAI LLM instance."""
    return ChatOpenAI(
        model=OPENAI_LLM_MODEL,
        openai_api_key=OPENAI_API_KEY,
        temperature=0.3,
    )


def ask_question(question: str) -> Dict[str, Any]:
    """
    Ask a question and get an answer based on the uploaded documents.
    Uses LCEL chain with retriever for modern LangChain compatibility.
    """
    try:
        vector_store = load_vector_store()
        if vector_store is None:
            raise ValueError(
                "No document database found. Please upload and process documents first."
            )

        # Set up retriever
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOP_K_RESULTS},
        )

        # Retrieve relevant documents
        docs = retriever.invoke(question)

        # Build context from retrieved documents
        context = "\n\n".join(doc.page_content for doc in docs)

        # Format prompt and invoke LLM
        llm = get_llm()
        prompt = ChatPromptTemplate.from_template(QA_SYSTEM_PROMPT)
        chain = prompt | llm
        response = chain.invoke({"context": context, "question": question})

        # Extract sources
        sources = []
        seen = set()

        for doc in docs:
            meta = doc.metadata
            source_key = (
                meta.get("source", "Unknown"),
                meta.get("page", meta.get("slide", 0)),
            )

            if source_key not in seen:
                seen.add(source_key)
                source_info = {
                    "file": meta.get("source", "Unknown"),
                    "type": meta.get("file_type", "unknown"),
                    "snippet": doc.page_content[:200] + "..."
                    if len(doc.page_content) > 200
                    else doc.page_content,
                }

                if "page" in meta:
                    source_info["page"] = meta["page"]
                if "slide" in meta:
                    source_info["slide"] = meta["slide"]

                sources.append(source_info)

        return {
            "answer": response.content,
            "sources": sources,
        }

    except ValueError as e:
        return {"answer": str(e), "sources": []}
    except Exception as e:
        return {
            "answer": f"An error occurred while processing your question: {str(e)}",
            "sources": [],
        }
