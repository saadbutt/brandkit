"""brandkit: turn a measured source into one kit that every artefact reads."""

from .assemble import AssemblyError, assemble_kit, fingerprint
from .measure import Metrics, measure_html
from .registry import Block, Registry, RegistryError, default_registry
from .schema import SchemaError, validate_draft

__all__ = [
    "AssemblyError",
    "Block",
    "Metrics",
    "Registry",
    "RegistryError",
    "SchemaError",
    "assemble_kit",
    "default_registry",
    "fingerprint",
    "measure_html",
    "validate_draft",
]
__version__ = "0.1.0"
