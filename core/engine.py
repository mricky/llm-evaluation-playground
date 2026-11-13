"""Concurrent Multi-Model Inference Engine.

Orchestrates asynchronous calls to local Ollama and Google Gemini.
Includes fallback mocks for zero-setup demo runs.
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional
import httpx


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


async def call_ollama(
    prompt: str,
    model: str = "llama3:latest",
    timeout_sec: float = 60.0
) -> Dict[str, Any]:
    """Asynchronously calls local Ollama instance."""
    start_time = time.perf_counter()
    endpoint = f"{OLLAMA_BASE_URL}/api/generate"
    
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            resp = await client.post(
                endpoint,
                json={"model": model, "prompt": prompt, "stream": False}
            )
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("response", "")
                eval_count = data.get("eval_count", len(text.split()))
                return {
                    "model": model,
                    "provider": "ollama (local)",
                    "status": "success",
                    "text": text,
                    "latency_ms": elapsed_ms,
                    "tokens_or_words": eval_count,
                    "error": None
                }
            else:
                return {
                    "model": model,
                    "provider": "ollama (local)",
                    "status": "error",
                    "text": "",
                    "latency_ms": elapsed_ms,
                    "tokens_or_words": 0,
                    "error": f"Ollama HTTP {resp.status_code}: {resp.text}"
                }
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "model": model,
            "provider": "ollama (local)",
            "status": "failed",
            "text": "",
            "latency_ms": elapsed_ms,
            "tokens_or_words": 0,
            "error": f"Connection error: {str(e)}. (Is Ollama running on {OLLAMA_BASE_URL}?)"
        }


async def call_gemini(
    prompt: str,
    model: str = "gemini-3-flash-preview",
    timeout_sec: float = 30.0
) -> Dict[str, Any]:
    """Asynchronously calls Google Gemini API with automatic retry & model failover."""
    start_time = time.perf_counter()
    api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
    
    # If no API key configured, use high-fidelity smart mock for demonstration
    if not api_key:
        await asyncio.sleep(0.65)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        mock_reply = (
            f"[Gemini Cloud Simulated Response for '{model}']\n\n"
            f"1. Executive Summary: Core requirements addressed accurately.\n"
            f"2. Technical Findings: Validated against standard enterprise schema.\n\n"
            f"(Note: To use live Gemini Cloud API, set GEMINI_API_KEY in your .env file)"
        )
        return {
            "model": model,
            "provider": "gemini (cloud-mock)",
            "status": "mock_success",
            "text": mock_reply,
            "latency_ms": elapsed_ms,
            "tokens_or_words": len(mock_reply.split()),
            "error": None
        }

    # Model candidates in priority order if 503 high demand occurs
    fallback_models = [model, "gemini-3-flash-preview", "gemini-3.5-flash-lite"]
    # Deduplicate while preserving order
    models_to_try = []
    for m in fallback_models:
        if m not in models_to_try:
            models_to_try.append(m)

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    last_error = ""

    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        for attempt_model in models_to_try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{attempt_model}:generateContent?key={api_key}"
            for retry_attempt in range(2):
                try:
                    resp = await client.post(endpoint, json=payload)
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

                    if resp.status_code == 200:
                        data = resp.json()
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        return {
                            "model": attempt_model,
                            "provider": "gemini (cloud)",
                            "status": "success",
                            "text": text,
                            "latency_ms": elapsed_ms,
                            "tokens_or_words": len(text.split()),
                            "error": None
                        }
                    elif resp.status_code in [503, 429]:
                        last_error = f"Gemini HTTP {resp.status_code}: {resp.text}"
                        await asyncio.sleep(0.5 * (retry_attempt + 1))  # Exponential backoff
                        continue
                    else:
                        last_error = f"Gemini HTTP {resp.status_code}: {resp.text}"
                        break
                except Exception as e:
                    last_error = str(e)
                    await asyncio.sleep(0.5)

    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "model": model,
        "provider": "gemini (cloud)",
        "status": "failed",
        "text": "",
        "latency_ms": elapsed_ms,
        "tokens_or_words": 0,
        "error": f"Gemini API request failed after failover retries: {last_error}"
    }


async def dispatch_model_call(prompt: str, model: str) -> Dict[str, Any]:
    """Smart router: routes to Gemini if model starts with 'gemini-', else Ollama."""
    if model.startswith("gemini-"):
        return await call_gemini(prompt, model=model)
    else:
        return await call_ollama(prompt, model=model)


async def run_arena_comparison(
    prompt: str,
    model_a: str = "llama3:latest",
    model_b: str = "gemini-3-flash-preview"
) -> Dict[str, Any]:
    """Runs Model A and Model B concurrently using asyncio.gather."""
    res_a, res_b = await asyncio.gather(
        dispatch_model_call(prompt, model=model_a),
        dispatch_model_call(prompt, model=model_b),
        return_exceptions=True
    )
    
    # Normalize potential unhandled exceptions
    if isinstance(res_a, Exception):
        res_a = {"model": model_a, "status": "exception", "text": "", "error": str(res_a), "latency_ms": 0}
    if isinstance(res_b, Exception):
        res_b = {"model": model_b, "status": "exception", "text": "", "error": str(res_b), "latency_ms": 0}

    return {
        "prompt": prompt,
        "model_a": res_a,
        "model_b": res_b,
        "timestamp": time.time()
    }

