from langchain_huggingface import HuggingFaceEmbeddings

def load_embedding_model():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")