"""
Retrieval module: handles question answering by retrieving relevant
document chunks and generating answers using OpenAI GPT-4o-mini.
"""

from typing import Dict, List, Any

from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
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


def get_qa_chain() -> RetrievalQA:
    """
    Build and return a RetrievalQA chain using the stored vector database
    and OpenAI LLM.
    """
    vector_store = load_vector_store()
    if vector_store is None:
        raise ValueError(
            "No document database found. Please upload and process documents first."
        )

    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K_RESULTS},
    )

    prompt = PromptTemplate(
        template=QA_SYSTEM_PROMPT,
        input_variables=["context", "question"],
    )

    llm = get_llm()
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt},
    )

    return qa_chain


def ask_question(question: str) -> Dict[str, Any]:
    """
    Ask a question and get an answer based on the uploaded documents.
    """
    try:
        qa_chain = get_qa_chain()
        result = qa_chain.invoke({"query": question})

        sources = []
        seen = set()

        if "source_documents" in result:
            for doc in result["source_documents"]:
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
            "answer": result.get("result", "No answer generated."),
            "sources": sources,
        }

    except ValueError as e:
        return {"answer": str(e), "sources": []}
    except Exception as e:
        return {
            "answer": f"An error occurred while processing your question: {str(e)}",
            "sources": [],
        }
