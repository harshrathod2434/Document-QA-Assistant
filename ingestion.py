"""
Ingestion module: orchestrates the full pipeline from file upload
to chunked LangChain Documents ready for embedding.

Pipeline: file → extraction → multimodal image description → combine → chunk
"""

import os
from typing import List, Callable, Optional

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP, TEMP_UPLOAD_DIR
from extraction import extract_content
from multimodal import process_images


def save_uploaded_file(uploaded_file) -> str:
    """
    Save a Streamlit UploadedFile to the temp directory.
    Returns the path to the saved file.
    """
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(TEMP_UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def cleanup_temp_files():
    """Remove all files in the temporary upload directory."""
    if os.path.exists(TEMP_UPLOAD_DIR):
        for f in os.listdir(TEMP_UPLOAD_DIR):
            file_path = os.path.join(TEMP_UPLOAD_DIR, f)
            try:
                os.remove(file_path)
            except OSError:
                pass


def process_single_file(
    file_path: str,
    status_callback: Optional[Callable[[str], None]] = None,
) -> List[Document]:
    """
    Process a single file through the full ingestion pipeline.
    
    Args:
        file_path: Path to the file to process
        status_callback: Optional function to report processing status
        
    Returns:
        List of LangChain Document objects ready for embedding
    """
    filename = os.path.basename(file_path)
    documents = []
    
    # Step 1: Extract text and images
    if status_callback:
        status_callback(f"📄 Extracting content from {filename}...")
    
    extracted_pages = extract_content(file_path)
    
    # Step 2: Process images through Gemini Vision
    for page_data in extracted_pages:
        combined_text_parts = []
        
        # Add the extracted text
        if page_data["text"]:
            combined_text_parts.append(page_data["text"])
        
        # Process images and add descriptions
        if page_data["images"]:
            num_images = len(page_data["images"])
            if status_callback:
                location = _format_location(page_data["metadata"])
                status_callback(
                    f"🖼️ Analyzing {num_images} image(s) from {filename} {location}..."
                )
            
            descriptions = process_images(page_data["images"])
            
            for img_info, desc in zip(page_data["images"], descriptions):
                combined_text_parts.append(
                    f"\n[Image Description - {img_info.get('label', 'Image')}]\n{desc}\n"
                )
        
        # Create the combined text
        combined_text = "\n\n".join(combined_text_parts).strip()
        
        if combined_text:
            # Build metadata
            metadata = {
                "source": page_data["metadata"].get("source", filename),
                "file_type": page_data["metadata"].get("file_type", "unknown"),
            }
            
            # Add page or slide number
            if "page" in page_data["metadata"]:
                metadata["page"] = page_data["metadata"]["page"]
            if "slide" in page_data["metadata"]:
                metadata["slide"] = page_data["metadata"]["slide"]
            if "total_pages" in page_data["metadata"]:
                metadata["total_pages"] = page_data["metadata"]["total_pages"]
            if "total_slides" in page_data["metadata"]:
                metadata["total_slides"] = page_data["metadata"]["total_slides"]
            
            documents.append(Document(page_content=combined_text, metadata=metadata))
    
    return documents


def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Split documents into smaller chunks for embedding.
    
    Args:
        documents: List of LangChain Documents
        
    Returns:
        List of chunked Documents with preserved metadata
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    
    chunks = text_splitter.split_documents(documents)
    return chunks


def ingest_files(
    uploaded_files: list,
    status_callback: Optional[Callable[[str], None]] = None,
) -> List[Document]:
    """
    Full ingestion pipeline: save files → extract → describe images → chunk.
    
    Args:
        uploaded_files: List of Streamlit UploadedFile objects
        status_callback: Optional function to report processing status
        
    Returns:
        List of chunked LangChain Document objects
    """
    all_documents = []
    
    for i, uploaded_file in enumerate(uploaded_files, 1):
        if status_callback:
            status_callback(
                f"📂 Processing file {i}/{len(uploaded_files)}: {uploaded_file.name}"
            )
        
        # Save to temp
        file_path = save_uploaded_file(uploaded_file)
        
        try:
            # Process the file
            docs = process_single_file(file_path, status_callback)
            all_documents.extend(docs)
        except Exception as e:
            if status_callback:
                status_callback(f"⚠️ Error processing {uploaded_file.name}: {str(e)}")
    
    # Chunk all documents
    if all_documents:
        if status_callback:
            status_callback(f"✂️ Splitting {len(all_documents)} document sections into chunks...")
        chunked = chunk_documents(all_documents)
        if status_callback:
            status_callback(f"✅ Created {len(chunked)} chunks from {len(uploaded_files)} file(s)")
        return chunked
    
    return []


def _format_location(metadata: dict) -> str:
    """Format a human-readable location string from metadata."""
    if "slide" in metadata:
        return f"(slide {metadata['slide']})"
    elif "page" in metadata and metadata["page"] > 0:
        return f"(page {metadata['page']})"
    return ""
