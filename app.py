"""
Streamlit UI for the Multimodal Document QA (RAG) Application.
Provides file upload, document processing, and a chat interface.
"""

import streamlit as st

from config import OPENAI_API_KEY, SUPPORTED_EXTENSIONS
from ingestion import ingest_files, cleanup_temp_files
from embedding import create_vector_store, load_vector_store, clear_vector_store, get_document_count
from retrieval import ask_question


# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📚 Document QA Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Source card styling */
    .source-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 8px 0;
        font-size: 0.85rem;
    }
    
    .source-card .source-file {
        color: #e94560;
        font-weight: 600;
    }
    
    .source-card .source-location {
        color: #a8a8b3;
        font-size: 0.8rem;
    }
    
    /* Header styling */
    .app-header {
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }
    
    .app-header h1 {
        background: linear-gradient(120deg, #e94560, #0f3460, #533483);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 800;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-ready {
        background: #1a3a2a;
        color: #4ade80;
        border: 1px solid #166534;
    }
    
    .status-empty {
        background: #3a2a1a;
        color: #fbbf24;
        border: 1px solid #92400e;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%);
    }
    
    /* Chat messages */
    .stChatMessage {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Initialization ───────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

if "processing" not in st.session_state:
    st.session_state.processing = False


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📂 Document Upload")
    st.markdown("---")
    
    # API Key check
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        st.error("⚠️ **OPENAI_API_KEY** not set!\n\nPlease add your API key to the `.env` file.")
        st.code("OPENAI_API_KEY=sk-your_actual_key", language="bash")
        st.stop()
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload your documents",
        type=list(SUPPORTED_EXTENSIONS.keys()),
        accept_multiple_files=True,
        help="Supported: PDF, DOCX, PPTX, PNG, JPG, JPEG",
    )
    
    # Show uploaded files
    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)}** file(s) selected:")
        for f in uploaded_files:
            size_kb = f.size / 1024
            st.markdown(f"- `{f.name}` ({size_kb:.1f} KB)")
    
    st.markdown("---")
    
    # Process button
    col1, col2 = st.columns(2)
    
    with col1:
        process_btn = st.button(
            "🚀 Process",
            use_container_width=True,
            disabled=not uploaded_files,
            type="primary",
        )
    
    with col2:
        clear_btn = st.button(
            "🗑️ Clear DB",
            use_container_width=True,
            type="secondary",
        )
    
    st.markdown("---")
    
    # Database status
    chunk_count = get_document_count()
    if chunk_count > 0:
        st.markdown(
            f'<span class="status-badge status-ready">✅ Ready — {chunk_count} chunks</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="status-badge status-empty">⏳ No documents processed</span>',
            unsafe_allow_html=True,
        )
    
    # Show previously processed files
    if st.session_state.processed_files:
        st.markdown("**Processed files:**")
        for fname in st.session_state.processed_files:
            st.markdown(f"- ✅ `{fname}`")
    
    st.markdown("---")
    st.markdown(
        "<small>Built with LangChain + OpenAI + ChromaDB</small>",
        unsafe_allow_html=True,
    )


# ── Main Area ──────────────────────────────────────────────────────────────────

# Header
st.markdown(
    '<div class="app-header"><h1>📚 Document QA Assistant</h1>'
    '<p style="color: #a8a8b3;">Upload documents and ask questions — powered by multimodal AI</p></div>',
    unsafe_allow_html=True,
)

# ── Process Documents ──────────────────────────────────────────────────────────
if process_btn and uploaded_files:
    status_container = st.empty()
    progress_bar = st.progress(0)
    status_messages = []
    
    def update_status(msg: str):
        status_messages.append(msg)
        status_container.markdown(f"**{msg}**")
    
    with st.spinner("Processing documents..."):
        try:
            # Step 1: Ingest and chunk
            update_status("📄 Starting document ingestion...")
            progress_bar.progress(10)
            
            chunks = ingest_files(uploaded_files, status_callback=update_status)
            progress_bar.progress(60)
            
            if chunks:
                # Step 2: Create embeddings and store
                update_status(f"🧮 Generating embeddings for {len(chunks)} chunks...")
                progress_bar.progress(70)
                
                vector_store = create_vector_store(chunks)
                progress_bar.progress(90)
                
                # Step 3: Cleanup
                cleanup_temp_files()
                progress_bar.progress(100)
                
                # Update session state
                st.session_state.processed_files = [f.name for f in uploaded_files]
                
                update_status(
                    f"✅ Done! Processed {len(uploaded_files)} file(s) → "
                    f"{len(chunks)} chunks stored in vector database."
                )
                st.balloons()
            else:
                update_status("⚠️ No content could be extracted from the uploaded files.")
                
        except Exception as e:
            st.error(f"❌ Error during processing: {str(e)}")
            cleanup_temp_files()
    
    # Clear progress bar after a moment
    progress_bar.empty()
    st.rerun()

# ── Clear Database ─────────────────────────────────────────────────────────────
if clear_btn:
    clear_vector_store()
    cleanup_temp_files()
    st.session_state.messages = []
    st.session_state.processed_files = []
    st.success("🗑️ Database cleared! You can now upload new documents.")
    st.rerun()

# ── Chat Interface ─────────────────────────────────────────────────────────────
# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)
        
        # Show sources for assistant messages
        if message["role"] == "assistant" and "sources" in message and message["sources"]:
            with st.expander(f"📎 Sources ({len(message['sources'])} references)", expanded=False):
                for src in message["sources"]:
                    location = ""
                    if "page" in src:
                        location = f"Page {src['page']}"
                    elif "slide" in src:
                        location = f"Slide {src['slide']}"
                    
                    st.markdown(f"""
**📄 {src['file']}** {f'— {location}' if location else ''} `[{src['type'].upper()}]`

> {src['snippet']}
""")

# Chat input
if prompt := st.chat_input("Ask a question about your documents..."):
    # Check if documents are processed
    if get_document_count() == 0:
        st.warning("⚠️ Please upload and process documents before asking questions.")
    else:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = ask_question(prompt)
            
            st.markdown(result["answer"], unsafe_allow_html=True)
            
            # Show sources
            if result["sources"]:
                with st.expander(
                    f"📎 Sources ({len(result['sources'])} references)", expanded=False
                ):
                    for src in result["sources"]:
                        location = ""
                        if "page" in src:
                            location = f"Page {src['page']}"
                        elif "slide" in src:
                            location = f"Slide {src['slide']}"
                        
                        st.markdown(f"""
**📄 {src['file']}** {f'— {location}' if location else ''} `[{src['type'].upper()}]`

> {src['snippet']}
""")
        
        # Save assistant message with sources
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        })
