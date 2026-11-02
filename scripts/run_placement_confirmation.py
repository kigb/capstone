"""Evaluate frozen behavior placement on 30 fresh questions with all degree ties."""

import argparse
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
import transformers

from confirmation_common import (
    ROOT, PRIOR, archive_jsonl, build_protocol, digest, file_hash, read_json,
    restore_jsonl, trial_specs,
)
from run_local_baseline import LocalBackend, install_tolerant_parser, upstream_runtime, utc_now, write_json
from run_placement_study import run_phase, save_once


def prepare(output):
    protocol, questions, frozen, behavior = build_protocol()
    specs = trial_specs(protocol, questions, behavior)
    output.mkdir(parents=True, exist_ok=True)
    save_once(output / "protocol.json", protocol)
    save_once(output / "evaluation_questions.json", questions)
    # Copy exact bytes, including the original freeze timestamp and parent hash.
    frozen_path = output / "behavior_model.json"
    if not frozen_path.exists():
        frozen_path.write_bytes((PRIOR / "behavior_model.json").read_bytes())
    assert file_hash(frozen_path) == file_hash(PRIOR / "behavior_model.json")
    save_once(output / "evaluation_manifest.json", {
        "protocol_sha256": digest(protocol), "behavior_model_sha256": file_hash(frozen_path), "trials": specs,
    })
    freeze_path = output / "freeze.json"
    save_once(freeze_path, {"protocol_sha256": digest(protocol),
        "behavior_model_sha256": file_hash(frozen_path),
        "manifest_sha256": file_hash(output / "evaluation_manifest.json"),
        "frozen_at_utc": read_json(freeze_path)["frozen_at_utc"] if freeze_path.exists() else utc_now()})
    return protocol, questions, specs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/netsafe_confirmation_qwen8b")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    protocol, questions, specs = prepare(args.output)
    if args.prepare_only:
        print(json.dumps({"protocol_sha256": digest(protocol), "new_questions": len(questions),
                          "named_trajectories": len(specs), "logical_responses": len(specs) * 8 * 5}, indent=2))
        return
    if (args.output / "summary_runtime.json").exists():
        raise ValueError("Confirmation complete; use another output directory for a repeat")
    assert subprocess.check_output(["git", "-C", str(ROOT / "third_party/NetSafe"), "rev-parse", "HEAD"], text=True).strip() == protocol["upstream_commit"]
    for name in ["generation_cache.jsonl", "evaluation.jsonl"]:
        restore_jsonl(args.output / name)
    source_files = ["run_placement_confirmation.py", "confirmation_common.py", "run_placement_study.py",
                    "run_local_baseline.py", "placement_common.py", "netsafe_metrics.py"]
    sources = {name: file_hash(ROOT / "scripts" / name) for name in source_files}
    started, started_utc = time.perf_counter(), utc_now()
    runtime, prompts = upstream_runtime()
    install_tolerant_parser(runtime)
    torch.manual_seed(protocol["split_seed"])
    backend = LocalBackend(protocol["model"], args.output, protocol["batch_size"], protocol["max_new_tokens"],
                           digest(protocol), revision=protocol["model_revision"], chat_template_kwargs=protocol["chat_template_kwargs"])
    runtime["Agent"].chat = lambda agent, prompt: backend.enqueue(agent, prompt)
    records = run_phase(backend, runtime, prompts, protocol, specs, questions, args.output, "evaluation")
    backend.cache_file.close()
    used = {r["cache_key"] for t in records for a in t["agents"] for r in a["rounds"]}
    entries = [backend.cache[k] for k in used]
    plain_hashes = {name: file_hash(args.output / name) for name in ("evaluation.jsonl", "generation_cache.jsonl")}
    archive_start = time.perf_counter()
    archives = {name: archive_jsonl(args.output / name) for name in plain_hashes}
    summary = {
        "started_utc": started_utc, "completed_utc": utc_now(), "wall_seconds": time.perf_counter() - started,
        "model_load_seconds": backend.load_seconds, "archive_seconds": time.perf_counter() - archive_start,
        "timing_scope": "wall_seconds covers this process; cached_at_start identifies a resumed invocation. Total cached batch compute includes completed batches from earlier invocations.",
        "total_cached_batch_compute_seconds": sum(e["batch_seconds"] / e["batch_size"] for e in backend.cache.values()),
        "logical_generations": len(specs) * protocol["num_agents"] * (protocol["discussion_rounds"] + 1),
        "named_trajectories": len(specs), "unique_generations": len(used), "cache_entries_including_unused": len(backend.cache),
        "cached_at_start": backend.cached_at_start, "new_generations_this_run": len(backend.cache) - backend.cached_at_start,
        "generated_batches": backend.generated_batches, "unique_input_tokens": sum(e["input_tokens"] for e in entries),
        "unique_output_tokens": sum(e["generated_tokens"] for e in entries), "unique_truncated_generations": sum(e["truncated"] for e in entries),
        "peak_torch_allocated_gib": torch.cuda.max_memory_allocated() / 2**30,
        "model_revision": getattr(backend.model.config, "_commit_hash", None), "gpu": torch.cuda.get_device_name(0),
        "platform": platform.platform(), "torch": torch.__version__, "torch_cuda": torch.version.cuda,
        "transformers": transformers.__version__, "numpy": np.__version__, "effective_generation": backend.effective_generation,
        "source_sha256": sources, "protocol_sha256": digest(protocol),
        "behavior_model_sha256": file_hash(args.output / "behavior_model.json"),
        "uncompressed_jsonl_sha256": plain_hashes,
        "archive_sha256": {p.name: file_hash(p) for p in archives.values()},
    }
    write_json(args.output / "summary_runtime.json", summary)
    print(json.dumps({"event": "confirmation_complete", **summary}, indent=2), flush=True)


if __name__ == "__main__":
    main()
