# imlx

Reference implementation of **IMLX: Invariant Markup Language (eXtended)** —
a plain-text format so constrained that a small deterministic program can
verify conformance completely and answer with a single bit.

The model produces; the gate decides.

- **Binary gate** — PASS or FAIL, per layer. No warnings, no partial
  acceptance, no quirks mode.
- **Closed alphabet** — anything not enumerated is forbidden by
  construction. Validation is membership testing.
- **21 opcodes, zero judgment** — every opcode is a computable function or
  a decidable predicate. Semantic production happens inside a SLOT, outside
  the language boundary, and the GATE decides what comes back.
- **Total execution** — every program provably halts before it runs.
- **Byte-identical traces** — a run's complete event log is itself a gated
  IMLX document, byte-identical across runs and implementations in
  skeleton mode. Proofs you can diff, animate, and audit.

## Install

    pip install imlx-gate

Zero runtime dependencies. The distribution is `imlx-gate`; the import
and the command are both `imlx`:

    import imlx

## Use

    imlx gate artifact.imlx --decls decls.imlx     # verdict; exit code is the bit
    imlx run artifact.imlx --trace out.trace.imlx  # gate, execute, emit the trace
    imlx run artifact.imlx --trace-json out.json   # 1:1 JSON projection

Python API:

    from imlx import gate_file, run_file
    result = gate_file("artifact.imlx", "decls.imlx")
    result.verdict            # "PASS" | "FAIL" | "L1-PASS"
    _, run_result = run_file("artifact.imlx", "decls.imlx")
    run_result.trace.render_imlx()

## Conformance

The spec is normative; no implementation is. `tests/conformance` and
`tests/adversarial` carry the fixture corpus: required verdicts, required
reason codes, and pinned byte-exact traces. Matching the corpus is what
conformance means. Divergence is a bug in at least one implementation —
falsify this.

Spec: SPEC.md v0.1 — github.com/passert-ai/imlx. License: MIT.
