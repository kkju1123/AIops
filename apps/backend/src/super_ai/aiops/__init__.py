"""AIOps diagnostic orchestration.

Exports load lazily so lightweight submodules (such as `fixtures`, used by the fault simulator
subprocess) do not pay for importing LangGraph and the diagnostic graph.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .cases import DiagnosisCasePersistor
    from .diagnostics import AiopsDiagnosticService

__all__ = ["AiopsDiagnosticService", "DiagnosisCasePersistor"]

_EXPORTS = {
    "AiopsDiagnosticService": ".diagnostics",
    "DiagnosisCasePersistor": ".cases",
}


def __getattr__(name: str) -> object:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(module_name, __name__), name)
