"""Utility for injecting user-provided context into agent prompts."""
from __future__ import annotations

from typing import Optional
from src.dto.context_dto import DiscoveryContext


def format_context_for_prompt(context: Optional[DiscoveryContext], max_chars: int = 4000) -> str:
    """Format discovery context for injection into LLM prompts.

    Args:
        context: The DiscoveryContext from state, or None.
        max_chars: Maximum characters to include (prevent token bloat).
                   Default 4000 chars ≈ ~1000 tokens.

    Returns:
        A formatted string ready for prompt injection, or empty string if no context.
        The string includes a clear section header so the LLM understands the context.
    """
    if context is None or not context.merged_context:
        return ""

    merged = context.merged_context.strip()

    # Truncate if too long (protect against token bloat)
    if len(merged) > max_chars:
        merged = merged[:max_chars] + "\n... [context truncated]"

    return f"""
## User-Provided Context
The following context was provided by the user to help with discovery. Use this information to make better decisions about service classification, tech stack detection, and naming conventions.

{merged}

---
"""
