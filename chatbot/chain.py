# chatbot/chain.py

from langchain.schema.runnable import RunnableLambda, RunnableSequence
from langchain.schema.runnable import RunnableBranch
from chatbot.prompt import get_qa_prompt, get_summarize_prompt
from chatbot.llm import get_llm_and_parser

qa_prompt = get_qa_prompt()
summarize_prompt = get_summarize_prompt()
model, parser = get_llm_and_parser()

def format_docs(docs):
    return "\n\n".join([doc.page_content for doc in docs])

# Function to retrieve context
def get_context_retriever(retriever):
    return RunnableLambda(lambda x: {
        "context": retriever.get_relevant_documents(x.get("question", "")),
        **x
    })

# Formatter for QA Chain
def get_chat_formatter():
    return RunnableLambda(lambda x: {
        "context": format_docs(x["context"]),
        "question": x["question"]
    })

# Formatter for Summarize Chain
def get_summarize_formatter():
    return RunnableLambda(lambda x: {
        "context": format_docs(x["context"])
    })

def build_rag_chain(retriever):
    context_retriever = get_context_retriever(retriever)
    chat_formatter = get_chat_formatter()
    summarize_formatter = get_summarize_formatter()

    chat_chain = RunnableSequence(
        context_retriever,
        chat_formatter,
        qa_prompt,
        model,
        parser
    )

    summarize_chain = RunnableSequence(
        context_retriever,
        summarize_formatter,
        summarize_prompt,
        model,
        parser
    )

    rag_mode_chain = RunnableBranch(
        (lambda x: x.get("mode", "").lower() == "chat", chat_chain),
        (lambda x: x.get("mode", "").lower() == "summarize", summarize_chain),
        RunnableLambda(lambda x: "❌ Invalid mode selected. Choose 'chat' or 'summarize'.")
    )

    return rag_mode_chain