import streamlit as st
import os
from langchain.docstore.document import Document

# Local imports
from parser.pdf_parser import parse_pdf_to_markdown
from chatbot.text_splitter import get_splitters
from chatbot.embedding import load_embedding_model
from chatbot.vector_store import build_vector_store
from chatbot.retriever import build_parent_retriever
from chatbot.chain import build_rag_chain
from utils.file_utils import save_uploaded_file, load_markdown_file, convert_to_langchain_docs

# Set up directories
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(CURRENT_DIR, "data", "input_pdf")
MD_DIR = os.path.join(CURRENT_DIR, "data", "parsed_md")

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(MD_DIR, exist_ok=True)

# Streamlit UI
st.set_page_config(page_title="PDF InsightBot", page_icon="📄")
st.title("📄 PDF InsightBot")

# Sidebar: Upload PDF
with st.sidebar:
    st.header("📂 Upload PDF")
    uploaded_file = st.file_uploader("Upload a single PDF", type="pdf", accept_multiple_files=False)

if uploaded_file is not None:
    # Generate a unique ID for this file
    file_key = uploaded_file.name.replace(".pdf", "").replace(" ", "_")
    
    # If file changed, clear only RAG-related session_state keys
    if 'last_uploaded_file_key' not in st.session_state or st.session_state.last_uploaded_file_key != file_key:
        for key in ['retriever', 'rag_chain']:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.last_uploaded_file_key = file_key

    st.sidebar.success(f"📁 Uploaded: `{uploaded_file.name}`")

    pdf_path = os.path.join(PDF_DIR, uploaded_file.name)
    md_path = os.path.join(MD_DIR, uploaded_file.name.replace(".pdf", ".md"))

    # Save PDF
    if not os.path.exists(pdf_path):
        save_uploaded_file(uploaded_file, pdf_path)
        st.sidebar.success(f"✅ Saved PDF: `{uploaded_file.name}`")

    # Parse PDF to Markdown
    if not os.path.exists(md_path):
        with st.spinner(f"🧠 Parsing: {uploaded_file.name}..."):
            parse_pdf_to_markdown(pdf_path, MD_DIR)
            if os.path.exists(md_path):
                st.sidebar.success(f"📄 Parsed: `{uploaded_file.name}.md`")

    # Load Markdown and convert to LangChain Docs
    try:
        md_text = load_markdown_file(md_path)
        lc_docs = convert_to_langchain_docs(md_text)
    except Exception as e:
        st.error(f"❌ Could not load markdown file: {e}")
        st.stop()

    # Load embedding model
    embedding_model = load_embedding_model()

    # Unique ChromaDB path per file
    CHROMA_DIR = os.path.join(CURRENT_DIR, "data", "chroma_db", file_key)
    os.makedirs(CHROMA_DIR, exist_ok=True)

    # Always build or load vector store
    vectorstore = build_vector_store(
        docs=lc_docs,
        persist_dir=CHROMA_DIR,
        embedding_model=embedding_model
    )

    # Build retriever and RAG chain if not in session
    if "retriever" not in st.session_state:
        st.session_state.retriever = build_parent_retriever(vectorstore, lc_docs)

    if "rag_chain" not in st.session_state:
        st.session_state.rag_chain = build_rag_chain(st.session_state.retriever)

    # Chat or Summarize Mode
    st.header("💬 Ask or Summarize")
    mode = st.radio("Choose mode", ["Chat", "Summarize"])

    if mode == "Chat":
        user_query = st.text_input("Ask a question about the document:")
        if st.button("🧠 Get Answer"):
            if "rag_chain" in st.session_state:
                with st.spinner("🔍 Retrieving context and generating answer..."):
                    result = st.session_state.rag_chain.invoke({
                        "mode": "chat",
                        "question": user_query
                    })
                    st.markdown("### 🤖 Answer:")
                    st.write(result)
            else:
                st.warning("⚠️ Please re-upload the file to refresh the context.")

    else:
        if st.button("🧾 Generate Summary"):
            if "rag_chain" in st.session_state:
                with st.spinner("📝 Generating summary..."):
                    result = st.session_state.rag_chain.invoke({
                        "mode": "summarize",
                        "question": "Summarize the document"
                    })
                    st.markdown("### 📚 Summary:")
                    st.write(result)
            else:
                st.warning("⚠️ Please re-upload the file to refresh the context.")

else:
    st.info("👆 Please upload a PDF file to begin.")