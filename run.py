"""One-command demo: generate data if missing, build the index, run the eval if no report exists, serve the UI.

    python run.py [--port 8000]
"""

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env reader so an optional LLM key can live in a local, untracked file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Cite or Refuse demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    load_dotenv()

    import uvicorn

    from cite_or_refuse.app import REPORTS, create_app
    from cite_or_refuse.evaluation import run_eval
    from cite_or_refuse.generator import ensure_data
    from cite_or_refuse.pipeline import Pipeline

    ensure_data()
    pipeline = Pipeline()
    print(f"Indexed {len(pipeline.corpus.chunks)} chunks from {len(pipeline.corpus.calls)} calls "
          f"and {len(pipeline.corpus.docs)} case files.")
    if not all(p.exists() for p in REPORTS.values()):
        import eval as eval_cli

        print("No eval report found, running the eval once...")
        eval_cli.write(run_eval(pipeline), REPORTS["clean"])
        eval_cli.write(run_eval(pipeline, inject_faults=True), REPORTS["faults"])
    print(f"Open http://{args.host}:{args.port}")
    uvicorn.run(create_app(pipeline), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
