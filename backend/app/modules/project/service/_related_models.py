"""Lazy resolution of models associated with projects."""

import importlib

from app.modules.project.domain.constants import PROJECT_RELATED_MODEL_PATHS
from app.shared.core.logger import log as logger


def get_related_models() -> list[type]:
    models = []
    for module_path, class_name in PROJECT_RELATED_MODEL_PATHS:
        try:
            module = importlib.import_module(module_path)
            models.append(getattr(module, class_name))
        except (ImportError, AttributeError) as exc:
            logger.warning("Failed to load related model {}.{}: {}", module_path, class_name, exc)
    return models


def find_model(related: list[type], name: str) -> type:
    for model in related:
        if model.__name__ == name:
            return model
    raise ValueError(
        f"Related model '{name}' is not registered in PROJECT_RELATED_MODEL_PATHS. "
        f"Available models: {[model.__name__ for model in related]}"
    )
