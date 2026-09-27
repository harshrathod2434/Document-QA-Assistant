"""FastAPI service for the Lumen document intelligence frontend."""

import json
import os
import re
from pathlib import Path
from typing import List, Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import OPENAI_API_KEY, SUPPORTED_EXTENSIONS, TEMP_UPLOAD_DIR
from embedding import clear_vector_store, create_vector_store, get_document_count
from ingestion import cleanup_temp_files, ingest_paths
from retrieval import ask_question, summarize_documents


BASE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BASE_DIR / "document_manifest.json"
MAX_FILE_SIZE = 25 * 1024 * 1024

app = FastAPI(
    title="Lumen Document Intelligence API",
    description="Multimodal extraction, vector indexing, and grounded retrieval.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    mode: Literal["auto", "search", "summary"] = "auto"


def small_talk_reply(question: str):
    normalized = re.sub(r"[^a-z\s']", " ", question.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if re.fullmatch(r"hi|hello|hey|hiya|yo|good morning|good afternoon|good evening", normalized):
        return "Hi! Upload a document whenever you're ready, or ask what I can help you do."
    if re.fullmatch(r"thanks|thank you|thx|great|cool|okay|ok", normalized):
        return "You're welcome. Send the next question whenever you're ready."
    if re.fullmatch(r"who are you|what can you do|help", normalized):
        return "I'm Lumen, a document research assistant. I can summarise complete documents, answer focused questions with evidence, compare ideas, and create notes or quizzes."
    return None


def is_summary_request(question: str) -> bool:
    return bool(re.search(
        r"\b(summarize|summarise|summary|overview|recap|key findings|executive brief)\b",
        question,
        re.IGNORECASE,
    ))


def read_manifest() -> List[dict]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def write_manifest(documents: List[dict]) -> None:
    MANIFEST_PATH.write_text(json.dumps(documents, indent=2), encoding="utf-8")


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(name).name).strip()
    return cleaned or "document"


@app.get("/health")
def health():
    return {
        "status": "ok",
        "configured": bool(OPENAI_API_KEY),
        "chunks": get_document_count(),
        "documents": read_manifest(),
    }


@app.post("/documents/process")
async def process_documents(files: List[UploadFile] = File(...)):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="Add OPENAI_API_KEY to langchain-portfolio/.env before indexing documents.")
    if not files:
        raise HTTPException(status_code=400, detail="Choose at least one document.")

    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    saved_paths: List[str] = []
    uploaded_meta: List[dict] = []
    try:
        for upload in files:
            filename = safe_filename(upload.filename or "document")
            extension = Path(filename).suffix.lower().lstrip(".")
            if extension not in SUPPORTED_EXTENSIONS:
                raise HTTPException(status_code=415, detail=f"{filename} is not a supported file type.")
            content = await upload.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"{filename} is larger than the 25 MB limit.")
            destination = Path(TEMP_UPLOAD_DIR) / filename
            destination.write_bytes(content)
            saved_paths.append(str(destination))
            uploaded_meta.append({"name": filename, "type": extension, "size": len(content)})

        chunks = ingest_paths(saved_paths)
        if not chunks:
            raise HTTPException(status_code=422, detail="No readable content was found in the uploaded documents.")
        create_vector_store(chunks)

        per_file = {}
        for chunk in chunks:
            source = chunk.metadata.get("source", "")
            per_file[source] = per_file.get(source, 0) + 1
        for item in uploaded_meta:
            item["chunks"] = per_file.get(item["name"], 0)

        documents = read_manifest()
        existing_names = {item.get("name") for item in uploaded_meta}
        documents = [item for item in documents if item.get("name") not in existing_names] + uploaded_meta
        write_manifest(documents)
        return {"documents": documents, "chunks": get_document_count()}
    finally:
        cleanup_temp_files()


@app.post("/chat")
def chat(request: ChatRequest):
    conversational_reply = small_talk_reply(request.question)
    if conversational_reply:
        return {"answer": conversational_reply, "sources": []}
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="The OpenAI API key is not configured.")
    if get_document_count() == 0:
        raise HTTPException(status_code=409, detail="Add and index a document before asking a question.")
    question = request.question.strip()
    summary_mode = request.mode == "summary" or (request.mode == "auto" and is_summary_request(question))
    result = summarize_documents(question) if summary_mode else ask_question(question)
    if result["answer"].startswith("An error occurred"):
        raise HTTPException(status_code=502, detail=result["answer"])
    return result


@app.delete("/documents")
def delete_documents():
    clear_vector_store()
    cleanup_temp_files()
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
    return {"status": "cleared", "documents": [], "chunks": 0}
