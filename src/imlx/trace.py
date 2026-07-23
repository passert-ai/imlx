"""
imlx.trace
==========
The deterministic execution trace (SPEC 13.6): the complete, ordered event
log of a run, and the documented public interface for visualizers,
animations, and audit tooling.

- Canonical form: the trace is itself an IMLX artifact (header + one pipe
  table in the closed alphabet) and MUST pass Layer 1. The language's
  proofs are themselves gated documents.
- Digests: lowercase hex SHA-256 of content UTF-8 bytes for events that
  carry content; content itself never appears in a trace.
- Determinism: in skeleton mode the trace of a given (artifact +
  declaration source) pair MUST be byte-identical across runs and across
  conforming implementations. Trace equality is a conformance test.
- Projection: 1:1 JSON, one object per row, same field names, no added
  fields. The IMLX table remains canonical.
"""

__version__ = "0.1.0"

import hashlib
import json
from dataclasses import dataclass

#: SPEC 13.6 event vocabulary.
EVENTS = {"GATE_L1", "GATE_L2", "STEP", "BIND", "SLOT_OPEN", "SLOT_FILL",
          "GATE_VERDICT", "HALT"}

#: SPEC 13.6 outcome vocabulary.
OUTCOMES = {"PASS", "FAIL", "BOUND", "FILLED", "SKELETON", "DONE"}

COLUMNS = ["seq", "event", "step", "opcode", "subject", "outcome", "digest"]


def sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class TraceEvent:
    seq: int
    event: str
    step: str      # step number as string, or "-"
    opcode: str    # or "-"
    subject: str
    outcome: str
    digest: str    # 64-char lowercase hex, or "-"

    def cells(self) -> list[str]:
        return [str(self.seq), self.event, self.step, self.opcode,
                self.subject, self.outcome, self.digest]

    def to_dict(self) -> dict:
        return {"seq": self.seq, "event": self.event, "step": self.step,
                "opcode": self.opcode, "subject": self.subject,
                "outcome": self.outcome, "digest": self.digest}


class Trace:
    def __init__(self, artifact_name: str):
        self.artifact_name = artifact_name
        self.events: list[TraceEvent] = []

    def emit(self, event: str, step: str, opcode: str, subject: str,
             outcome: str, digest: str = "-") -> TraceEvent:
        assert event in EVENTS and outcome in OUTCOMES
        ev = TraceEvent(seq=len(self.events) + 1, event=event, step=step,
                        opcode=opcode, subject=subject, outcome=outcome,
                        digest=digest)
        self.events.append(ev)
        return ev

    # -- canonical IMLX rendering (SPEC 13.6) -------------------------------

    def render_imlx(self) -> str:
        lines = [
            "IMLX: 0.1",
            "DECLARATIONS: INLINE",
            "",
            f"# TRACE {self.artifact_name}",
            "",
            "| " + " | ".join(COLUMNS) + " |",
            "| " + " | ".join([":---"] * len(COLUMNS)) + " |",
        ]
        for ev in self.events:
            lines.append("| " + " | ".join(ev.cells()) + " |")
        return "\n".join(lines) + "\n"

    # -- JSON projection (SPEC 13.6): 1:1, same field names, nothing added --

    def render_json(self) -> str:
        return json.dumps([ev.to_dict() for ev in self.events],
                          separators=(",", ":"), sort_keys=False)
