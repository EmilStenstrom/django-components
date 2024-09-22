import pytest

from tests.e2e.utils import run_django_dev_server


@pytest.fixture(scope="session", autouse=True)
def django_dev_server():
    """Fixture to run Django development server in the background."""
    yield from run_django_dev_server()
