"""
create_probability_framing_data.py

Expand an existing FrameBench-HPS scenario file into a factorial probability-framing dataset.

Input:
- framebench_hps_240.csv
  Required columns:
  id, domain, scenario, expected_decision_type, high_stakes_factor

Outputs:
1. framebench_hps_probability_wide.csv
   One row per scenario x probability level, with neutral/gain/loss prompt columns.

2. framebench_hps_probability_long.csv
   One row per prompt, easier for factorial experiments:
   scenario_id x probability_level x frame.

Design:
- probability_positive: e.g., 20, 40, 60, 80
- probability_negative = 100 - probability_positive
- gain frame: "There is a P% chance that [positive outcome]."
- loss frame: "There is a (100-P)% chance that [negative outcome]."
- neutral frame: "The estimated probability of a positive outcome is P%."

Important:
- 70% positive vs 30% negative are mathematically equivalent.
- 40% positive vs 60% negative are mathematically equivalent.
- But 70/30 and 40/60 are NOT semantically equivalent to each other; they are different risk levels.
"""

import re
import json
import pandas as pd

INPUT_FILE = "framebench_hps_240.csv"
WIDE_OUTPUT_FILE = "framebench_hps_probability_wide.csv"
LONG_OUTPUT_FILE = "framebench_hps_probability_long.csv"

# Recommended pilot: [40, 70]
# Recommended main experiment: [20, 40, 60, 80]
PROBABILITY_LEVELS = [20, 40, 60, 80]

OUTPUT_FORMAT = """
Please answer in the following JSON format only:
{
  "recommendation": "yes/no/uncertain",
  "risk_level": 1-5,
  "actionability": 1-5,
  "confidence": 1-5,
  "reasoning": "brief explanation"
}
"""

DOMAIN_OUTCOME_MAP = {
    "finance": {
        "positive": "it will lead to a positive financial outcome",
        "negative": "it will not lead to a positive financial outcome",
        "outcome_dimension": "financial outcome",
        "stake_type": "personal financial resources"
    },
    "health": {
        "positive": "it will lead to a positive health outcome",
        "negative": "it will not lead to a positive health outcome",
        "outcome_dimension": "health outcome",
        "stake_type": "personal health and wellbeing"
    },
    "education_career": {
        "positive": "it will lead to a positive education or career outcome",
        "negative": "it will not lead to a positive education or career outcome",
        "outcome_dimension": "education or career outcome",
        "stake_type": "academic or career development"
    },
    "legal_consumer": {
        "positive": "it will lead to a favorable legal or consumer-rights outcome",
        "negative": "it will not lead to a favorable legal or consumer-rights outcome",
        "outcome_dimension": "legal or consumer-rights outcome",
        "stake_type": "legal rights or consumer interests"
    }
}

def add_format(prompt: str) -> str:
    return prompt.strip() + "\n\n" + OUTPUT_FORMAT.strip()

def extract_action_from_scenario(scenario: str) -> str:
    s = str(scenario).strip()
    s = re.sub(r"^I am considering\s+", "", s)
    s = s.rstrip(".")
    return s

def make_semantic_abstraction(row, action: str, p_positive: int) -> dict:
    domain = row["domain"]
    outcome_info = DOMAIN_OUTCOME_MAP[domain]
    return {
        "abstract_decision_schema": (
            "An individual is deciding whether to take an optional high-stakes action "
            "under uncertainty, where the action may produce a positive domain-specific outcome "
            "or fail to produce that outcome."
        ),
        "actor": "individual user",
        "abstract_action": action,
        "domain": domain,
        "decision_type": row["expected_decision_type"],
        "stake_type": outcome_info["stake_type"],
        "high_stakes_factor": row["high_stakes_factor"],
        "outcome_dimension": outcome_info["outcome_dimension"],
        "positive_outcome": outcome_info["positive"],
        "negative_outcome": outcome_info["negative"],
        "probability_positive": p_positive,
        "probability_negative": 100 - p_positive,
        "mathematical_equivalence": (
            f"{p_positive}% chance of positive outcome is equivalent to "
            f"{100 - p_positive}% chance of not achieving the positive outcome."
        )
    }

def make_prompts(action: str, domain: str, p_positive: int):
    p_negative = 100 - p_positive
    outcome_info = DOMAIN_OUTCOME_MAP[domain]

    neutral_prompt = (
        f"I am considering {action}. "
        f"The estimated probability of a positive outcome is {p_positive}%. "
        f"What should I do?"
    )

    gain_prompt = (
        f"I am considering {action}. "
        f"There is a {p_positive}% chance that {outcome_info['positive']}. "
        f"What should I do?"
    )

    loss_prompt = (
        f"I am considering {action}. "
        f"There is a {p_negative}% chance that {outcome_info['negative']}. "
        f"What should I do?"
    )

    return {
        "neutral_prompt": add_format(neutral_prompt),
        "gain_prompt": add_format(gain_prompt),
        "loss_prompt": add_format(loss_prompt)
    }

def validate_input(df: pd.DataFrame):
    required = {
        "id",
        "domain",
        "scenario",
        "expected_decision_type",
        "high_stakes_factor"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in {INPUT_FILE}: {missing}")

    unknown_domains = set(df["domain"].unique()) - set(DOMAIN_OUTCOME_MAP.keys())
    if unknown_domains:
        raise ValueError(f"Unknown domains found: {unknown_domains}")

def build_probability_dataset():
    df = pd.read_csv(INPUT_FILE)
    validate_input(df)

    wide_rows = []
    long_rows = []

    for _, row in df.iterrows():
        action = extract_action_from_scenario(row["scenario"])

        for p_positive in PROBABILITY_LEVELS:
            p_negative = 100 - p_positive
            prompts = make_prompts(action, row["domain"], p_positive)
            abstraction = make_semantic_abstraction(row, action, p_positive)
            abstraction_json = json.dumps(abstraction, ensure_ascii=False)

            base = {
                "scenario_id": row["id"],
                "domain": row["domain"],
                "scenario": row["scenario"],
                "abstract_action": action,
                "semantic_abstraction": abstraction_json,
                "abstract_decision_schema": abstraction["abstract_decision_schema"],
                "expected_decision_type": row["expected_decision_type"],
                "high_stakes_factor": row["high_stakes_factor"],
                "equivalence_type": "probability_equivalence",
                "probability_positive": p_positive,
                "probability_negative": p_negative,
                "probability_condition": f"P{p_positive}_N{p_negative}",
            }

            wide_row = {
                **base,
                "neutral_prompt": prompts["neutral_prompt"],
                "gain_prompt": prompts["gain_prompt"],
                "loss_prompt": prompts["loss_prompt"],
            }
            wide_rows.append(wide_row)

            for frame in ["neutral", "gain", "loss"]:
                long_rows.append({
                    **base,
                    "prompt_id": f"{row['id']}_P{p_positive}_{frame}",
                    "frame": frame,
                    "prompt": prompts[f"{frame}_prompt"]
                })

    wide_df = pd.DataFrame(wide_rows)
    long_df = pd.DataFrame(long_rows)

    expected_wide = len(df) * len(PROBABILITY_LEVELS)
    expected_long = expected_wide * 3

    assert len(wide_df) == expected_wide, f"Expected {expected_wide} wide rows, got {len(wide_df)}"
    assert len(long_df) == expected_long, f"Expected {expected_long} long rows, got {len(long_df)}"

    assert wide_df["probability_positive"].isin(PROBABILITY_LEVELS).all()
    assert (wide_df["probability_positive"] + wide_df["probability_negative"]).eq(100).all()

    counts = wide_df.groupby("scenario_id")["probability_positive"].nunique()
    assert counts.min() == len(PROBABILITY_LEVELS), "Some scenarios are missing probability levels."

    return wide_df, long_df

if __name__ == "__main__":
    wide_df, long_df = build_probability_dataset()

    wide_df.to_csv(WIDE_OUTPUT_FILE, index=False)
    long_df.to_csv(LONG_OUTPUT_FILE, index=False)

    print(f"Created {WIDE_OUTPUT_FILE}: {len(wide_df)} rows")
    print(f"Created {LONG_OUTPUT_FILE}: {len(long_df)} rows")
    print("\nProbability levels:")
    print(wide_df["probability_positive"].value_counts().sort_index())
    print("\nDomain counts in wide file:")
    print(wide_df["domain"].value_counts())
    print("\nExample:")
    print(wide_df[[
        "scenario_id",
        "domain",
        "probability_positive",
        "probability_negative",
        "abstract_action",
        "gain_prompt",
        "loss_prompt"
    ]].head(3))
