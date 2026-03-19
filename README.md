# 📚 Document QA Assistant

A multimodal document question-answering web application (RAG system) built with **LangChain**, **Streamlit**, and **OpenAI**.

Upload documents (PDF, DOCX, PPTX, images) and ask questions — the system answers using both text and diagram understanding.

## ✨ Features

- **Multi-format support**: PDF, DOCX, PPTX, PNG, JPG
- **Multimodal understanding**: Extracts and interprets diagrams/images using GPT-4o-mini Vision
- **RAG pipeline**: LangChain chunking → OpenAI embeddings → ChromaDB vector store → Retrieval QA
- **Persistent storage**: ChromaDB saves embeddings locally for reuse
- **Source citations**: Answers include file name, page/slide references
- **Flexible queries**: Ask questions, generate quizzes, true/false statements, summaries

## 🚀 Setup

```bash
# 1. Clone the repo
git clone https://github.com/harshrathod2434/Document-QA-Assistant.git
cd Document-QA-Assistant

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your OpenAI API key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 5. Run the app
streamlit run app.py
```

The app will open at **http://localhost:8501**.

## 📂 Project Structure

```
├── app.py              # Streamlit UI
├── config.py           # Configuration & constants
├── extraction.py       # Text & image extraction (PDF, DOCX, PPTX)
├── multimodal.py       # OpenAI Vision: image → text description
├── ingestion.py        # Pipeline: extract → describe → chunk
├── embedding.py        # OpenAI embeddings + ChromaDB storage
├── retrieval.py        # RetrievalQA chain with source references
├── requirements.txt    # Python dependencies
└── .env                # API key (not tracked by git)
```

## 🔧 Configuration

| Setting | Value | File |
|---|---|---|
| LLM Model | `gpt-4o-mini` | `config.py` |
| Vision Model | `gpt-4o-mini` | `config.py` |
| Embedding Model | `text-embedding-3-small` | `config.py` |
| Chunk Size | 500 tokens | `config.py` |
| Chunk Overlap | 100 tokens | `config.py` |
| Top-K Results | 5 | `config.py` |

## 📝 Usage

1. **Upload** documents via the sidebar
2. Click **🚀 Process** to extract text, analyze images, and build the vector database
3. **Ask questions** in the chat — the system answers based on your documents
4. Click **🗑️ Clear DB** to reset and upload new documents
