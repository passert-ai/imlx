"""
imlx.executor
=============
The execution model (SPEC 13). State is the register file; steps execute in
step-number order; SLOT fills are sequential, never parallel.

- Skeleton mode (13.3): runs every program end-to-end with no engine; each
  SLOT renders a placeholder displaying its full contract. Fully
  deterministic; no network, no credentials; the mode conformance tests
  run in.
- Engine mode (13.4): an engine adapter fills SLOTs; the paired GATE is
  applied immediately to what returns. The engine is outside the guarantee
  boundary.
- Failure semantics (13.5): a runtime GATE FAIL halts at that step with
  verdict FAIL and a failure record (step, opcode, reason code, violated
  contract). A conforming executor MUST NOT retry internally.

SKELETON DIGEST CANON (SPEC 13.6, ratified v0.1.0-rc.2): the
content of a skeleton-mode binding is defined as the canonical string
``SKELETON|<step>|<opcode>|<operand>|<bind>`` (UTF-8). SPEC 13.6 requires
byte-identical skeleton traces across implementations, which requires the
digested content to be canonically defined; this string is that definition,
ratified, and the trace fixtures pin it.
"""

__version__ = "0.1.0"

from dataclasses import dataclass, field
from typing import Callable

from . import charset as cs
from .declarations import Registries
from .layer1 import Document
from .layer2 import parse_steps, Step, SLOT_CONTRACT_KEYS
from .trace import Trace, sha256_hex

#: Engine adapter: contract dict -> payload string.
EngineAdapter = Callable[[dict], str]


@dataclass
class FailureRecord:
    """SPEC 13.5: step number, opcode, reason code, violated contract."""
    step: int
    opcode: str
    reason_code: str
    contract: str

    def to_dict(self) -> dict:
        return {"step": self.step, "opcode": self.opcode,
                "reason_code": self.reason_code, "contract": self.contract}


@dataclass
class RunResult:
    verdict: str  # PASS | FAIL
    trace: Trace
    registers: dict[str, str] = field(default_factory=dict)
    failure: FailureRecord | None = None
    outputs: list[tuple[str, str]] = field(default_factory=list)  # (type, content)


def skeleton_content(st: Step) -> str:
    """Canonical skeleton-mode binding content (module docstring)."""
    return f"SKELETON|{st.number}|{st.opcode}|{st.operand}|{st.bind}"


def slot_placeholder(contract: dict) -> str:
    """SPEC 13.3: a placeholder displaying the SLOT's full contract."""
    body = "; ".join(f"{k}={contract[k]}" for k in sorted(contract))
    return f"[SLOT UNFILLED: {body}]"


def parse_contract(operand: str) -> dict:
    kv = {}
    for p in (x.strip() for x in operand.split(";")):
        if "=" in p:
            k, v = p.split("=", 1)
            kv[k] = v
    return kv


def run(doc: Document, registries: Registries,
        engine: EngineAdapter | None = None,
        policy_payloads: dict[str, list[str]] | None = None) -> RunResult:
    """Execute a Layer 1- and Layer 2-passed document (SPEC 13).

    ``policy_payloads`` supplies blocklist policy data (Law 6): a mapping
    from POLICY name to its list of forbidden substrings. Policy is data
    given to the gate, never spec or code content.
    """
    trace = Trace(doc.name)
    trace.emit("GATE_L1", "-", "-", doc.name, "PASS")
    l2_subject = (f"{registries.source_name}; {registries.source_version}"
                  if registries.source_name else "INLINE")
    trace.emit("GATE_L2", "-", "-", l2_subject, "PASS")

    steps = parse_steps(doc)
    registers: dict[str, str] = {}
    slot_contracts: dict[str, dict] = {}
    slot_payloads: dict[str, str] = {}
    policy_payloads = policy_payloads or {}

    for st in steps:
        s = str(st.number)

        if st.opcode == "SLOT":
            contract = parse_contract(st.operand)
            trace.emit("SLOT_OPEN", s, "SLOT", f"type={contract.get('type', '-')}", "DONE")
            if engine is None:
                registers[st.bind] = slot_placeholder(contract)
                slot_contracts[st.bind] = contract
                trace.emit("SLOT_FILL", s, "SLOT", st.bind, "SKELETON")
            else:
                payload = engine(contract)  # sequential, program order (13.2)
                registers[st.bind] = payload
                slot_contracts[st.bind] = contract
                slot_payloads[st.bind] = payload
                trace.emit("SLOT_FILL", s, "SLOT", st.bind, "FILLED",
                           sha256_hex(payload))
            continue

        if st.opcode == "GATE":
            target = st.operand.strip()
            contract = slot_contracts.get(target, {})
            if target in slot_payloads:  # engine mode: gate what returned
                verdict, code = _gate_slot_payload(
                    slot_payloads[target], contract, registries, policy_payloads)
            else:  # skeleton fill: the placeholder is the deterministic pass
                verdict, code = "PASS", ""
            trace.emit("GATE_VERDICT", s, "GATE", target, verdict)
            if st.bind != "-":
                registers[st.bind] = verdict
            if verdict == "FAIL":
                trace.emit("HALT", s, "-", doc.name, "FAIL")
                return RunResult(
                    verdict="FAIL", trace=trace, registers=registers,
                    failure=FailureRecord(step=st.number, opcode="GATE",
                                          reason_code=code,
                                          contract="; ".join(
                                              f"{k}={contract[k]}"
                                              for k in sorted(contract))))
            continue

        if st.opcode == "OUTPUT_PRINT":
            target = st.operand.strip()
            trace.emit("STEP", s, st.opcode, target, "DONE")
            continue

        # all other opcodes: deterministic step; binding opcodes emit BIND
        subject = st.bind if st.bind != "-" else st.operand
        trace.emit("STEP", s, st.opcode, subject, "DONE")
        bind_name = st.bind if st.bind != "-" else None
        if bind_name:
            content = skeleton_content(st) if engine is None else \
                _engine_mode_binding_content(st, registers)
            registers[bind_name] = content
            trace.emit("BIND", s, st.opcode, bind_name, "BOUND", sha256_hex(content))

    # collect outputs after a completed run
    outputs = [(st.style, registers.get(st.operand.strip(), ""))
               for st in steps if st.opcode == "OUTPUT_PRINT"]

    last = str(steps[-1].number) if steps else "-"
    trace.emit("HALT", last, "-", doc.name, "PASS")
    return RunResult(verdict="PASS", trace=trace, registers=registers,
                     outputs=outputs)


def _engine_mode_binding_content(st: Step, registers: dict[str, str]) -> str:
    """Deterministic data-opcode semantics shared by both modes.

    Phase 1 executes data opcodes symbolically: the binding's content is the
    canonical step description. Real corpus-backed LOAD/QUERY semantics are
    toolchain integrations layered on later; the trace interface does not
    change. In engine mode the SLOT is the only moving part (SPEC 13.6).
    """
    return skeleton_content(st)


# ---------------------------------------------------------------------------
# The runtime GATE on a SLOT payload (SPEC 13.4, 11.2)
# ---------------------------------------------------------------------------

def _gate_slot_payload(payload: str, contract: dict, regs: Registries,
                       policy_payloads: dict[str, list[str]]) -> tuple[str, str]:
    """One-bit verdict on an engine payload: charset law + blocklist policy.

    The charset law is always in force on what returns; the blocklist is
    the policy data the contract names (Law 6). RT-GATE01 on FAIL.
    """
    # charset law: every payload line must satisfy content-space rules
    for line in payload.split("\n"):
        if line == "":
            continue
        if cs.illegal_content_chars(line):
            return "FAIL", "RT-GATE01"
        bare = cs.bare_math_chars_outside_fences(line)
        if bare:
            return "FAIL", "RT-GATE01"
        if "@" in line:
            return "FAIL", "RT-GATE01"

    # blocklist policy
    ref = contract.get("blocklist", "")
    policy_name = ref[1:] if ref.startswith("@") else ref
    target = regs.symbols.get(policy_name, policy_name)
    blocked = policy_payloads.get(policy_name) or policy_payloads.get(target) or []
    for term in blocked:
        if term and term in payload:
            return "FAIL", "RT-GATE01"

    return "PASS", ""
