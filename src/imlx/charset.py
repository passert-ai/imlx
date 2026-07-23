"""
imlx.charset
============
The closed alphabet (SPEC Section 6) and Layer 1 character law.

Binary determinism: every check is a membership test over an enumerated set.
Absence from the allowlist is what forbids (Law 1); the forbidden list in
SPEC 6.3 exists only so this module can emit useful reason codes.

Spec basis (SPEC.md v0.1.0-rc.1):
- 5.1 encoding and line discipline
- 6.1 allowed characters (content space)
- 6.2 allowed constructs
- 6.4 straight quote codification
- 9   the @ reference namespace (program/declaration space only)

IMPLEMENTATION NOTES (ratified in SPEC v0.1.0-rc.2):
- PROGRAM_SPACE_EXTRA: characters permitted inside program-space and
  declaration-space pipe-table cells beyond the content alphabet. `@` and
  `=` are attested by SPEC Appendix B/D examples; `< > +` are included to
  make SELECT predicates and COMPUTE operators expressible per 11.2
  ("closed operator set"). Interpretation, not verbatim spec text.
"""

__version__ = "0.1.0"

import re

# ---------------------------------------------------------------------------
# Character sets (SPEC 6.1, 6.4)
# ---------------------------------------------------------------------------

_LETTERS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
_DIGITS = set("0123456789")

# Punctuation allowed in content space, subject to positional rules
# (SPEC 6.1). Straight double quote and apostrophe per 6.4.
_CONTENT_PUNCT = set(". , : ; - ' \" ( ) [ ] | * # $ %".split()) | {"/", "?"}

#: Every character legal anywhere in content space (positional rules are
#: enforced in layer1, not here). LF is handled at the line level.
CONTENT_CHARS = _LETTERS | _DIGITS | {" "} | _CONTENT_PUNCT

#: Characters that MUST appear only inside $-fences in content space
#: (SPEC 6.2 math fencing). `%` bare is legal only within %%PAGEBREAK%%.
MATH_ONLY_CHARS = set("<>=+")

#: Extra characters legal inside program-space / declaration-space /
#: trace-space pipe-table cells (see module docstring).
PROGRAM_SPACE_EXTRA = {"@", "=", "<", ">", "+", "_"}

#: Full alphabet for program/declaration/trace table cells.
PROGRAM_CELL_CHARS = CONTENT_CHARS | PROGRAM_SPACE_EXTRA

#: Characters legal on an envelope opening line, beyond content letters and
#: digits (SPEC 7.1): ::: { } = " - and space are all consumed by the exact
#: line regex in layer1; no free-form check applies to envelope lines.

# ---------------------------------------------------------------------------
# Exact tokens and line-form regexes
# ---------------------------------------------------------------------------

PAGEBREAK_TOKEN = "%%PAGEBREAK%%"

#: SPEC 5.2 header line 1.
HEADER_IMLX_RE = re.compile(r"^IMLX: (\d+\.\d+)$")

#: SPEC 5.2 header line 2: external pairing or the literal INLINE.
HEADER_DECL_RE = re.compile(
    r"^DECLARATIONS: (?:(INLINE)|([A-Za-z0-9._-]+\.imlx); (\d+\.\d+))$"
)

#: SPEC 10.3 declaration-file third header line.
HEADER_DECLVER_RE = re.compile(r"^DECL_VERSION: (\d+\.\d+)$")

#: SPEC 7.1 envelope opening line, exact form.
ENVELOPE_OPEN_RE = re.compile(r'^::: \{custom-style="([A-Za-z][A-Za-z0-9_]*)"\}$')

#: SPEC 7.1 envelope closing line.
ENVELOPE_CLOSE = ":::"

#: Headings: #, ##, ### + one space (SPEC 6.2). Deeper levels are illegal.
HEADING_RE = re.compile(r"^(#{1,3}) (\S.*)$")
HEADING_TOO_DEEP_RE = re.compile(r"^#{4,}")

#: Bullets: `* ` and one indented sublevel `* * ` (SPEC 6.2).
BULLET_RE = re.compile(r"^\* (?:\* )?(\S.*)$")

#: Legal-numbered list line (SPEC 6.2): 1.1, 1.2 ... at line start.
LEGAL_LIST_RE = re.compile(r"^\d+\.\d+ \S")

#: Step numbering (SPEC 6.2): Step 1:, Step 2:, ... at line start.
STEP_LINE_RE = re.compile(r"^Step \d+: \S")

#: Pipe-table row: starts and ends with |, at least two pipes.
TABLE_ROW_RE = re.compile(r"^\|.*\|$")

#: Pipe-table separator row (SPEC 6.2): | :--- | :--- |
TABLE_SEP_CELL = ":---"

#: Reference name (SPEC 9): letters, digits, _, beginning with a letter.
REFERENCE_RE = re.compile(r"^@([A-Za-z][A-Za-z0-9_]*)$")
REFERENCE_SCAN_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_]*)")

#: Program-table header cells, exact (SPEC 11.1).
PROGRAM_HEADER = ["step", "opcode", "operand", "bind", "style"]

#: Trace-table header cells, exact (SPEC 13.6).
TRACE_HEADER = ["seq", "event", "step", "opcode", "subject", "outcome", "digest"]

#: DECLARE section heading (SPEC 10.4): `# DECLARE <kind>`.
DECLARE_HEADING_RE = re.compile(r"^# DECLARE ([A-Z]+)$")


# ---------------------------------------------------------------------------
# Character-law checks
# ---------------------------------------------------------------------------

def illegal_content_chars(text: str) -> list[str]:
    """Characters in ``text`` outside the content-space alphabet, fence-aware.

    Outside $-fences the alphabet is CONTENT_CHARS; inside a fence the
    mathematical symbols (SPEC 6.2) are additionally legal. Positional
    rules remain layer1's job; this is membership.
    """
    outside, inside, _balanced = split_math_fences(text)
    bad = {c for c in outside if c not in CONTENT_CHARS}
    bad |= {c for c in inside if c not in CONTENT_CHARS | MATH_ONLY_CHARS}
    return sorted(bad)


def illegal_program_cell_chars(text: str) -> list[str]:
    """Characters in a program/declaration/trace cell outside its alphabet."""
    return sorted({c for c in text if c not in PROGRAM_CELL_CHARS})


def split_math_fences(line: str):
    """Split a line into (outside, inside) character streams by $-fences.

    Returns (outside_text, inside_text, balanced) where ``balanced`` is
    False if the line ends inside an unclosed fence (fences MUST close
    within the line; multi-line blocks are hard-broken lines, SPEC 6.2).
    """
    outside: list[str] = []
    inside: list[str] = []
    in_fence = False
    for ch in line:
        if ch == "$":
            in_fence = not in_fence
            continue
        (inside if in_fence else outside).append(ch)
    return "".join(outside), "".join(inside), not in_fence


def bare_math_chars_outside_fences(line: str) -> list[str]:
    """Math-only characters appearing outside $-fences on a content line.

    ``%`` is excluded when the line is exactly %%PAGEBREAK%% (caller
    handles that line form before reaching here).
    """
    outside, _inside, _balanced = split_math_fences(line)
    hits = [c for c in outside if c in MATH_ONLY_CHARS]
    if "%" in outside:
        hits.append("%")
    return sorted(set(hits))
