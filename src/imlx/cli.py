"""
imlx.cli
========
Command-line interface. Zero dependencies (argparse), mirroring the
recovered iml-cli's verdict-first ergonomics.

    imlx gate ARTIFACT [--decls FILE] [--json]
    imlx run ARTIFACT [--decls FILE] [--trace OUT] [--trace-json OUT] [--json]
    imlx version

Exit code IS the verdict: 0 = PASS, 1 = FAIL, 2 = usage error.
"""

__version__ = "0.1.0"

import argparse
import json
import sys
from pathlib import Path

from . import __version__ as pkg_version
from .gate import gate_file, run_file


def _print_gate(result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
        return
    print(f"Layer 1: {result.layer1.bit}")
    for r in result.layer1.reasons:
        print(f"  {r.code}  line {r.line}: {r.message}")
    if result.layer2 is None:
        if not result.layer1.passed:
            print("Layer 2: not attempted (Layer 1 failed; nothing runs, SPEC 13.5)")
        else:
            print("Layer 2: not attempted (no declaration source; artifact remains "
                  "fully Layer 1-validatable alone, SPEC 5.2)")
    else:
        print(f"Layer 2: {result.layer2.bit}")
        for r in result.layer2.reasons:
            print(f"  {r.code}  line {r.line}: {r.message}")
    print(f"VERDICT: {result.verdict}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="imlx",
                                     description="IMLX gate and executor. One bit.")
    sub = parser.add_subparsers(dest="cmd")

    p_gate = sub.add_parser("gate", help="render the conformance verdict")
    p_gate.add_argument("artifact")
    p_gate.add_argument("--decls", help="external declaration file")
    p_gate.add_argument("--json", action="store_true")

    p_run = sub.add_parser("run", help="gate, then execute (skeleton mode)")
    p_run.add_argument("artifact")
    p_run.add_argument("--decls")
    p_run.add_argument("--trace", help="write canonical IMLX trace to this path")
    p_run.add_argument("--trace-json", help="write JSON trace projection to this path")
    p_run.add_argument("--json", action="store_true")

    sub.add_parser("version", help="print version")

    args = parser.parse_args(argv)
    if args.cmd == "version":
        print(f"imlx {pkg_version} (SPEC v0.1)")
        return 0
    if args.cmd is None:
        parser.print_help()
        return 2

    if not Path(args.artifact).is_file():
        print(f"error: no such file: {args.artifact}", file=sys.stderr)
        return 2

    if args.cmd == "gate":
        result = gate_file(args.artifact, args.decls)
        _print_gate(result, args.json)
        return 0 if result.verdict in ("PASS", "L1-PASS") else 1

    if args.cmd == "run":
        result, run_result = run_file(args.artifact, args.decls)
        if run_result is None:
            _print_gate(result, args.json)
            return 1
        if args.trace:
            Path(args.trace).write_text(run_result.trace.render_imlx(), encoding="utf-8")
        if args.trace_json:
            Path(args.trace_json).write_text(run_result.trace.render_json(), encoding="utf-8")
        if args.json:
            out = {"verdict": run_result.verdict,
                   "events": [e.to_dict() for e in run_result.trace.events]}
            if run_result.failure:
                out["failure"] = run_result.failure.to_dict()
            print(json.dumps(out, indent=2))
        else:
            print(run_result.trace.render_imlx(), end="")
            if run_result.failure:
                f = run_result.failure
                print(f"FAILURE RECORD: step {f.step} {f.opcode} {f.reason_code} "
                      f"[{f.contract}]")
            print(f"VERDICT: {run_result.verdict}")
        return 0 if run_result.verdict == "PASS" else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
