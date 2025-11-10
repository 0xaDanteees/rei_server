from __future__ import annotations

from typing import Optional

from langchain_openai import ChatOpenAI, AzureChatOpenAI

from .settings import settings


def get_chat_model(streaming: bool = True):
    """Return a LangChain chat model configured from settings.

    Supports OpenAI (default) and Azure OpenAI. Temperature kept low for agentic reliability.
    """
    provider = (settings.LLM_PROVIDER or "openai").lower()
    if provider == "azure":
        if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_DEPLOYMENT:
            raise RuntimeError("Azure OpenAI settings are incomplete")
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            max_retries=2,
            temperature=0.2,
            streaming=streaming,
        )
    else:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not set")
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            max_retries=2,
            temperature=0.2,
            streaming=streaming,
        )
