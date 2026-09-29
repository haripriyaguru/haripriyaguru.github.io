Title: Async vs Sync in FastAPI — When It Actually Matters
Date: 2026-09-29
Category: Tutorial
Tags: FastAPI, Python, async, performance, beginner
Slug: async-vs-sync-in-fastapi-when-it-actually-matters
status: Published

## Why This Confuses Beginners

One of the first things that trips people up in FastAPI is seeing both `def` and `async def` used for routes, sometimes in the same codebase, and not knowing which one to use or why it matters. Some tutorials use `async def` everywhere out of habit, others mix freely, and beginners are left guessing whether this is a big performance decision or just a stylistic choice. It's actually a real decision with real consequences — just not the ones most people assume.

## First, What "Async" Actually Means

In normal (synchronous) code, each operation blocks the program until it finishes:

```python
def get_data():
    result = call_slow_api()   # program waits here, doing nothing else
    return result
```

While `call_slow_api()` is waiting for a network response, your program is just sitting idle — it can't do anything else, even though it's not actually using the CPU during that wait.

**Async code** allows the program to pause a task that's waiting on something (like a network call), work on something else in the meantime, and come back to finish the first task once it's ready:

```python
async def get_data():
    result = await call_slow_api()   # program can handle other work while waiting
    return result
```

This matters enormously for web servers, because a server is almost always waiting on something — a database query, an external API call, a file read — rather than doing heavy CPU computation.

## How FastAPI Handles Both

FastAPI is built to support both styles in the same app:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/sync-route")
def sync_route():
    return {"message": "This is a normal sync function"}

@app.get("/async-route")
async def async_route():
    return {"message": "This is an async function"}
```

Here's the part that surprises people: **FastAPI runs both of these correctly, without you needing to manually manage threads or event loops.** Under the hood, FastAPI (built on Starlette) automatically runs synchronous route functions in a separate thread pool, so a slow `def` route doesn't block the entire server the way it would in some other frameworks. This is genuinely one of FastAPI's most underappreciated design choices.

## So When Does It Actually Matter?

Given that FastAPI handles both automatically, the real question isn't "sync or async in general" — it's **"does the specific work inside this route benefit from async, and are you actually using it correctly?"**

### Case 1: I/O-Bound Work (Where Async Genuinely Helps)

This is the classic case where async makes a real difference: calling an external API, querying a database, reading a file — anything where your code spends most of its time *waiting*, not computing.

```python
import httpx

@app.get("/weather")
async def get_weather():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.weather.example.com/data")
    return response.json()
```

While this request waits for the weather API to respond, FastAPI's event loop is free to handle other incoming requests on the same worker — instead of that worker being stuck doing nothing but waiting. For an LLM-backed API specifically, this matters a lot: calling an LLM provider's API is exactly this kind of I/O-bound wait.

### Case 2: CPU-Bound Work (Where Async Doesn't Help, and Can Hurt)

Async doesn't make computation faster — it only helps with *waiting*. If your route is doing heavy CPU work (image processing, large data crunching, complex calculations), wrapping it in `async def` doesn't parallelize the math. Worse, if you write CPU-heavy work directly inside an `async def` route without offloading it, you can actually **block the entire event loop**, freezing every other request being handled by that worker.

```python
# Bad: CPU-heavy work directly inside async def blocks everything else
@app.get("/process")
async def process_data():
    result = heavy_cpu_computation()  # blocks the event loop for everyone
    return result
```

For CPU-bound work, a plain `def` route (which FastAPI runs in a thread pool automatically) or explicitly offloading to a background process is usually the safer choice.

### Case 3: Using a Sync Library Inside an Async Route (The Common Mistake)

This is probably the most common real-world mistake: writing `async def` but calling a library that isn't actually async underneath.

```python
import requests  # this is a SYNC library

@app.get("/bad-example")
async def bad_example():
    response = requests.get("https://api.example.com/data")  # blocks the event loop!
    return response.json()
```

Even though the route is declared `async def`, `requests.get()` is a blocking synchronous call. It will still block the entire event loop while it waits, defeating the whole purpose of using async in the first place. The fix is using an actual async-compatible library, like `httpx` with `await`, instead of a sync library inside an async function.

## A Simple Rule of Thumb

- **Calling an external API, database, or doing any network I/O?** Use `async def`, and make sure you're using an async-compatible library (`httpx`, async database drivers like `asyncpg`, etc.) — not a sync one like `requests`.
- **Doing heavy CPU computation?** A plain `def` route is often safer, since FastAPI runs it in a thread pool automatically. For genuinely heavy work, consider offloading to a background task or separate worker process entirely.
- **Not sure, and just calling simple, fast logic with no I/O?** It barely matters either way at small scale — don't over-optimize a route that isn't actually a bottleneck.
- **Using an async library? Actually `await` it.** Writing `async def` without ever using `await` inside gains you nothing.

## Why This Matters More for GenAI Apps Specifically

If you're building an AI-powered API, this decision comes up constantly, because calling an LLM provider's API is a textbook I/O-bound operation — your server sends a request and waits for the model to generate a response. Using `async def` with an async-compatible client library (most major LLM SDKs support this) lets your FastAPI server handle multiple concurrent chat requests efficiently, instead of one slow LLM call blocking every other user's request behind it.

## Closing Thought

Async isn't a blanket performance upgrade — it's a tool for a specific problem: efficiently handling work that spends time waiting rather than computing. FastAPI's automatic handling of both styles is genuinely convenient, but it doesn't remove the need to understand which kind of work you're actually writing. Get that distinction right, especially in a GenAI API where every request involves waiting on an LLM response, and your server stays responsive under real load instead of quietly bottlenecking on requests that should never have been blocking each other in the first place.