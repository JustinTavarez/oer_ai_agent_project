import pytest

from app.routes.search import clear_search_cache
from app.services.lmstudio import _response_cache


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear all in-memory caches before each test."""
    clear_search_cache()
    _response_cache.clear()
    yield
    clear_search_cache()
    _response_cache.clear()
