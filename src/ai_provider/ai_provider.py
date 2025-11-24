import os
from typing import Any
import logging

logger = logging.getLogger(__name__)


def _init_openai_llm(model_name: str) -> Any:
    """Initialize OpenAI LLM."""
    try:
        from langchain_openai import ChatOpenAI
        logger.info(f"Initializing OpenAI LLM with model: {model_name}")
        return ChatOpenAI(model=model_name)
    except ImportError as e:
        raise ImportError("langchain_openai is required for OpenAI provider") from e


def _init_anthropic_llm(model_name: str) -> Any:
    """Initialize Anthropic LLM."""
    try:
        from langchain_anthropic import ChatAnthropic
        logger.info(f"Initializing Anthropic LLM with model: {model_name}")
        return ChatAnthropic(model_name=model_name)
    except ImportError as e:
        raise ImportError("langchain_anthropic is required for Anthropic provider") from e


def _init_sap_aicore_llm(model_name: str) -> Any:
    """Initialize SAP AI Core LLM."""
    try:
        from gen_ai_hub.proxy.langchain import init_llm
        logger.info(f"Initializing AI Core LLM with model: {model_name}")
        return init_llm(model_name)
    except ImportError as e:
        raise ImportError("gen_ai_hub is required for AI Core provider") from e

def _init_azure_llm(model_name: str) -> Any:
    """Initialize Azure OpenAI LLM."""
    try:
        from langchain_openai import AzureChatOpenAI
        logger.info(f"Initializing Azure OpenAI LLM with model: {model_name}")
        return AzureChatOpenAI(
            azure_deployment=model_name,
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("OPENAI_API_VERSION", "2023-12-01-preview")
        )
    except ImportError as e:
        raise ImportError("langchain_openai is required for Azure OpenAI provider") from e

def init_llm_by_provider() -> Any:
    """
    Initialize an LLM instance based on available provider configuration.

    Returns:
        An initialized LLM instance from the first available provider.

    Raises:
        ValueError: If no LLM provider is configured.
        ImportError: If required dependencies for the provider are missing.
    """
    # Check providers and set appropriate default model for each
    if os.getenv("OPENAI_API_KEY"):
        model_name = os.getenv("LLM_DEPLOYMENT", "gpt-4o")
        logger.info("Using OpenAI as LLM provider")
        return _init_openai_llm(model_name)
    elif os.getenv("ANTHROPIC_API_KEY"):
        model_name = os.getenv("LLM_DEPLOYMENT", "claude-3-5-sonnet-20241022")
        logger.info("Using Anthropic as LLM provider")
        return _init_anthropic_llm(model_name)
    elif os.getenv("AICORE_CLIENT_ID"):
        model_name = os.getenv("LLM_DEPLOYMENT", "gpt-4o")
        logger.info("Using SAP AI Core as LLM provider")
        return _init_sap_aicore_llm(model_name)
    elif os.getenv("AZURE_OPENAI_API_KEY"):
        model_name = os.getenv("LLM_DEPLOYMENT", "gpt-4o")
        logger.info("Using Azure OpenAI as LLM provider")
        return _init_azure_llm(model_name)

    raise ValueError(
        "No LLM provider configured. Please set one of: "
        "OPENAI_API_KEY, ANTHROPIC_API_KEY, AICORE_CLIENT_ID, or AZURE_OPENAI_API_KEY"
    )

