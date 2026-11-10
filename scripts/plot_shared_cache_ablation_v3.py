"""Create exportable cache-ablation figures from audited cells, without reruns."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def run(audit, output):
    if output.exists():
        raise ValueError("Require fresh figure allocation")
    report = json.loads((audit / "result.json").read_bytes())
    if report["status"] != "passed_read_only_raw_cell_and_source_audit":
        raise ValueError("Require completed read audit")
    expected = next(row for row in report["exports"] if row["path"] == "budget-methods.csv")
    data = (audit / "budget-methods.csv").read_bytes()
    if hashlib.sha256(data).hexdigest() != expected["sha256"]:
        raise ValueError("Audited table changed")
    rows = list(csv.DictReader(data.decode().splitlines()))
    methods = ("direct_pruned", "cache_neither", "cache_prefix", "cache_relation", "cache_both")
    labels = ("Goal-pruned direct", "Neither cache", "Prefix only", "Relation only", "Both caches")
    colors = ("#1f4d77", "#686868", "#3e7c59", "#9b6e26", "#a4474b")
    indexed = {(int(r["budget"]), r["method"]): r for r in rows}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "pdf.fonttype": 42,
                         "svg.fonttype": "none", "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.3), constrained_layout=True)
    for method, label, color in zip(methods, labels, colors):
        values = [int(indexed[b, method]["certified"]) for b in (32, 256, 4096, 100000)]
        axes[0, 0].plot(range(4), values, label=label, color=color, marker="o", linewidth=1.8)
    axes[0, 0].set_xticks(range(4), ("32", "256", "4,096", "100,000"))
    axes[0, 0].set_ylim(0, 66)
    axes[0, 0].set_ylabel("Certified profiles / 66")
    axes[0, 0].set_xlabel("Method-specific work allowance (categorical)")
    axes[0, 0].set_title("A  Certified coverage at each allowance", loc="left", fontweight="bold")
    for ax, field, title, ylabel in (
        (axes[0, 1], "work_units_sum", "B  Charged solver work at 100,000", "Method-specific work units (sum)"),
        (axes[1, 0], "proof_bytes_sum", "C  Accepted proof bytes at 100,000", "Canonical JSON bytes (sum)")):
        values = [int(indexed[100000, method][field]) for method in methods]
        ax.bar(range(5), values, color=colors)
        ax.set_xticks(range(5), ("Direct", "Neither", "Prefix", "Relation", "Both"))
        ax.set_ylim(bottom=0)
        ax.set_ylabel(ylabel)
        ax.set_title(title, loc="left", fontweight="bold")
    ax = axes[1, 1]
    policies = methods[1:]
    xs = list(range(4))
    ax.bar([x - .18 for x in xs], [int(indexed[100000, m]["prefix_cache_hits_sum"]) for m in policies],
           width=.36, label="Prefix hits", color="#3e7c59")
    ax.bar([x + .18 for x in xs], [int(indexed[100000, m]["relation_cache_hits_sum"]) for m in policies],
           width=.36, label="Relation hits", color="#9b6e26")
    ax.set_xticks(xs, ("Neither", "Prefix", "Relation", "Both"))
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Recorded cache hits (sum)")
    ax.set_title("D  Reuse at 100,000; hits are not speed", loc="left", fontweight="bold")
    ax.legend(frameon=False, fontsize=9)
    for ax in axes.flat:
        ax.grid(axis="y", alpha=.18)
        ax.set_axisbelow(True)
    axes[0, 0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("Cache ablations on 66 authored development profiles\nAll four budgets retained; no held-out or CPU-speed claim", fontsize=13)
    output.mkdir(parents=True)
    artifacts = []
    for suffix in ("png", "svg", "pdf"):
        path = output / ("shared-cache-ablation." + suffix)
        fig.savefig(path, dpi=190, metadata={"Creator": "Matplotlib"})
        raw = path.read_bytes()
        artifacts.append({"path": path.name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    plt.close(fig)
    value = {"status": "generated_from_audited_tables", "source_table_sha256": expected["sha256"], "artifacts": artifacts,
             "python_executable": sys.executable, "matplotlib": importlib.metadata.version("matplotlib"),
             "new_solver_checker_application_or_provider_calls": 0,
             "caption": "Five arms from a six-arm ablation on the same 66 related authored profiles. Every y-axis starts at zero. All 54 profiles are certified at 100000; unknowns remain in the denominator. Work is method-specific, proof bytes canonical JSON; neither cache changes accepted proof size at the largest allowance. Reuse counts do not demonstrate CPU speed or novelty."}
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2); stream.write("\n")
    print(json.dumps(value))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.audit, args.output)
