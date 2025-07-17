# chatbot/vector_store.py

from langchain_community.vectorstores import Chroma

def build_vector_store(docs, persist_dir="../data/chroma_db", embedding_model=None):
    """
    Builds or loads a Chroma vector store with the given documents and embedding model.
    """
    if embedding_model is None:
        from chatbot.embedding import load_embedding_model
        embedding_model = load_embedding_model()

    vectorstore = Chroma(
        collection_name="child_chunks",
        embedding_function=embedding_model,
        persist_directory=persist_dir
    )

    # Only add documents if they're not already in the store
    vectorstore.add_documents(docs)
    vectorstore.persist()

    return vectorstore