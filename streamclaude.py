import streamlit as st
import os
import tempfile
from llama_parse import LlamaParse
from dotenv import load_dotenv
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryByteStore
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableLambda, RunnableSequence, RunnableBranch

# Load environment variables
load_dotenv()

# Initialize session state
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'retriever' not in st.session_state:
    st.session_state.retriever = None
if 'rag_chain' not in st.session_state:
    st.session_state.rag_chain = None
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []

def parse_pdf(pdf_path, output_dir, pdf_name):
    """Parse PDF using LlamaParse and save as markdown"""
    API_KEY = os.getenv("LLAMA_PARSE_API_KEY")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{pdf_name}.md")

    if os.path.exists(output_file):
        st.info(f"Markdown file already exists at {output_file}. Skipping parsing.")
        docs = []  # Placeholder; will be loaded later
        with open(output_file, "r", encoding="utf-8") as f:
            combined_text = f.read()
        docs.append(Document(page_content=combined_text))
        return output_file, docs

    parser = LlamaParse(
        api_key=API_KEY,
        result_type="markdown",
        verbose=True,
        parsing_instruction="""
            Please extract all content including tables, images, lists, and headers 
            in clean and readable markdown format.
        """
    )

    docs = parser.load_data(pdf_path)

    with open(output_file, "w", encoding="utf-8") as f:
        for i, doc in enumerate(docs):
            f.write(doc.text)  # Use .text attribute to get string content
            f.write("\n\n---\n\n")  # Separator between pages/docs

    st.success(f"✅ PDF successfully parsed and saved to {output_file}")
    return output_file, docs


def create_vector_store(docs, pdf_name):
    """Create vector store from parsed documents"""
    lc_docs = [Document(page_content=doc.text if hasattr(doc, "text") else doc.page_content) for doc in docs]

    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)

    parent_chunks = parent_splitter.split_documents(lc_docs)
    child_chunk = child_splitter.split_documents(lc_docs)

    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    persist_directory = f"data/chroma_db_{pdf_name}"
    os.makedirs("data", exist_ok=True)

    vector_store = Chroma(
        collection_name="child_chunks",
        embedding_function=embedding_model,
        persist_directory=persist_directory
    )

    vector_store.add_documents(child_chunk)

    store = InMemoryByteStore()
    retriever = ParentDocumentRetriever(
        vectorstore=vector_store,
        docstore=store,
        child_splitter=child_splitter,
        parent_splitter=parent_splitter
    )

    retriever.add_documents(parent_chunks)

    return vector_store, retriever


def setup_rag_chain(retriever):
    """Setup RAG chain with prompts and model"""

    prompt = PromptTemplate(
        template="""
You are an AI assistant that answers questions based on provided document content.

Use the following context from the document to answer the question accurately.

If the question is unrelated to the context, respond with:
"sorry, I don't know related to this topic"

Context:
{context}

Question:
{question}

Answer:
""",
        input_variables=["context", "question"]
    )

    summarize_prompt = PromptTemplate(
        template="""You are an AI assistant that summarizes documents.
Use the following context to create a concise summary.  
Context:{context}
Summary:""",
        input_variables=["context"]
    )

    api_key = os.getenv("GOOGLE_API_KEY")  # Ensure correct variable name
    model = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,
        google_api_key=api_key
    )

    parser = StrOutputParser()

    context_retriever = RunnableLambda(
        lambda x: {"context": retriever.get_relevant_documents(x.get("question", "")), **x}
    )

    chat_formatter = RunnableLambda(lambda x: {
        "context": "\n\n".join([doc.page_content for doc in x["context"]]),
        "question": x["question"]
    })

    summarize_formatter = RunnableLambda(lambda x: {
        "context": "\n\n".join([doc.page_content for doc in x["context"]])
    })

    chat_chain = RunnableSequence(context_retriever, chat_formatter, prompt, model, parser)
    summarize_chain = RunnableSequence(context_retriever, summarize_formatter, summarize_prompt, model, parser)

    rag_mode_chain = RunnableBranch(
        (lambda x: x.get("mode", "").lower() == "chat", chat_chain),
        (lambda x: x.get("mode", "").lower() == "summarize", summarize_chain),
        RunnableLambda(lambda x: "❌ Invalid mode selected. Choose 'chat' or 'summarize'.")
    )

    return rag_mode_chain


def main():
    st.set_page_config(page_title="PDF RAG Assistant", page_icon="📄", layout="wide")
    st.title("📄 PDF RAG Assistant")
    st.markdown("Upload PDF files and chat with them using AI!")

    with st.sidebar:
        st.header("📁 Upload PDF")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", help="Upload a PDF file to process and chat with")

        if uploaded_file is not None:
            pdf_name = os.path.splitext(uploaded_file.name)[0]
            if pdf_name not in st.session_state.processed_files:
                with st.spinner("Processing PDF..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name

                    try:
                        output_dir = "data/parsed_md"
                        markdown_file, docs = parse_pdf(tmp_path, output_dir, pdf_name)
                        vector_store, retriever = create_vector_store(docs, pdf_name)
                        rag_chain = setup_rag_chain(retriever)

                        st.session_state.vector_store = vector_store
                        st.session_state.retriever = retriever
                        st.session_state.rag_chain = rag_chain
                        st.session_state.processed_files.append(pdf_name)

                        st.success(f"✅ Successfully processed: {uploaded_file.name}")
                        st.info(f"📄 Processed file: {uploaded_file.name}")
                        st.info(f"📝 Markdown saved to: {markdown_file}")
                        st.info(f"🗄️ Vector DB: data/chroma_db_{pdf_name}")

                    except Exception as e:
                        st.error(f"Error processing PDF: {str(e)}")
                    finally:
                        os.unlink(tmp_path)
            else:
                st.info(f"📄 File already processed: {uploaded_file.name}")

        if st.session_state.processed_files:
            st.header("📋 Processed Files")
            for file in st.session_state.processed_files:
                st.text(f"• {file}")

    if st.session_state.rag_chain is not None:
        st.header("💬 Chat with your PDF")
        mode = st.radio("Select mode:", ["chat", "summarize"], horizontal=True)

        if mode == "chat":
            user_question = st.text_input("Ask a question about your PDF:", placeholder="e.g., What is the main topic?")
            if user_question:
                with st.spinner("Thinking..."):
                    try:
                        response = st.session_state.rag_chain.invoke({
                            "mode": "chat",
                            "question": user_question
                        })
                        st.markdown("### 🤖 Answer:")
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")

        elif mode == "summarize":
            if st.button("📋 Generate Summary", type="primary"):
                with st.spinner("Generating summary..."):
                    try:
                        response = st.session_state.rag_chain.invoke({
                            "mode": "summarize",
                            "question": "Summarize the document"
                        })
                        st.markdown("### 📋 Document Summary:")
                        st.markdown(response)
                    except Exception as e:
                        st.error(f"Error generating summary: {str(e)}")
    else:
        st.info("👆 Please upload a PDF file to get started!")
        st.markdown("### 🚀 How to use:")
        st.markdown("""
        1. **Upload PDF**: Use the sidebar to upload your PDF file
        2. **Wait for processing**: The app will parse the PDF and create a vector database
        3. **Chat or Summarize**: Choose your preferred mode and interact with the document
        """)


if __name__ == "__main__":
    main()