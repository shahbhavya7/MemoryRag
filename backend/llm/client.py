import os

from langchain_openai import ChatOpenAI

# Both Groq and OpenRouter expose OpenAI-compatible APIs, so one ChatOpenAI
# client works for either — we just point it at a different base URL and
# supply the matching API key. Add more OpenAI-compatible providers here.
PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "meta-llama/llama-3.3-70b-instruct",
}


def get_llm() -> ChatOpenAI:
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider)
    base_url = PROVIDER_BASE_URLS.get(provider)

    if base_url is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Supported: {', '.join(PROVIDER_BASE_URLS)}."
        )
    if not api_key:
        raise ValueError("LLM_API_KEY is not set. Add it to your .env (see .env.example).")

    # temperature=0 keeps answers as deterministic/grounded as possible, which
    # is what we want for RAG — creativity here just means more hallucination.
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0)
