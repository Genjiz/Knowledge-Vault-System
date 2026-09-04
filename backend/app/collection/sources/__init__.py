from app.collection.sources.base import ProviderError, SourceAdapter
from app.collection.sources.ncpssd import NcpssdSource
from app.collection.sources.elsevier import ElsevierSource
from app.collection.sources.magtech import MagtechSource

__all__ = [
    "ProviderError",
    "SourceAdapter",
    "NcpssdSource",
    "ElsevierSource",
    "MagtechSource",
]
