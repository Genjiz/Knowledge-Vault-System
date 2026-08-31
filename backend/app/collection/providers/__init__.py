from app.collection.sources.base import ProviderError

__all__ = [
    "AnalysisProvider",
    "NcpssdSource",
    "ElsevierSource",
    "ProviderError",
    "TranslationProvider",
]


def __getattr__(name):
    if name == "AnalysisProvider":
        from app.collection.providers.analysis_provider import AnalysisProvider

        return AnalysisProvider
    if name == "NcpssdSource":
        from app.collection.sources.ncpssd import NcpssdSource

        return NcpssdSource
    if name == "ElsevierSource":
        from app.collection.sources.elsevier import ElsevierSource

        return ElsevierSource
    if name == "TranslationProvider":
        from app.collection.providers.translation_provider import TranslationProvider

        return TranslationProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
