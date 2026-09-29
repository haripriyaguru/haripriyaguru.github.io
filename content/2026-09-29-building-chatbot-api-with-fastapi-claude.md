Title: Building a Chatbot API with FastAPI + OpenAI/Claude — Step by Step
Date: 2026-09-29
Category: Tutorial
Tags: FastAPI, Python, chatbot, OpenAI, Claude, GenAI, LLM
Slug: building-chatbot-api-fastapi-openai-claude
status: Published

## Why This Matters

Every GenAI journey eventually hits the same milestone: building your first real chatbot API, not just calling a model from a script. This is the project that ties together everything else — API keys, request/response models, calling an LLM provider, and returning a clean response your frontend can actually use.

This walkthrough builds a simple but properly structured chatbot API using FastAPI, that you can extend later with streaming, memory, or RAG.

## What We're Building

A minimal API with one core endpoint:

```
POST /chat  →  { "message": "your question" }  →  { "response": "the AI's answer" }
```

Simple on purpose. Once this works, adding conversation history, streaming, or tool use is much easier on top of a solid base.

## Step 1: Project Setup

```bash
mkdir chatbot-api && cd chatbot-api
python -m venv venv
source venv/bin/activate    # on Windows: venv\Scripts\activate

pip install fastapi uvicorn python-dotenv pydantic-settings
pip install openai          # if using OpenAI
pip install anthropic       # if using Claude
```

Project structure:

```
chatbot-api/
├── main.py
├── config.py
├── .env
├── .gitignore
```

## Step 2: Managing the API Key Properly

As covered in an earlier post on environment variables, never hardcode API keys. Set up `.env` and `.gitignore`:

```
# .env
OPENAI_API_KEY=sk-your-real-key-here
```

```
# .gitignore
.env
venv/
```

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

## Step 3: Defining the Request and Response Models

FastAPI leans on Pydantic to define exactly what a valid request looks like:

```python
# main.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
```

This gives you free input validation — if `message` is missing or the wrong type, FastAPI rejects the request with a clear error before your code even runs.

## Step 4: Calling the LLM (OpenAI Version)

```python
# main.py
from fastapi import FastAPI
from openai import OpenAI
from config import settings

app = FastAPI()
client = OpenAI(api_key=settings.openai_api_key)

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": request.message}
        ]
    )
    reply = completion.choices[0].message.content
    return ChatResponse(response=reply)
```

## Step 4 (Alternative): Calling the LLM (Claude Version)

If you're using Anthropic's API instead:

```python
# main.py
from fastapi import FastAPI
from anthropic import Anthropic
from config import settings

app = FastAPI()
client = Anthropic(api_key=settings.anthropic_api_key)

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": request.message}
        ]
    )
    reply = message.content[0].text
    return ChatResponse(response=reply)
```

The overall shape is nearly identical between providers — build a request, send it, extract the text from the response. This is why swapping providers later isn't usually a huge rewrite.

## Step 5: Running the API

```bash
uvicorn main:app --reload --port 8000
```

Test it directly from the auto-generated docs at `http://localhost:8000/docs` — no frontend needed yet. Send a request through the interactive UI and confirm you get a real response back from the model.

You can also test with `curl`:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is FastAPI?"}'
```

## Step 6: Handling Errors Gracefully

Right now, if the LLM API call fails (rate limit, network issue, invalid key), the error bubbles up as an ugly 500 response. Wrap it properly:

```python
from fastapi import HTTPException

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": request.message}
            ]
        )
        reply = completion.choices[0].message.content
        return ChatResponse(response=reply)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI provider error: {str(e)}")
```

A `502` here signals to the client that the failure came from the upstream AI provider, not from your own API — a small detail that makes debugging much easier later.

## Step 7: Adding Basic Conversation Memory (Optional Next Step)

The version above has no memory — every request is treated as a brand-new conversation. A simple way to add short-term memory is accepting the conversation history from the client and passing it straight through:

```python
from typing import List
from pydantic import BaseModel

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": m.role, "content": m.content} for m in request.messages]
    )
    reply = completion.choices[0].message.content
    return ChatResponse(response=reply)
```

This pushes memory management to the client for now (it resends the full history each time) — a reasonable starting point before introducing server-side session storage or a database.

## What to Add Next

Once this base is working, natural next steps (each a solid follow-up project) include:

- **Streaming responses** using Server-Sent Events, so replies appear word by word instead of all at once
- **Rate limiting** so one user can't drain your API budget
- **Server-side conversation storage**, instead of relying on the client to resend history every time
- **RAG integration**, grounding responses in your own documents instead of just the model's training data

## Closing Thought

A chatbot API looks simple from the outside — send a message, get a response — but building it properly, with clean request validation, safe key management, and real error handling, sets up a foundation that's actually easy to extend later. Get this base right first, and streaming, memory, and RAG all become incremental additions instead of a rewrite.