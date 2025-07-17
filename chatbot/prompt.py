from langchain_core.prompts import PromptTemplate

def get_qa_prompt():
    return PromptTemplate.from_template("""
You are an AI assistant that answers questions based on provided document content.
Use the following context to answer the question accurately.
If the question is unrelated to the context, respond with:
"sorry, I don't know related to this topic"

Context:
{context}

Question:
{question}

Answer:
""")

def get_summarize_prompt():
    return PromptTemplate.from_template("""
You are an AI assistant that creates comprehensive document summaries.

Based on the following context from the document, create a detailed and well-structured summary that covers:
-Introduction  on topic                                        
- Main topics and key points
- Important findings or conclusions
- Relevant details and insights

Use the following context to generate the summary.  
                                        

Context:
{context}

Please provide a comprehensive summary:
""")