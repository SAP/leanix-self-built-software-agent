import os
from typing import Any, Optional
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


def _init_anthropic_custom_llm(model_name: str) -> Any:
    """Initialize Anthropic LLM with custom base URL and auth token."""
    try:
        from langchain_anthropic import ChatAnthropic

        base_url = os.getenv("ANTHROPIC_BASE_URL")
        auth_token = os.getenv("ANTHROPIC_AUTH_TOKEN")

        logger.info(f"Initializing Anthropic LLM (custom hosting) with model: {model_name}")
        logger.info(f"Using base URL: {base_url}")

        return ChatAnthropic(
            model_name=model_name,
            base_url=base_url,
            default_headers={"x-api-key": auth_token},
        )
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

def init_llm_by_provider(model_name: Optional[str] = None) -> Any:
    """
    Initialize an LLM instance based on available provider configuration.

    Args:
        model_name: Optional model name to use. If None, uses LLM_DEPLOYMENT env var or defaults.

    Returns:
        An initialized LLM instance from the first available provider.

    Raises:
        ValueError: If no LLM provider is configured or model is invalid.
        ImportError: If required dependencies for the provider are missing.
    """
    # Determine provider and get model name
    provider = None
    provider_name = None
    default_model = None

    if os.getenv("OPENAI_API_KEY"):
        provider = _init_openai_llm
        provider_name = "openai"
        default_model = "gpt-4o"
    elif os.getenv("ANTHROPIC_BASE_URL") and os.getenv("ANTHROPIC_AUTH_TOKEN"):
        provider = _init_anthropic_custom_llm
        provider_name = "anthropic-custom"
        default_model = "claude-3-5-sonnet-20241022"
    elif os.getenv("ANTHROPIC_API_KEY"):
        provider = _init_anthropic_llm
        provider_name = "anthropic"
        default_model = "claude-3-5-sonnet-20241022"
    elif os.getenv("AICORE_CLIENT_ID"):
        provider = _init_sap_aicore_llm
        provider_name = "aicore"
        default_model = "gpt-4o"
    elif os.getenv("AZURE_OPENAI_API_KEY"):
        provider = _init_azure_llm
        provider_name = "azure"
        default_model = "gpt-4o"
    else:
        raise ValueError(
            "No LLM provider configured. Please set one of: "
            "OPENAI_API_KEY, ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL+ANTHROPIC_AUTH_TOKEN, "
            "AICORE_CLIENT_ID, or AZURE_OPENAI_API_KEY"
        )

    # Determine which model to use (priority: parameter > env var > default)
    final_model = model_name or os.getenv("LLM_DEPLOYMENT", default_model)

    logger.info(f"Using {provider_name} as LLM provider with model: {final_model}")

    # Initialize the LLM
    llm = provider(final_model)

    return llm


def validate_llm_availability(model_name: Optional[str] = None) -> tuple[bool, Optional[str]]:
    """
    Validate that the LLM model is actually available and accessible.

    Makes a simple test call to verify:
    - API credentials are valid
    - Model exists and is accessible
    - Network connectivity works

    Args:
        model_name: Optional model name to test. If None, uses default for configured provider.

    Returns:
        Tuple of (is_available, error_message)
        - (True, None) if model is available
        - (False, error_message) if model is not available
    """
    try:
        # Initialize the LLM
        llm = init_llm_by_provider(model_name)

        # Make a minimal test call to verify the model is accessible
        logger.info("Testing LLM availability with a simple prompt...")

        # Use a very simple prompt to minimize cost and latency
        test_response = llm.invoke("Hi")

        # If we got here, the model is available
        logger.info("LLM availability test passed")
        return (True, None)

    except Exception as e:
        error_message = str(e)
        logger.error(f"LLM availability test failed: {error_message}")

        # Provide helpful error messages based on common issues
        if "authentication" in error_message.lower() or "api key" in error_message.lower():
            return (False, f"Authentication failed: {error_message}\n\nPlease check your API key is valid and has not expired.")
        elif "not found" in error_message.lower() or "does not exist" in error_message.lower():
            return (False, f"Model not found: {error_message}\n\nThe model may not be available in your account or region.")
        elif "quota" in error_message.lower() or "rate limit" in error_message.lower():
            return (False, f"Rate limit or quota exceeded: {error_message}\n\nPlease check your API usage limits.")
        elif "permission" in error_message.lower() or "access" in error_message.lower():
            return (False, f"Permission denied: {error_message}\n\nYou may not have access to this model.")
        else:
            return (False, f"LLM validation failed: {error_message}")

