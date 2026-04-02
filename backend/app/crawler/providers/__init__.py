from app.crawler.providers.base import ProviderError

__all__ = [
    "AnalysisProvider",
    "DomesticCrawlerProvider",
    "ForeignCrawlerProvider",
    "ProviderError",
    "TranslationProvider",
]


def __getattr__(name):
    if name == "AnalysisProvider":
        from app.crawler.providers.analysis_provider import AnalysisProvider

        return AnalysisProvider
    if name == "DomesticCrawlerProvider":
        from app.crawler.providers.domestic_provider import DomesticCrawlerProvider

        return DomesticCrawlerProvider
    if name == "ForeignCrawlerProvider":
        from app.crawler.providers.foreign_provider import ForeignCrawlerProvider

        return ForeignCrawlerProvider
    if name == "TranslationProvider":
        from app.crawler.providers.translation_provider import TranslationProvider

        return TranslationProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
