# Changelog

## 0.1.0 (unreleased)

Initial reference implementation against SPEC v0.1.

- Layer 1 gate: encoding, header, closed alphabet, constructs, envelopes,
  table shape, step and sequence discipline
- Layer 2 gate: declaration resolution (inline and external with pairing
  verification), type and capability checks, reference resolution,
  register discipline, per-opcode operand checks for all 21 opcodes,
  semantic-verb exclusion
- Executor: total execution, skeleton and engine SLOT modes, runtime GATE
  (charset law and blocklist policies), failure records, halt-on-fail
- Trace emitter: canonical IMLX trace, byte-identical across runs and
  processes in skeleton mode; 1:1 JSON projection; traces gate themselves
- Conformance corpus (20 fixtures) and adversarial suite (17 fixtures)
  with required verdicts, required reason codes, and pinned byte-exact
  trace fixtures
- Zero-dependency CLI: gate, run, version; exit code is the verdict
