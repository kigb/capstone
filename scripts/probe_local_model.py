"""Run a short GPU inference using cached weights, without downloading files."""

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--revision")
    parser.add_argument("--disable-thinking", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("A working CUDA device is required for this probe.")

    print(f"Loading cached {args.model} on {torch.cuda.get_device_name(0)}", flush=True)
    started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        revision=args.revision,
        local_files_only=True,
        dtype=torch.bfloat16,
        device_map="cuda:0",
        attn_implementation="sdpa",
    ).eval()
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - started

    messages = [
        {"role": "system", "content": "Answer the multiple-choice question accurately and briefly."},
        {
            "role": "user",
            "content": (
                "Where should fresh milk be kept to stay cold?\n"
                "A: oven\nB: refrigerator\nC: bookshelf\nD: wardrobe\nE: desk\n"
                "Use exactly three lines:\n"
                "<REASON>: one short sentence\n"
                "<ANSWER>: one option letter\n"
                "<MEMORY>: one short sentence"
            ),
        },
    ]
    template_kwargs = {"enable_thinking": False} if args.disable_thinking else {}
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, **template_kwargs)
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda:0")
    generation_config = GenerationConfig(
        do_sample=False,
        max_new_tokens=96,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=model.generation_config.eos_token_id,
    )
    with torch.inference_mode():
        model.generate(**inputs, generation_config=generation_config, max_new_tokens=4, use_model_defaults=False, do_sample=False)
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        output = model.generate(**inputs, generation_config=generation_config, use_model_defaults=False, do_sample=False)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - started

    generated = output[0, inputs["input_ids"].shape[1]:]
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "revision": getattr(model.config, "_commit_hash", None),
        "gpu": torch.cuda.get_device_name(0),
        "compute_capability": list(torch.cuda.get_device_capability(0)),
        "architecture": platform.machine(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "dtype": str(next(model.parameters()).dtype),
        "device": str(next(model.parameters()).device),
        "attention": model.config._attn_implementation,
        "local_files_only": True,
        "chat_template_kwargs": template_kwargs,
        "use_model_defaults": False,
        "do_sample": False,
        "load_seconds": round(load_seconds, 3),
        "input_tokens": int(inputs["input_ids"].shape[1]),
        "generated_tokens_including_eos": int(generated.numel()),
        "generation_seconds_including_prefill": round(elapsed, 3),
        "tokens_per_second_including_prefill": round(generated.numel() / elapsed, 2),
        "peak_torch_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
        "messages": messages,
        "response": tokenizer.decode(generated, skip_special_tokens=True),
        "scope": "One short warmed-up request; not a NetSafe or concurrency benchmark.",
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered, flush=True)


if __name__ == "__main__":
    main()
