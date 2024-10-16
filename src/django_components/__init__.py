# flake8: noqa F401
"""Main package for Django Components."""

import django as _django

# Public API
# NOTE: Middleware is exposed via django_components.middleware
# NOTE: Some of the documentation is generated based on these exports
from django_components.app_settings import ContextBehavior
from django_components.autodiscovery import autodiscover, import_libraries
from django_components.component import Component, ComponentView
from django_components.component_registry import (
    AlreadyRegistered,
    ComponentRegistry,
    NotRegistered,
    RegistrySettings,
    register,
    registry,
)
from django_components.components import DynamicComponent
from django_components.dependencies import render_dependencies
from django_components.library import TagProtectedError
from django_components.slots import SlotContent, SlotFunc
from django_components.tag_formatter import (
    ComponentFormatter,
    ShorthandComponentFormatter,
    TagFormatterABC,
    TagResult,
    component_formatter,
    component_shorthand_formatter,
)
from django_components.template import cached_template
import django_components.types as types
from django_components.util.types import EmptyTuple, EmptyDict


if _django.VERSION < (3, 2):
    default_app_config = "django_components.apps.ComponentsConfig"

__all__ = [
    "AlreadyRegistered",
    "autodiscover",
    "cached_template",
    "ContextBehavior",
    "Component",
    "ComponentFormatter",
    "ComponentRegistry",
    "ComponentView",
    "component_formatter",
    "component_shorthand_formatter",
    "DynamicComponent",
    "EmptyTuple",
    "EmptyDict",
    "import_libraries",
    "NotRegistered",
    "register",
    "registry",
    "RegistrySettings",
    "render_dependencies",
    "ShorthandComponentFormatter",
    "SlotContent",
    "SlotFunc",
    "TagFormatterABC",
    "TagProtectedError",
    "TagResult",
    "types",
]
