# IMLX for Visual Studio Code

Syntax highlighting for `.imlx` files - IMLX: Invariant Markup Language
(eXtended), the gated plain-text format where conformance is decided by a
deterministic gate with a single-bit verdict.

Highlights headers, headings, envelopes, bullets, math fences, page breaks,
pipe tables, the 21 opcodes, trace events and outcomes, registers,
`@references`, SLOT contracts, and SHA-256 digests.

Language and reference gate: https://github.com/passert-ai/imlx

    pip install imlx
    imlx gate artifact.imlx
