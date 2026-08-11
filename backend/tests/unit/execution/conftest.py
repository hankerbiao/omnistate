import pytest

from app.shared.config import RuntimeSettings, clear_runtime_settings, install_runtime_settings


@pytest.fixture(autouse=True)
def _runtime_settings_snapshot():
    install_runtime_settings(RuntimeSettings())
    yield
    clear_runtime_settings()
