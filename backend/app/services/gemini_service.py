"""
Wraps the Gemini call using the current `google-genai` SDK (the older
`google-generativeai` package is deprecated and no longer receiving
updates — worth knowing this if you see the old package referenced
anywhere online, it's outdated advice now).

The prompt is deliberately strict about grounding — we want the model to
say "I don't know" rather than hallucinate when the retrieved chunks
don't actually answer the question. This is the core difference between
a RAG app and a generic chatbot.
"""
import logging

from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.core.config import settings

logger = logging.getLogger("documind")

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


SYSTEM_PROMPT = """You are a document assistant. Answer the user's question using ONLY the context provided below.

Rules:
- If the answer is not contained in the context, say "I don't have enough information in the uploaded documents to answer that" — do NOT guess or use outside knowledge.
- Keep answers concise and directly grounded in the context.
- Do not mention "the context" or "the chunks" in your answer — just answer naturally as if you'd read the documents.
"""


def build_prompt(question: str, context_chunks: list[str]) -> str:
    context_block = "\n\n---\n\n".join(context_chunks) if context_chunks else "(no relevant context found)"
    return f"{SYSTEM_PROMPT}\n\nContext:\n{context_block}\n\nQuestion: {question}\n\nAnswer:"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),  # 1s, then 2s, then 4s
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def generate_answer(question: str, context_chunks: list[str]) -> str:
    """
    Returns the model's answer text. Retries up to 3 times with exponential
    backoff on transient failures before giving up. Note: this retries on
    ANY exception, including non-transient ones like a bad API key — a more
    precise version would only retry specific transient error types once
    you know which exceptions the SDK raises for each failure mode;
    flagged here rather than hidden.
    """
    client = _get_client()
    prompt = build_prompt(question, context_chunks)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )
    return response.text