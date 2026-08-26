Title: What is a Token? Why Do LLMs Charge You Per Token?
Date: 2026-08-26
Category: Tokens
Tags: GenAI, LLM, tokens, tokenization, pricing, beginner
Slug: what-is-a-token-why-llms-charge-per-token

## Why This Matters

If you've used the OpenAI or Claude API even once, you've seen the word "tokens" everywhere — in the pricing page, in the error messages ("context length exceeded"), in the response object. For a beginner, this is confusing. Why not just charge per word? Or per API call? Why tokens?

This article breaks it down in the simplest way possible — no heavy math, just intuition.

## So, What Exactly is a Token?

A token is a chunk of text — it could be a whole word, part of a word, a punctuation mark, or even just a space. LLMs don't read text the way humans do (letter by letter or word by word). They break the input into these chunks first, and that process is called tokenization.

## Here's a simple example:

Text: "ChatGPT is amazing!"
Tokens: "Chat", "G", "PT", " is", " amazing", "!"

Notice how "ChatGPT" itself got split into three pieces. That's because the tokenizer doesn't know the whole word as a single unit — it only knows common chunks of text that it saw a lot during training.

A rough rule of thumb for English text:

1 token is roughly 4 characters
1 token is roughly ¾ of a word
100 tokens is roughly 75 words

So a 1,000-word blog post is roughly 1,300 tokens.

## Why Not Just Split by Word?

Splitting by word sounds simpler, but it breaks down fast:

Different languages don't split cleanly by spaces (Tamil, Chinese, Japanese, etc.)
New/rare words (brand names, typos, code, slang) would need their own entry in a "word dictionary," which becomes huge and inefficient.
Splitting into smaller, reusable chunks (called subword tokenization) lets the model handle any word — even ones it has never seen — by combining known pieces.

This is why "ChatGPT" becomes Chat + G + PT instead of one clean token. The model never "memorized" the word ChatGPT as a whole — it built it from smaller, familiar pieces.

## Why Do LLMs Charge Per Token?

This is where it clicks for most people. Every token — in your prompt and in the model's response — has to pass through the model's internal computations (matrix multiplications across billions of parameters). More tokens means more compute, which means more cost for the provider (OpenAI, Anthropic, etc.) to run the model.

So pricing is split into two parts:

Input tokens — the tokens in your prompt (what you send)
Output tokens — the tokens the model generates (what you get back)

Output tokens are usually priced higher than input tokens, because generating text token-by-token is more computationally expensive than just reading it.

Here's an illustrative example (not exact real pricing): if input costs $3 per 1 million tokens and output costs $15 per 1 million tokens, and your prompt is 500 tokens with an 800-token response, you're billed for both amounts separately — a small input cost plus a slightly larger output cost.

## Why This Matters for You as a Developer

Understanding tokens isn't just trivia — it directly affects how you build with LLMs:

Context window limits — every model has a max token limit (input + output combined). If your prompt + expected response goes over that, you'll get an error or truncated output.
Cost control — long system prompts, huge chat histories, or verbose responses all cost real money at scale. Trimming unnecessary text saves you money.
Latency — more output tokens means the model takes longer to respond, since tokens are generated one at a time.

## Quick Summary

A token is a chunk of text (word, sub-word, or symbol)
Tokenization is the process of breaking text into tokens
Input tokens are the tokens in your prompt
Output tokens are the tokens in the model's response
Pricing is charged separately for input and output tokens

Rule of thumb: shorter, focused prompts and responses mean lower cost and faster replies.

## Wrapping Up

Tokens are the real "unit of currency" in the LLM world — not words, not characters, not API calls. Once this clicks, a lot of other things start making sense too: why long conversations get expensive, why context windows matter, and why prompt engineering isn't just about clarity but also about efficiency.