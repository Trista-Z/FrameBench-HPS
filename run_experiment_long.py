"""
run_experiment_long.py

Run the expanded probability-framing experiment using the LONG dataset.

Input:
- framebench_hps_probability_long.csv
  One row = one prompt:
  scenario_id x probability_level x frame

Output:
- results_probability_framing_raw.csv

Why long format?
- Easier for factorial analysis:
  frame: neutral / gain / loss
  probability_positive: 20 / 40 / 60 / 80
  model_alias: deepseek / qwen / gpt4omini / etc.

Required environment variables:
- DEEPSEEK_API_KEY
- QWEN_API_KEY, if using Qwen
- OPENAI_API_KEY, if using OpenAI

Examples:
python3 run_experiment_long.py --models deepseek --limit 10
python3 run_experiment_long.py --models deepseek qwen gpt4omini
"""

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
from openai import OpenAI
from tqdm import tqdm

INPUT_FILE = "framebench_hps_probability_long.csv"
OUTPUT_FILE = "results_probability_framing_raw.csv"

MODEL_CONFIGS = {
    "deepseek": {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "provider": "qwen",
        "model": "qwen-plus",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "QWEN_API_KEY",
    },
    "gpt4omini": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
    },
    "gpt41mini": {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "base_url": None,
        "api_key_env": "OPENAI_API_KEY",
    },
}

SYSTEM_PROMPT = (
    "You are a careful decision-support assistant. "
    "You must follow the requested JSON format exactly. "
    "Do not include markdown fences or extra prose outside JSON."
)

def make_client(config):
    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise ValueError(
            f"Missing API key. Please set environment variable {config['api_key_env']}."
        )

    if config["base_url"]:
        return OpenAI(api_key=api_key, base_url=config["base_url"])
    return OpenAI(api_key=api_key)

def parse_json_safely(text):
    if not isinstance(text, str):
        return {}

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except Exception:
        pass

    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end])
    except Exception:
        return {}

    return {}

def normalize_recommendation(value):
    if not isinstance(value, str):
        return ""
    v = value.strip().lower()

    if v in {"yes", "no", "uncertain"}:
        return v

    # Very conservative fallback
    if "uncertain" in v or "depends" in v:
        return "uncertain"
    if "yes" in v and "no" not in v:
        return "yes"
    if "no" in v and "yes" not in v:
        return "no"

    return v[:30]

def to_int_or_blank(value):
    try:
        if value == "":
            return ""
        x = int(float(value))
        if 1 <= x <= 5:
            return x
        return ""
    except Exception:
        return ""

def ask_model(client, model_name, prompt, max_retries=4, sleep_base=2):
    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                max_tokens=400,
            )
            return response.choices[0].message.content, None
        except Exception as e:
            last_error = str(e)
            wait = sleep_base * (attempt + 1)
            print(f"\nAPI error attempt {attempt + 1}/{max_retries}: {last_error}")
            time.sleep(wait)

    return "ERROR", last_error

def load_completed(output_file):
    if not Path(output_file).exists():
        return set()

    existing = pd.read_csv(output_file)
    completed = set()

    required = {"prompt_id", "model_alias"}
    if required.issubset(existing.columns):
        for _, row in existing.iterrows():
            if str(row.get("raw_answer", "")) != "ERROR":
                completed.add((str(row["prompt_id"]), str(row["model_alias"])))

    return completed

def append_rows(output_file, rows):
    out_df = pd.DataFrame(rows)
    if Path(output_file).exists():
        out_df.to_csv(output_file, mode="a", header=False, index=False)
    else:
        out_df.to_csv(output_file, index=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=INPUT_FILE)
    parser.add_argument("--output", default=OUTPUT_FILE)
    parser.add_argument("--models", nargs="+", default=["deepseek"])
    parser.add_argument("--limit", type=int, default=None, help="For testing only.")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    required_cols = {
        "prompt_id",
        "scenario_id",
        "domain",
        "probability_positive",
        "probability_negative",
        "probability_condition",
        "frame",
        "prompt",
        "semantic_abstraction",
        "abstract_decision_schema",
        "expected_decision_type",
        "high_stakes_factor",
        "equivalence_type",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in input file: {missing}")

    if args.limit:
        df = df.head(args.limit)

    completed = load_completed(args.output)

    total = len(df) * len(args.models)
    pbar = tqdm(total=total)

    buffered_rows = []
    buffer_size = 20

    for model_alias in args.models:
        if model_alias not in MODEL_CONFIGS:
            raise ValueError(f"Unknown model alias: {model_alias}. Available: {list(MODEL_CONFIGS)}")

        config = MODEL_CONFIGS[model_alias]
        client = make_client(config)
        model_name = config["model"]

        for _, row in df.iterrows():
            key = (str(row["prompt_id"]), model_alias)
            if key in completed:
                pbar.update(1)
                continue

            raw_answer, error = ask_model(client, model_name, row["prompt"])
            parsed = parse_json_safely(raw_answer)

            result_row = {
                "prompt_id": row["prompt_id"],
                "scenario_id": row["scenario_id"],
                "domain": row["domain"],
                "model_alias": model_alias,
                "provider": config["provider"],
                "model_name": model_name,

                "probability_positive": row["probability_positive"],
                "probability_negative": row["probability_negative"],
                "probability_condition": row["probability_condition"],
                "frame": row["frame"],

                "scenario": row.get("scenario", ""),
                "abstract_action": row.get("abstract_action", ""),
                "semantic_abstraction": row["semantic_abstraction"],
                "abstract_decision_schema": row["abstract_decision_schema"],
                "expected_decision_type": row["expected_decision_type"],
                "high_stakes_factor": row["high_stakes_factor"],
                "equivalence_type": row["equivalence_type"],

                "raw_answer": raw_answer,
                "api_error": error or "",

                "recommendation": normalize_recommendation(parsed.get("recommendation", "")),
                "risk_level": to_int_or_blank(parsed.get("risk_level", "")),
                "actionability": to_int_or_blank(parsed.get("actionability", "")),
                "confidence": to_int_or_blank(parsed.get("confidence", "")),
                "reasoning": parsed.get("reasoning", ""),
            }

            buffered_rows.append(result_row)
            completed.add(key)

            if len(buffered_rows) >= buffer_size:
                append_rows(args.output, buffered_rows)
                buffered_rows = []

            time.sleep(args.sleep)
            pbar.update(1)

    if buffered_rows:
        append_rows(args.output, buffered_rows)

    pbar.close()
    print(f"Saved results to {args.output}")

if __name__ == "__main__":
    main()
