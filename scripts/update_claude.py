from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE = ROOT / "CLAUDE.md"
BENCH_SCRIPT = ROOT / "tests" / "bench_comparison.py"

START = "<!-- BENCHMARK_TABLE:START -->"
END = "<!-- BENCHMARK_TABLE:END -->"


def run_bench() -> str:
    proc = subprocess.run(
        [
            "python",
            str(BENCH_SCRIPT),
            "--rounds",
            "5",
            "--warmup",
            "2",
            "--iters",
            "100",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    out = proc.stdout
    start = out.find(START)
    end = out.find(END)
    if start == -1 or end == -1:
        raise RuntimeError("Benchmark output did not contain benchmark markers")
    end += len(END)
    return out[start:end]


def update_claude(benchmark_block: str) -> None:
    text = CLAUDE.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        re.DOTALL,
    )
    if pattern.search(text):
        new_text = pattern.sub(benchmark_block, text)
    else:
        new_text = text.rstrip() + "\n\n" + benchmark_block + "\n"
    CLAUDE.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    block = run_bench()
    update_claude(block)
    print("Updated CLAUDE.md benchmark table")
