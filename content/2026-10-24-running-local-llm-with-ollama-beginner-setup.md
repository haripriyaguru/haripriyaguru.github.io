Title: I Ran an LLM on My Own Laptop: Here's How (Ollama Setup for Beginners)
Date: 2026-10-24
Category: Tutorial
Tags: Ollama, local-LLM, GenAI, FastAPI, Python, beginner
Slug: running-local-llm-with-ollama-beginner-setup

## The Moment It Clicked

For a long time, "using an LLM" meant one thing for me: sign up, paste an API key, send a request to someone else's server, and watch the token counter tick up. Then I tried running a model on my own laptop, with the Wi-Fi turned off, and it answered. No API key, no bill, no data leaving my machine.

It felt like the first time I ran a web server on localhost. Suddenly the "magic" was just a program running on my computer. This post is the exact path I followed, so you can do the same in about fifteen minutes.

## What Is Ollama?

Ollama is a free tool that makes running open-source LLMs locally almost boringly easy. It handles downloading the model, loading it into memory, and exposing it through a simple command line and a local HTTP API. You don't need to compile anything or touch model files yourself.

Think of it as Docker for LLMs: you pull a model by name, run it, and talk to it.

## Why Bother With a Local Model?

Cloud APIs are great, but local models have their own real advantages:

- **Privacy.** Your prompts stay on your machine, which matters if you're experimenting with sensitive text.
- **No per-token cost.** Once the model is downloaded, experimenting is free, which is wonderful for learning and for testing pipelines you'll run thousands of times.
- **Works offline.** Planes, trains, and bad Wi-Fi stop being a problem.
- **You learn how things work.** Seeing model size, memory use, and speed on your own hardware teaches you more than any diagram.

The honest tradeoff: small local models are generally less capable than the biggest cloud models, so expect weaker answers on hard reasoning tasks. For learning, prototyping, and simple tasks, they're more than good enough.

## What Your Machine Needs

You don't need a monster GPU to start. Rough, beginner-friendly guidance:

- **8 GB of RAM:** small models (around 1B to 3B parameters) run fine.
- **16 GB of RAM:** comfortable for 7B to 8B models in their compressed (quantized) form.
- **A GPU helps a lot** with speed, but Ollama runs on CPU too, just more slowly.

Exact requirements depend on the model and its quantization level, so treat these numbers as a starting point and check each model's page. If a model is too heavy, your computer will let you know by getting very slow, in which case just pick a smaller one.

## Step 1: Install Ollama

Go to ollama.com and download the installer for your system. On Windows and macOS it's a normal installer. On Linux, the site gives you a one-line install command.

Check that it worked:

```bash
ollama --version
```

If you see a version number, you're ready.

## Step 2: Download and Run Your First Model

Pick a small model to start. Model names change over time, so browse the library on the Ollama website, but something like Llama 3.2 in its small size is a friendly first choice:

```bash
ollama run llama3.2
```

The first time, this downloads the model (a couple of gigabytes, so be patient), then drops you into a chat prompt:

```
>>> Explain what a token is in one sentence.
```

Type a question, press enter, and watch it answer. Type `/bye` to exit. That's it. You just ran an LLM locally.

## Step 3: A Few Commands Worth Knowing

```bash
ollama list            # see models you've downloaded
ollama pull <model>    # download a model without starting a chat
ollama rm <model>      # delete a model to free up disk space
ollama ps              # see which models are currently loaded in memory
```

Models take real disk space, so `ollama rm` is useful once you start trying several.

## Step 4: Use It From Code

The part that matters for builders: Ollama runs a local server, by default at `http://localhost:11434`. Yes, that's a high port number, which connects nicely to the earlier post on why low ports are avoided: it's a normal unprivileged port, no root needed.

You can call it with plain HTTP:

```python
import requests

response = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3.2",
        "messages": [{"role": "user", "content": "What is FastAPI?"}],
        "stream": False,
    },
)
print(response.json()["message"]["content"])
```

Or use the official Python library:

```bash
pip install ollama
```

```python
import ollama

reply = ollama.chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "What is FastAPI?"}],
)
print(reply["message"]["content"])
```

Notice how similar this looks to calling a cloud LLM API: a model name, a list of messages, and a text reply. That similarity is the whole point, and it means moving between local and cloud is usually a small change, not a rewrite.

## Step 5: Plug It Into FastAPI

If you've followed the chatbot API tutorial on this blog, swapping in a local model is easy. Since calling a model is an I/O-bound wait, an async client fits well (as covered in the async vs sync post):

```python
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "llama3.2",
                    "messages": [{"role": "user", "content": request.message}],
                    "stream": False,
                },
            )
            r.raise_for_status()
        return ChatResponse(response=r.json()["message"]["content"])
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Local model error: {e}")
```

Run it with `uvicorn main:app --port 8000`, open `/docs`, and test it. No API key, no environment variable for secrets, no bill. The long timeout is deliberate, because local generation on a modest laptop can take a while.

## Things That Surprised Me

- **The first response is slow.** The model has to load into memory on the first request, so the first answer lags and later ones are faster.
- **Quality varies a lot by model size.** A 3B model is fun and useful, but it makes mistakes a bigger model wouldn't. Don't judge "local LLMs" by the smallest one.
- **Memory is the real limit.** Speed matters less than whether the model fits in RAM at all.
- **It teaches you about tokens and context windows for real.** Longer prompts visibly slow things down, which makes the earlier concepts about context size feel concrete.

## Troubleshooting Quick Hits

- **"Connection refused" on port 11434:** Ollama isn't running. Start the app, or run `ollama serve` in a terminal.
- **Model is painfully slow:** Try a smaller model, close memory-hungry apps, or check whether your machine is using the GPU.
- **Disk filling up:** Run `ollama list` and remove models you don't use.
- **Weird or low-quality answers:** Try a larger model if your hardware allows, and write clearer prompts, since small models are less forgiving.

## When Local Makes Sense (And When It Doesn't)

Local is a great fit for learning, privacy-sensitive experiments, offline work, and cheap prototyping. Cloud APIs still win when you need the strongest reasoning, large context windows, high concurrency, or zero hardware management. Most real projects end up using both: local for development and testing, cloud for production-grade quality.

## Closing Thought

Running a model locally changed how I think about LLMs. They stopped being a mysterious service and became a program with a size, a memory footprint, and a port number. If you've only ever used cloud APIs, spend fifteen minutes with Ollama. You'll come away understanding the technology a little better, and you'll have a free, private model to experiment with whenever you want.