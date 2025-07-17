from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryByteStore
from chatbot.text_splitter import get_splitters

def build_parent_retriever(vectorstore, docs):
    parent_splitter, child_splitter = get_splitters()

    retriever = ParentDocumentRetriever(
        vectorstore=vectorstore,
        docstore=InMemoryByteStore(),
        child_splitter=child_splitter,
        parent_splitter=parent_splitter
    )

    retriever.add_documents(docs)
    return retriever