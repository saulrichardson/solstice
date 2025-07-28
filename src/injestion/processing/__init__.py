"""Agentic helpers that interact with the LLM gateway.

All code in this sub-package talks exclusively to the **Responses API** exposed
by the gateway service.  Higher-level ingestion modules can therefore remain
vendor-agnostic while still benefitting from retries, caching and analytics
implemented inside the gateway.
"""

