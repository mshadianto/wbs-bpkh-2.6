"""
WBS BPKH AI - Agent Utilities
==============================
Shared utilities for AI agents: retry logic, input management.
"""

import asyncio
from loguru import logger


async def retry_llm_call(func, max_retries: int = 3, base_delay: float = 2.0):
    """
    Retry an async LLM call with exponential backoff.

    Args:
        func: Async callable that makes the LLM API call
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)

    Returns:
        The result of the successful call

    Raises:
        The last exception if all retries fail
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_error = e
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                f"LLM call failed (attempt {attempt + 1}/{max_retries}), "
                f"retrying in {delay}s: {type(e).__name__}: {e}"
            )
            await asyncio.sleep(delay)
    raise last_error


def truncate_content(content: str, max_chars: int = 15000) -> str:
    """
    Truncate content to stay within token limits.

    Args:
        content: The text content to truncate
        max_chars: Maximum character count (~4 chars per token)

    Returns:
        Truncated content with indicator if truncated
    """
    if len(content) <= max_chars:
        return content

    logger.warning(f"Content truncated from {len(content)} to {max_chars} chars")
    return content[:max_chars] + "\n\n[...konten dipotong karena terlalu panjang...]"
