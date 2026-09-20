"""
Configuration module for the Multimodal RAG application.
Loads environment configuration and defines application constants.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── API Configuration ──────────────────────────────────────────────────────────
load_dotenv(Path(__file__).with_name(".env"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

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
   - Use headings (##, ###) to organize longer responses
   - Use tables when comparing information

6. Mathematical Formatting Rules (VERY IMPORTANT):
   - Every mathematical expression MUST be written in valid LaTeX.
   - Every inline mathematical expression MUST be wrapped in $...$.
   - Every standalone equation MUST be wrapped in $$...$$.
   - Never output raw LaTeX commands in plain text.
   - Never write expressions like:
       (\alpha^2 \left( ... \right))
     or
       [ E = \int ... ]
   - Instead write:
       $\alpha^2 \left( ... \right)$
     and
       $$
       E = \int ...
       $$
   - If a formula appears in the source document, convert it to properly formatted LaTeX before including it in the response.

Context:
{context}

User Request: {question}

Response:"""
