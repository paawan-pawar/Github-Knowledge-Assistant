"""
Thin wrapper around Groq's OpenAI-compatible chat completions endpoint.
Uses AsyncOpenAI so streaming plays nicely with FastAPI's async event loop.
"""
from __future__ import annotations

from functools import lru_cache
from typing import AsyncIterator

from openai import AsyncOpenAI

from app.config import get_settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


@lru_cache
def _client() -> AsyncOpenAI:
    settings = get_settings()
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env.")
    return AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=GROQ_BASE_URL)


async def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    settings = get_settings()
    resp = await _client().chat.completions.create(
        model=model or settings.GROQ_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


async def stream(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    settings = get_settings()
    completion = await _client().chat.completions.create(
        model=model or settings.GROQ_CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in completion:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content
