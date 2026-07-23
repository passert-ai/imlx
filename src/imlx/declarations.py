"""
imlx.declarations
=================
The declaration resolver (SPEC Section 10). Populates the registries Layer 2
validates against: block types (with capabilities), procedures, converters,
registers, symbols, policy data.

- Exactly one declaration source per artifact, named by the header pairing
  line (10.2). External is canonical; INLINE is permitted.
- A declaration file is itself an IMLX artifact (10.3): same parser, no
  second format. It MUST pass Layer 1.
- Duplicates fail the gate: L2-DUP01. No precedence, no overlay, no merge.

L2-DEC01 ("malformed declaration table": unknown DECLARE kind or wrong
column set) is ratified in SPEC Appendix C as of v0.1.0-rc.2 and ships
here with its fixtures.
"""

__version__ = "0.1.0"

from dataclasses import dataclass, field

from . import charset as cs
from .layer1 import Document, Reason, Table, Verdict, gate_layer1_bytes

#: SPEC 10.4: registry kinds and their REQUIRED columns.
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "TYPE": ["name", "capabilities"],
    "PROCEDURE": ["name", "arity", "operand_schema"],
    "CONVERTER": ["name", "from_type", "to_type"],
    "REGISTER": ["name", "type"],
    "SYMBOL": ["sigil_name", "target"],
    "POLICY": ["name", "kind", "payload_ref"],
}

#: Capabilities defined by SPEC 8. The only sanctioned relaxation mechanism.
KNOWN_CAPABILITIES = {"legal_lists", "-"}


@dataclass
class Registries:
    """The declaration space in force for one artifact."""
    types: dict[str, dict] = field(default_factory=dict)        # name -> {capabilities}
    procedures: dict[str, dict] = field(default_factory=dict)   # name -> {arity, operand_schema}
    converters: dict[str, dict] = field(default_factory=dict)   # name -> {from_type, to_type}
    registers: dict[str, dict] = field(default_factory=dict)    # name -> {type}
    symbols: dict[str, str] = field(default_factory=dict)       # sigil_name -> target
    policies: dict[str, dict] = field(default_factory=dict)     # name -> {kind, payload_ref}
    source_name: str = ""
    source_version: str = ""

    _KIND_MAP = {
        "TYPE": ("types", "name"),
        "PROCEDURE": ("procedures", "name"),
        "CONVERTER": ("converters", "name"),
        "REGISTER": ("registers", "name"),
        "SYMBOL": ("symbols", "sigil_name"),
        "POLICY": ("policies", "name"),
    }

    def type_capabilities(self, type_name: str) -> set[str]:
        entry = self.types.get(type_name)
        if not entry:
            return set()
        caps = entry.get("capabilities", "-")
        return set() if caps == "-" else {c.strip() for c in caps.split(";")}


def parse_declarations(doc: Document, reasons: list[Reason]) -> Registries:
    """Build registries from a document's # DECLARE sections (SPEC 10.4).

    Works identically for a declaration file and for an INLINE artifact's
    own declaration section: one parser, no second format (SPEC 10.3).
    """
    regs = Registries()
    for tbl in doc.declaration_tables:
        _ingest_table(tbl, regs, reasons)
    return regs


def _ingest_table(tbl: Table, regs: Registries, reasons: list[Reason]) -> None:
    kind = tbl.declare_kind or ""
    required = REQUIRED_COLUMNS.get(kind)
    if required is None:
        reasons.append(Reason("L2-DEC01", tbl.start_line,
                              f"unknown DECLARE kind '{kind}' (SPEC 10.4 enumerates "
                              f"{sorted(REQUIRED_COLUMNS)})"))
        return
    if tbl.header_cells != required:
        reasons.append(Reason("L2-DEC01", tbl.start_line,
                              f"DECLARE {kind} requires columns {required}, "
                              f"found {tbl.header_cells} (SPEC 10.4)"))
        return

    attr, key_col = Registries._KIND_MAP[kind]
    store = getattr(regs, attr)
    key_idx = required.index(key_col)

    for cells, ln in zip(tbl.rows, tbl.row_lines):
        name = cells[key_idx]
        if name in store:
            reasons.append(Reason("L2-DUP01", ln,
                                  f"duplicate {kind} declaration '{name}' "
                                  f"(SPEC 10.2: no precedence, no overlay, no merge)"))
            continue
        if kind == "SYMBOL":
            store[name] = cells[required.index("target")]
        else:
            store[name] = {col: cells[idx] for idx, col in enumerate(required) if idx != key_idx}
        # entry-shape checks decidable without other registries
        if kind == "TYPE":
            caps = store[name]["capabilities"]
            unknown = {c.strip() for c in caps.split(";")} - KNOWN_CAPABILITIES
            if caps != "-" and unknown:
                reasons.append(Reason("L2-DEC01", ln,
                                      f"unknown capability {sorted(unknown)} "
                                      f"(SPEC 8 defines: legal_lists)"))
        if kind == "PROCEDURE" and not store[name]["arity"].isdigit():
            reasons.append(Reason("L2-DEC01", ln, "PROCEDURE arity must be a non-negative integer"))
        if kind == "SYMBOL" and not cs.REFERENCE_RE.match("@" + name):
            reasons.append(Reason("L2-DEC01", ln,
                                  "sigil_name must be letters, digits, _, beginning "
                                  "with a letter (SPEC 9)"))


def load_external_source(path_bytes: bytes, file_name: str,
                         expected_name: str, expected_version: str,
                         reasons: list[Reason]) -> Registries | None:
    """Load and verify an external declaration file (SPEC 5.2, 10.3).

    The Layer 2 gate MUST verify that the declaration source it was given
    matches the name and version the artifact demands (L2-PAIR01), and the
    file itself MUST pass Layer 1.
    """
    verdict, decl_doc = gate_layer1_bytes(path_bytes, file_name)
    if not verdict.passed:
        reasons.append(Reason("L2-PAIR01", 0,
                              f"declaration file '{file_name}' fails Layer 1 "
                              f"({verdict.reasons[0].code} at its line "
                              f"{verdict.reasons[0].line}); a declaration file MUST "
                              f"pass Layer 1 like any artifact (SPEC 10.3)"))
        return None

    if file_name != expected_name:
        reasons.append(Reason("L2-PAIR01", 2,
                              f"artifact header pairs '{expected_name}' but was given "
                              f"'{file_name}' (SPEC 5.2)"))
        return None

    if decl_doc.header.decl_mode != "INLINE" or decl_doc.header.file_decl_version is None:
        reasons.append(Reason("L2-PAIR01", 0,
                              f"'{file_name}' is not a declaration file: its DECLARATIONS "
                              f"line must read INLINE and it must carry DECL_VERSION "
                              f"(SPEC 10.3)"))
        return None

    if decl_doc.header.file_decl_version != expected_version:
        reasons.append(Reason("L2-PAIR01", 2,
                              f"artifact header demands version {expected_version}; "
                              f"'{file_name}' declares DECL_VERSION "
                              f"{decl_doc.header.file_decl_version} (SPEC 5.2)"))
        return None

    regs = parse_declarations(decl_doc, reasons)
    regs.source_name = file_name
    regs.source_version = decl_doc.header.file_decl_version
    return regs
