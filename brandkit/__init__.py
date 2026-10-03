"""brandkit: turn a measured source into one kit that every artefact reads."""

from .assemble import assemble_kit, fingerprint, AssemblyError
from .measure import Metrics, measure_html
from .registry import Block, Registry, RegistryError, default_registry
from .schema import SchemaError, validate_draft

__all__ = [
    "assemble_kit", "fingerprint", "AssemblyError",
    "Metrics", "measure_html",
    "Block", "Registry", "RegistryError", "default_registry",
    "SchemaError", "validate_draft",
]
__version__ = "0.1.0"
