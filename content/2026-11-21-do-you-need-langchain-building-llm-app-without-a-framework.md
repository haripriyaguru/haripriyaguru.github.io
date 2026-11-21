Title: Do You Need LangChain? Building an LLM App Without a Framework
Date: 2026-11-21
Category: GenAI
Tags: GenAI, LLM, LangChain, frameworks, Python, FastAPI, opinion
Slug: do-you-need-langchain-building-llm-app-without-a-framework

## The Question Every Beginner Asks

When you start learning GenAI, you quickly notice that a huge number of tutorials begin the same way: `pip install langchain`. So a natural question follows. Is a framework like LangChain something you *need* to build an LLM app, or is it optional?

My honest answer after building the projects on this blog is: **you don't need one to get started, and you'll understand more if you build the basics by hand first. But frameworks solve real problems, and there are situations where they genuinely save time.** This post is about telling those situations apart, without the usual tribal "framework good / framework bad" arguing.

## What a Framework Actually Gives You

Before deciding whether you need one, it helps to list what these tools provide:

- **A common interface across providers,** so switching between model APIs is easier
- **Building blocks for common patterns:** prompt templates, output parsing, retrieval, text splitters, document loaders, vector store integrations
- **An agent loop,** so the "call the model, run the tool, feed back the result" cycle is already written
- **State and persistence,** so long-running or interrupted workflows can pause and resume
- **Ready-made integrations** with databases, search tools, file formats, and APIs
- **Tracing and observability hooks,** often tied to companion tools
- **Standard patterns a team can share,** which matters once more than one person works on the code

None of these is magic. Each is something you could write yourself. The question is whether writing it yourself is worth it.

## A Quick Note: This Ecosystem Moves Fast

One reason to be careful with older tutorials: LangChain has changed a lot. With its 1.0 release, the project streamlined itself around agents. According to its documentation, `create_agent` became the standard way to build agents, built on top of LangGraph, with middleware as a key feature for customization, and legacy functionality such as the older chain implementations moved into a separate `langchain-classic` package.

That's a healthy sign of maturing, and the 1.0 releases promise more stable core APIs. But it also means that code from a 2023 or 2024 tutorial may use patterns that are now deprecated or relocated. Whatever framework you choose, **check the version a tutorial was written for**, and pin your own versions. Details here may have changed again by the time you read this, so confirm in the current docs.

## What a Framework-Free App Looks Like

Here's the thing that surprised me: nearly everything an LLM app needs is only a few small pieces, and we've already built most of them in earlier posts without any framework:

- **Calling the model:** the official SDK (a few lines)
- **Prompts:** versioned text files with placeholders (the prompt versioning post)
- **Structured output:** Pydantic validation with retries (the structured outputs post)
- **RAG:** a chunker, a vector database client, and a prompt (the RAG API post)
- **Tools:** a schema plus a loop (the function calling post)
- **Streaming:** Server-Sent Events from FastAPI (the streaming post)
- **Logging:** a wrapper and a request ID (the observability post)
- **Safety:** allowlists, validation, and approvals (the prompt injection and human-in-the-loop posts)

The piece people think of as "framework territory" is the agent loop, so let's see how small it really is.

### An Agent Loop in About 25 Lines

```python
import json

def run_agent(user_message: str, tools: dict, tool_specs: list, max_steps: int = 5) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tool_specs,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:          # the model is done and answered in text
            return msg.content

        messages.append(msg)            # keep the model's tool request in the history

        for call in msg.tool_calls:
            name = call.function.name
            if name not in tools:       # allowlist: unknown tools are rejected
                result = {"error": f"Unknown tool: {name}"}
            else:
                try:
                    args = json.loads(call.function.arguments)
                    result = tools[name](**args)
                except Exception as exc:
                    result = {"error": str(exc)}   # specific errors help the model recover

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, default=str),
            })

    return "I couldn't finish within the step limit."
```

That's the whole core: ask the model, run the tools it requests, feed the results back, repeat until it answers, with a **step limit** so it can't loop forever. Everything else, such as approvals, logging, and validation, plugs into this loop at obvious places.

For comparison, here's roughly what the same idea looks like using LangChain's documented agent helper:

```python
from langchain.agents import create_agent

agent = create_agent(
    model="claude-sonnet-4-6",          # model names change; use one you have access to
    tools=[search_docs, get_order_status],
    system_prompt="You are a helpful support assistant.",
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Where is my order 1234?"}]
})
```

Much shorter, and it comes with extras the 25-line version doesn't have, such as persistence for long-running agents and built-in middleware options, which the docs describe as including human approval for tool calls, conversation summarization, and PII redaction. That's the real trade-off in one picture: **less code and more built-in features, versus more transparency and control.**

## The Case for Going Without a Framework

**You learn what's actually happening.** When you've written the loop yourself, a framework stops being magic. You know what request goes to the model, and why it behaves the way it does. Beginners who start with a high-level abstraction often can't debug a problem because they never saw the layer underneath.

**Debugging is simpler.** With direct SDK calls, the stack trace is short and the request is exactly what you wrote. With deeper abstractions, an error can pass through many layers before reaching you.

**Full control over the prompt and the cost.** Some higher-level components include default prompts you didn't write, or make extra model calls behind the scenes. When you care about token usage, caching (as in the prompt caching post), and exact wording, you want to see every character you're sending.

**Fewer moving parts.** Every dependency is something that can break, change, or conflict with another library. A small app with a handful of well-chosen libraries is easier to maintain than one built around a large framework.

**New provider features show up first in the official SDK.** If a model provider releases a feature, the direct SDK usually supports it right away, while a framework may take time to expose it.

**Less churn.** Direct SDKs change too, but you're depending on one layer instead of two.

## The Case for Using a Framework

**You avoid rebuilding solved problems.** Document loaders for dozens of file types, text splitters, integrations with many vector databases, and retry and streaming handling are tedious to write and maintain.

**Complex workflows are genuinely hard.** Once you have branching logic, parallel steps, loops with conditions, long-running tasks that must pause for human approval and resume hours later, and state that survives restarts, you're building a workflow engine. Tools like LangGraph exist precisely for this, and writing your own robust version is a real project.

**Provider flexibility.** If you truly need to switch between or combine many model providers, a common interface saves effort. (A thin wrapper or a gateway library can also do this without a full framework.)

**Team consistency.** A shared set of patterns can help a larger team write code that looks alike and is easier to review.

**Faster prototypes.** For a quick experiment or demo, a framework's ready-made pieces can get you to a working result sooner.

**Ecosystem and tooling.** Tracing, evaluation, and deployment tools that integrate smoothly with a framework can be worth the buy-in.

## A Middle Path: Libraries, Not Frameworks

It's not a binary choice. A useful distinction is between a **framework** (it calls your code and defines the structure of your app) and a **library** (your code calls it when needed). You can build a very capable app from focused libraries:

- The **official model SDKs** for calling APIs (they also handle basic retries, which you can usually configure)
- **Pydantic** for schemas and validation
- A **vector database client** such as Chroma
- A **PDF or document parser** for your file types
- **tiktoken** or a similar tokenizer for counting tokens
- A **retry library** if you need more control over backoff
- A **gateway library or service** if you want one interface across many providers

This gives you most of the benefits of a framework's building blocks while keeping the structure of the app in your own hands.

There are also other frameworks and SDKs beyond LangChain, some focused on retrieval and data (such as LlamaIndex or Haystack), some on structured prompting and optimization (such as DSPy), some built around typed Python (such as Pydantic AI), and agent SDKs from the model providers themselves. The landscape shifts quickly, so check current status rather than relying on a snapshot.

## A Practical Decision Guide

**Go framework-free (or library-only) when:**
- You're learning. Build the loop by hand at least once.
- Your app is simple: a chatbot, a RAG endpoint, or an agent with a few tools
- You use one main provider
- You want complete control over prompts, tokens, and costs
- The team is small and the codebase is easy to hold in your head

**Reach for a framework (or parts of one) when:**
- You need many integrations (loaders, vector stores, tools) quickly
- Your workflow is complex: branching, persistence, pause and resume, multiple cooperating agents
- You need to support several providers and switch between them
- A larger team benefits from shared structure
- You're prototyping and speed matters more than control

**Either way:**
- Know what request is actually sent to the model
- Keep the framework behind a thin interface of your own, so you can replace it
- Pin versions and read migration notes
- Don't adopt a whole framework just to use one feature. Many offer individual components (like text splitters) that you can use alone.

## How to Avoid Getting Locked In

If you do use a framework, a few habits keep your options open:

- **Wrap it.** Have your app call your own functions (`answer_question()`, `run_agent()`), and put the framework inside them. Swapping it later then touches one module, not the whole app.
- **Keep prompts and settings outside the framework,** in your own versioned files.
- **Log the actual requests,** so you always see what's being sent to the model.
- **Keep your eval set independent.** It should test your app's behavior, not the framework's internals, so you can compare implementations fairly.
- **Pin dependency versions** and upgrade deliberately.
- **Be wary of old tutorials,** since APIs may have moved or been deprecated.

## A Simple Test of Understanding

Here's a quick check I use: **can you explain exactly what text is sent to the model for a given user action?** If you can, your abstractions aren't hiding anything important from you, and whatever tools you use are fine. If you can't, you don't fully understand your own app yet, and a bug or a surprising bill will eventually make that painfully obvious.

## My Take for Beginners

If you're learning, build one full app without a framework: a chat endpoint, a RAG pipeline, and a simple tool loop. It takes a weekend and teaches you more than any amount of framework documentation. Then try the same app with a framework, and compare. You'll see exactly what it saves you and exactly what it hides, which makes you far better at choosing tools afterward.

## Quick Checklist

- Learn the basics by hand first: model call, tool loop, retrieval, validation
- Remember the core agent loop is small, so don't fear it
- Use libraries freely, and adopt a framework deliberately
- Choose a framework for complexity (workflows, persistence, many integrations), not for fear of writing code
- Check which version a tutorial targets, and pin your own versions
- Keep prompts, logging, and evals independent of any framework
- Wrap the framework behind your own interface
- Make sure you can always see what's sent to the model

## Closing Thought

Frameworks aren't a requirement, and they aren't a mistake. They're a trade between speed and visibility. Early on, visibility is worth far more, because understanding the layer underneath is what lets you debug, optimize, and make good decisions later. As your app grows more complex, a framework's building blocks may earn their place. The best developers I see aren't the ones who picked the "right" side. They're the ones who could build it either way, and chose on purpose.