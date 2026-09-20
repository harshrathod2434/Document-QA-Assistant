# Lumen — Grounded Document Intelligence

A portfolio-grade multimodal RAG workspace with a custom Next.js interface and a FastAPI/LangChain service. Upload reports, papers, presentations, or images; ask natural-language questions; and inspect the passages used to produce every answer.

![Next.js](https://img.shields.io/badge/Next.js-16-111111?logo=nextdotjs)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-05998b?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-RAG-1c3c3c)
![OpenAI](https://img.shields.io/badge/OpenAI-Multimodal-412991?logo=openai)

## Product highlights

- Bespoke responsive interface built with React, TypeScript, and accessible controls
- Drag-and-drop source library for PDF, DOCX, PPTX, PNG, and JPG files
- Multimodal extraction for text, tables, diagrams, and embedded imagery
- LangChain retrieval with OpenAI embeddings and persistent ChromaDB storage
- Grounded answers with page/slide citations and a dedicated evidence drawer
- Optimistic upload feedback, useful empty/loading/error states, and mobile navigation
- API boundary that keeps secrets and document processing out of the browser

## Architecture

```text
Next.js client
  ├─ document library + upload experience
  ├─ research conversation UI
  └─ citation/evidence explorer
              │ REST
FastAPI service
  ├─ PyMuPDF / python-docx / python-pptx extraction
  ├─ OpenAI vision descriptions
  ├─ LangChain chunking + embeddings
  └─ ChromaDB retrieval + grounded generation
```

## Run locally

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your OpenAI key to .env
uvicorn server:app --reload --port 8000
```

### Frontend

In a second terminal:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Set `NEXT_PUBLIC_API_URL` if the API is not available at `http://127.0.0.1:8000`.

## Deployment

- Deploy the Next.js frontend to Vercel with `NEXT_PUBLIC_API_URL` set to the public API URL.
- Deploy the FastAPI service to Render/Railway using:
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- Configure `OPENAI_API_KEY` and `ALLOWED_ORIGINS` on the backend host.
- Use persistent storage or a managed vector database for production deployments.

The original Streamlit interface remains in `app.py` as a legacy comparison; `server.py` powers the custom frontend.
