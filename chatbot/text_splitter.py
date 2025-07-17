# text_splitter.py

from langchain.text_splitter import RecursiveCharacterTextSplitter

def get_splitters():
    """
    Returns parent and child text splitters.
    """
    parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=400)
    return parent_splitter, child_splitter