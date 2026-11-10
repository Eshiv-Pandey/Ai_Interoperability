"""Regenerate tables and scientific figures from all retained development results."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = (32, 256, 4096, 100000)
ARMS = ("baseline", "direct_pruned", "candidate", "shared_lift")
LABELS = ("Legacy direct", "Goal-pruned direct", "Original refinement", "Shared lifting")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def write_csv(path, rows):
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def quantile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    index = int(position)
    return values[index] + (values[min(index + 1, len(values) - 1)] - values[index]) * (position - index)


def collect(source):
    raw_rows, input_records, pair_rows, manifest_files = [], [], [], 0
    input_records.append({"path": (source / "result.json").relative_to(ROOT).as_posix(),
                          "sha256": sha(source / "result.json")})
    terminal = load(source / "result.json")
    assert terminal["status"] == "passed" and terminal["all_four_budget_bundles_verified"]
    for budget in BUDGETS:
        folder = source / f"budget-{budget}"
        for name in ("manifest.json", "results.jsonl", "summary.json", "execution.json"):
            path = folder / name
            input_records.append({"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
        for record in load(folder / "manifest.json")["files"]:
            path = folder / record["path"]
            assert path.resolve().is_relative_to(folder.resolve()) and not path.is_symlink()
            assert path.stat().st_size == record["bytes"] and sha(path) == record["sha256"]
            manifest_files += 1
        cases = [json.loads(line) for line in (folder / "results.jsonl").read_text().splitlines()]
        assert len(cases) == len({row["case_id"] for row in cases}) == 66
        summary = load(folder / "summary.json")
        for case in cases:
            pair = {"budget": budget, "case_id": case["case_id"], "family": case["family"]}
            for arm in ARMS:
                entry = case["algorithms"][arm]
                execution = entry["execution"]
                result = execution.get("result") or {}
                decision = result.get("decision", "execution_error")
                certificate = result.get("certificate")
                certified = decision in ("supported", "unsupported") and entry["certificate_valid"] is True
                if decision in ("supported", "unsupported"):
                    assert certified and entry["certificate_check"]["result"] is True
                if decision == "unknown":
                    assert certificate is None
                pair[arm] = int(certified)
                raw_rows.append({"budget": budget, "case_id": case["case_id"], "family": case["family"],
                                 "method": arm, "decision": decision, "certified": int(certified),
                                 "solver_work_units": result.get("stats", {}).get("work_units", ""),
                                 "certificate_bytes": len(canonical(certificate)) if certified else "",
                                 "model_sha256": case["model_sha256"], "worker_status": execution["status"]})
            pair_rows.append(pair)
        for arm in ARMS:
            rows = [row for row in raw_rows if row["budget"] == budget and row["method"] == arm]
            assert sum(row["certified"] for row in rows) == summary["algorithms"][arm]["certificates_valid"]
    assert len(raw_rows) == 1056 and len(pair_rows) == 264
    return raw_rows, pair_rows, input_records, manifest_files


def aggregates(rows, fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    result = []
    for key, values in sorted(groups.items()):
        decisions = Counter(row["decision"] for row in values)
        result.append({**dict(zip(fields, key)), "profiles": len(values),
                       "certified": sum(row["certified"] for row in values),
                       "supported": decisions["supported"], "unsupported": decisions["unsupported"],
                       "unknown": decisions["unknown"], "execution_error": decisions["execution_error"],
                       "solver_work_units": sum(row["solver_work_units"] for row in values if row["solver_work_units"] != ""),
                       "certificate_bytes": sum(row["certificate_bytes"] for row in values if row["certificate_bytes"] != "")})
    return result


def paired_sensitivity(pairs):
    output = []
    for budget in BUDGETS:
        values = [row for row in pairs if row["budget"] == budget]
        families = defaultdict(list)
        for row in values:
            families[row["family"]].append(row["shared_lift"] - row["direct_pruned"])
        rng, names, samples = random.Random(1729), sorted(families), []
        for _ in range(2000):
            sampled = [item for name in rng.choices(names, k=len(names)) for item in families[name]]
            samples.append(sum(sampled) / len(sampled))
        output.append({"budget": budget, "profiles": len(values), "development_families": len(names),
                       "both_certified": sum(row["shared_lift"] and row["direct_pruned"] for row in values),
                       "direct_only": sum(row["direct_pruned"] and not row["shared_lift"] for row in values),
                       "shared_only": sum(row["shared_lift"] and not row["direct_pruned"] for row in values),
                       "neither_certified": sum(not row["direct_pruned"] and not row["shared_lift"] for row in values),
                       "paired_coverage_difference": sum(row["shared_lift"] - row["direct_pruned"] for row in values) / len(values),
                       "family_resampling_lower": quantile(samples, .025), "family_resampling_upper": quantile(samples, .975)})
    return output


def plot(output, budgets, families):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.hashsalt": "research-analysis-v1", "pdf.fonttype": 42})
    colors = ("#777777", "#0072B2", "#D55E00", "#009E73")
    figure, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for arm, label, color, marker in zip(ARMS, LABELS, colors, ("o", "s", "^", "D")):
        selected = sorted((row for row in budgets if row["method"] == arm), key=lambda row: row["budget"])
        axes[0, 0].plot(BUDGETS, [100 * row["certified"] / row["profiles"] for row in selected],
                        marker=marker, color=color, label=label)
    axes[0, 0].set(xscale="log", xlabel="Method-specific work allowance", ylabel="Certified profiles (%)",
                   title="A. Coverage across all 66 development profiles", ylim=(-2, 100))
    axes[0, 0].legend(fontsize=8, loc="lower right")
    high = {row["method"]: row for row in budgets if row["budget"] == 100000}
    short = ("Legacy", "Pruned", "Refinement", "Shared")
    for axis, field, title, label in ((axes[0, 1], "solver_work_units", "B. Solver work at allowance 100,000", "Method-specific operations (all 66 profiles)"),
                                      (axes[1, 0], "certificate_bytes", "C. Independently accepted proof representation", "Canonical JSON bytes (54 certified profiles)")):
        bars = axis.bar(short, [high[arm][field] for arm in ARMS], color=colors)
        axis.set(title=title, ylabel=label, ylim=(0, max(high[arm][field] for arm in ARMS) * 1.25))
        axis.bar_label(bars, padding=3, fontsize=8)
        axis.margins(y=.22)
    names = sorted({row["family"] for row in families})
    x = list(range(len(names)))
    for arm, offset, color, label in (("direct_pruned", -.18, colors[1], "Goal-pruned direct"), ("shared_lift", .18, colors[3], "Shared lifting")):
        selected = {row["family"]: row for row in families if row["method"] == arm and row["budget"] == 256}
        axes[1, 1].bar([value + offset for value in x], [100 * selected[name]["certified"] / selected[name]["profiles"] for name in names],
                        width=.36, color=color, label=label)
    axes[1, 1].set_xticks(x, [name.replace("_", "\n") for name in names], fontsize=7)
    axes[1, 1].set(ylabel="Certified profiles (%)", ylim=(0, 110), title="D. Existing development families at allowance 256")
    axes[1, 1].legend(fontsize=8)
    figure.suptitle("Development comparison: coverage, charged work and proof size", fontsize=12)
    for extension in ("png", "pdf", "svg"):
        figure.savefig(output / f"development-comparison.{extension}", dpi=180)
    plt.close(figure)
    return {name: importlib.metadata.version(name) for name in ("matplotlib", "numpy", "pillow")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "runs/shared-lifting-scaling/v3-20261110-1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    assert source.is_relative_to(ROOT) and output.is_relative_to(ROOT / "runs/research-analysis")
    assert not output.exists() and not source.is_relative_to(output)
    rows, pairs, inputs, checked = collect(source)
    totals, families, paired = aggregates(rows, ("budget", "method")), aggregates(rows, ("budget", "family", "method")), paired_sensitivity(pairs)
    output.mkdir(parents=True)
    for name, data in (("case-methods", rows), ("budget-methods", totals), ("family-methods", families), ("paired-certification", paired)):
        write_csv(output / f"{name}.csv", data)
    dependencies = plot(output, totals, families) if args.plot else {}
    assert all(sha(ROOT / record["path"]) == record["sha256"] for record in inputs)
    result = {"schema_version": "research-development-analysis/1", "status": "verified",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "script_sha256": sha(Path(__file__)),
              "python_version": list(sys.version_info[:3]), "python_executable": str(Path(sys.executable).resolve()),
              "input_files": inputs, "manifest_files_verified": checked, "case_method_rows": len(rows),
              "budget_method_totals": totals, "paired_certification": paired, "plot_dependencies": dependencies,
              "scope": "Exploratory analysis of authored development profiles; no new solver/model/application execution.",
              "sensitivity_scope": "Resampling complete existing families; not a population confidence interval.",
              "outputs": [{"path": path.name, "sha256": sha(path), "bytes": path.stat().st_size} for path in sorted(output.iterdir())]}
    with (output / "result.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"status": result["status"], "manifest_files_verified": checked,
                      "case_method_rows": len(rows), "outputs": [row["path"] for row in result["outputs"]]}))


if __name__ == "__main__":
    main()
