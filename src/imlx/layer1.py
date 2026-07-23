"""
imlx.layer1
===========
The Layer 1 gate (SPEC 14.2): encoding, header, charset law, construct law,
envelope well-formedness, table shape, step-number discipline. Requires
nothing but the artifact. Emits one bit plus diagnostic reason codes
(Appendix C) that never soften the verdict.

On PASS, also returns a parsed Document consumed by Layer 2 and the
executor. On FAIL the Document is None; nothing downstream runs (SPEC 13.5).
"""

__version__ = "0.1.0"

from dataclasses import dataclass, field

from . import charset as cs

# ---------------------------------------------------------------------------
# Verdict model
# ---------------------------------------------------------------------------

@dataclass
class Reason:
    code: str
    line: int  # 1-based; 0 = whole-artifact
    message: str

    def to_dict(self) -> dict:
        return {"code": self.code, "line": self.line, "message": self.message}


@dataclass
class Verdict:
    """One bit per layer (SPEC 14.3). Reasons are diagnostics only."""
    passed: bool
    reasons: list[Reason] = field(default_factory=list)

    @property
    def bit(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def to_dict(self) -> dict:
        return {"verdict": self.bit, "reasons": [r.to_dict() for r in self.reasons]}


# ---------------------------------------------------------------------------
# Document model (produced on Layer 1 PASS)
# ---------------------------------------------------------------------------

@dataclass
class Header:
    spec_version: str
    decl_mode: str            # "INLINE" or "EXTERNAL"
    decl_name: str | None     # external pairing target file name
    decl_version: str | None  # external pairing target version
    file_decl_version: str | None  # DECL_VERSION line (declaration files)


@dataclass
class Heading:
    level: int
    text: str
    line: int


@dataclass
class PageBreak:
    line: int


@dataclass
class Paragraph:
    lines: list[str]
    start_line: int


@dataclass
class BulletList:
    lines: list[str]
    start_line: int


@dataclass
class Table:
    space: str                # "content" | "program" | "declaration" | "trace"
    header_cells: list[str]
    rows: list[list[str]]
    row_lines: list[int]      # line number of each data row
    start_line: int
    declare_kind: str | None  # for declaration tables: TYPE, SYMBOL, ...


@dataclass
class Envelope:
    type_name: str
    lines: list[str]
    start_line: int
    legal_list_lines: list[int] = field(default_factory=list)


@dataclass
class Document:
    name: str
    header: Header
    elements: list = field(default_factory=list)

    @property
    def program_tables(self) -> list[Table]:
        return [e for e in self.elements if isinstance(e, Table) and e.space == "program"]

    @property
    def declaration_tables(self) -> list[Table]:
        return [e for e in self.elements if isinstance(e, Table) and e.space == "declaration"]

    @property
    def envelopes(self) -> list[Envelope]:
        return [e for e in self.elements if isinstance(e, Envelope)]


# ---------------------------------------------------------------------------
# Layer 1 gate
# ---------------------------------------------------------------------------

def gate_layer1_bytes(data: bytes, name: str) -> tuple[Verdict, Document | None]:
    """Full Layer 1 verdict from raw bytes (SPEC 5.1 encoding discipline)."""
    reasons: list[Reason] = []

    # -- 5.1 encoding and line discipline -> L1-ENC01
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return Verdict(False, [Reason("L1-ENC01", 0, "artifact is not valid UTF-8")]), None

    if "\r" in text:
        reasons.append(Reason("L1-ENC01", _line_of(text, "\r"), "CR or CRLF line terminator"))
    if "\t" in text:
        reasons.append(Reason("L1-ENC01", _line_of(text, "\t"), "tab character"))
    for ch in set(text):
        if ord(ch) < 32 and ch not in ("\n", "\r", "\t"):
            reasons.append(Reason("L1-ENC01", _line_of(text, ch),
                                  "control character U+%04X" % ord(ch)))
    if not text.endswith("\n"):
        reasons.append(Reason("L1-ENC01", 0, "missing REQUIRED trailing final newline"))
    if reasons:
        return Verdict(False, reasons), None

    return gate_layer1_text(text, name)


def gate_layer1_text(text: str, name: str) -> tuple[Verdict, Document | None]:
    """Layer 1 over decoded text known to satisfy encoding discipline."""
    reasons: list[Reason] = []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the REQUIRED final newline

    # -- 5.2 header -> L1-HDR01
    header, header_len = _parse_header(lines, reasons)
    if header is None:
        return Verdict(False, reasons), None

    body = lines[header_len:]
    body_offset = header_len  # 0-based index of first body line
    if body:
        if body[0] != "":
            reasons.append(Reason("L1-HDR01", header_len + 1,
                                  "header must be followed by a blank line"))
        else:
            body = body[1:]
            body_offset += 1

    doc = Document(name=name, header=header)
    _parse_body(body, body_offset, doc, reasons)
    _check_step_discipline(doc, reasons)

    passed = not reasons
    return Verdict(passed, reasons), (doc if passed else None)


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _parse_header(lines: list[str], reasons: list[Reason]):
    if len(lines) < 2:
        reasons.append(Reason("L1-HDR01", 1, "artifact shorter than the two-line header"))
        return None, 0

    m1 = cs.HEADER_IMLX_RE.match(lines[0])
    if not m1:
        reasons.append(Reason("L1-HDR01", 1, "line 1 must be exactly 'IMLX: <version>'"))
        return None, 0
    spec_version = m1.group(1)
    if spec_version != "0.1":
        reasons.append(Reason("L1-HDR01", 1,
                              f"unsupported specification version {spec_version}; "
                              f"this gate validates version 0.1 exactly (SPEC 4.3)"))
        return None, 0

    m2 = cs.HEADER_DECL_RE.match(lines[1])
    if not m2:
        reasons.append(Reason("L1-HDR01", 2,
                              "line 2 must be 'DECLARATIONS: <file>.imlx; <version>' "
                              "or 'DECLARATIONS: INLINE'"))
        return None, 0

    if m2.group(1) == "INLINE":
        decl_mode, decl_name, decl_version = "INLINE", None, None
    else:
        decl_mode, decl_name, decl_version = "EXTERNAL", m2.group(2), m2.group(3)

    header_len = 2
    file_decl_version = None
    if len(lines) > 2:
        m3 = cs.HEADER_DECLVER_RE.match(lines[2])
        if m3:
            file_decl_version = m3.group(1)
            header_len = 3
            if decl_mode != "INLINE":
                reasons.append(Reason("L1-HDR01", 3,
                                      "DECL_VERSION is legal only on a declaration file, "
                                      "whose DECLARATIONS line reads INLINE (SPEC 10.3)"))

    return Header(spec_version, decl_mode, decl_name, decl_version, file_decl_version), header_len


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------

def _parse_body(body: list[str], offset: int, doc: Document, reasons: list[Reason]) -> None:
    i = 0
    n = len(body)
    in_env: Envelope | None = None
    last_heading: Heading | None = None
    prev_blank = False

    def lineno(k: int) -> int:
        return offset + k + 1

    while i < n:
        raw = body[i]
        ln = lineno(i)

        # blank-line discipline (6.2 / 6.3)
        if raw == "":
            if prev_blank:
                reasons.append(Reason("L1-CON01", ln, "consecutive blank lines"))
            prev_blank = True
            i += 1
            continue
        prev_blank = False

        if raw != raw.strip():
            reasons.append(Reason("L1-CON01", ln, "leading or trailing whitespace"))
            raw = raw.strip()

        # ---- envelope machinery (7.1) ----
        m_open = cs.ENVELOPE_OPEN_RE.match(raw)
        if m_open:
            if in_env is not None:
                reasons.append(Reason("L1-ENV01", ln, "envelopes MUST NOT nest"))
            in_env = Envelope(type_name=m_open.group(1), lines=[], start_line=ln)
            i += 1
            continue
        if raw == cs.ENVELOPE_CLOSE:
            if in_env is None:
                reasons.append(Reason("L1-ENV01", ln, "envelope close without open"))
            else:
                doc.elements.append(in_env)
                in_env = None
            i += 1
            continue
        if ":::" in raw or "{" in raw or "}" in raw:
            reasons.append(Reason("L1-CHR01", ln,
                                  "{, }, and ::: are legal only in the two envelope "
                                  "line forms (SPEC 6.1, 7.1)"))
            i += 1
            continue

        # ---- inside an envelope: content-space lines, capability tracking ----
        if in_env is not None:
            if cs.LEGAL_LIST_RE.match(raw) or cs.STEP_LINE_RE.match(raw):
                in_env.legal_list_lines.append(ln)
            else:
                _check_content_line(raw, ln, reasons, allow_bullet=True)
            in_env.lines.append(raw)
            i += 1
            continue

        # ---- bare constructs outside envelopes ----
        if raw == cs.PAGEBREAK_TOKEN:
            doc.elements.append(PageBreak(ln))
            i += 1
            continue

        if cs.HEADING_TOO_DEEP_RE.match(raw):
            reasons.append(Reason("L1-CON01", ln, "heading deeper than ### (SPEC 6.2)"))
            i += 1
            continue
        m_h = cs.HEADING_RE.match(raw)
        if m_h:
            h = Heading(level=len(m_h.group(1)), text=m_h.group(2), line=ln)
            _check_content_text(m_h.group(2), ln, reasons)
            doc.elements.append(h)
            last_heading = h
            i += 1
            continue

        if cs.TABLE_ROW_RE.match(raw):
            i = _parse_table(body, i, offset, doc, last_heading, reasons)
            continue

        if cs.LEGAL_LIST_RE.match(raw) or cs.STEP_LINE_RE.match(raw):
            reasons.append(Reason("L1-CON01", ln,
                                  "legal-numbered lists and Step numbering are permitted "
                                  "only inside blocks whose type declares the legal_lists "
                                  "capability (SPEC 6.2); outside any envelope they can "
                                  "never be legal"))
            i += 1
            continue

        if raw.startswith("- ") or raw.startswith("+ "):
            reasons.append(Reason("L1-CON01", ln,
                                  "bullet form other than '* ' (SPEC 6.2: one form only)"))
            i += 1
            continue

        if raw.startswith("* "):
            start = i
            bl = BulletList(lines=[], start_line=ln)
            while i < n and body[i].startswith("* "):
                m_b = cs.BULLET_RE.match(body[i])
                if not m_b:
                    reasons.append(Reason("L1-CON01", lineno(i),
                                          "malformed bullet line (SPEC 6.2)"))
                else:
                    _check_content_text(m_b.group(1), lineno(i), reasons)
                bl.lines.append(body[i])
                i += 1
            doc.elements.append(bl)
            continue

        # ---- default: paragraph line(s) ----
        start = i
        para = Paragraph(lines=[], start_line=ln)
        while i < n and body[i] != "" and _is_plain_text(body[i]):
            if body[i] != body[i].strip():
                reasons.append(Reason("L1-CON01", lineno(i),
                                      "leading or trailing whitespace"))
            _check_content_line(body[i].strip(), lineno(i), reasons, allow_bullet=False)
            para.lines.append(body[i])
            i += 1
        if not para.lines:  # defensive: consume one line to guarantee progress
            para.lines.append(body[i])
            i += 1
        doc.elements.append(para)

    if in_env is not None:
        reasons.append(Reason("L1-ENV01", in_env.start_line, "envelope never closed"))


def _is_plain_text(line: str) -> bool:
    s = line.strip()
    return not (
        cs.TABLE_ROW_RE.match(s)
        or cs.HEADING_RE.match(s)
        or cs.HEADING_TOO_DEEP_RE.match(s)
        or s.startswith("* ")
        or s == cs.PAGEBREAK_TOKEN
        or cs.ENVELOPE_OPEN_RE.match(s)
        or s == cs.ENVELOPE_CLOSE
    )


# ---------------------------------------------------------------------------
# Tables (6.2 shape; 11.1 program form; 13.6 trace form; 10.4 declarations)
# ---------------------------------------------------------------------------

def _parse_table(body, i, offset, doc, last_heading, reasons) -> int:
    start = i
    raw_rows: list[tuple[int, str]] = []
    while i < len(body) and cs.TABLE_ROW_RE.match(body[i].strip()) and body[i] == body[i].strip():
        raw_rows.append((offset + i + 1, body[i]))
        i += 1
    # a table line with stray whitespace already reported above; stop cleanly

    if len(raw_rows) < 2:
        reasons.append(Reason("L1-TBL01", raw_rows[0][0],
                              "pipe table requires a header row and a separator row"))
        return i

    parsed: list[tuple[int, list[str] | None]] = []
    for ln, row in raw_rows:
        cells = _split_cells(row, ln, reasons)
        parsed.append((ln, cells))

    header_ln, header_cells = parsed[0]
    sep_ln, sep_cells = parsed[1]
    if header_cells is None:
        return i
    ncols = len(header_cells)

    if sep_cells is None or len(sep_cells) != ncols or any(c != cs.TABLE_SEP_CELL for c in sep_cells):
        reasons.append(Reason("L1-TBL01", sep_ln,
                              "separator row must be | :--- | ... | matching the "
                              "header column count (SPEC 6.2)"))
        return i

    rows: list[list[str]] = []
    row_lines: list[int] = []
    for ln, cells in parsed[2:]:
        if cells is None:
            continue
        if len(cells) != ncols:
            reasons.append(Reason("L1-TBL01", ln, "row cell count differs from header"))
            continue
        rows.append(cells)
        row_lines.append(ln)

    # classify table space
    declare_kind = None
    m_decl = (cs.DECLARE_HEADING_RE.match("# " + last_heading.text)
              if last_heading is not None and last_heading.level == 1 else None)
    if header_cells == cs.PROGRAM_HEADER:
        space = "program"
    elif header_cells == cs.TRACE_HEADER:
        space = "trace"
    elif m_decl:
        space = "declaration"
        declare_kind = m_decl.group(1)
    else:
        space = "content"

    # per-space cell charset
    for (ln, cells) in [(l, c) for (l, c) in parsed[2:] if c is not None] + [(header_ln, header_cells)]:
        for cell in cells:
            if space == "content":
                bad = cs.illegal_content_chars(cell)
                if bad:
                    reasons.append(Reason("L1-CHR01", ln,
                                          f"character(s) outside closed alphabet in table cell: {bad}"))
                else:
                    bare = cs.bare_math_chars_outside_fences(cell)
                    if bare:
                        reasons.append(Reason("L1-CON01", ln,
                                              f"math character(s) {bare} outside $ fences (SPEC 6.2)"))
            else:
                bad = cs.illegal_program_cell_chars(cell)
                if bad:
                    reasons.append(Reason("L1-CHR01", ln,
                                          f"character(s) outside program-space alphabet: {bad}"))

    doc.elements.append(Table(space=space, header_cells=header_cells, rows=rows,
                              row_lines=row_lines, start_line=raw_rows[0][0],
                              declare_kind=declare_kind))
    return i


def _split_cells(row: str, ln: int, reasons: list[Reason]) -> list[str] | None:
    parts = row.split("|")
    if len(parts) < 3 or parts[0] != "" or parts[-1] != "":
        reasons.append(Reason("L1-TBL01", ln, "table row must start and end with |"))
        return None
    cells = []
    for cell in parts[1:-1]:
        if not (cell.startswith(" ") and cell.endswith(" ")) or cell.strip() == "":
            reasons.append(Reason("L1-TBL01", ln,
                                  "cell must be a single-space-padded, non-empty value "
                                  "(use - for none)"))
            return None
        inner = cell[1:-1]
        if inner != inner.strip():
            reasons.append(Reason("L1-TBL01", ln, "extra whitespace inside cell"))
            return None
        cells.append(inner)
    return cells


# ---------------------------------------------------------------------------
# Content-line character and positional law
# ---------------------------------------------------------------------------

def _check_content_line(line: str, ln: int, reasons: list[Reason], allow_bullet: bool) -> None:
    if line.startswith("* ") and allow_bullet:
        m_b = cs.BULLET_RE.match(line)
        if m_b:
            _check_content_text(m_b.group(1), ln, reasons)
            return
        reasons.append(Reason("L1-CON01", ln, "malformed bullet line (SPEC 6.2)"))
        return
    _check_content_text(line, ln, reasons)


def _check_content_text(text: str, ln: int, reasons: list[Reason]) -> None:
    bad = cs.illegal_content_chars(text)
    if bad:
        pretty = ", ".join("U+%04X" % ord(c) if ord(c) > 126 else repr(c) for c in bad)
        reasons.append(Reason("L1-CHR01", ln,
                              f"character(s) outside closed alphabet: {pretty}"))
        return

    if text == cs.PAGEBREAK_TOKEN:
        return

    outside, inside, balanced = cs.split_math_fences(text)
    if not balanced:
        reasons.append(Reason("L1-CON01", ln, "unclosed $ math fence (SPEC 6.2)"))
    bare = [c for c in outside if c in cs.MATH_ONLY_CHARS]
    if "%" in outside:
        bare.append("%")
    if bare:
        reasons.append(Reason("L1-CON01", ln,
                              f"math character(s) {sorted(set(bare))} outside $ fences "
                              f"(SPEC 6.2)"))
    # positional rules outside fences
    if "*" in outside:
        reasons.append(Reason("L1-CON01", ln,
                              "* is legal only as a bullet marker at line start or in "
                              "mathematical use inside $ fences (SPEC 6.1-6.3)"))
    if "#" in outside:
        reasons.append(Reason("L1-CON01", ln,
                              "# is legal only as a heading marker at line start (SPEC 6.2)"))
    if "|" in outside:
        reasons.append(Reason("L1-CON01", ln,
                              "| is legal only in pipe-table rows (SPEC 6.2)"))
    if "@" in text:
        reasons.append(Reason("L1-CHR01", ln,
                              "@ is FORBIDDEN in content space (Law 5, SPEC 6.1)"))


# ---------------------------------------------------------------------------
# Step-number discipline (11.1) and trace seq discipline (13.6)
# ---------------------------------------------------------------------------

def _check_step_discipline(doc: Document, reasons: list[Reason]) -> None:
    expected = 1
    for tbl in doc.program_tables:
        for cells, ln in zip(tbl.rows, tbl.row_lines):
            step = cells[0]
            if not step.isdigit() or int(step) != expected:
                reasons.append(Reason("L1-PGM01", ln,
                                      f"step counter must be ascending, contiguous, from 1; "
                                      f"expected {expected}, found '{step}'"))
                return
            expected += 1

    expected = 1
    for tbl in [e for e in doc.elements if isinstance(e, Table) and e.space == "trace"]:
        for cells, ln in zip(tbl.rows, tbl.row_lines):
            seq = cells[0]
            if not seq.isdigit() or int(seq) != expected:
                reasons.append(Reason("L1-PGM01", ln,
                                      f"trace seq must be ascending, contiguous, from 1; "
                                      f"expected {expected}, found '{seq}'"))
                return
            expected += 1


def _line_of(text: str, ch: str) -> int:
    idx = text.find(ch)
    return text.count("\n", 0, idx) + 1 if idx >= 0 else 0
