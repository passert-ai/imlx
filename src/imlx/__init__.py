"""
imlx
====
Reference implementation of IMLX: Invariant Markup Language (eXtended).

Binary determinism: a deterministic pass/fail gate at input, a
deterministic, auditable pass/fail at output. The model produces; the
gate decides.

Spec: SPEC.md v0.1.0-rc.1 (github.com/passert-ai/imlx). Foundation:
the recovered iml-cli v1.0.0 validator core's result-object and CLI
patterns, rebuilt spec-facing against SPEC v0.1. Zero runtime
dependencies.
"""

__version__ = "0.1.0"

from .gate import GateResult, gate_bytes, gate_file, run_file
from .layer1 import Verdict, Reason, gate_layer1_bytes
from .layer2 import gate_layer2, OPCODES
from .declarations import Registries, parse_declarations
from .executor import RunResult, FailureRecord, run
from .trace import Trace, TraceEvent

__all__ = [
    "GateResult", "gate_bytes", "gate_file", "run_file",
    "Verdict", "Reason", "gate_layer1_bytes", "gate_layer2",
    "Registries", "parse_declarations", "RunResult", "FailureRecord",
    "run", "Trace", "TraceEvent", "OPCODES", "__version__",
]
