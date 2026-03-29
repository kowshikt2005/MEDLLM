"""
MedQA USMLE Benchmark
=====================
Evaluates a model on USMLE medical licensing exam questions.
Supports both local Ollama models and Groq cloud models.

Run this BEFORE fine-tuning to get a baseline, then AFTER fine-tuning
to measure improvement.

Usage:
    # Baseline — local Mistral via Ollama (100 questions)
    python scripts/benchmark_medqa.py

    # More questions for a more accurate score
    python scripts/benchmark_medqa.py --n 200

    # Run against Groq's LLaMA-3.3-70B (requires GROQ_API_KEY in .env)
    python scripts/benchmark_medqa.py --provider groq

    # Run Groq with a different model
    python scripts/benchmark_medqa.py --provider groq --model mixtral-8x7b-32768

    # After fine-tuning, run on your custom model
    python scripts/benchmark_medqa.py --model medllm

    # Compare all saved results (before vs after, Ollama vs Groq)
    python scripts/benchmark_medqa.py --compare

Dataset fields (GBaker/MedQA-USMLE-4-options):
    question   — the question text
    options    — dict {"A": "...", "B": "...", "C": "...", "D": "..."}
    answer_idx — the correct letter ("A", "B", "C", or "D")
    answer     — the full text of the correct answer
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent
RESULTS_DIR = BACKEND_DIR / "data" / "benchmark_results"

# Add backend/ to path so we can import app.config for API keys/model names
sys.path.insert(0, str(BACKEND_DIR))

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """\
You are a medical expert taking a licensing examination.
Answer the following multiple choice question.
Respond with ONLY the letter of the correct answer: A, B, C, or D.
Do not explain your reasoning.

{question}

A) {A}
B) {B}
C) {C}
D) {D}

Answer:"""


# ── Answer parsing ─────────────────────────────────────────────────────────────
def parse_answer(response: str) -> str | None:
    """
    Extract A/B/C/D from the model's raw response.

    Why this is needed: even with "respond ONLY with the letter",
    models sometimes say "The answer is B" or "B. Type 2 Diabetes".
    This handles the common formats gracefully.

    Returns None if no valid answer letter found (counted as wrong).
    """
    text = response.strip().upper()

    # Best case: model responded with just the letter
    if text and text[0] in "ABCD":
        return text[0]

    # Second: "The answer is B" or "Answer: C"
    match = re.search(r'\b([ABCD])\b', text)
    if match:
        return match.group(1)

    return None


# ── Provider: Ollama ──────────────────────────────────────────────────────────
def get_answer_ollama(client, model: str, prompt: str) -> str:
    """Send one question to Ollama, return raw response text."""
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": 0,    # deterministic — same question = same answer every run
            "num_predict": 16,   # we only need a few tokens (the letter + maybe one word)
        },
    )
    return response["message"]["content"]


# ── Provider: Groq ────────────────────────────────────────────────────────────
def get_answer_groq(client, model: str, prompt: str) -> str:
    """Send one question to Groq, return raw response text."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=16,
    )
    return response.choices[0].message.content


# ── Build provider client ─────────────────────────────────────────────────────
def build_client(provider: str, model: str):
    """
    Initialise and verify the client for the chosen provider.
    Returns (client, get_answer_fn, model_name).
    """
    if provider == "ollama":
        import ollama as ollama_lib
        from app.config import settings

        client = ollama_lib.Client(host=settings.ollama_host)

        # Verify Ollama is reachable and model exists
        try:
            available = [m["name"] for m in client.list()["models"]]
            if not any(model in m for m in available):
                print(f"\nWarning: '{model}' not found in Ollama.")
                print(f"Available models: {available}")
                print(f"Run: ollama pull {model}\n")
                sys.exit(1)
        except Exception as e:
            print(f"\nCould not connect to Ollama: {e}")
            print("Make sure Ollama is running (ollama serve)\n")
            sys.exit(1)

        return client, get_answer_ollama, model

    elif provider == "groq":
        from groq import Groq
        from app.config import settings

        api_key = settings.groq_api_key
        if not api_key:
            print("\nGroq API key not found.")
            print("Add GROQ_API_KEY=gsk_... to backend/.env and try again.\n")
            sys.exit(1)

        # Use model from config if not overridden on CLI
        if model == "mistral":           # default Ollama model — swap to Groq default
            model = settings.groq_model  # llama-3.3-70b-versatile

        client = Groq(api_key=api_key)

        # Quick sanity check — will raise if key is invalid
        try:
            client.models.list()
        except Exception as e:
            print(f"\nGroq API key invalid or network error: {e}\n")
            sys.exit(1)

        return client, get_answer_groq, model

    else:
        print(f"Unknown provider: {provider}. Choose 'ollama' or 'groq'.")
        sys.exit(1)


# ── Core benchmark loop ───────────────────────────────────────────────────────
def run_benchmark(provider: str, model: str, n: int) -> dict:
    """
    Run the full benchmark. Returns a results dict with accuracy + per-question details.
    """
    client, get_answer_fn, model = build_client(provider, model)

    # Load dataset from HuggingFace (downloads ~50MB on first run, cached after)
    print("Loading MedQA USMLE dataset from HuggingFace...")
    print("(First run downloads ~50MB — cached after that)\n")
    dataset = load_dataset("GBaker/MedQA-USMLE-4-options", split="test")

    # Sample N questions from the test set
    total_available = len(dataset)
    if n > total_available:
        print(f"Requested {n} questions but only {total_available} available. Using all.")
        n = total_available
    dataset = dataset.select(range(n))

    correct     = 0
    unparseable = 0
    per_question = []

    for item in tqdm(dataset, desc=f"[{provider}] {model}", unit="q"):
        question       = item["question"]
        options        = item["options"]   # {"A": "...", "B": "...", "C": "...", "D": "..."}
        correct_answer = item["answer_idx"]

        prompt = PROMPT_TEMPLATE.format(
            question=question,
            A=options["A"],
            B=options["B"],
            C=options["C"],
            D=options["D"],
        )

        try:
            raw_response = get_answer_fn(client, model, prompt)
            predicted    = parse_answer(raw_response)
        except Exception as e:
            raw_response = f"ERROR: {e}"
            predicted    = None

        is_correct = predicted == correct_answer

        if predicted is None:
            unparseable += 1
        elif is_correct:
            correct += 1

        per_question.append({
            "question":           question[:120] + "..." if len(question) > 120 else question,
            "correct_answer":     correct_answer,
            "correct_answer_text": options[correct_answer],
            "predicted":          predicted,
            "raw_response":       raw_response.strip(),
            "is_correct":         is_correct,
        })

    accuracy = correct / n * 100

    return {
        "provider":    provider,
        "model":       model,
        "timestamp":   datetime.now().isoformat(),
        "n_questions": n,
        "correct":     correct,
        "incorrect":   n - correct - unparseable,
        "unparseable": unparseable,
        "accuracy":    round(accuracy, 2),
        "per_question": per_question,
    }


# ── Compare all saved results ──────────────────────────────────────────────────
def compare_results():
    """Print a comparison table of all saved benchmark JSON files."""
    # Sort by the timestamp stored inside the JSON, not by filename.
    # Filename sort is alphabetical (groq_... before mistral_...) which makes
    # the before/after delta misleading when providers are mixed.
    result_files = sorted(
        RESULTS_DIR.glob("*.json"),
        key=lambda f: json.load(open(f)).get("timestamp", "")
    )

    if not result_files:
        print("No benchmark results found in data/benchmark_results/")
        print("Run a benchmark first: python scripts/benchmark_medqa.py")
        return

    print(f"\n{'='*70}")
    print("  Benchmark Results Comparison")
    print(f"{'='*70}")
    print(f"  {'File':<36} {'Provider':<8} {'Model':<30} {'Accuracy':>10}")
    print(f"  {'-'*36} {'-'*8} {'-'*30} {'-'*10}")

    all_results = []
    for f in result_files:
        with open(f) as fh:
            r = json.load(fh)
        all_results.append(r)
        provider = r.get("provider", "ollama")
        ts       = r["timestamp"][:16].replace("T", " ")
        print(f"  {f.name:<36} {provider:<8} {r['model']:<30} {r['accuracy']:>9.2f}%  ({ts})")

    if len(all_results) >= 2:
        first = all_results[0]["accuracy"]
        last  = all_results[-1]["accuracy"]
        delta = last - first
        sign  = "+" if delta >= 0 else ""
        print(f"\n  Change from first to last run: {sign}{delta:.2f}%")

    print(f"\n  Reference scores:")
    print(f"  Random guessing (4 options):      25.00%")
    print(f"  Human passing threshold (USMLE):  ~60.00%")
    print(f"  LLaMA-3.3-70B (Groq, expected):   ~75-80%")
    print(f"{'='*70}\n")


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Benchmark a model on MedQA USMLE"
    )
    parser.add_argument(
        "--provider", default="ollama", choices=["ollama", "groq"],
        help="Which backend to use: 'ollama' (local) or 'groq' (cloud). Default: ollama"
    )
    parser.add_argument(
        "--model", default="mistral",
        help="Model name. For ollama: 'mistral', 'medllm', etc. "
             "For groq: auto-uses groq_model from config if not set."
    )
    parser.add_argument(
        "--n", type=int, default=100,
        help="Number of questions to evaluate (default: 100)"
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Compare all saved benchmark results"
    )
    args = parser.parse_args()

    if args.compare:
        compare_results()
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  MedQA USMLE Benchmark")
    print(f"{'='*50}")
    print(f"  Provider:  {args.provider}")
    print(f"  Model:     {args.model}")
    print(f"  Questions: {args.n}")
    print(f"  Dataset:   GBaker/MedQA-USMLE-4-options (test split)")
    print(f"{'='*50}\n")

    results = run_benchmark(args.provider, args.model, args.n)

    # Save to JSON (timestamped — keeps both before and after runs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = RESULTS_DIR / f"{results['provider']}_{results['model']}_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n{'='*50}")
    print(f"  Results")
    print(f"{'='*50}")
    print(f"  Provider:    {results['provider']}")
    print(f"  Model:       {results['model']}")
    print(f"  Questions:   {results['n_questions']}")
    print(f"  Correct:     {results['correct']}")
    print(f"  Incorrect:   {results['incorrect']}")
    print(f"  Unparseable: {results['unparseable']}")
    print(f"  Accuracy:    {results['accuracy']}%")
    print(f"  Saved to:    {out_path.relative_to(BACKEND_DIR)}")
    print(f"{'='*50}")
    print(f"\n  Score context:")
    print(f"  Random guessing (4 options):      25%")
    print(f"  Typical base Mistral-7B:           ~47-55%")
    print(f"  Human passing threshold:           ~60%")
    print(f"  After QLoRA fine-tuning (target):  ~58-65%")
    print(f"  LLaMA-3.3-70B via Groq (expected): ~75-80%")
    print()


if __name__ == "__main__":
    main()
