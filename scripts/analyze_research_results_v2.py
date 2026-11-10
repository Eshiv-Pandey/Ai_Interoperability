"""Merge preserved four-arm development evidence with one supplemental arm.

Reads retained outputs only. The original 1,056 cell dictionaries are preserved;
264 conventional constraint-pruning cells are appended on exact case/profile/
clock joins. No solver, certificate checker, application or model is executed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_research_results_v1 as original

BUDGETS = original.BUDGETS
ARMS = original.ARMS + ("guard_pruned",)
LABELS = original.LABELS + ("Constraint-pruned direct",)
SHORT = ("Legacy\ndirect", "Goal-pruned\ndirect", "Original\nrefinement", "Shared\nlifting", "Constraint-pruned\ndirect")
COLORS = ("#777777", "#0072B2", "#D55E00", "#009E73", "#CC79A7")
GUARD_ARCHIVE_SHA = "ae24d4ed85f23100f6e994d26386322d7d7ac781d22d180200c687d611c666fc"


def input_record(path):
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": original.sha(path)}


def deterministic(execution):
    result = dict(execution["result"])
    if "stats" in result:
        result["stats"] = {key: value for key, value in result["stats"].items() if key != "elapsed_ns"}
    return result


def collect_guard(source, guard, retained_rows, pairs):
    result = original.load(guard / "result.json")
    assert result["status"] == "passed" and result["original_four_arm_outputs_changed"] is False
    assert result["new_application_requests"] == result["new_live_model_requests"] == 0
    records = [input_record(guard / name) for name in ("result.json", "manifest.json", "plan.json", "driver-source.py", "guard-source.py")]
    checked = 0
    for record in original.load(guard / "manifest.json")["files"]:
        path = guard / record["path"]
        assert path.resolve().is_relative_to(guard) and not path.is_symlink()
        assert path.stat().st_size == record["bytes"] and original.sha(path) == record["sha256"]
        checked += 1
    plan = original.load(guard / "plan.json")
    assert tuple(plan["budgets"]) == BUDGETS and plan["case_count"] == 66 and plan["clock"] == 100
    assert original.sha(guard / "guard-source.py") == plan["new_guard_source"]["sha256"]
    addition, joins = [], []
    pairs_by_key = {(row["budget"], row["case_id"]): row for row in pairs}
    for budget in BUDGETS:
        old_folder, folder = source / f"budget-{budget}", guard / f"budget-{budget}"
        assert original.sha(old_folder / "manifest.json") == plan["old_manifests"][str(budget)]["sha256"]
        records.extend(input_record(folder / name) for name in ("results.jsonl", "summary.json", "execution.json"))
        previous = [json.loads(line) for line in (old_folder / "results.jsonl").read_bytes().splitlines()]
        current = [json.loads(line) for line in (folder / "results.jsonl").read_bytes().splitlines()]
        assert len(current) == len(previous) == len({row["case_id"] for row in current}) == 66
        for old, now in zip(previous, current):
            for key in ("case_id", "family", "model_sha256", "evaluation_clock", "input_schema"):
                assert old[key] == now[key], "exact_join_changed:" + key
            assert old["evaluation_clock"] == 100
            old_input, new_input = old_folder / old["input_snapshot"], folder / now["input_snapshot"]
            assert old_input.resolve().is_relative_to(old_folder) and new_input.resolve().is_relative_to(folder)
            old_profile, new_profile = original.load(old_input), original.load(new_input)
            assert original.canonical(old_profile) == original.canonical(new_profile), "captured_profile_changed"
            assert old_profile["model"]["horizon"] == new_profile["model"]["horizon"]
            assert deterministic(now["algorithms"]["baseline"]["execution"]) == deterministic(old["algorithms"]["baseline"]["execution"])
            entry = now["algorithms"]["guard_pruned"]
            execution, value = entry["execution"], entry["execution"]["result"]
            assert execution["status"] == "returned" and execution["process"]["returncode"] == 0
            assert not execution["process"]["timed_out"] and execution["input_unchanged"]
            decision, certificate = value["decision"], value["certificate"]
            assert decision in {"supported", "unsupported", "unknown"} and entry["valid_result"] is True
            certified = decision in {"supported", "unsupported"} and entry["certificate_valid"] is True
            if decision == "unknown":
                assert certificate is None and entry["certificate_valid"] is None
            else:
                assert certified and entry["certificate_check"]["result"] is True
                assert certificate["checked_at"] == now["evaluation_clock"]
            assert value["stats"]["budget"] == budget
            addition.append({"budget": budget, "case_id": now["case_id"], "family": now["family"],
                             "method": "guard_pruned", "decision": decision, "certified": int(certified),
                             "solver_work_units": value["stats"].get("work_units", ""),
                             "certificate_bytes": len(original.canonical(certificate)) if certified else "",
                             "model_sha256": now["model_sha256"], "worker_status": execution["status"]})
            pairs_by_key[budget, now["case_id"]]["guard_pruned"] = int(certified)
            joins.append({"budget": budget, "case_id": now["case_id"], "family": now["family"],
                          "model_sha256": now["model_sha256"], "evaluation_clock": now["evaluation_clock"],
                          "horizon": new_profile["model"]["horizon"], "input_schema": now["input_schema"],
                          "original_captured_input_sha256": original.sha(old_input),
                          "supplement_captured_input_sha256": original.sha(new_input),
                          "parsed_profile_equal": True, "fresh_baseline_deterministic_result_equal": True})
        selected = [row for row in addition if row["budget"] == budget]
        report = result["reports"][str(budget)]
        assert sum(row["certified"] for row in selected) == report["certified"]
        assert sum(row["solver_work_units"] for row in selected) == report["solver_work_units"]
    assert len(addition) == len(joins) == 264
    assert len(retained_rows) == 1056
    return addition, joins, records, checked


def paired_comparisons(pairs):
    output = []
    for left, right in (("shared_lift", "direct_pruned"), ("guard_pruned", "direct_pruned"), ("shared_lift", "guard_pruned")):
        for budget in BUDGETS:
            values = [row for row in pairs if row["budget"] == budget]
            families = defaultdict(list)
            for row in values:
                families[row["family"]].append(row[left] - row[right])
            rng, names, samples = random.Random(1729), sorted(families), []
            for _ in range(2000):
                sample = [item for name in rng.choices(names, k=len(names)) for item in families[name]]
                samples.append(sum(sample) / len(sample))
            output.append({"budget": budget, "left_method": left, "right_method": right,
                           "profiles": len(values), "development_families": len(names),
                           "both_certified": sum(row[left] and row[right] for row in values),
                           "left_only": sum(row[left] and not row[right] for row in values),
                           "right_only": sum(row[right] and not row[left] for row in values),
                           "neither_certified": sum(not row[left] and not row[right] for row in values),
                           "paired_coverage_difference": sum(row[left] - row[right] for row in values) / len(values),
                           "family_resampling_lower": original.quantile(samples, .025),
                           "family_resampling_upper": original.quantile(samples, .975),
                           "range_scope": "exploratory family-mixture sensitivity; not a population confidence interval"})
    return output


def plot(output, totals, families):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.hashsalt": "research-analysis-v2-five-arm", "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.3))
    fig.subplots_adjust(left=.08, right=.98, top=.88, bottom=.23, hspace=.60, wspace=.31)
    x = list(range(len(BUDGETS)))
    width = .15
    for index, (arm, label, color) in enumerate(zip(ARMS, LABELS, COLORS)):
        selected = {row["budget"]: row for row in totals if row["method"] == arm}
        axes[0, 0].bar([value + (index - 2) * width for value in x],
                       [100 * selected[budget]["certified"] / selected[budget]["profiles"] for budget in BUDGETS],
                       width=width, color=color, label=label)
    axes[0, 0].set_xticks(x, [f"{budget:,}" for budget in BUDGETS])
    axes[0, 0].set(title="A. Certified coverage, all 66 development profiles", xlabel="Method-specific work allowance (categorical)",
                   ylabel="Certified profiles (%)", ylim=(0, 100))
    high = {row["method"]: row for row in totals if row["budget"] == 100000}
    for axis, field, title, label in ((axes[0, 1], "solver_work_units", "B. Charged solver work at allowance 100,000", "Charged operations\n(method-specific units; all 66 profiles)"),
                                     (axes[1, 0], "certificate_bytes", "C. Accepted proof bytes: 54 certified profiles per method", "Canonical proof JSON (bytes)")):
        values = [high[arm][field] for arm in ARMS]
        bars = axis.bar(range(len(ARMS)), values, color=COLORS, width=.65)
        axis.set_xticks(range(len(ARMS)), SHORT, fontsize=8)
        axis.set(title=title, ylabel=label, ylim=(0, max(values) * 1.22))
        axis.bar_label(bars, labels=[f"{value:,}" for value in values], padding=3, fontsize=8)
        axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{int(value):,}"))
    names = sorted({row["family"] for row in families})
    methods = ("direct_pruned", "shared_lift", "guard_pruned")
    for index, arm in enumerate(methods):
        selected = {row["family"]: row for row in families if row["method"] == arm and row["budget"] == 256}
        axes[1, 1].bar([value + (index - 1) * .25 for value in range(len(names))],
                       [100 * selected[name]["certified"] / selected[name]["profiles"] for name in names],
                       width=.25, color=COLORS[ARMS.index(arm)])
    axes[1, 1].set_xticks(range(len(names)), [name.replace("_", "\n") for name in names], fontsize=7)
    axes[1, 1].set(title="D. Existing development families at allowance 256", ylabel="Certified profiles (%)", ylim=(0, 100))
    for axis in axes.flat:
        axis.set_axisbelow(True)
        axis.grid(axis="y", color="#e6e6e6", linewidth=.6)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=3, loc="lower center", bbox_to_anchor=(.5, .09), frameon=False, fontsize=9)
    fig.suptitle("Five-method development comparison", fontsize=14, y=.96)
    fig.text(.5, .035, "Preserved Windows four-arm evidence + separate Linux constraint-pruning supplement.\n"
             "Related authored profiles; method-specific work charges; unknown proof sizes are missing. No CPU-speed or held-out claim.",
             ha="center", fontsize=8)
    for extension in ("png", "svg", "pdf"):
        fig.savefig(output / f"development-comparison-five-arm.{extension}", dpi=180)
    plt.close(fig)
    return {name: importlib.metadata.version(name) for name in ("matplotlib", "numpy", "pillow")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "runs/shared-lifting-scaling/v3-20261110-1")
    parser.add_argument("--guard", type=Path, default=ROOT / "runs/guard-pruned-comparison/download-42836579527")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plot", action="store_true")
    args = parser.parse_args()
    source, guard, output = args.source.resolve(), args.guard.resolve(), args.output.resolve()
    assert source.is_relative_to(ROOT) and guard.is_relative_to(ROOT) and output.is_relative_to(ROOT / "runs/research-analysis")
    assert not output.exists() and not source.is_relative_to(output) and not guard.is_relative_to(output)
    output.mkdir(parents=True)
    result = {"schema_version": "research-development-analysis/2", "status": "failed",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "new_solver_or_checker_requests": 0,
              "new_application_or_model_requests": 0}
    try:
        retained, pairs, inputs, original_checked = original.collect(source)
        retained_identity = original.canonical(retained)
        added, joins, guard_inputs, guard_checked = collect_guard(source, guard, retained, pairs)
        rows = retained + added
        assert len(rows) == len({(row["budget"], row["case_id"], row["method"]) for row in rows}) == 1320
        assert original.canonical(rows[:1056]) == retained_identity
        assert all(row["certificate_bytes"] == "" for row in rows if row["decision"] == "unknown")
        inputs += guard_inputs + [input_record(Path(__file__)), input_record(Path(original.__file__))]
        archive = ROOT / "runs/guard-pruned-comparison/retained-42836579527.zip"
        if archive.is_file():
            assert original.sha(archive) == GUARD_ARCHIVE_SHA
            inputs.append(input_record(archive))
        totals, families = original.aggregates(rows, ("budget", "method")), original.aggregates(rows, ("budget", "family", "method"))
        paired = original.paired_sensitivity(pairs)
        comparisons = paired_comparisons(pairs)
        for name, data in (("case-methods", rows), ("budget-methods", totals), ("family-methods", families),
                           ("paired-certification-original", paired), ("paired-comparisons", comparisons), ("join-ledger", joins)):
            original.write_csv(output / (name + ".csv"), data)
        dependencies = plot(output, totals, families) if args.plot else {}
        assert all(original.sha(ROOT / row["path"]) == row["sha256"] for row in inputs)
        result.update(status="verified", script_sha256=original.sha(Path(__file__)),
                      original_v1_helper_sha256=original.sha(Path(original.__file__)),
                      python_version=list(sys.version_info[:3]), python_executable=str(Path(sys.executable).resolve()),
                      input_files=inputs, original_manifest_files_verified=original_checked,
                      guard_manifest_files_verified=guard_checked, preserved_original_cells=1056,
                      supplemental_guard_cells=264, case_method_rows=1320, exact_profile_clock_joins=264,
                      original_cell_projection_unchanged=True, unknown_proof_metrics_blank=True,
                      budget_method_totals=totals, paired_comparisons=comparisons, plot_dependencies=dependencies,
                      scope="Exploratory authored-development evidence; deterministic work/proof metrics only; separate Windows and Linux runs",
                      sensitivity_scope="Complete existing-family resampling; not a population confidence interval")
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    result["outputs"] = [{"path": path.name, "sha256": original.sha(path), "bytes": path.stat().st_size}
                         for path in sorted(output.iterdir()) if path.is_file()]
    with (output / "result.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: result.get(key) for key in ("status", "case_method_rows", "exact_profile_clock_joins", "error_type", "error")}))
    return 0 if result["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
