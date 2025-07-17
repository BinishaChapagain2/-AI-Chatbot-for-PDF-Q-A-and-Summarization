# file_utils.py

import os
from langchain.docstore.document import Document

def save_uploaded_file(uploaded_file, save_path):
    """
    Saves an uploaded PDF file to disk.
    """
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path

def load_markdown_file(file_path):
    """
    Reads a Markdown (.md) file and returns its text content.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
    
SEPARATOR = "\n\n---\n\n"

def convert_to_langchain_docs(md_text):
    """
    Converts Markdown text into a list of LangChain Document objects.
    Splits by SEPARATOR used during parsing.
    """
    chunks = md_text.split(SEPARATOR)
    return [Document(page_content=chunk.strip()) for chunk in chunks if chunk.strip()]    