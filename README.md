# FrameBench-HPS: High-Stakes Personal Decision Framing Benchmark

This repository contains scripts for generating and running a controlled framing-effect experiment on large language models (LLMs).

The project studies whether semantically equivalent gain/loss framings change LLM behavior in high-stakes personal decision-support scenarios.

## Research Goal

We evaluate whether LLMs are sensitive to framing in high-stakes personal decision support.

The experiment separates two effects:

1. **Probability sensitivity**  
   Whether the model rationally changes its recommendation when the probability of a positive outcome changes, e.g., 20%, 40%, 60%, 80%.

2. **Framing sensitivity**  
   Whether the model changes its recommendation or reasoning style when mathematically equivalent information is expressed as a gain frame or a loss frame.

Example:

- Gain frame: `There is a 70% chance of a positive outcome.`
- Loss frame: `There is a 30% chance of not achieving a positive outcome.`

## Experimental Design

Base dataset:

- 4 domains
  - finance
  - health
  - education/career
  - legal/consumer rights
- 60 scenarios per domain
- 240 scenarios total

Expanded probability-framing dataset:

- 240 scenarios
- 4 probability levels
  - 20% positive / 80% negative
  - 40% positive / 60% negative
  - 60% positive / 40% negative
  - 80% positive / 20% negative
- 3 frames
  - neutral
  - gain
  - loss

Total prompts:

```text
240 scenarios × 4 probability levels × 3 frames = 2880 prompts
```

If using 3 models:

```text
2880 prompts × 3 models = 8640 model responses
```

The dataset is already prepared in long format:

```text
framebench_hps_probability_long.csv
```

Each row in this file corresponds to one prompt:

```text
scenario_id × probability_level × frame
```

The experiment tests whether LLMs respond differently to mathematically equivalent gain/loss framings under different probability levels.

---

## 1. Repository Structure

```text
.
├── framebench_hps_probability_long.csv
├── run_experiment_long.py
└── README.md
```

Required files:

| File | Purpose |
|---|---|
| `framebench_hps_probability_long.csv` | Input dataset. One row = one prompt. |
| `run_experiment_long.py` | Main script for running model inference. |
| `README.md` | Running instructions. |

---

## 2. Dataset Format

The input file should be:

```text
framebench_hps_probability_long.csv
```

Each row contains one prompt and its metadata.

Important fields:

| Field | Meaning |
|---|---|
| `prompt_id` | Unique prompt ID, e.g., `F001_P20_gain` |
| `scenario_id` | Original scenario ID, e.g., `F001` |
| `domain` | Domain: `finance`, `health`, `education_career`, `legal_consumer` |
| `probability_positive` | Probability of positive outcome: `20`, `40`, `60`, or `80` |
| `probability_negative` | Complementary negative probability: `80`, `60`, `40`, or `20` |
| `probability_condition` | Probability label, e.g., `P20_N80` |
| `frame` | Prompt frame: `neutral`, `gain`, or `loss` |
| `prompt` | Full prompt sent to the model |
| `semantic_abstraction` | Structured semantic abstraction of the scenario |
| `expected_decision_type` | Type of decision, e.g., investment, treatment, contract |
| `high_stakes_factor` | Why the scenario is high-stakes |
| `equivalence_type` | Usually `probability_equivalence` |

---

## 3. Model Output Format

Each prompt asks the model to return JSON only:

```json
{
  "recommendation": "yes/no/uncertain",
  "risk_level": 1-5,
  "actionability": 1-5,
  "confidence": 1-5,
  "reasoning": "brief explanation"
}
```

Meaning:

| Output Field | Meaning |
|---|---|
| `recommendation` | Final recommendation: `yes`, `no`, or `uncertain` |
| `risk_level` | Model-perceived risk level, from 1 to 5 |
| `actionability` | Strength of action recommendation, from 1 to 5 |
| `confidence` | Model confidence, from 1 to 5 |
| `reasoning` | Brief explanation |

---

## 4. Install Dependencies

Use Python 3.9 or later.

Install dependencies:

```bash
pip install -r requirements.txt
```

If `requirements.txt` does not exist, create one with:

```text
pandas
openai
tqdm
```

Then run:

```bash
pip install -r requirements.txt
```

---

## 5. API Keys

Set keys through environment variables.

### DeepSeek

```bash
export DEEPSEEK_API_KEY="your_deepseek_api_key"
```

### Qwen

```bash
export QWEN_API_KEY="your_qwen_api_key"
```

### OpenAI

```bash
export OPENAI_API_KEY="your_openai_api_key"
```

---

## 6. Test Run

Before running the full experiment, test on 10 prompts:

```bash
python3 run_experiment_long.py --models deepseek --limit 10
```

This creates or updates:

```text
results_probability_framing_raw.csv
```

Check that the file contains model outputs before launching the full run.

---

## 7. Run One Model

To run DeepSeek on the full dataset:

```bash
python3 run_experiment_long.py --models deepseek
```

Output:

```text
results_probability_framing_raw.csv
```

---

## 8. Run Multiple Models

To run multiple models:

```bash
python3 run_experiment_long.py --models deepseek qwen gpt4omini
```

Available model aliases:

| Alias | Provider | Model |
|---|---|---|
| `deepseek` | DeepSeek | `deepseek-chat` |
| `qwen` | Alibaba DashScope | `qwen-plus` |
| `gpt4omini` | OpenAI | `gpt-4o-mini` |
| `gpt41mini` | OpenAI | `gpt-4.1-mini` |

The script will append all results to the same output file:

```text
results_probability_framing_raw.csv
```

---

## 9. Resume Interrupted Runs

The script supports automatic resume.

If `results_probability_framing_raw.csv` already exists, the script checks completed pairs:

```text
(prompt_id, model_alias)
```

and skips them.

So if the run stops halfway, simply rerun the same command:

```bash
python3 run_experiment_long.py --models deepseek
```

It will continue from unfinished prompts.

---

## 10. Expected Output File

The main output is:

```text
results_probability_framing_raw.csv
```

Each row is one model response.

Important output fields:

| Field | Meaning |
|---|---|
| `prompt_id` | Prompt ID |
| `scenario_id` | Scenario ID |
| `domain` | Domain |
| `model_alias` | Model alias used in the script |
| `provider` | API provider |
| `model_name` | Actual model name |
| `probability_positive` | Positive outcome probability |
| `probability_negative` | Negative outcome probability |
| `probability_condition` | Probability condition label |
| `frame` | `neutral`, `gain`, or `loss` |
| `raw_answer` | Full raw model response |
| `api_error` | API error message, if any |
| `recommendation` | Parsed recommendation |
| `risk_level` | Parsed risk score |
| `actionability` | Parsed actionability score |
| `confidence` | Parsed confidence score |
| `reasoning` | Parsed reasoning text |

---

## 11. Full Recommended Run

For the full experiment, run:

```bash
pip install -r requirements.txt

export DEEPSEEK_API_KEY="your_deepseek_api_key"
export QWEN_API_KEY="your_qwen_api_key"
export OPENAI_API_KEY="your_openai_api_key"

python3 run_experiment_long.py --models deepseek qwen gpt4omini
```

After completion, send back:

```text
results_probability_framing_raw.csv
```

---

## 12. Security Reminder

Never commit API keys to GitHub.

Before pushing the repository, check:

```bash
git status
```

Make sure no file contains API keys.

Recommended `.gitignore`:

```text
.env
*.key
secrets.json
results_probability_framing_raw.csv
```
