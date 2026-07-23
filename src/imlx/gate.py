"""
imlx.gate
=========
The gate (SPEC 14): the program that renders the verdict. One bit per
layer; "PASS" unqualified means both layers passed. Reason codes accompany
FAIL as diagnostics and never soften it.
"""

__version__ = "0.1.0"

from dataclasses import dataclass
from pathlib import Path

from .declarations import Registries, load_external_source, parse_declarations
from .executor import EngineAdapter, RunResult, run
from .layer1 import Document, Reason, Verdict, gate_layer1_bytes
from .layer2 import gate_layer2


@dataclass
class GateResult:
    layer1: Verdict
    layer2: Verdict | None      # None: not attempted (L1 failed, or no source)
    document: Document | None
    registries: Registries | None

    @property
    def verdict(self) -> str:
        """Unqualified verdict: PASS means both layers passed (SPEC 14.2)."""
        if not self.layer1.passed:
            return "FAIL"
        if self.layer2 is None:
            return "L1-PASS"  # artifact Layer 1-validatable alone, by design
        return "PASS" if self.layer2.passed else "FAIL"

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "layer1": self.layer1.to_dict(),
            "layer2": self.layer2.to_dict() if self.layer2 else None,
        }


def gate_bytes(artifact: bytes, name: str,
               decl_bytes: bytes | None = None,
               decl_name: str | None = None) -> GateResult:
    """Gate an artifact from raw bytes, optionally with its declaration file."""
    l1, doc = gate_layer1_bytes(artifact, name)
    if not l1.passed:
        return GateResult(layer1=l1, layer2=None, document=None, registries=None)

    reasons: list[Reason] = []
    registries: Registries | None = None

    if doc.header.decl_mode == "EXTERNAL":
        if decl_bytes is None:
            # Layer 2 not attemptable: not a failure, by design (SPEC 5.2)
            return GateResult(layer1=l1, layer2=None, document=doc, registries=None)
        registries = load_external_source(decl_bytes, decl_name or "",
                                          doc.header.decl_name,
                                          doc.header.decl_version, reasons)
        if registries is None:
            return GateResult(layer1=l1, layer2=Verdict(False, reasons),
                              document=doc, registries=None)

    l2 = gate_layer2(doc, registries)
    if reasons:
        l2 = Verdict(False, reasons + l2.reasons)
    if registries is None and l2.passed:
        registries = parse_declarations(doc, [])
        registries.source_name = ""
    return GateResult(layer1=l1, layer2=l2, document=doc, registries=registries)


def gate_file(path: str | Path, decl_path: str | Path | None = None) -> GateResult:
    path = Path(path)
    decl_bytes = decl_name = None
    if decl_path is not None:
        decl_path = Path(decl_path)
        decl_bytes, decl_name = decl_path.read_bytes(), decl_path.name
    else:
        # header-named source in the same directory is the natural pairing
        peek = path.read_bytes()
        l1, doc = gate_layer1_bytes(peek, path.name)
        if l1.passed and doc.header.decl_mode == "EXTERNAL":
            candidate = path.parent / doc.header.decl_name
            if candidate.is_file():
                decl_bytes, decl_name = candidate.read_bytes(), candidate.name
    return gate_bytes(path.read_bytes(), path.name, decl_bytes, decl_name)


def run_file(path: str | Path, decl_path: str | Path | None = None,
             engine: EngineAdapter | None = None,
             policy_payloads: dict[str, list[str]] | None = None
             ) -> tuple[GateResult, RunResult | None]:
    """Gate, then execute. A Layer 1 or Layer 2 failure rejects the artifact
    before execution; nothing runs (SPEC 13.5)."""
    result = gate_file(path, decl_path)
    if result.verdict != "PASS":
        return result, None
    return result, run(result.document, result.registries, engine, policy_payloads)
