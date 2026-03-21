"""
Configuration module for the Multimodal RAG application.
Loads Streamlit secrets and defines application constants.
"""

import os
import streamlit as st

# ── API Configuration ──────────────────────────────────────────────────────────
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")

# ── Model Configuration ────────────────────────────────────────────────────────
OPENAI_LLM_MODEL = "gpt-4o-mini"          # Cheapest GPT-4 class model
OPENAI_VISION_MODEL = "gpt-4o-mini"       # Supports vision, very affordable
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"  # Cheapest embedding model

# ── Chunking Configuration ─────────────────────────────────────────────────────
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# ── Retrieval Configuration ────────────────────────────────────────────────────
TOP_K_RESULTS = 5

# ── Storage Configuration ──────────────────────────────────────────────────────
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
TEMP_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")

# ── Supported File Types ───────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

# ── Prompts ────────────────────────────────────────────────────────────────────
IMAGE_DESCRIPTION_PROMPT = (
    "Explain this diagram/image in detail, including all visible components, "
    "relationships, labels, arrows, flow, and any text present. "
    "Provide a structured, comprehensive textual description."
)

QA_SYSTEM_PROMPT = """You are a helpful document assistant. Use the provided context from uploaded documents to help the user.

Rules:
1. Use ONLY the information from the provided context. Do not use outside knowledge.
2. If the context does not contain enough information, say: 
   "I don't have enough information in the uploaded documents to answer this question."
3. Always cite your sources by mentioning the file name and page/slide number when available.
4. You CAN generate questions, quizzes, true/false statements, summaries, or any other format the user requests — as long as the content is based on the provided context.
5. Format your response using proper Markdown:
   - Use **bold**, *italic*, bullet points, and numbered lists
   - For math equations, use LaTeX notation: $inline$ or $$block$$
   - Use headings (##, ###) to organize longer responses
   - Use tables when comparing information

Context:
{context}

User Request: {question}

Response:"""
