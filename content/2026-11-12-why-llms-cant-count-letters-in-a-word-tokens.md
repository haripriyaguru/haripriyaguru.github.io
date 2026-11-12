Title: Why LLMs Can't Count Letters in a Word: Tokens
Date: 2026-11-12
Category: Beginner Guide
Tags: GenAI, LLM, tokens, tokenization, beginner
Slug: why-llms-cant-count-letters-in-a-word-tokens

## The Question That Trips Up Every Model

Ask an LLM how many times the letter "r" appears in the word "strawberry" and there's a good chance it gets it wrong. Ask it to reverse a simple word and it fumbles. Count vowels in a sentence — wrong again. For a system that can write code and explain quantum physics, this feels absurd.

The reason isn't that LLMs are bad at counting. It's that they never actually see individual letters. They see **tokens**.

## What a Token Is

A token is the basic unit an LLM works with. It's not a letter, and it's not always a word. It's a chunk of text, usually somewhere between a character and a word in length, defined by a process called tokenization that runs before the model sees anything at all.

Here's what that looks like in practice. The sentence:

```
I love strawberry ice cream.
```

might get split into tokens like:

```
["I", " love", " straw", "berry", " ice", " cream", "."]
```

The word "strawberry" becomes two tokens: `" straw"` and `"berry"`. The model never encounters the full word as a single thing. It sees two separate chunks with no internal structure.

## How Tokenization Works

The most common tokenization method used by modern LLMs is called **Byte Pair Encoding (BPE)**. The short version: it starts with individual characters, then repeatedly merges the most frequently co-occurring pairs into new tokens, until it has a fixed vocabulary (typically 50,000–100,000 tokens).

The result is that common words become single tokens, common prefixes and suffixes get their own tokens, and rare or made-up words get split into smaller pieces.

A few examples of how tokens typically fall:

- `"the"` → one token
- `"running"` → one token (common enough)
- `"tokenization"` → might be `["token", "ization"]`
- `"strawberry"` → `["straw", "berry"]`
- `"xkqzwm"` → character by character, something like `["x", "k", "q", "z", "w", "m"]`

You can try OpenAI's tokenizer at [platform.openai.com/tokenizer](https://platform.openai.com/tokenizer) to see exactly how any text gets split.

## Why This Breaks Letter Counting

When you ask an LLM "how many r's are in strawberry," here's what it's actually working with:

- Token 1: `" straw"` — contains one r
- Token 2: `"berry"` — contains two r's

To count all the r's correctly, the model would need to look inside each token, treat each token as a sequence of characters, count across token boundaries, and sum the result. That's a multi-step reasoning process that the model has to construct — it's not automatic. The model doesn't have an inherent character-level view of the text.

GPT-4 and similar models have gotten better at this through chain-of-thought reasoning — if you ask it to "think step by step," it's more likely to spell out the word token by token and count carefully. But it's working harder to compensate for a structural limitation, not solving it natively.

## Why Numbers Are Also Weird

The same issue applies to arithmetic with large numbers. The number `12345` might be one token, `123` and `45` as two tokens, or even split differently depending on the tokenizer. When a model does arithmetic, it's manipulating token representations, not digits. This is why LLMs sometimes make basic arithmetic mistakes on numbers they'd never encounter frequently during training.

Models with code training tend to do better here, partly because code training includes many explicit numeric manipulations that help ground the representations.

## Other Practical Consequences of Tokens

Understanding tokens explains several other LLM behaviors that seem strange at first:

**Why some languages are more expensive.** English text tokenizes efficiently — roughly 1 token per 4 characters, or about 0.75 tokens per word. Languages with less training data, or languages using different scripts, often tokenize less efficiently. Some Chinese or Arabic text might use 2–3× more tokens than equivalent English, which means higher API costs for the same content volume.

**Why spelling matters more than you'd think.** An intentional misspelling might tokenize completely differently from the correct word, landing the model in an unfamiliar distribution. Unusual spellings can degrade response quality noticeably.

**Why prompts have token limits, not word or character limits.** When a provider says a model has a 128K context window, that's 128,000 tokens, not characters or words. For typical English prose, that's roughly 100,000 words. But if your content tokenizes inefficiently, you'll hit the limit faster.

**Why copy-pasting code with unusual indentation sometimes breaks things.** Whitespace tokenizes in specific ways. Unusual indentation patterns can produce unexpected token splits that subtly shift the model's interpretation.

## What Tokens Are Good For

Tokens aren't a design flaw — they're what makes LLMs work at scale. Training on raw characters would be computationally prohibitive and would force the model to learn language from scratch at every level. Tokens let the model operate at a meaningful semantic grain, where `"running"` already carries the concept of motion without the model assembling it letter by letter.

The tradeoff is that tasks requiring character-level precision — exact letter counting, precise string reversal, careful character manipulation — require extra effort from the model. For those tasks, it helps to prompt explicitly: "spell out the word letter by letter, then count each one."

## The One-Line Intuition

LLMs read in chunks, not characters. When a task requires character-level precision, the model has to work backward from chunks to characters — which is possible, but error-prone. That's the whole story behind the strawberry problem.
