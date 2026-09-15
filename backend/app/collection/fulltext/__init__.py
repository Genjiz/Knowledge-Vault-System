"""统一全文提供器。"""

from app.collection.fulltext.base import (
    AccessBlockedError,
    AccessDeniedError,
    FullTextProviderError,
    FullTextReference,
    HumanVerificationRequired,
)
from app.collection.fulltext.registry import (
    build_fulltext_provider,
    resolve_fulltext_reference,
)

__all__ = [
    "AccessBlockedError",
    "AccessDeniedError",
    "FullTextProviderError",
    "FullTextReference",
    "HumanVerificationRequired",
    "build_fulltext_provider",
    "resolve_fulltext_reference",
]
