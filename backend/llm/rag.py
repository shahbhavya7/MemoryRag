from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.llm.client import get_llm

# The system message is what keeps answers *grounded*: we explicitly tell the
# model to use only the retrieved context and to admit when the answer isn't
# there, instead of guessing from its own training knowledge.
_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant for the MemoryRAG project. "
            "Answer the user's question using ONLY the context below. "
            "If the answer is not in the context, say you don't know based on the "
            "available documents — do not make anything up.",
        ),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


def answer_with_context(question: str, chunks: list[str]) -> str:
    # This is the "chain" in the RAG sense: prompt -> LLM -> plain-text output.
    # LangChain's `|` operator wires these three steps into one callable.
    chain = _PROMPT | get_llm() | StrOutputParser()
    context = "\n\n---\n\n".join(chunks) if chunks else "(no relevant documents found)"
    return chain.invoke({"context": context, "question": question})
