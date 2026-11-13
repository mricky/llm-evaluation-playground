# ⚔️ LLM Evaluation Arena & FACTS Studio

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.128-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/pytest-10%20passed-success.svg)](tests/)
[![Rubric](https://img.shields.io/badge/rubric-FACTS-orange.svg)](#the-facts-evaluation-rubric)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Enterprise Multi-Model Inference & Ground-Truth Evaluator Calibration Studio**  
> Compare local models (Ollama: `llama3`, `qwen2.5-coder`, `gemma4`) against cloud models (Google Gemini API) concurrently, score outputs using the weighted **FACTS Rubric**, and calibrate human evaluator precision against curated enterprise ground-truth benchmarks.

---

## 🌟 Key Features

1. **⚡ Concurrent Multi-Model Inference:**
   - Powered by Python `asyncio.gather()` and HTTPX.
   - Evaluates local Ollama instances side-by-side with Google Gemini Cloud.
   - Live latency tracking (ms), word/token counting, and error isolation.
   - Built-in smart mock fallbacks if external API keys are not yet configured.

2. **📊 FACTS Rubric Assessment Engine:**
   Standardizes unstructured evaluation into a 5-pillar weighted composite score (0–100%):
   - **F**actual Accuracy (**30%**): Mathematical correctness, entity integrity, zero hallucinations.
   - **A**dherence to Constraints (**25%**): Strict compliance with negative constraints and formatting bans.
   - **C**ompleteness (**20%**): Addressing every clause and edge case.
   - **T**one & Persona (**10%**): Appropriate tone (concise, professional, empathetic).
   - **S**tructure & Schema (**15%**): Clean parseable JSON/Markdown adhering to type contracts.

3. **🎯 Evaluator Trainer (Ground-Truth Calibration Mode):**
   - Addresses reviewer cognitive biases (such as length bias) and tests evaluator attention to detail.
   - Curated enterprise challenges (Customs Logistics PEB calculations, InsurTech deductible triage).
   - Features **deliberate hidden traps** (e.g., negative constraint violations, decimal miscalculations).
   - Grades the evaluator with an **Alignment Score** (0–100%) and provides immediate feedback.

4. **📜 Zero-External-Dependency Persistence:**
   - Lightweight SQLite storage (`data/evaluations.db`) for full audit history.
   - REST Webhook endpoints (`/api/webhook/evaluate`) ready for CI/CD runners or n8n workflow triggers.

---

## 🏛️ Architecture Overview

```
                                  [ User Web Browser ]
                                           │
                                  HTTP / SSE Streaming
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FASTAPI CORE ENGINE                                  │
│                                                                                        │
│  ┌───────────────────────┐  ┌────────────────────────┐  ┌───────────────────────────┐  │
│  │   /api/compare        │  │   /api/evaluate        │  │   /api/trainer/submit     │  │
│  │   (Dual Async Runner) │  │   (FACTS Scorecard)    │  │   (Ground Truth Matcher)  │  │
│  └───────────┬───────────┘  └───────────┬────────────┘  └─────────────┬─────────────┘  │
│              │                          │                             │                │
│              ▼                          ▼                             ▼                │
│  ┌───────────────────────┐  ┌────────────────────────┐  ┌───────────────────────────┐  │
│  │     Engine Router     │  │   FACTS Rubric Math    │  │   Trainer Scoring Engine  │  │
│  │    (asyncio.gather)   │  │   (Weighted Composite) │  │   (Deviation & Feedback)  │  │
│  └───────┬───────┬───────┘  └───────────┬────────────┘  └─────────────┬─────────────┘  │
└──────────┼───────┼──────────────────────┼─────────────────────────────┼────────────────┘
           │       │                      ▼                             ▼
           │       │             ┌─────────────────┐           ┌─────────────────┐
           │       │             │   SQLite DB     │           │ benchmarks.json │
           │       │             │ (evaluations.db)│           │ (Gold Standard) │
           │       │             └─────────────────┘           └─────────────────┘
           ▼       ▼
    ┌──────────┐ ┌───────────────┐
    │  Ollama  │ │ Google Gemini │
    │  (Local) │ │    (Cloud)    │
    └──────────┘ └───────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/your-username/llm-eval-arena.git
cd llm-eval-arena

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
```bash
cp .env.example .env
# (Optional) Add your Google Gemini API key:
# GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run the Studio
```bash
python app.py
```
Open **`http://localhost:8088`** in your browser to start comparing models and calibrating your evaluation precision!

---

## 🧪 Running Unit & Integration Tests

The test suite covers FACTS mathematical formulas, alignment scoring, database persistence, and FastAPI endpoints:

```bash
pytest -v
```

Output:
```text
tests/test_api_endpoints.py::test_api_benchmarks_endpoint PASSED         [ 10%]
tests/test_api_endpoints.py::test_api_history_endpoint PASSED            [ 20%]
tests/test_api_endpoints.py::test_api_evaluate_endpoint PASSED           [ 30%]
tests/test_facts_engine.py::TestFACTSRubric::test_compare_assessments_determines_winner PASSED [ 40%]
tests/test_facts_engine.py::TestFACTSRubric::test_minimum_scores_yield_20_percent PASSED [ 50%]
tests/test_facts_engine.py::TestFACTSRubric::test_perfect_scores_yield_100_percent PASSED [ 60%]
tests/test_facts_engine.py::TestFACTSRubric::test_weighted_composite_calculation PASSED [ 70%]
tests/test_facts_engine.py::TestGroundTruthTrainer::test_missed_trap_lowers_score_and_flags_critique PASSED [ 80%]
tests/test_facts_engine.py::TestGroundTruthTrainer::test_perfect_alignment_gives_100_percent PASSED [ 90%]
tests/test_facts_engine.py::TestStorageLayer::test_save_and_retrieve_evaluation PASSED [100%]

============================== 10 passed in 0.17s ==============================
```

---

## 📡 Webhook Integration (e.g., n8n / CI/CD)

Automate model regression testing by sending a POST request to `/api/webhook/evaluate`:

```bash
curl -X POST http://localhost:8000/api/webhook/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Extract invoice total from: Invoice #123 Total: $450.00. Return valid JSON only.",
    "model_a": "llama3:latest",
    "model_b": "gemini-1.5-flash"
  }'
```

---

## 📄 License
MIT License. Created by **Mochamad Ricky Susanto**.
