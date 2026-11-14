Title: Logging and Observability for LLM Apps
Date: 2026-11-14
Category: Tutorial
Tags: GenAI, LLM, logging, observability, production, Python, FastAPI
Slug: logging-and-observability-for-llm-apps

## Why LLM Apps Need Different Observability

Traditional apps fail in predictable ways. A function throws an exception. A query times out. The error is binary: it worked or it didn't, and the stack trace points you to the line.

LLM apps fail softly. The API call succeeds. The response arrives. And the answer is subtly wrong, confidently hallucinated, or completely off-topic — with no exception raised and no stack trace to follow. The only way to know something went wrong is to look at what went in and what came out.

That's why observability for LLM apps isn't optional. It's the only way to debug, improve, and trust what you've built.

## The Minimum You Need to Log

Before thinking about tools, nail down what to capture on every LLM call:

```python
{
    "timestamp": "2026-11-14T10:23:11Z",
    "request_id": "a3f2c1d9",
    "model": "gpt-4o-mini",
    "prompt_name": "rag_answer",
    "prompt_version": "v3",
    "input_tokens": 842,
    "output_tokens": 213,
    "latency_ms": 1340,
    "temperature": 0.2,
    "user_id": "u_8821",           # optional, only if you have users
    "session_id": "sess_441",       # for multi-turn conversations
    "status": "success"             # or "error"
}
```

This is the baseline. With these fields you can answer: when did it happen, which model and prompt ran, how much did it cost, how long did it take, and did it succeed.

**Cost** isn't in the log directly but falls out of `input_tokens` and `output_tokens` multiplied by the model's per-token price. Log the counts; derive the cost when you need it.

## A Practical Logging Setup in FastAPI

Using the structured logging pattern from earlier posts, here's how this looks in a FastAPI app:

```python
import logging
import time
import uuid
from contextlib import contextmanager
from openai import OpenAI

logger = logging.getLogger("llm")

client = OpenAI()

@contextmanager
def llm_span(prompt_name: str, prompt_version: str, model: str, **extra):
    request_id = str(uuid.uuid4())[:8]
    start = time.monotonic()
    try:
        yield request_id
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "llm_call",
            extra={
                "request_id": request_id,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "model": model,
                "latency_ms": latency_ms,
                "status": "success",
                **extra,
            },
        )
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "llm_call_error",
            extra={
                "request_id": request_id,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "model": model,
                "latency_ms": latency_ms,
                "status": "error",
                "error": str(exc),
                **extra,
            },
        )
        raise


def call_llm(prompt: str, prompt_name: str, prompt_version: str, model: str = "gpt-4o-mini", temperature: float = 0.2) -> str:
    with llm_span(prompt_name, prompt_version, model) as request_id:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        usage = response.usage

        logger.info(
            "llm_usage",
            extra={
                "request_id": request_id,
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "model": model,
            },
        )
        return content
```

Usage in an endpoint:

```python
@app.post("/ask")
def ask(request: AskRequest):
    prompt = build_prompt(request.question, retrieved_docs)
    answer = call_llm(
        prompt=prompt,
        prompt_name="rag_answer",
        prompt_version="v3",
        model="gpt-4o-mini",
    )
    return {"answer": answer}
```

Every call now logs timing, token usage, the prompt version, and whether it succeeded — all without touching the business logic.

## Logging the Inputs and Outputs

Token counts tell you cost and volume. The actual prompt and response tell you *why* something went wrong. For debugging, log both — but carefully:

```python
logger.debug(
    "llm_io",
    extra={
        "request_id": request_id,
        "prompt_preview": prompt[:500],   # first 500 chars only
        "response_preview": content[:500],
    },
)
```

A few ground rules:

- Log at `DEBUG` level, not `INFO`. You don't want full prompts in production logs by default — they're noisy and can contain user data.
- Truncate. A 2000-token prompt doesn't need to be stored verbatim on every call.
- Never log API keys, passwords, or PII that the user submitted in their question. If your prompts include user data, anonymize or redact before logging.

## What to Track Over Time

Individual call logs are for debugging specific incidents. Aggregated metrics are for understanding the system's health. The ones worth tracking:

**Latency percentiles.** The mean latency hides problems. Track p50, p95, and p99. A p99 of 20 seconds means 1 in 100 users waits 20 seconds — that's a product problem even if the average is fine.

**Token usage per endpoint.** Which endpoints are expensive? Is token usage growing over time? A prompt that ballooned from 500 to 2000 tokens after a few edits might not be obvious until you look at the chart.

**Error rate by model and prompt version.** If `v4` of a prompt has a higher error rate than `v3`, you know immediately. Without version tracking in your logs, you'd never know which change caused it.

**Cache hit rate.** If you're using prompt caching (covered in the previous post), log whether each call was a cache hit. A low hit rate when you expected high means your cache prefix is being invalidated somewhere.

## Structured Logging Makes This Usable

Plain text logs are hard to query. If your log line looks like:

```
2026-11-14 10:23:11 INFO llm_call model=gpt-4o-mini latency=1340ms tokens=1055
```

You can grep it, but that's about it. With structured JSON logs:

```json
{"timestamp": "2026-11-14T10:23:11Z", "event": "llm_call", "model": "gpt-4o-mini", "latency_ms": 1340, "input_tokens": 842, "output_tokens": 213}
```

You can ship these to any log aggregation tool (Datadog, Grafana Loki, CloudWatch, Elasticsearch) and run real queries: average latency by model, token usage over time, error rate by prompt version.

Python's built-in `logging` module emits text by default. Add `python-json-logger` to get JSON output:

```python
import logging
from pythonjsonlogger import jsonlogger

handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter())
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
```

That's the only setup change needed. Everything else stays the same.

## Tracing Across Multiple LLM Calls

Agentic systems make several LLM calls to complete one user request. A single `request_id` per user request lets you stitch all those calls together:

```python
@app.post("/ask")
def ask(request: AskRequest, x_request_id: str = Header(default_factory=lambda: str(uuid.uuid4()))):
    # pass x_request_id into every call_llm invocation
    ...
```

When something goes wrong, you filter logs by `request_id` and see the full sequence: which call failed, what the prompt looked like at that step, how long each step took.

## OpenTelemetry for Deeper Tracing

If your app is more complex — multiple services, background jobs, retrieval + generation pipelines — consider OpenTelemetry. Libraries like `opentelemetry-instrumentation-openai` auto-instrument OpenAI calls and emit spans to any compatible backend (Jaeger, Tempo, Honeycomb, etc.).

For simple FastAPI + LLM setups, structured JSON logs shipped to a log aggregator is enough. Add OpenTelemetry when you have multiple services and need distributed traces.

## Quick Checklist

- Log model, prompt name, prompt version, latency, token counts, and status on every LLM call
- Use structured JSON logs, not plain text
- Log prompts and responses at DEBUG level only, truncated, with PII removed
- Track p95/p99 latency, not just mean
- Include a `request_id` to correlate multi-step calls
- Alert on error rate spikes and latency regressions
- Never log secrets or raw API keys

## The Underlying Principle

A model returning a wrong answer is not an exception — it's just an output. Catching it requires you to have recorded what went in and what came out. Logging isn't overhead on an LLM app; it's the feedback loop that makes the app improvable.
