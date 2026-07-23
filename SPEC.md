# IMLX: Invariant Markup Language (eXtended)
## Specification, Version 0.1 (DRAFT)

Status: RATIFIED DRAFT (release candidate for implementation). Not yet published.
Version: 0.1.0-rc.2
Date: 2026-07-23
License: MIT (applies to this specification text and the reference implementations)
Canonical repository: github.com/passert-ai/imlx
File extension: `.imlx` (the only recognized extension)
Proposed media type: `text/vnd.passert.imlx` (provisional registration pending)

> RATIFICATION RECORD (moves to the repo decisions log at publication)
> rc.2 additions ratified 2026-07-23: skeleton digest canon (13.6);
> program-space cell alphabet (6.1); trace-space recognition (13.6);
> IF/THEN/ELSE operand syntax (11.2); LABEL binding form (11.2);
> skeleton GATE verdict (13.3); bare pipe tables as blocks (5.3);
> reason codes L2-CAP01 and L2-DEC01 (Appendix C); Appendix B
> declaration correction (POLICY row).
> All drafted proposals ratified 2026-07-23: hybrid declaration-source
> model (10.2); header pairing syntax (5.2); declaration-file convention
> (10.3); failure semantics (13.5); reason-code scheme (Appendix C);
> deterministic execution trace (13.6); envelope independence clarification
> (7.2). The 21-opcode set, envelope inclusion, and straight-quote
> codification were ratified previously. No open rulings remain in this
> document.

---

## 1. Conformance Language

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, MAY, and OPTIONAL in this document are to be interpreted as
described in RFC 2119 and RFC 8174 when, and only when, they appear in all
capitals, as shown here.

An implementation that fails any MUST is nonconforming. There is no partial
conformance. This mirrors the language it specifies.

## 2. Introduction

### 2.1 The problem

Large language models cannot guarantee the structure of their own output. A
model can be instructed, prompted, and reminded; it can attach self-assessed
quality stamps to what it produces; it cannot promise. Any pipeline that
treats model output as trustworthy-by-construction has placed a guarantee
where no guarantee can exist.

IMLX is a response to that fact. It does not ask the model to be reliable. It
moves the guarantee outside the model, into a format so constrained that a
small deterministic program (the gate) can verify conformance completely and
answer with a single bit: pass or fail. Structural responsibility returns to
the human and the toolchain. The model produces; the gate decides.

### 2.2 What IMLX is

IMLX is a plain-text, UTF-8, ASCII-safe markup language with:

- a finite, closed character and construct alphabet (Section 6);
- a binary conformance gate with no warnings and no partial acceptance
  (Section 14);
- a versioned, invariant grammar that no document, operator, or model can
  modify in-band (Section 4.3);
- typed content blocks bound to a declared registry (Section 8);
- a strict separation between reference space and content space (Section 9);
- a deliberately non-Turing-complete instruction set of 21 opcodes, every one
  of which is a computable function or a decidable predicate (Section 11);
- an explicit boundary that excludes semantic production from the language
  entirely (Section 12).

The design thesis is binary determinism: a deterministic pass/fail gate at
input, and a deterministic, auditable pass/fail at output. The thesis is
domain-agnostic. Nothing in this specification is specific to any subject
matter; IMLX applies wherever structured content must survive probabilistic
generation, in science, engineering, medicine, law, finance, or education.

### 2.3 What an .imlx file is

An `.imlx` file is a deterministic input contract: a document whose
conformance to this specification is decidable in full before any downstream
system consumes it.

### 2.4 Heritage

IMLX generalizes a private production format developed for large-scale
educational content pipelines, in which the constrained-format approach was
exercised across thousands of generated units before this public
specification existed. The word behind the historical initialism was
"instructional." The public language is domain-neutral; the heritage survives
only as the origin story and first proof point.

## 3. Terminology

- **Artifact**: a single `.imlx` file.
- **Gate**: a program that renders the one-bit conformance verdict on an
  artifact (Section 14).
- **Content space**: the payload portions of an artifact, governed by the
  closed alphabet (Section 6).
- **Reference space**: the `@`-sigil namespace used for deterministic
  dereference (Section 9).
- **Declaration space**: the registries (block types, procedures, converters,
  registers, symbols) against which an artifact resolves (Section 10).
- **Toolchain space**: everything outside the artifact (build scripts,
  renderers, editors). Outside the guarantee boundary; unconstrained.
- **Block**: one element of the ordered sequence composing an artifact's
  body, bound to a registered type (Section 8).
- **Envelope**: the fenced-div wrapper syntax that carries block typing and
  style binding (Section 7).
- **Program**: an artifact (or artifact section) whose body is an instruction
  table executed under Section 13.
- **Register**: a named, typed binding created during program execution.
- **SLOT**: the sole opening in the language through which semantically
  produced content enters, under contract (Sections 11, 12).
- **Verdict**: PASS or FAIL. There is no third value.

## 4. The Six Laws

The six laws are the normative core. Every other section elaborates one or
more of them. Each law is stated, then given its normative force, then
situated against prior art (informative).

### 4.1 Law 1: Closed Alphabet

**Statement.** The set of permitted characters and constructs is finite and
enumerated in this specification. Anything not enumerated is forbidden by
construction, not by listing.

**Normative force.** A gate MUST reject an artifact containing any character
or construct outside the allowlist of Section 6. Implementations MUST NOT
extend the alphabet. A blocklist is never needed for the language itself;
blocklists exist only as pluggable policy data (Law 6) applied to SLOT
payloads.

**Why it is load-bearing.** Validation over an open alphabet requires
anticipating violations; validation over a closed alphabet requires only
membership testing. The closed alphabet is what makes full conformance
checking decidable and cheap, and it is the property every other law leans on.

**Precedent (informative).** Safety-critical language subsets (MISRA C, the
SPARK subset of Ada) achieve analyzability by exclusion. JSON achieved
universal parseability by being a closed subset of JavaScript literal syntax.
Security allowlisting is preferred over blocklisting for the same structural
reason: the space of permitted things can be enumerated; the space of
dangerous things cannot.

### 4.2 Law 2: Binary Gate

**Statement.** An artifact conforms or it is rejected. The verdict is one
bit. There are no warnings, no partial acceptance, no recoverable errors, no
quirks mode.

**Normative force.** A gate MUST emit exactly one verdict, PASS or FAIL, for
Layer 1 and (when declarations are available) for Layer 2 (Section 14.2). A
gate MAY additionally emit diagnostic reason codes (Appendix C), but
diagnostics MUST NOT alter the verdict and a FAIL artifact MUST NOT be passed
onward by any conforming tool.

**Precedent (informative).** XML's draconian error handling made
well-formedness violations fatal, and the ecosystem of reliable XML tooling
exists because of that severity; HTML's tag-soup tolerance produced decades
of divergent parsers until the parsing algorithm itself had to be
standardized. Compilers reject; linters advise. IMLX has no linter mode
because advice is a second bit.

### 4.3 Law 3: Invariance

**Statement.** The specification is versioned. Within a version, nothing is
runtime-interpretable, extensible, or negotiable. No document, operator, or
model can modify the grammar in-band.

**Normative force.** An artifact MUST declare the specification version it
targets (Section 5.2). A gate MUST validate against exactly that version. A
gate MUST NOT honor any construct that attempts to alter, extend, or
parameterize the grammar from within an artifact. Grammar change happens in
exactly one place: a new version of this document.

**Precedent (informative).** The stability of JSON (RFC 8259 changed nothing
material for a decade) is why JSON is trusted at every boundary. TeX's
version number converges to a constant as its grammar froze. The
counterexample is instructive: XML's internal DTD subset allowed documents to
modify their own grammar in-band, and became a canonical attack and
complexity surface (entity expansion). IMLX documents cannot say anything
about IMLX.

### 4.4 Law 4: Typed Block

**Statement.** An artifact's body is an ordered sequence of blocks. Every
block is bound to a type from a declared registry. An unregistered type fails
the gate.

**Normative force.** Every block MUST carry exactly one type binding
(Section 7). The type MUST resolve against the type registry in force
(Section 10). Layer 2 validation MUST fail on any unresolvable type. Type
registries are data (Law 6), never spec content: this specification defines
no built-in block types.

**Precedent (informative).** Validated XML requires every element to be
declared; Protocol Buffers require every message to have a schema; typed
ASTs are what make document toolchains (such as Pandoc's) reliable. The IMLX
difference is that the registry is external policy data, so the public
mechanism carries no vocabulary.

### 4.5 Law 5: Two Namespaces

**Statement.** Reference space and content space are disjoint. `@` sigils
are deterministic one-to-one handles for navigation and dereference. They
never appear in content output.

**Normative force.** The `@` character MUST NOT appear in content space
(Section 6). In program and declaration space, every `@` reference MUST
resolve one-to-one against the declared symbol table; an unresolvable or
ambiguous reference MUST fail the gate. Renderers MUST NOT emit sigils into
output.

**Precedent (informative).** Label/reference systems (LaTeX labels, XML
IDREF) separate naming from content; macro hygiene research separates the
program's names from the meta-program's names. The historical note is
informative: in this language's v1 lineage, `@` tags were semantic labels;
the redesign deliberately re-founded `@` as pure reference machinery and
expelled semantics from the language (Section 12). The namespace boundary is
that decision made structural.

### 4.6 Law 6: Pluggable Policy

**Statement.** Blocklists, type registries, grounding manifests, style
registries, and procedure registries are data supplied to the gate, not
contents of the specification. The public specification defines mechanisms
only.

**Normative force.** A gate MUST accept policy data through the declaration
mechanism of Section 10 and MUST apply it during Layer 2 validation.
Implementations MUST NOT hard-code policy vocabularies. Policy files are
themselves expressible as IMLX pipe tables and, when so expressed, MUST pass
the gate.

**Precedent (informative).** Mechanism/policy separation is a classical
systems principle (X11, microkernel design); CSS separated presentation
policy from HTML mechanism; Protocol Buffers ship schemas as artifacts, not
compiler contents. For IMLX the law is also an architecture statement: any
operator's private vocabulary remains private plug-in data, while the public
mechanism is fully specified and testable.

## 5. Artifact Anatomy

### 5.1 Encoding and line discipline

An artifact MUST be UTF-8 encoded text whose every character falls in the
allowlist of Section 6 (which confines content to the ASCII range). Line
terminator MUST be LF (`\n`). A trailing final newline is REQUIRED. CR, CRLF,
tabs, and any control character other than LF MUST fail Layer 1.

### 5.2 The header

Every artifact MUST begin with a header of exactly two lines, before any
blank line or body content:

```
IMLX: 0.1
DECLARATIONS: catalog-decls.imlx; 1.0
```

Line 1: the literal token `IMLX`, colon, space, the specification version
targeted. Line 2: the literal token `DECLARATIONS`, colon, space, then
either the pairing target (a declaration-file name, semicolon, space, and
that file's declared version) or the literal token `INLINE`.

The header pairing line makes the (artifact + declarations) pair explicit
and checkable: a Layer 2 gate MUST verify that the declaration source it was
given matches the name and version the artifact demands, and MUST fail on
mismatch. An artifact whose header names an external file is not
Layer 2-validatable without it, by design; it remains fully
Layer 1-validatable alone (Section 14.2).

### 5.3 The body

The body is an ordered sequence of blocks (Section 8) separated by single
blank lines. Content outside a block is limited to headings, page breaks,
and pipe tables (Section 6.2); a bare pipe table is itself a block, and its
space (content, program, declaration, or trace) is determined by its header
row (Sections 10.4, 11.1, 13.6).

## 6. The Character and Construct Law

This section is the closed alphabet. It is exhaustive: a character or
construct not named here is forbidden in content space (Law 1). The rules
below carry the language's production-proven charset forward without
addition or removal, with one codification (6.4).

### 6.1 Allowed characters (content space)

- Letters `A-Z a-z`, digits `0-9`, the space character, LF.
- Punctuation, subject to the positional rules of 6.2 and 6.3:
  `. , : ; - ' " ( ) [ ] | * # $ %`
- `{ }` and `:::` ONLY within the envelope syntax of Section 7.
- `/` and `?` as ordinary text characters.
- `@` is FORBIDDEN in content space (Law 5); it is legal only in program and
  declaration space (Sections 10, 11).

Cells of program, declaration, and trace tables (Sections 10.4, 11.1, 13.6)
use the content alphabet extended by exactly six characters: `@` (references,
Law 5), `=` (contract and branch keys), `_` (reference and register names,
Section 9), and `< > +` (the closed operator set of SELECT and COMPUTE,
Section 11.2). These six remain forbidden in content space; the extension
applies inside those table cells only.

### 6.2 Allowed constructs

- **Headings**: `#`, `##`, or `###` at line start, followed by one space and
  the heading text. No deeper levels.
- **Bullets**: `* ` at line start (one form only), and `* * ` for one
  indented sublevel. No other bullet or indentation forms.
- **Numbered lists**: legal-numbered form only (`1.1`, `1.2`, ... at line
  start). Permitted only inside blocks whose registered type declares the
  `legal_lists` capability (Section 10.4); elsewhere they fail the gate.
- **Step numbering**: `Step 1:`, `Step 2:`, ... at line start; permitted
  only in combination with legal lists, under the same type capability.
- **Pipe tables**: rows of `|`-delimited cells, with a separator row of the
  form `| :--- | :--- |`. Cells are single-line.
- **Multi-line blocks**: paragraphs wrap as hard-broken lines within a
  block; no soft-return constructs.
- **Page break**: the exact token `%%PAGEBREAK%%` alone on a line.
- **Math fencing**: `$`-fenced spans. All mathematical and comparison
  symbols (`< > = + %` and arithmetic operators in mathematical use) MUST
  appear only inside `$` fences. Bare occurrence outside a fence fails the
  gate. (`%` appears bare only within `%%PAGEBREAK%%`.)
- **Section separation**: single blank line between blocks.

### 6.3 Forbidden (enumerated for diagnostics; the list is not the law)

Bold, italic, underline; markdown emphasis of any kind; backtick fences and
inline code; HTML or XML tags; tabs and indentation whitespace; em and en
dashes; ellipsis character; ampersand; smart quotes and curly apostrophes;
Unicode bullets, arrows, and symbols of any kind; nested formatting; leading
or trailing extra whitespace; consecutive blank lines. Inside the envelope
wrapper only, the envelope's own tokens are exempt (Section 7). This list
exists so gates can emit useful reason codes; the normative rule remains
Law 1: absence from Section 6.1/6.2 is what forbids.

### 6.4 Straight quote codification

The straight double quote `"` is an allowed payload character in content
space, including within pipe-table cells. (This codifies longstanding
production practice and the format's CSV lineage, where the straight quote
is the native escape character. Ruled 2026-07-23.) Smart quotes remain
forbidden. The straight apostrophe `'` is likewise allowed.

## 7. Envelope Syntax

The envelope is the block-typing wrapper. It reuses the publicly documented
Pandoc fenced-div syntax, restricted.

### 7.1 Form

```
::: {custom-style="TypeName"}
...block content...
:::
```

- The opening line is `:::`, one space, `{custom-style=`, a straight-quoted
  type name, `}`.
- The closing line is `:::` alone.
- `{`, `}`, `:::`, and the envelope's quotes are legal ONLY in these two
  line forms. Anywhere else they fail the gate.
- Envelopes MUST NOT nest.
- The type name MUST match a registered block type (Law 4). Names are
  policy data (Law 6): this specification defines the wrapper, never the
  vocabulary.

### 7.2 Prior art and leakage (informative)

The syntax is standard Pandoc fenced-div with a custom-style attribute,
chosen deliberately: the mechanism is public prior art and leaks nothing.
Only the style names bound through it are private policy. A conforming
artifact renders through stock Pandoc into styled targets (such as .docx via
a reference template) with no custom software, which is part of the interop
posture (Section 15.4). The envelope is defined by this specification and
validated by IMLX gates directly; Pandoc is prior art for the character
sequence and one render path among many, never a dependency. A conforming
gate or renderer requires no Pandoc.

## 8. Blocks and the Type Registry

- An artifact body is an ordered sequence of blocks (Law 4).
- A block is either (a) an enveloped block (Section 7) whose type is its
  envelope binding, or (b) a bare construct permitted outside envelopes
  (headings, `%%PAGEBREAK%%`).
- Layer 2 validation MUST resolve every envelope type against the type
  registry in force and MUST fail on any miss.
- A type registry entry MAY declare capabilities that relax positional
  construct rules inside blocks of that type (currently defined:
  `legal_lists`, enabling legal-numbered lists and Step numbering per
  Section 6.2). Capabilities are the only sanctioned relaxation mechanism,
  and they relax construct positioning only, never the character alphabet.

## 9. The Reference Namespace

- `@Name` is a reference: a deterministic, one-to-one handle.
- References are legal only in program space (operands, Section 11) and
  declaration space (Section 10). Never in content space (Law 5).
- Every reference MUST resolve against the declared symbol table: exactly
  one target, no fallbacks, no fuzzy matching, no most-recent-wins. Zero
  targets or more than one target MUST fail the gate.
- Reference names use letters, digits, and `_`, beginning with a letter.
- Renderers MUST NOT emit references into output; a reference reaching a
  renderer is a toolchain error.

## 10. Declarations

### 10.1 What declarations are

Declarations populate the registries Layer 2 validates against: block types
(with capabilities), procedures, converters, named registers, symbols, and
policy data such as SLOT blocklists and grounding manifests (Law 6).

### 10.2 Declaration sources

Exactly one declaration source per artifact, named by the header pairing
line (Section 5.2):

- **External (canonical)**: a separate declaration file. This is the normal
  mode, and the only mode for private registries: vocabulary never ships
  inside distributed artifacts.
- **Inline (permitted)**: the artifact's own declaration section, for
  self-contained artifacts. The literal header value `INLINE`.

A duplicate or conflicting definition, within a source or between an
artifact and its named source, MUST fail the gate. There is no precedence,
no overlay, no merge.

(Informative: the `imlx bundle` tool compiles an external-mode artifact into
inline mode deterministically, producing a single fully self-contained,
fully Layer 2-validatable file. Prior art for dual-mode declarations: XML's
internal versus external DTD subset; JSON Schema's local versus remote
references.)

### 10.3 Declaration files

A declaration file is itself an IMLX artifact: extension `.imlx`, the same
header form (its `DECLARATIONS` line reads `INLINE`), a version stated in a
`DECL_VERSION: 1.0` third header line, and a body consisting solely of
declaration tables. It MUST pass Layer 1 like any artifact. No second file
format and no second parser exist.

### 10.4 Declaration tables

Declarations are pipe tables with a declared shape. Registry kinds and
their REQUIRED columns:

| kind | columns |
| :--- | :--- |
| TYPE | name, capabilities |
| PROCEDURE | name, arity, operand_schema |
| CONVERTER | name, from_type, to_type |
| REGISTER | name, type |
| SYMBOL | sigil_name, target |
| POLICY | name, kind, payload_ref |

Each table is introduced by a heading line `# DECLARE <kind>`. A row whose
name duplicates any prior name of the same kind MUST fail the gate
(Section 10.2). Well-formedness of every entry is decidable by shape alone.

## 11. The Instruction Set

### 11.1 Program form (the von Neumann property)

A program serializes as an IMLX pipe table inside the closed alphabet:

```
| step | opcode | operand | bind | style |
| :--- | :--- | :--- | :--- | :--- |
| 1 | LOAD | @Corpus_A | reg_corpus | - |
| 2 | QUERY | reg_corpus; part_no; "PX-140" | reg_part | - |
```

Code and data share one gated representation; the gate can therefore
pass or fail the PROGRAM itself at input, before anything runs. The program
counter is the step number: ascending, contiguous, starting at 1. Any gap,
duplicate, or disorder fails the gate.

### 11.2 The 21 opcodes

Ratified 2026-07-23. Every opcode is a computable function or a decidable
predicate; the third column is the static, decidable check the gate applies
before execution.

| opcode | operation | decidable gate check |
| :--- | :--- | :--- |
| LOAD | bring named artifacts into the working set | named artifacts present in working set |
| SEARCH (corpus form) | scoped retrieval from a closed, declared corpus; returns a bound set | corpus declared and closed; scope fields in schema |
| SEARCH (register form) | scoped retrieval within a bound register (formerly SCAN) | source register bound; scope fields in schema |
| QUERY | exact-key record lookup against a declared field | field declared; key literal in alphabet |
| SELECT | filter a bound finite set by a decidable predicate on declared fields | predicate over declared fields, closed operator set |
| PARSE | resolve a dot-path against a declared schema | path resolves against declared schema |
| LABEL | bind a literal label to a register; the operand is the label text, the bind column names the receiving register | register bound exactly once, before any use; label text charset-legal |
| EXTRACT | read a field from a bound register | field exists in bound register per schema |
| CONCAT | deterministic string composition | all operands bound; result charset-legal |
| INSERT | deterministic register merge | source and target bound; schemas compatible |
| APPEND | add an element to a bound ordered register | target bound and ordered; element type matches |
| POPULATE | fill a declared template one-to-one from bound values | every template field maps to exactly one bound source; none unfilled |
| FOR_EACH | iterate a bound finite set | set bound and finite; termination provable |
| IF/THEN/ELSE | branch on equality over enumerated metadata; operand form `comparand; comparand; THEN=<step>; ELSE=<step>`, both targets strictly greater than the current step (forward-only) | comparands enumerated; both branches present; both targets forward |
| EXECUTE | invoke a target from the declared procedure registry | target exists in declared procedure registry |
| DECLARE | register a runtime-named type, procedure, or register | entry well-formed; name unique in registry |
| SLOT | open a contracted payload position | contract complete: grounding key + charset law + type + blocklist |
| VERIFY | decidable assertion on a bound register; yields one bit | predicate decidable over declared schema |
| CONVERT | apply a declared converter | converter registered; input type matches from_type |
| COMPUTE | arithmetic over bound numeric operands | operands bound numeric; operators from the closed set |
| OUTPUT_PRINT | emit a payload | type declared; payload previously gate-passed |
| GATE | one-bit verdict on a SLOT payload | contract present; verdict binds to one bit |

(SEARCH's two forms are one opcode with two declared scopes, not two
opcodes; the table lists both rows for the two distinct checks.)

### 11.3 Totality

The language is deliberately not Turing-complete. Every program terminates:
loops iterate only bound finite sets (FOR_EACH), branching is finite, there
is no recursion, no unbounded jump, and no self-modification (Law 3). A
gate can therefore statically confirm, before execution, that a program
halts. Precedent (informative): total configuration languages (Dhall,
Starlark) trade expressiveness for exactly this guarantee.

## 12. The Semantic Exclusion Boundary

The language contains no semantic opcodes. The following verbs, present in
the v1 lineage, are deliberately excluded and published here as boundary
evidence:

IDENTIFY, DEFINE, CITE-AND-DEFINE, SUMMARIZE, RESTATE, APPLY, NETWORK_MAP,
TRUNCATE (as semantically used).

The exclusion test is precise: an operation belongs in the language if and
only if a decidable conformance check exists for it. No decidable predicate
answers "is this a correct definition" or "is this a faithful summary."
Such operations are SLOT work: they happen inside a SLOT, outside the
language boundary, performed by an engine the language never names. The
SLOT contract constrains what comes back (grounding key, charset, type,
blocklist) and the GATE opcode renders the verdict on it. Binary
determinism with no leaks in the language opcodes.

## 13. Execution Model

### 13.1 State

Execution state is the register file: named, typed bindings created by
LABEL/DECLARE and populated by the data opcodes. No global mutable state
exists outside registers.

### 13.2 Order

Steps execute in step-number order. SLOT fills, when an engine is attached,
occur sequentially in program order; implementations MUST NOT parallelize
SLOT fills. (Determinism of the audit trail outranks throughput.)

### 13.3 Skeleton mode

An executor without an attached engine MUST run every program end-to-end,
rendering each SLOT as a placeholder displaying its full contract. Skeleton
execution is fully deterministic, requires no network and no credentials,
and is the mode conformance tests run in. The paired GATE on a skeleton
placeholder renders PASS: the placeholder is the deterministic, conforming
payload (see Appendix D).

### 13.4 Engine mode

An executor MAY accept an engine adapter. At each SLOT, the executor passes
the contract to the engine, receives a payload, and MUST immediately apply
the paired GATE. The engine is outside the guarantee boundary; the language
does not name, constrain, or trust it. The gate applies to what returns.

### 13.5 Failure semantics

A Layer 1 or Layer 2 failure rejects the artifact before execution; nothing
runs. At runtime, a GATE verdict of FAIL on a SLOT payload MUST halt the
program at that step with verdict FAIL and a failure record: step number,
opcode, reason code, and the contract that was violated. Retry is toolchain
policy, outside the language: a toolchain MAY re-run the program, but a
conforming executor MUST NOT retry internally, because internal retry makes
the audit trail nondeterministic.

### 13.6 The execution trace

An executor MUST be able to emit a trace: the complete, ordered event log of
a run. The trace is the documented public interface for visualizers,
animations, and audit tooling; anything a run did is reconstructible from
its trace and nothing a run did is absent from it.

**Canonical form.** The canonical trace is itself an IMLX artifact: header,
then a single pipe table, one row per event, in the closed alphabet. A
trace MUST pass Layer 1. A pipe table whose header row is exactly the
column set below is trace space and uses the program-space cell alphabet
(Section 6.1). The language's proofs are themselves gated documents.

Columns:

```
| seq | event | step | opcode | subject | outcome | digest |
```

- `seq`: ascending, contiguous event counter from 1.
- `event`: one of `GATE_L1`, `GATE_L2`, `STEP`, `BIND`, `SLOT_OPEN`,
  `SLOT_FILL`, `GATE_VERDICT`, `HALT`.
- `step`: the program step number the event belongs to (`-` for the
  pre-execution gate events).
- `opcode`: the opcode at that step (`-` where not applicable).
- `subject`: the register, artifact, or contract element involved.
- `outcome`: `PASS`, `FAIL`, `BOUND`, `FILLED`, `SKELETON`, or `DONE`.
- `digest`: for events that carry content (BIND, SLOT_FILL), the lowercase
  hex SHA-256 of the content's UTF-8 bytes; `-` otherwise. In skeleton
  mode, the digested content of a data-opcode BIND is canonically the
  UTF-8 string `SKELETON|<step>|<opcode>|<operand>|<bind>` (the four cells
  verbatim, `|`-joined with the literal prefix); a skeleton SLOT_FILL
  carries digest `-`. This canon is what makes skeleton traces
  byte-identical across implementations. Content itself
  never appears in a trace; traces are structural, so they are shareable
  without leaking payloads.

**Determinism requirement.** In skeleton mode, the trace of a given
(artifact + declaration source) pair MUST be byte-identical across runs and
across conforming implementations. Trace equality is therefore a
conformance test (Section 15.1 fixtures include required traces), and the
two-implementation claim becomes visually checkable: identical inputs,
identical traces, always. In engine mode, `SLOT_FILL` digests vary with the
engine's payload; every other row remains identical, which makes the
engine's contribution exactly visible as the only moving part.

**Projection.** A toolchain MAY project the canonical trace 1:1 into JSON
for browser consumption (one object per row, same field names, no added
fields). The IMLX table remains canonical; the projection is defined so
visualizers need no IMLX parser.

## 14. The Gate

### 14.1 Definition

A gate is any program that renders the verdict of this specification.
The reference implementations (Section 15) are gates; so is any
independent implementation that matches them on the conformance corpus.

### 14.2 Layers

- **Layer 1 (standalone)**: encoding, header, charset law, construct law,
  envelope well-formedness, table shape, step-number discipline. Layer 1
  requires nothing but the artifact. Every artifact is Layer 1-validatable
  alone, always.
- **Layer 2 (resolved)**: everything requiring declarations: type
  resolution, reference resolution, register discipline, operand schema
  checks, procedure/converter existence, policy application. Layer 2
  requires the artifact plus its declaration source (Section 10.2), and
  MUST verify the header pairing before applying it.

A verdict MUST be reported per layer. "PASS" unqualified means both layers
passed.

### 14.3 Verdict discipline

One bit per layer. A gate MUST NOT emit warnings, scores, or partial
results. Reason codes (Appendix C) accompany FAIL verdicts as diagnostics
and never soften them.

## 15. Conformance and Interoperability

### 15.1 The conformance corpus

The repository ships a corpus of fixture artifacts, each paired with its
required verdict and, for FAIL fixtures, its required reason code. A
conforming implementation MUST produce the required verdict on every
fixture. The corpus is the shared oracle across implementations: any
divergence between implementations is, by definition, a bug in at least one
of them, and its resolution adds a fixture.

### 15.2 The adversarial suite

A second corpus of hostile inputs: charset smuggling, envelope abuse,
in-band grammar modification attempts, reference ambiguity, step-counter
games, YAML-lookalike traps, unicode confusables. Same rule: required
verdict, required reason code, zero implementation divergence. The suite is
public and contributions of new attacks are the intended failure-reporting
path ("falsify this").

### 15.3 Independent implementations

The specification is normative; no implementation is. Reference
implementations exist in Python (`imlx` on PyPI) and JavaScript (`imlx` on
npm, gate scope). Matching the corpus, not matching the reference code, is
what conformance means.

### 15.4 Interoperability posture

An `.imlx` artifact is plain text consumable with zero dependencies in any
language. Documented render paths: Pandoc to .docx via reference templates
(with a style coverage check: every declared type must have a matching
named style, or render refuses); HTML to print PDF; spreadsheet-safe
interchange per the CSV lineage. Programs are pipe tables and therefore
spreadsheet-inspectable by construction.

## 16. Media Type and Extension

- Extension: `.imlx`. No other extension is recognized; gates MAY refuse
  other extensions outright.
- Media type: `text/vnd.passert.imlx` proposed for provisional vendor-tree
  registration under RFC 6838.

## 17. Versioning Policy

This specification uses semantic versioning. Within a version, the grammar
is frozen (Law 3). A new minor version may add to registrable mechanism
kinds; it may never relax the alphabet of an existing version. Artifacts
state their version (Section 5.2) and are validated against it exactly.

---

## Appendix A: Opcode Quick Reference

LOAD, SEARCH (corpus | register), QUERY, SELECT, PARSE, LABEL, EXTRACT,
CONCAT, INSERT, APPEND, POPULATE, FOR_EACH, IF/THEN/ELSE, EXECUTE, DECLARE,
SLOT, VERIFY, CONVERT, COMPUTE, OUTPUT_PRINT, GATE. Excluded by boundary:
IDENTIFY, DEFINE, CITE-AND-DEFINE, SUMMARIZE, RESTATE, APPLY, NETWORK_MAP,
TRUNCATE-as-used.

## Appendix B: Example (invented domain: industrial parts catalog)

Declaration file `catalog-decls.imlx`:

```
IMLX: 0.1
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
```

Artifact `px140-brief.imlx`:

```
IMLX: 0.1
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
```

Step 4 is where an engine may produce prose about the part; step 5 is where
the language decides whether that prose enters the document. Steps 1-3 and 6
never involve judgment at all.

## Appendix C: Reason Codes

Format: `L<layer>-<AREA><nn>`. Initial set:

| code | meaning |
| :--- | :--- |
| L1-ENC01 | invalid encoding or line terminator |
| L1-HDR01 | missing or malformed header |
| L1-CHR01 | character outside closed alphabet |
| L1-CON01 | construct outside closed construct set |
| L1-ENV01 | envelope malformed or nested |
| L1-TBL01 | pipe table shape violation |
| L1-PGM01 | step-number discipline violation |
| L2-PAIR01 | declaration source mismatch with header pairing |
| L2-TYP01 | unresolvable block type |
| L2-REF01 | unresolvable or ambiguous reference |
| L2-REG01 | register bound twice, or used before bind |
| L2-OPD01 | operand fails opcode's decidable check |
| L2-DUP01 | duplicate declaration |
| L2-CAP01 | construct requires a type capability the block's type does not declare |
| L2-DEC01 | malformed declaration table: unknown DECLARE kind or wrong column set |
| L2-POL01 | policy violation in SLOT payload |
| RT-GATE01 | runtime GATE verdict FAIL on SLOT payload |

The set grows only with the corpus; a new failure mode ships with its
fixture.

## Appendix D: Example Trace (skeleton mode, for the Appendix B program)

```
IMLX: 0.1
DECLARATIONS: INLINE

# TRACE px140-brief.imlx

| seq | event | step | opcode | subject | outcome | digest |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | GATE_L1 | - | - | px140-brief.imlx | PASS | - |
| 2 | GATE_L2 | - | - | catalog-decls.imlx; 1.0 | PASS | - |
| 3 | STEP | 1 | LOAD | reg_corpus | DONE | - |
| 4 | BIND | 1 | LOAD | reg_corpus | BOUND | 9f2c...e1a0 |
| 5 | STEP | 2 | QUERY | reg_part | DONE | - |
| 6 | BIND | 2 | QUERY | reg_part | BOUND | 4b77...c3d9 |
| 7 | STEP | 3 | EXTRACT | reg_torque | DONE | - |
| 8 | BIND | 3 | EXTRACT | reg_torque | BOUND | a118...02fe |
| 9 | SLOT_OPEN | 4 | SLOT | type=PartSummary | DONE | - |
| 10 | SLOT_FILL | 4 | SLOT | reg_summary | SKELETON | - |
| 11 | GATE_VERDICT | 5 | GATE | reg_summary | PASS | - |
| 12 | STEP | 6 | OUTPUT_PRINT | reg_summary | DONE | - |
| 13 | HALT | 6 | - | px140-brief.imlx | PASS | - |
```

(Digests abbreviated here for page width; real traces carry full 64-char
hashes. A visualizer consuming rows 1-13 has the entire animation: gates,
steps, bindings, the SLOT opening, the verdict, the halt.)

---
End of SPEC.md v0.1 draft.
