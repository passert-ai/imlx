"""
imlx.layer2
===========
The Layer 2 gate (SPEC 14.2): everything requiring declarations. Type
resolution, reference resolution, register discipline, operand schema
checks, procedure/converter existence, capability checks, policy presence.

Layer 2 requires the artifact plus its declaration source, and verifies the
header pairing before applying it (L2-PAIR01).

L2-CAP01 is ratified in SPEC Appendix C as of v0.1.0-rc.2:
"construct requires a type capability the block's type does not declare".
The capability mechanism is SPEC 8; Appendix C carries no code for its
violation.
"""

__version__ = "0.1.0"

from dataclasses import dataclass

from . import charset as cs
from .declarations import Registries, parse_declarations
from .layer1 import Document, Reason, Table, Verdict

#: The ratified 21 opcodes (SPEC 11.2). SEARCH's two forms are one opcode.
OPCODES = {
    "LOAD", "SEARCH", "QUERY", "SELECT", "PARSE", "LABEL", "EXTRACT",
    "CONCAT", "INSERT", "APPEND", "POPULATE", "FOR_EACH", "IF/THEN/ELSE",
    "EXECUTE", "DECLARE", "SLOT", "VERIFY", "CONVERT", "COMPUTE",
    "OUTPUT_PRINT", "GATE",
}

#: SPEC 12: the semantic exclusion boundary, published as boundary evidence.
EXCLUDED_VERBS = {
    "IDENTIFY", "DEFINE", "CITE-AND-DEFINE", "SUMMARIZE", "RESTATE",
    "APPLY", "NETWORK_MAP", "TRUNCATE",
}

#: SLOT contract keys (SPEC 11.2): grounding key + type + blocklist.
#: The charset law is the fourth contract element and is always in force.
SLOT_CONTRACT_KEYS = {"ground", "type", "blocklist"}

_REGISTER_NAME = cs.REFERENCE_RE  # same shape, without the sigil


@dataclass
class Step:
    number: int
    opcode: str
    operand: str
    bind: str
    style: str
    line: int


def gate_layer2(doc: Document, registries: Registries | None) -> Verdict:
    """Full Layer 2 verdict for a Layer 1-passed document.

    ``registries`` is the resolved declaration source; None means the
    artifact is INLINE and its own DECLARE sections are the source
    (SPEC 10.2).
    """
    reasons: list[Reason] = []

    if registries is None:
        if doc.header.decl_mode != "INLINE":
            reasons.append(Reason("L2-PAIR01", 2,
                                  f"artifact pairs external source "
                                  f"'{doc.header.decl_name}; {doc.header.decl_version}' "
                                  f"but no declaration source was supplied (SPEC 5.2)"))
            return Verdict(False, reasons)
        registries = parse_declarations(doc, reasons)
    else:
        if doc.header.decl_mode == "INLINE":
            # INLINE artifacts name themselves as the single source; an
            # externally supplied source would be a second one (SPEC 10.2).
            reasons.append(Reason("L2-PAIR01", 2,
                                  "artifact declares INLINE but an external "
                                  "declaration source was supplied; exactly one "
                                  "source per artifact (SPEC 10.2)"))
            return Verdict(False, reasons)
        # duplicate/conflicting definitions between artifact and its named
        # source fail the gate (SPEC 10.2)
        inline_reasons: list[Reason] = []
        inline = parse_declarations(doc, inline_reasons)
        reasons.extend(inline_reasons)
        for kind, (attr, _key) in Registries._KIND_MAP.items():
            overlap = set(getattr(inline, attr)) & set(getattr(registries, attr))
            for name in sorted(overlap):
                reasons.append(Reason("L2-DUP01", 0,
                                      f"{kind} '{name}' defined both in the artifact and "
                                      f"in its named source (SPEC 10.2)"))

    _check_envelope_types(doc, registries, reasons)
    _check_programs(doc, registries, reasons)
    _check_symbol_references(doc, registries, reasons)

    return Verdict(not reasons, reasons)


# ---------------------------------------------------------------------------
# Blocks: type resolution (Law 4) and capabilities (SPEC 8)
# ---------------------------------------------------------------------------

def _check_envelope_types(doc: Document, regs: Registries, reasons: list[Reason]) -> None:
    for env in doc.envelopes:
        if env.type_name not in regs.types:
            reasons.append(Reason("L2-TYP01", env.start_line,
                                  f"unresolvable block type '{env.type_name}' (Law 4)"))
            continue
        if env.legal_list_lines and "legal_lists" not in regs.type_capabilities(env.type_name):
            reasons.append(Reason("L2-CAP01", env.legal_list_lines[0],
                                  f"legal-numbered list or Step numbering inside a block "
                                  f"of type '{env.type_name}', which does not declare the "
                                  f"legal_lists capability (SPEC 6.2, 8)"))


# ---------------------------------------------------------------------------
# References (Law 5, SPEC 9)
# ---------------------------------------------------------------------------

def _check_symbol_references(doc: Document, regs: Registries, reasons: list[Reason]) -> None:
    for tbl in doc.elements:
        if not isinstance(tbl, Table) or tbl.space not in ("program", "declaration"):
            continue
        for cells, ln in zip(tbl.rows, tbl.row_lines):
            for cell in cells:
                for name in cs.REFERENCE_SCAN_RE.findall(cell):
                    if name not in regs.symbols and name not in regs.policies:
                        reasons.append(Reason("L2-REF01", ln,
                                              f"unresolvable reference @{name}: exactly one "
                                              f"target required, found zero (SPEC 9)"))


# ---------------------------------------------------------------------------
# Programs: opcodes, registers, operands (SPEC 11)
# ---------------------------------------------------------------------------

def parse_steps(doc: Document) -> list[Step]:
    steps: list[Step] = []
    for tbl in doc.program_tables:
        for cells, ln in zip(tbl.rows, tbl.row_lines):
            steps.append(Step(number=int(cells[0]), opcode=cells[1], operand=cells[2],
                              bind=cells[3], style=cells[4], line=ln))
    return steps


def _check_programs(doc: Document, regs: Registries, reasons: list[Reason]) -> None:
    steps = parse_steps(doc)
    bound: dict[str, int] = {}       # register -> binding step number
    slot_bound: dict[str, int] = {}  # SLOT-bound register -> step number
    gated: set[str] = set()          # SLOT registers that passed a GATE step

    # registers pre-typed by DECLARE REGISTER exist as names but are NOT
    # bound until a step binds them (SPEC 13.1: bindings are created during
    # execution; SPEC 11.2: bound exactly once, before any use)

    for st in steps:
        op = st.opcode

        if op in EXCLUDED_VERBS:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"'{op}' is outside the language by the semantic "
                                  f"exclusion boundary (SPEC 12); it is SLOT work"))
            continue
        if op not in OPCODES:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"unknown opcode '{op}' (SPEC 11.2 ratifies 21)"))
            continue

        _check_operand(st, regs, bound, slot_bound, gated, reasons)

        # bind-column discipline (L2-REG01)
        if st.bind != "-":
            if not _REGISTER_NAME.match("@" + st.bind):
                reasons.append(Reason("L2-REG01", st.line,
                                      f"bind target '{st.bind}' is not a legal register name"))
            elif st.bind in bound:
                reasons.append(Reason("L2-REG01", st.line,
                                      f"register '{st.bind}' bound twice (first at step "
                                      f"{bound[st.bind]}; SPEC 11.2 LABEL: exactly once)"))
            else:
                bound[st.bind] = st.number
                if op == "SLOT":
                    slot_bound[st.bind] = st.number
        elif op in ("LOAD", "SEARCH", "QUERY", "SELECT", "PARSE", "LABEL",
                    "EXTRACT", "CONCAT", "SLOT", "VERIFY", "CONVERT", "COMPUTE",
                    "GATE"):
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"{op} produces a binding and requires a bind target"))

        # style column: '-' or a registered type (Law 4 via OUTPUT_PRINT/SLOT)
        if st.style != "-" and st.style not in regs.types:
            reasons.append(Reason("L2-TYP01", st.line,
                                  f"style '{st.style}' is not a registered block type"))

        if op == "GATE":
            target = st.operand.strip()
            if target in slot_bound:
                gated.add(target)

    # OUTPUT_PRINT payloads previously gate-passed (SPEC 11.2)
    for st in steps:
        if st.opcode == "OUTPUT_PRINT":
            target = st.operand.strip()
            if target in slot_bound and target not in gated:
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"OUTPUT_PRINT payload '{target}' is SLOT-produced "
                                      f"but no GATE step passed it (SPEC 11.2)"))


def _parts(operand: str) -> list[str]:
    return [p.strip() for p in operand.split(";")]


def _is_register_token(tok: str) -> bool:
    return bool(_REGISTER_NAME.match("@" + tok)) and not tok.startswith("@") \
        and not (tok.startswith('"') and tok.endswith('"'))


def _require_bound(tok: str, st: Step, bound: dict, reasons: list[Reason], role: str) -> None:
    if tok not in bound:
        reasons.append(Reason("L2-REG01", st.line,
                              f"{st.opcode} {role} register '{tok}' used before bind "
                              f"(SPEC 11.2)"))


def _check_operand(st: Step, regs: Registries, bound: dict, slot_bound: dict,
                   gated: set, reasons: list[Reason]) -> None:
    op, parts = st.opcode, _parts(st.operand)

    if op == "LOAD":
        for tok in parts:
            if not tok.startswith("@") and not _is_register_token(tok):
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"LOAD operand '{tok}' must name an artifact by "
                                      f"reference (SPEC 11.2)"))

    elif op == "QUERY":
        if len(parts) != 3:
            reasons.append(Reason("L2-OPD01", st.line,
                                  "QUERY operand form: source; field; \"key\" (SPEC 11.2)"))
            return
        src, _field_name, key = parts
        if _is_register_token(src):
            _require_bound(src, st, bound, reasons, "source")
        if not (key.startswith('"') and key.endswith('"') and len(key) >= 2):
            reasons.append(Reason("L2-OPD01", st.line,
                                  "QUERY key must be a quoted literal in the alphabet"))

    elif op == "SEARCH":
        if len(parts) < 2:
            reasons.append(Reason("L2-OPD01", st.line,
                                  "SEARCH operand form: source; scope... (SPEC 11.2, "
                                  "corpus form or register form)"))
            return
        src = parts[0]
        if src.startswith("@"):
            pass  # corpus form: reference resolution handled globally
        elif _is_register_token(src):
            _require_bound(src, st, bound, reasons, "source")  # register form
        else:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"SEARCH source '{src}' is neither a declared corpus "
                                  f"reference nor a register (SPEC 11.2)"))

    elif op in ("SELECT", "EXTRACT", "PARSE", "VERIFY", "FOR_EACH"):
        if not parts or not parts[0]:
            reasons.append(Reason("L2-OPD01", st.line, f"{op} requires a source register"))
            return
        if op == "FOR_EACH" and len(parts) != 1:
            reasons.append(Reason("L2-OPD01", st.line,
                                  "FOR_EACH operand is a single bound finite set (SPEC 11.2)"))
        if op in ("SELECT", "EXTRACT", "PARSE", "VERIFY") and len(parts) < 2:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"{op} operand form: source; <field or predicate or path>"))
        if _is_register_token(parts[0]):
            _require_bound(parts[0], st, bound, reasons, "source")
        else:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"{op} source '{parts[0]}' must be a bound register"))

    elif op in ("CONCAT", "COMPUTE"):
        for tok in parts:
            if _is_register_token(tok):
                _require_bound(tok, st, bound, reasons, "operand")
            elif op == "COMPUTE" and not _numeric_or_operator(tok):
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"COMPUTE operand '{tok}' is neither a bound numeric "
                                      f"register, a numeric literal, nor an operator from "
                                      f"the closed set (SPEC 11.2)"))
            elif op == "CONCAT" and not (tok.startswith('"') and tok.endswith('"')):
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"CONCAT operand '{tok}' must be a bound register or "
                                      f"a quoted literal"))

    elif op in ("INSERT", "APPEND"):
        if len(parts) != 2:
            reasons.append(Reason("L2-OPD01", st.line, f"{op} operand form: source; target"))
            return
        for role, tok in zip(("source", "target"), parts):
            if _is_register_token(tok):
                _require_bound(tok, st, bound, reasons, role)
            elif role == "target" or not (tok.startswith('"') and tok.endswith('"')):
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"{op} {role} '{tok}' must be a bound register"))

    elif op == "POPULATE":
        if len(parts) < 2:
            reasons.append(Reason("L2-OPD01", st.line,
                                  "POPULATE operand form: template; field=source; ... "
                                  "every template field maps to exactly one bound source "
                                  "(SPEC 11.2)"))
            return
        seen_fields: set[str] = set()
        for mapping in parts[1:]:
            if "=" not in mapping:
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"POPULATE mapping '{mapping}' must be field=source"))
                continue
            fld, src = mapping.split("=", 1)
            if fld in seen_fields:
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"POPULATE field '{fld}' mapped more than once "
                                      f"(one-to-one, SPEC 11.2)"))
            seen_fields.add(fld)
            if _is_register_token(src):
                _require_bound(src, st, bound, reasons, "mapping source")

    elif op == "IF/THEN/ELSE":
        # SPEC 11.2 (rc.2) operand syntax:
        #   comparand; comparand; THEN=<step>; ELSE=<step>
        # 11.2 check as ratified: comparands enumerated; both branches present.
        has_then = any(p.startswith("THEN=") for p in parts)
        has_else = any(p.startswith("ELSE=") for p in parts)
        if not (has_then and has_else):
            reasons.append(Reason("L2-OPD01", st.line,
                                  "IF/THEN/ELSE requires both branches present (SPEC 11.2)"))
        for p in parts:
            if p.startswith(("THEN=", "ELSE=")):
                tgt = p.split("=", 1)[1]
                if not tgt.isdigit() or int(tgt) <= st.number:
                    reasons.append(Reason("L2-OPD01", st.line,
                                          f"branch target '{tgt}' must be a forward step "
                                          f"number (totality, SPEC 11.3)"))
        for p in parts:
            if not p.startswith(("THEN=", "ELSE=")) and _is_register_token(p):
                _require_bound(p, st, bound, reasons, "comparand")

    elif op == "EXECUTE":
        if not parts or parts[0] not in regs.procedures:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"EXECUTE target '{parts[0] if parts else ''}' not in "
                                  f"declared procedure registry (SPEC 11.2)"))
        else:
            arity = int(regs.procedures[parts[0]]["arity"])
            if len(parts) - 1 != arity:
                reasons.append(Reason("L2-OPD01", st.line,
                                      f"EXECUTE '{parts[0]}' arity {arity}, "
                                      f"{len(parts) - 1} operand(s) given"))

    elif op == "CONVERT":
        if len(parts) != 2:
            reasons.append(Reason("L2-OPD01", st.line, "CONVERT operand form: converter; source"))
            return
        conv, src = parts
        if conv not in regs.converters:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"converter '{conv}' not registered (SPEC 11.2)"))
        if _is_register_token(src):
            _require_bound(src, st, bound, reasons, "source")
            if conv in regs.converters and src in regs.registers:
                from_type = regs.converters[conv]["from_type"]
                reg_type = regs.registers[src]["type"]
                if reg_type != from_type:
                    reasons.append(Reason("L2-OPD01", st.line,
                                          f"CONVERT input type '{reg_type}' does not match "
                                          f"converter from_type '{from_type}' (SPEC 11.2)"))

    elif op == "DECLARE":
        if len(parts) < 2 or parts[0] not in ("TYPE", "PROCEDURE", "REGISTER"):
            reasons.append(Reason("L2-OPD01", st.line,
                                  "DECLARE operand form: kind; name; ... where kind is "
                                  "TYPE, PROCEDURE, or REGISTER (SPEC 11.2)"))

    elif op == "SLOT":
        kv = {}
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                kv[k] = v
        missing = SLOT_CONTRACT_KEYS - set(kv)
        if missing:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"SLOT contract incomplete: missing {sorted(missing)} "
                                  f"(SPEC 11.2: grounding key + charset law + type + "
                                  f"blocklist; the charset law is always in force)"))
            return
        if kv["type"] not in regs.types:
            reasons.append(Reason("L2-TYP01", st.line,
                                  f"SLOT type '{kv['type']}' is not a registered block type"))
        if _is_register_token(kv["ground"]):
            _require_bound(kv["ground"], st, bound, reasons, "grounding")

    elif op == "GATE":
        target = parts[0] if parts else ""
        if target not in slot_bound:
            reasons.append(Reason("L2-OPD01", st.line,
                                  f"GATE operand '{target}' is not a SLOT-bound register; "
                                  f"the verdict binds to a SLOT payload (SPEC 11.2)"))

    elif op == "OUTPUT_PRINT":
        target = parts[0] if parts else ""
        if _is_register_token(target):
            _require_bound(target, st, bound, reasons, "payload")
        if st.style == "-":
            reasons.append(Reason("L2-OPD01", st.line,
                                  "OUTPUT_PRINT requires a declared type in the style "
                                  "column (SPEC 11.2: type declared)"))

    elif op == "LABEL":
        # SPEC 11.2 (rc.2): operand is the label text; the bind column names
        # the receiving register. Charset legality is already Layer 1's job.
        if st.operand == "-":
            reasons.append(Reason("L2-OPD01", st.line,
                                  "LABEL operand is the label text and MUST be "
                                  "present (SPEC 11.2)"))


def _numeric_or_operator(tok: str) -> bool:
    if tok in ("+", "-", "*", "/"):
        return True
    t = tok[1:] if tok.startswith("-") else tok
    return t.replace(".", "", 1).isdigit()
