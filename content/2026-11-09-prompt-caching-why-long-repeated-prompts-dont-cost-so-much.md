Title: Prompt Caching: Why Long Repeated Prompts Don't Cost So Much
Date: 2026-11-09
Category: Beginner Guide
Tags: GenAI, LLM, prompt-caching, cost, performance, API, production
Slug: prompt-caching-why-long-repeated-prompts-dont-cost-so-much

## The Problem With Long System Prompts

If you've built anything with an LLM API, you've probably added a system prompt. At first it's a sentence or two. Then you add instructions. Then examples. Then context about your product. Before long, your system prompt is a few hundred lines and every single API call ships the whole thing again, even when the only thing that changed was the user's latest message.

You're paying for those tokens every time. On a busy app, that adds up fast. Prompt caching is the feature that changes this.

## What Prompt Caching Actually Does

When you send a request to an LLM API, the model has to process every token in the input before it can generate a response. That processing — called the **prefill** step — takes compute and costs money.

Prompt caching lets the provider store the processed state of a prompt prefix on their servers. On the next request that starts with the same prefix, the provider skips reprocessing those cached tokens and jumps straight to the new part. You pay a lower rate for the cache hit instead of the full input rate.

The analogy: imagine reading the same long document at the start of every meeting to catch new attendees up. Prompt caching means you only read it once. After that, everyone in the meeting already has it in working memory.

## What Gets Cached

Not the raw text — what gets cached is the model's internal processed representation of those tokens (the KV cache, short for key-value cache). This is an implementation detail you don't need to manage directly, but it explains why caching is powerful: the expensive computation is what's skipped, not just the data transfer.

For a cache hit to occur, the beginning of your prompt must match the beginning of a previously cached prompt **exactly**, character for character. Even a single character difference breaks the match.

This means caching works best for content that is:

- **Fixed across many requests:** system prompts, instructions, personas
- **Long:** the more tokens, the bigger the saving
- **Sent frequently:** cache entries expire after a period of inactivity (typically around 5 minutes for short-lived caches, up to an hour with some providers)

## How to Use It

The exact API varies by provider, but the pattern is similar across all of them.

**Anthropic (Claude)** uses a `cache_control` marker to tell the API where to draw the cache boundary:

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are a helpful assistant for Acme Corp...\n\n[very long system prompt here]",
            "cache_control": {"type": "ephemeral"}   # cache up to this point
        }
    ],
    messages=[
        {"role": "user", "content": "What is your return policy?"}
    ]
)
```

The `cache_control` marker tells the API: "cache everything up to and including this block." On subsequent requests that send the same system block, you pay the cached input rate instead of the standard input rate — roughly 10% of the normal price on Anthropic's current pricing.

**OpenAI** handles this automatically for prompts over 1024 tokens. You don't add any marker; the API detects repeated prefixes and applies a 50% discount on cached tokens without you doing anything.

**Google (Gemini)** calls this feature "context caching" and requires you to create a named cache object explicitly via a separate API call, then reference it by ID in your requests. More setup, but it supports very large contexts and longer TTLs.

## A Concrete Cost Example

Say your system prompt is 2000 tokens, and your app handles 10,000 requests per day. Without caching, you pay for 2000 × 10,000 = **20 million input tokens** just for the system prompt every day.

With caching, the first request of each session pays full price. Subsequent requests in the same session pay the cached rate. If 90% of your requests are cache hits and the cached rate is 10% of full price:

- 1,000,000 tokens at full price
- 19,000,000 tokens at 10% of full price = 1,900,000 token-equivalents
- Total: ~2,900,000 effective tokens, instead of 20,000,000

That's an 85% reduction on the system prompt portion of your bill, without changing your app's behavior at all.

## What Caching Doesn't Help With

It's worth being clear about the limits:

- **Output tokens are never cached.** Caching only applies to the input (prompt) side.
- **Short prompts don't benefit much.** Providers have minimum thresholds — typically 1024 tokens on OpenAI, 2048 on Anthropic — before caching kicks in.
- **Cache misses still cost full price.** The first request always pays full rate. If your traffic is sparse enough that cache entries expire between calls, you'll see few hits.
- **Exact prefix matching is required.** Any change to the cached portion breaks the cache. This is why dynamic content (like today's date, or the current user's name) should go at the *end* of the prompt, after the stable cached section.

## Structuring Your Prompt for Maximum Cache Hits

The key rule is: **put the stable content first, the dynamic content last.**

Bad order (cache-unfriendly):
```
Today is {date}.
You are an assistant for Acme Corp...
[2000 tokens of stable instructions]
User name: {user_name}
```

Good order (cache-friendly):
```
You are an assistant for Acme Corp...
[2000 tokens of stable instructions]
Today is {date}. User name: {user_name}.
```

In the bad version, changing the date at the top invalidates the entire cached prefix. In the good version, the stable instructions form a fixed prefix that caches reliably, and the dynamic parts sit after it where they're filled in fresh each time.

A useful mental model: think of your prompt like a book. The table of contents, chapters, and reference sections are stable — cache those. The bookmark showing where you left off is per-session — keep that at the end.

## Checking If It's Working

Most providers return cache usage statistics in the API response. On Anthropic, look at `usage.cache_read_input_tokens` and `usage.cache_creation_input_tokens`. On OpenAI, check `usage.prompt_tokens_details.cached_tokens`.

If `cached_tokens` is 0 on calls you expect to hit, the prefix may be mismatched. Common causes: whitespace differences, a timestamp embedded in the system prompt, or content that changes per user placed before the stable section.

## When to Bother Setting This Up

Prompt caching is worth it when:

- Your system prompt is long (over 1000 tokens)
- You have repetitive workloads: chatbots, document Q&A, multi-turn conversations
- You're making many calls with the same context (batch processing, agent loops)

It's less impactful when:

- You have very short prompts
- Each request has a unique, fully dynamic context
- Traffic is too low or too infrequent for cache entries to survive between requests

For most production LLM apps, the system prompt alone justifies enabling caching. It's one of those rare optimizations that costs nothing to try on OpenAI (it's automatic), and takes only a few minutes to add on Anthropic.

## Quick Summary

- Prompt caching stores the processed state of a repeated prompt prefix on the provider's servers
- Cache hits are charged at a fraction of the normal input token rate
- Structure prompts with stable content first, dynamic content last
- OpenAI applies it automatically above 1024 tokens; Anthropic requires a `cache_control` marker; Gemini requires an explicit cache object
- Check `cached_tokens` in the API response to verify hits are occurring
- Most impactful for long system prompts in high-traffic or multi-turn applications
