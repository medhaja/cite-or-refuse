"""Offline eval: python eval.py [--inject-faults] [--rate 0.2] [--seed 7]

Writes eval_report.json (and eval_report_faults.json with --inject-faults) and prints a summary.
"""

import argparse
import json
from pathlib import Path

from cite_or_refuse.evaluation import run_eval
from cite_or_refuse.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent


def _print(report: dict, title: str) -> None:
    print(f"\n{title}  (mode: {report['mode']}, judge: {report['judge']}, {report['questions']} questions, "
          f"{report['claims_drafted']} claims drafted, {report['claims_shown']} shown)")
    targets = report["targets"]
    for name, value in report["metrics"].items():
        t = targets.get(name)
        mark = "" if t is None else f"   target {t['op']} {t['target']}  {'PASS' if t['pass'] else 'FAIL'}"
        print(f"  {name:<28}{'n/a' if value is None else f'{value:.3f}':>7}{mark}")
    fi = report["fault_injection"]
    if fi:
        print(f"  faults injected: {fi['injected']}, caught: {fi['caught']}, "
              f"clean claims wrongly refused: {fi['clean_claims_refused']}")
        for t, c in fi["by_type"].items():
            print(f"    {t:<18} {c['caught']}/{c['injected']}")
    if report["failures"]:
        print("  questions with issues:")
        for q in report["failures"]:
            print(f"    {q['qid']} {q['question'][:60]:<60} {'; '.join(q['issues'])}")


def write(report: dict, path: Path) -> None:
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--inject-faults", action="store_true", help="also run with corrupted claims")
    parser.add_argument("--rate", type=float, default=0.2, help="share of drafted claims to corrupt")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    pipeline = Pipeline()
    clean = run_eval(pipeline)
    write(clean, ROOT / "eval_report.json")
    _print(clean, "Clean run -> eval_report.json")
    if args.inject_faults:
        faulted = run_eval(pipeline, inject_faults=True, fault_rate=args.rate, seed=args.seed)
        write(faulted, ROOT / "eval_report_faults.json")
        _print(faulted, f"Fault injection ({args.rate:.0%}) -> eval_report_faults.json")


if __name__ == "__main__":
    main()
