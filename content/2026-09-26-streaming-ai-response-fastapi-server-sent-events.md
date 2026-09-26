Title: Streaming AI Responses in FastAPI Using Server-Sent Events (SSE)
Date: 2026-09-26
Category: Tutorial
Tags: FastAPI, Python, SSE, streaming, GenAI, LLM
Slug: streaming-ai-responses-fastapi-sse
status: Published


## Why This Matters

If you've used ChatGPT or Claude, you've seen the response appear word by word instead of showing up all at once after a long wait. That's not just a visual nicety — it makes the app feel dramatically faster, even though the total time to finish the response is roughly the same. When you're building your own AI-powered API with FastAPI, this streaming behavior doesn't happen automatically. You have to build it yourself, and **Server-Sent Events (SSE)** is one of the simplest, most reliable ways to do it.

## What SSE Actually Is

SSE is a web standard that lets a server push a continuous stream of small text updates to a client over a single, long-lived HTTP connection — without needing the client to keep asking "is there more?" It's simpler than WebSockets because it's one-directional (server to client only) and works over plain HTTP, which makes it a great fit for streaming AI-generated text.

The core idea:

```
Client opens a connection → Server keeps it open → Server sends small chunks of data as they become available →
Client processes each chunk as it arrives → Server closes the connection when done
```

## Why Not Just Return the Full Response at Once?

Technically, you could wait for the entire AI response to finish generating, then send it all back in one normal HTTP response. But this has real downsides:

- **Perceived latency is much worse.** Users stare at a loading spinner for the entire generation time, instead of seeing progress immediately.
- **Long responses risk timeouts.** Some infrastructure (proxies, load balancers) has request timeout limits that a very long, non-streamed AI generation can exceed.
- **No early feedback.** If something looks wrong early in the response, the user has no way to know until the whole thing finishes.

## Setting Up a Basic SSE Endpoint in FastAPI

FastAPI supports this cleanly using `StreamingResponse`. Here's a minimal example that streams fake incremental text, just to show the mechanics:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

async def fake_ai_stream():
    words = ["Hello", "this", "is", "a", "streamed", "response", "from", "FastAPI"]
    for word in words:
        yield f"data: {word}\n\n"
        await asyncio.sleep(0.3)  # simulate generation delay

@app.get("/stream")
async def stream_endpoint():
    return StreamingResponse(fake_ai_stream(), media_type="text/event-stream")
```

A few details that matter here:

- **`media_type="text/event-stream"`** tells the client this is an SSE stream, not a normal response.
- **The `data: ... \n\n` format** is part of the SSE spec — each message needs to be prefixed with `data:` and end with a double newline.
- **The generator function (`async def ... yield`)** is what makes this work — FastAPI sends each yielded chunk to the client as soon as it's produced, instead of waiting for the whole function to finish.

## Connecting This to a Real LLM API

Most LLM providers support streaming natively — instead of waiting for the full response, you get the response back in small chunks as it's generated. Here's the general shape of how you'd wire that into the SSE pattern above (illustrative, adjust to your actual SDK):

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

async def llm_stream(prompt: str):
    async for chunk in call_llm_streaming_api(prompt):  # your LLM SDK's streaming call
        yield f"data: {chunk}\n\n"

@app.get("/chat")
async def chat_endpoint(prompt: str):
    return StreamingResponse(llm_stream(prompt), media_type="text/event-stream")
```

The key idea doesn't change: as each piece of text comes back from the LLM provider, you immediately `yield` it to the client instead of accumulating the full response first.

## Reading the Stream on the Client Side

On the frontend, the browser's built-in `EventSource` API makes consuming this straightforward:

```javascript
const eventSource = new EventSource("/chat?prompt=hello");

eventSource.onmessage = (event) => {
  console.log("Received chunk:", event.data);
  // append event.data to your UI here
};

eventSource.onerror = () => {
  eventSource.close();
};
```

Each `data:` chunk sent from the server triggers `onmessage` on the client, letting you append text to the UI in real time as it arrives.

## Common Pitfalls to Watch For

A few things that trip people up when first implementing this:

- **Forgetting the double newline (`\n\n`).** SSE requires this exact formatting to separate messages — a single `\n` will break parsing on the client side.
- **Buffering issues from proxies.** Some reverse proxies (like Nginx) buffer responses by default, which defeats streaming entirely. You often need to explicitly disable buffering for streaming endpoints (`proxy_buffering off` in Nginx, for example).
- **Not handling client disconnects.** If a user closes the tab mid-stream, your generator should stop cleanly rather than continuing to burn API costs generating a response nobody will see.
- **Assuming SSE handles bidirectional communication.** SSE is server-to-client only. If you need the client to send data back mid-stream (like a "stop generating" button), you'll need a separate mechanism alongside it — or consider WebSockets instead.

## SSE vs WebSockets — Which Should You Use?

For simple AI response streaming, SSE is usually the better fit:

- **Use SSE** when you just need one-directional streaming (server pushes text to client) — this covers the vast majority of "stream an AI response" use cases.
- **Use WebSockets** when you need full bidirectional, real-time communication — for example, a chat app where the client also needs to send interrupt signals or multiple messages while a response is still streaming.

Most basic "AI writes text, user watches it appear" features don't need the added complexity of WebSockets — SSE covers it cleanly.

## Closing Thought

Streaming isn't just a cosmetic upgrade — it changes how responsive your AI feature actually feels, often more than any backend optimization would. SSE gives you a simple, standard way to do this in FastAPI without reaching for the added complexity of WebSockets, and once the basic pattern clicks — yield chunks as they arrive, format them correctly, handle disconnects gracefully — it's a pattern you'll reuse across almost every AI-powered endpoint you build.