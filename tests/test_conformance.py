"""
Conformance and adversarial corpus runner (SPEC 15.1, 15.2), trace
determinism (SPEC 13.6), and executor mode tests (SPEC 13.3, 13.4).

Divergence from a required verdict is, by definition, a bug (SPEC 15.1).
"""

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "src"))

from imlx.gate import gate_file, run_file                     # noqa: E402
from imlx.layer1 import gate_layer1_bytes                     # noqa: E402
from imlx.executor import run                                 # noqa: E402


def _load(corpus: str):
    manifest = json.loads((HERE / corpus / "manifest.json").read_text())
    return [pytest.param(m, id=f"{corpus}:{m['artifact']}") for m in manifest]


def _run_fixture(corpus: str, m: dict):
    art = HERE / corpus / m["artifact"]
    decls = (HERE / "conformance" / m["decls"]) if m.get("decls") else None
    result = gate_file(art, decls)

    assert result.layer1.bit == m["expect_l1"], (
        f"L1 {result.layer1.bit} != required {m['expect_l1']}: "
        f"{[r.to_dict() for r in result.layer1.reasons]}")

    if m["expect_l2"] is not None:
        assert result.layer2 is not None, "Layer 2 verdict required but not attempted"
        assert result.layer2.bit == m["expect_l2"], (
            f"L2 {result.layer2.bit} != required {m['expect_l2']}: "
            f"{[r.to_dict() for r in result.layer2.reasons]}")

    got_codes = {r.code for r in result.layer1.reasons}
    if result.layer2:
        got_codes |= {r.code for r in result.layer2.reasons}
    for code in m["codes"]:
        assert code in got_codes, f"required reason code {code} absent; got {got_codes}"


@pytest.mark.parametrize("m", _load("conformance"))
def test_conformance(m):
    _run_fixture("conformance", m)


@pytest.mark.parametrize("m", _load("adversarial"))
def test_adversarial(m):
    _run_fixture("adversarial", m)


# ---------------------------------------------------------------------------
# Trace determinism (SPEC 13.6): byte-identical, self-gating, pinned fixture
# ---------------------------------------------------------------------------

FLAGSHIP = HERE / "conformance" / "px140-brief.imlx"
FLAGSHIP_DECLS = HERE / "conformance" / "catalog-decls.imlx"
TRACE_FIXTURE = HERE / "conformance" / "px140-brief.trace.imlx"
TRACE_JSON_FIXTURE = HERE / "conformance" / "px140-brief.trace.json"


def _flagship_trace():
    result, run_result = run_file(FLAGSHIP, FLAGSHIP_DECLS)
    assert result.verdict == "PASS" and run_result is not None
    assert run_result.verdict == "PASS"
    return run_result


def test_trace_byte_identical_across_runs():
    a = _flagship_trace().trace.render_imlx()
    b = _flagship_trace().trace.render_imlx()
    assert a.encode("utf-8") == b.encode("utf-8")


def test_trace_matches_pinned_fixture():
    got = _flagship_trace().trace.render_imlx().encode("utf-8")
    required = TRACE_FIXTURE.read_bytes()
    assert got == required, "skeleton trace diverged from the pinned byte-exact fixture"


def test_trace_json_projection_matches_fixture():
    got = _flagship_trace().trace.render_json()
    assert got == TRACE_JSON_FIXTURE.read_text(encoding="utf-8").rstrip("\n")


def test_trace_is_itself_layer1_valid():
    """SPEC 13.6: a trace MUST pass Layer 1. The proofs are gated documents."""
    text = _flagship_trace().trace.render_imlx()
    verdict, _doc = gate_layer1_bytes(text.encode("utf-8"), "px140-brief.trace.imlx")
    assert verdict.passed, [r.to_dict() for r in verdict.reasons]


def test_trace_event_shape_matches_appendix_d():
    """Same 13-event shape as SPEC Appendix D for the Appendix B program."""
    tr = _flagship_trace().trace
    shape = [(e.event, e.outcome) for e in tr.events]
    assert shape == [
        ("GATE_L1", "PASS"), ("GATE_L2", "PASS"),
        ("STEP", "DONE"), ("BIND", "BOUND"),
        ("STEP", "DONE"), ("BIND", "BOUND"),
        ("STEP", "DONE"), ("BIND", "BOUND"),
        ("SLOT_OPEN", "DONE"), ("SLOT_FILL", "SKELETON"),
        ("GATE_VERDICT", "PASS"), ("STEP", "DONE"), ("HALT", "PASS"),
    ]
    assert [e.seq for e in tr.events] == list(range(1, 14))


# ---------------------------------------------------------------------------
# Executor modes (SPEC 13.3, 13.4, 13.5)
# ---------------------------------------------------------------------------

def test_skeleton_placeholder_displays_full_contract():
    rr = _flagship_trace()
    payload = rr.registers["reg_summary"]
    for key in ("ground=reg_part", "type=PartSummary", "blocklist=@Policy_Std"):
        assert key in payload, "SPEC 13.3: placeholder displays its full contract"


def test_engine_mode_pass_and_slot_is_only_moving_part():
    result = gate_file(FLAGSHIP, FLAGSHIP_DECLS)
    skeleton = run(result.document, result.registries).trace
    engine_run = run(result.document, result.registries,
                     engine=lambda contract: "The torque value is documented.")
    assert engine_run.verdict == "PASS"
    sk, en = skeleton.events, engine_run.trace.events
    assert len(sk) == len(en)
    for a, b in zip(sk, en):
        if a.event == "SLOT_FILL":
            assert (b.outcome, a.outcome) == ("FILLED", "SKELETON")
            assert b.digest != "-" and len(b.digest) == 64
        else:
            assert a.cells() == b.cells(), (
                "SPEC 13.6: in engine mode every row but SLOT_FILL is identical")


def test_engine_mode_gate_fail_halts_with_failure_record():
    result = gate_file(FLAGSHIP, FLAGSHIP_DECLS)
    rr = run(result.document, result.registries,
             engine=lambda contract: "Curly \u201cquotes\u201d violate the charset law.")
    assert rr.verdict == "FAIL"
    assert rr.failure is not None
    assert rr.failure.reason_code == "RT-GATE01"
    assert rr.failure.step == 5 and rr.failure.opcode == "GATE"
    assert rr.trace.events[-1].event == "HALT" and rr.trace.events[-1].outcome == "FAIL"
    # nothing after the halt: step 6 never ran (SPEC 13.5)
    assert all(e.step != "6" for e in rr.trace.events)


def test_engine_mode_blocklist_policy_fail():
    result = gate_file(FLAGSHIP, FLAGSHIP_DECLS)
    rr = run(result.document, result.registries,
             engine=lambda contract: "This payload names a forbidden term.",
             policy_payloads={"Policy_Std": ["forbidden term"]})
    assert rr.verdict == "FAIL" and rr.failure.reason_code == "RT-GATE01"


def test_engine_mode_blocklist_policy_pass():
    result = gate_file(FLAGSHIP, FLAGSHIP_DECLS)
    rr = run(result.document, result.registries,
             engine=lambda contract: "A clean payload.",
             policy_payloads={"Policy_Std": ["forbidden term"]})
    assert rr.verdict == "PASS"


# ---------------------------------------------------------------------------
# Layer 2 not attemptable without the paired source (SPEC 5.2), by design
# ---------------------------------------------------------------------------

def test_external_artifact_is_layer1_validatable_alone(tmp_path):
    lone = tmp_path / "px140-brief.imlx"
    lone.write_bytes(FLAGSHIP.read_bytes())
    result = gate_file(lone)
    assert result.layer1.passed and result.layer2 is None
    assert result.verdict == "L1-PASS"
