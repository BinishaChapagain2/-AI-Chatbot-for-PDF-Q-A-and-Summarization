# parser.py

from llama_parse import LlamaParse
from dotenv import load_dotenv
import os

load_dotenv()
LLAMA_PARSE_API_KEY = os.getenv("LLAMA_PARSE_API_KEY")

def parse_pdf_to_markdown(pdf_path: str, output_dir: str = "../data/parsed_md") -> str:
    """
    Parses a PDF using LlamaParse and saves it as Markdown.
    Returns path to the saved .md file.
    """
    if not LLAMA_PARSE_API_KEY:
        raise ValueError("LLAMA_PARSE_API_KEY not found in environment variables.")

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, os.path.basename(pdf_path).replace(".pdf", ".md"))

    if os.path.exists(output_file):
        print(f"✅ File {output_file} already exists. Skipping parsing.")
        return output_file

    print(f"🧠 Parsing PDF: {pdf_path}")
    parser = LlamaParse(
        api_key=LLAMA_PARSE_API_KEY,
        result_type="markdown",
        verbose=True,
        user_prompt="""
            Please extract all content including tables, images, lists, and headers 
            in clean and readable markdown format.
        """
    )

    docs = parser.load_data(pdf_path)

    with open(output_file, "w", encoding="utf-8") as f:
        for doc in docs:
            f.write(doc.text)
            f.write("\n\n---\n\n")

    print(f"✅ PDF successfully parsed and saved to {output_file}")
    return output_file