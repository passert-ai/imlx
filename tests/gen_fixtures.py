"""
Generate the conformance corpus and adversarial suite (SPEC 15.1, 15.2).

Every fixture is written byte-exactly with LF terminators and a trailing
final newline (except fixtures whose required failure is precisely the
absence of one). Run from the tests/ directory:

    python3 gen_fixtures.py

The manifest pairs each artifact with its required verdict and, for FAIL
fixtures, its required reason code (SPEC 15.1). The corpus is the shared
oracle across implementations.
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
CONF = HERE / "conformance"
ADV = HERE / "adversarial"
CONF.mkdir(exist_ok=True)
ADV.mkdir(exist_ok=True)

manifest_conf: list[dict] = []
manifest_adv: list[dict] = []


def w(dirpath: Path, name: str, text: str, binary: bytes | None = None) -> None:
    if binary is not None:
        (dirpath / name).write_bytes(binary)
    else:
        (dirpath / name).write_text(text, encoding="utf-8", newline="\n")


def fx(manifest: list, artifact: str, l1: str, l2: str | None, codes: list[str],
       decls: str | None = None, note: str = "") -> None:
    manifest.append({"artifact": artifact, "decls": decls, "expect_l1": l1,
                     "expect_l2": l2, "codes": codes, "note": note})


# ===========================================================================
# Shared declaration file (corrected Appendix B: Policy_Std declared)
# ===========================================================================

CATALOG_DECLS = """IMLX: 0.1
DECLARATIONS: INLINE
DECL_VERSION: 1.0

# DECLARE TYPE

| name | capabilities |
| :--- | :--- |
| PartSummary | - |
| InspectionSteps | legal_lists |

# DECLARE SYMBOL

| sigil_name | target |
| :--- | :--- |
| Corpus_Catalog | catalog-2026.imlx |

# DECLARE REGISTER

| name | type |
| :--- | :--- |
| reg_part | PartRecord |

# DECLARE POLICY

| name | kind | payload_ref |
| :--- | :--- | :--- |
| Policy_Std | blocklist | policies-std.imlx |
"""

PX140 = """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0

# PX-140 Service Brief

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LOAD | @Corpus_Catalog | reg_corpus | - |
| 2 | QUERY | reg_corpus; part_no; "PX-140" | reg_part | - |
| 3 | EXTRACT | reg_part; torque_spec | reg_torque | - |
| 4 | SLOT | ground=reg_part; type=PartSummary; blocklist=@Policy_Std | reg_summary | PartSummary |
| 5 | GATE | reg_summary | reg_verdict | - |
| 6 | OUTPUT_PRINT | reg_summary | - | PartSummary |
"""

w(CONF, "catalog-decls.imlx", CATALOG_DECLS)
w(CONF, "px140-brief.imlx", PX140)
fx(manifest_conf, "px140-brief.imlx", "PASS", "PASS", [], "catalog-decls.imlx",
   "flagship: corrected SPEC Appendix B program, external declaration mode")
fx(manifest_conf, "catalog-decls.imlx", "PASS", "PASS", [], None,
   "a declaration file is itself an IMLX artifact (SPEC 10.3)")

# ===========================================================================
# PASS fixtures
# ===========================================================================

w(CONF, "content-basics.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

# Field Notes

## Observations

A plain paragraph with straight "quotes" and an apostrophe's use.
It continues on a second hard-broken line; punctuation like (this) is fine.

* first bullet
* second bullet
* * indented sublevel

The relation $a + b = c$ and the bound $x < 10$ stay inside fences.

%%PAGEBREAK%%

| site | reading |
| :--- | :--- |
| north | 12.4 |
| south | 9.87 |
""")
fx(manifest_conf, "content-basics.imlx", "PASS", "PASS", [], None,
   "headings, bullets, sublevel, math fencing, pagebreak, content table")

w(CONF, "capability-pass.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

# DECLARE TYPE

| name | capabilities |
| :--- | :--- |
| ProcedureSteps | legal_lists |

::: {custom-style="ProcedureSteps"}
Step 1: open the intake valve
1.1 confirm the seal
1.2 record the reading
Step 2: close the intake valve
:::
""")
fx(manifest_conf, "capability-pass.imlx", "PASS", "PASS", [], None,
   "legal lists and Step numbering inside a legal_lists-capable type (SPEC 6.2, 8)")

# ===========================================================================
# FAIL fixtures: one per Layer 1 reason code
# ===========================================================================

w(CONF, "f-enc01-crlf.imlx", "", binary=b"IMLX: 0.1\r\nDECLARATIONS: INLINE\r\n")
fx(manifest_conf, "f-enc01-crlf.imlx", "FAIL", None, ["L1-ENC01"], None, "CRLF")

w(CONF, "f-enc01-no-final-newline.imlx", "",
  binary=b"IMLX: 0.1\nDECLARATIONS: INLINE\n\nA line without a final newline")
fx(manifest_conf, "f-enc01-no-final-newline.imlx", "FAIL", None, ["L1-ENC01"], None,
   "trailing final newline is REQUIRED (SPEC 5.1)")

w(CONF, "f-hdr01-malformed.imlx", """IMLX: 0.1
DECLARATION FILE: catalog-decls.imlx

Body text.
""")
fx(manifest_conf, "f-hdr01-malformed.imlx", "FAIL", None, ["L1-HDR01"], None,
   "line 2 is not a legal pairing line")

w(CONF, "f-chr01-emdash.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

A sentence with an em dash \u2014 fails the closed alphabet.
""")
fx(manifest_conf, "f-chr01-emdash.imlx", "FAIL", None, ["L1-CHR01"], None, "em dash")

w(CONF, "f-con01-emphasis.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

This uses **bold emphasis** which is banned outside math fences.
""")
fx(manifest_conf, "f-con01-emphasis.imlx", "FAIL", None, ["L1-CON01"], None,
   "asterisk emphasis (SPEC 6.3)")

w(CONF, "f-env01-nested.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

::: {custom-style="Outer"}
outer content
::: {custom-style="Inner"}
inner content
:::
:::
""")
fx(manifest_conf, "f-env01-nested.imlx", "FAIL", None, ["L1-ENV01"], None,
   "envelopes MUST NOT nest (SPEC 7.1)")

w(CONF, "f-tbl01-ragged.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

| site | reading |
| :--- | :--- |
| north | 12.4 | extra |
""")
fx(manifest_conf, "f-tbl01-ragged.imlx", "FAIL", None, ["L1-TBL01"], None,
   "row cell count differs from header")

w(CONF, "f-pgm01-gap.imlx", """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LOAD | @Corpus_Catalog | reg_corpus | - |
| 3 | EXTRACT | reg_corpus; torque_spec | reg_torque | - |
""")
fx(manifest_conf, "f-pgm01-gap.imlx", "FAIL", None, ["L1-PGM01"], "catalog-decls.imlx",
   "step counter gap (SPEC 11.1)")

# ===========================================================================
# FAIL fixtures: Layer 2 reason codes
# ===========================================================================

w(CONF, "f-pair01-version.imlx", """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 2.0

# Version Mismatch

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LOAD | @Corpus_Catalog | reg_corpus | - |
""")
fx(manifest_conf, "f-pair01-version.imlx", "PASS", "FAIL", ["L2-PAIR01"],
   "catalog-decls.imlx", "artifact demands 2.0; file declares DECL_VERSION 1.0")

w(CONF, "f-typ01-unregistered.imlx", """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0

::: {custom-style="UnknownType"}
content in an unregistered type
:::
""")
fx(manifest_conf, "f-typ01-unregistered.imlx", "PASS", "FAIL", ["L2-TYP01"],
   "catalog-decls.imlx", "unresolvable block type (Law 4)")

w(CONF, "f-ref01-unresolved.imlx", """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LOAD | @Corpus_Missing | reg_corpus | - |
""")
fx(manifest_conf, "f-ref01-unresolved.imlx", "PASS", "FAIL", ["L2-REF01"],
   "catalog-decls.imlx", "zero targets for @Corpus_Missing (SPEC 9)")

w(CONF, "f-reg01-use-before-bind.imlx", """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | EXTRACT | reg_part; torque_spec | reg_torque | - |
""")
fx(manifest_conf, "f-reg01-use-before-bind.imlx", "PASS", "FAIL", ["L2-REG01"],
   "catalog-decls.imlx", "register used before bind (SPEC 11.2)")

w(CONF, "f-opd01-slot-contract.imlx", """IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LOAD | @Corpus_Catalog | reg_corpus | - |
| 2 | SLOT | ground=reg_corpus; type=PartSummary | reg_summary | PartSummary |
""")
fx(manifest_conf, "f-opd01-slot-contract.imlx", "PASS", "FAIL", ["L2-OPD01"],
   "catalog-decls.imlx", "SLOT contract missing blocklist (SPEC 11.2)")

w(CONF, "f-dup01-decl.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

# DECLARE TYPE

| name | capabilities |
| :--- | :--- |
| Summary | - |
| Summary | legal_lists |
""")
fx(manifest_conf, "f-dup01-decl.imlx", "PASS", "FAIL", ["L2-DUP01"], None,
   "duplicate declaration: no precedence, no overlay, no merge (SPEC 10.2)")

# ---- L2-CAP01 and L2-DEC01 (SPEC Appendix C, rc.2) ----

w(CONF, "f-cap01-missing-capability.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

# DECLARE TYPE

| name | capabilities |
| :--- | :--- |
| PlainProse | - |

::: {custom-style="PlainProse"}
1.1 a legal-numbered line in a type without the capability
:::
""")
fx(manifest_conf, "f-cap01-missing-capability.imlx", "PASS", "FAIL", ["L2-CAP01"], None,
   "PROPOSED CODE: construct requires undeclared type capability (SPEC 6.2, 8)")

w(CONF, "f-dec01-unknown-kind.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

# DECLARE GRAMMAR

| name | rule |
| :--- | :--- |
| Extension | anything |
""")
fx(manifest_conf, "f-dec01-unknown-kind.imlx", "PASS", "FAIL", ["L2-DEC01"], None,
   "PROPOSED CODE: unknown DECLARE kind; also an in-band grammar-modification "
   "attempt made inert (Law 3)")

# ===========================================================================
# Adversarial suite (SPEC 15.2)
# ===========================================================================

def adv(name: str, text: str, l1: str, l2: str | None, codes: list[str],
        note: str, binary: bytes | None = None, decls: str | None = None) -> None:
    w(ADV, name, text, binary=binary)
    manifest_adv.append({"artifact": name, "decls": decls, "expect_l1": l1,
                         "expect_l2": l2, "codes": codes, "note": note})

HDR = "IMLX: 0.1\nDECLARATIONS: INLINE\n\n"

adv("a-zero-width.imlx", HDR + "Smuggled\u200bcharacter.\n", "FAIL", None,
    ["L1-CHR01"], "zero-width space U+200B")
adv("a-nbsp.imlx", HDR + "A non\u00a0breaking space.\n", "FAIL", None,
    ["L1-CHR01"], "NBSP U+00A0")
adv("a-smart-quote.imlx", HDR + "A \u201csmart\u201d quotation.\n", "FAIL", None,
    ["L1-CHR01"], "curly quotes U+201C/U+201D")
adv("a-confusable-cyrillic.imlx", HDR + "P\u0430ss with a Cyrillic a.\n", "FAIL", None,
    ["L1-CHR01"], "unicode confusable U+0430 in latin word")
adv("a-ellipsis.imlx", HDR + "Trailing off\u2026\n", "FAIL", None,
    ["L1-CHR01"], "ellipsis character U+2026")
adv("a-ampersand.imlx", HDR + "Salt & pepper.\n", "FAIL", None,
    ["L1-CHR01"], "ampersand")
adv("a-unicode-bullet.imlx", HDR + "\u2022 a unicode bullet\n", "FAIL", None,
    ["L1-CHR01"], "bullet U+2022")
adv("a-backtick-fence.imlx", HDR + "```\ncode\n```\n", "FAIL", None,
    ["L1-CHR01"], "backtick fences")
adv("a-html-tag.imlx", HDR + "Some <b>bold</b> html.\n", "FAIL", None,
    ["L1-CHR01"], "HTML tags: < and > are fence-only mathematical symbols")
adv("a-tab.imlx", "", "FAIL", None, ["L1-ENC01"], "tab character (SPEC 5.1)",
    binary=b"IMLX: 0.1\nDECLARATIONS: INLINE\n\nA\ttab.\n")
adv("a-yaml-indent.imlx", HDR + "config:\n  key: value\n", "FAIL", None,
    ["L1-CON01"], "YAML-lookalike indentation (leading whitespace)")
adv("a-envelope-trailing.imlx",
    HDR + '::: {custom-style="X"} trailing\ncontent\n:::\n', "FAIL", None,
    ["L1-CHR01"], "envelope abuse: tokens outside the two exact line forms")
adv("a-step-zero.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 0 | LABEL | alpha | reg_a | - |
""", "FAIL", None, ["L1-PGM01"], "step counter starts at 0")
adv("a-step-duplicate.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LABEL | alpha | reg_a | - |
| 1 | LABEL | beta | reg_b | - |
""", "FAIL", None, ["L1-PGM01"], "duplicate step number")
adv("a-symbol-ambiguity.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

# DECLARE SYMBOL

| sigil_name | target |
| :--- | :--- |
| Corpus_A | one.imlx |
| Corpus_A | two.imlx |
""", "PASS", "FAIL", ["L2-DUP01"],
    "reference ambiguity: two targets for one sigil (SPEC 9, 10.2)")
adv("a-inband-header.imlx",
    HDR + "The literal text IMLX: 9.9 in a paragraph is inert content.\n",
    "PASS", "PASS", [],
    "in-band grammar modification attempt: documents cannot say anything "
    "about IMLX (Law 3); the gate treats it as plain text")
adv("a-excluded-verb.imlx", """IMLX: 0.1
DECLARATIONS: INLINE

| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | SUMMARIZE | reg_a | reg_b | - |
""", "PASS", "FAIL", ["L2-OPD01"],
    "semantic verb outside the boundary (SPEC 12): SLOT work, not an opcode")

# ===========================================================================

w(CONF, "manifest.json", json.dumps(manifest_conf, indent=2) + "\n")
w(ADV, "manifest.json", json.dumps(manifest_adv, indent=2) + "\n")
print(f"conformance: {len(manifest_conf)} fixtures; adversarial: {len(manifest_adv)} fixtures")
