"""
Scraper Registry and Plugin Manager.
Allows dynamic registration and instantiation of source scrapers.
"""

from typing import Dict, List, Type
from src.scrapers.base import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger("scraper_registry")


class ScraperRegistry:
    """Registry holding all available BaseScraper implementations."""

    _scrapers: Dict[str, Type[BaseScraper]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a concrete scraper class."""
        def decorator(subclass: Type[BaseScraper]):
            cls._scrapers[name.lower()] = subclass
            subclass.source_name = name.lower()
            return subclass
        return decorator

    @classmethod
    def get_scraper_class(cls, name: str) -> Type[BaseScraper]:
        """Retrieve scraper class by name."""
        name_lower = name.lower()
        if name_lower not in cls._scrapers:
            raise KeyError(f"Scraper '{name}' not found in registry. Available: {list(cls._scrapers.keys())}")
        return cls._scrapers[name_lower]

    @classmethod
    def list_available(cls) -> List[str]:
        """List all registered scraper source names."""
        return list(cls._scrapers.keys())

    @classmethod
    def create_scraper(cls, name: str, **kwargs) -> BaseScraper:
        """Instantiate a registered scraper by name."""
        scraper_cls = cls.get_scraper_class(name)
        return scraper_cls(**kwargs)
