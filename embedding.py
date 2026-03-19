"""
Embedding module: generates embeddings using OpenAI and
stores/retrieves them from a persistent ChromaDB vector database.
"""

import os
import shutil
from typing import List, Optional

from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, CHROMA_PERSIST_DIR


def get_embedding_function() -> OpenAIEmbeddings:
    """Create and return the OpenAI embedding function."""
    return OpenAIEmbeddings(
        model=OPENAI_EMBEDDING_MODEL,
        openai_api_key=OPENAI_API_KEY,
    )


def create_vector_store(documents: List[Document]) -> Chroma:
    """
    Create a new ChromaDB vector store from the given documents.
    Persists the database to disk for reuse.
    """
    embedding_fn = get_embedding_function()

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embedding_fn,
        persist_directory=CHROMA_PERSIST_DIR,
        collection_name="document_qa",
    )

    return vector_store


def load_vector_store() -> Optional[Chroma]:
    """Load an existing ChromaDB vector store from disk."""
    if not os.path.exists(CHROMA_PERSIST_DIR):
        return None

    try:
        embedding_fn = get_embedding_function()
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embedding_fn,
            collection_name="document_qa",
        )

        if vector_store._collection.count() == 0:
            return None

        return vector_store
    except Exception:
        return None


def clear_vector_store():
    """Delete the persistent ChromaDB database to start fresh."""
    if os.path.exists(CHROMA_PERSIST_DIR):
        shutil.rmtree(CHROMA_PERSIST_DIR)


def get_document_count() -> int:
    """Return the number of document chunks stored in the vector database."""
    try:
        vector_store = load_vector_store()
        if vector_store:
            return vector_store._collection.count()
        return 0
    except Exception:
        return 0
