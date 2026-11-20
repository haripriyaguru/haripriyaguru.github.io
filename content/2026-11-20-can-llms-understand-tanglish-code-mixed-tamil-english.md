Title: Can LLMs Understand Tanglish? Testing Code-Mixed Tamil-English Prompts
Date: 2026-11-20
Category: GenAI
Tags: GenAI, LLM, Tamil, Tanglish, code-mixed, multilingual, evals
Slug: can-llms-understand-tanglish-code-mixed-tamil-english

## Why I Care About This

Most of my own conversations with AI tools don't happen in clean English or in Tamil script. They happen in **Tanglish**: Tamil written in English letters, mixed with English words, the way we actually text and talk. Something like:

```
Indha error ku reason enna? Konjam simple ah explain pannunga.
```

(Roughly: "What's the reason for this error? Please explain it a bit simply.")

It works fine in conversation with people, and it usually seems to work with AI too. But "usually seems to work" isn't something I'd ship in a product. If you're building an app for users in Tamil Nadu, or anywhere Tanglish is the natural way to type, the question becomes serious: **how reliably do LLMs actually understand this?** And how would you find out?

This post covers what research says so far, why Tanglish is genuinely hard for models, and a simple experiment you can run yourself instead of trusting anyone's claims, including mine.

## What Is Tanglish, Exactly?

Linguists call this **romanized code-mixing**: bilingual speakers blending a local language with English, written in the Latin alphabet. There are two separate things going on at once:

- **Code-mixing:** switching between Tamil and English *within* a sentence
- **Romanization (transliteration):** writing Tamil words using English letters instead of Tamil script

Each is a challenge for a model. Together, they create something that looks like neither English nor Tamil in the way most training data does.

## Why Tanglish Is Hard for LLMs

### 1. There's No Standard Spelling

Tamil script has an official way to write each word. Romanized Tamil doesn't. People spell by sound, and sounds can be written many ways:

```
Enakku idhu puriyala
Enaku ithu puriyala
Yenakku idhu purila
```

All three mean roughly "I don't understand this." To a human, they're obviously the same. To a model, they're three different strings, and rarer spellings may look like noise.

### 2. English Words Get Tamil Suffixes

Tamil is agglutinative, meaning grammar is built by attaching endings to words. In Tanglish, those endings get attached to English words too:

```
Meeting ah tomorrow ku shift pannidunga.
Mail la attachment irukku.
Bug fix pannitu push pannunga.
```

"Meeting ah," "mail la," and "tomorrow ku" are English words wearing Tamil grammar. A tokenizer built mostly around English has never seen most of those combinations.

### 3. The Grammar Isn't English Grammar

Tamil puts verbs at the end of the sentence. In heavily mixed sentences, the English words sit inside a Tamil sentence structure, so models can't lean on familiar English word order.

### 4. Slang, Tone, and Culture

Informal Tamil is full of expressions that don't translate literally. Words like "semma" (roughly, "awesome") or "mokka" (roughly, "lame") carry sentiment that a literal reading would miss, and sarcasm adds another layer.

### 5. Most Training Data Doesn't Look Like This

Models learn from huge amounts of text. There's a lot of English, a smaller amount of Tamil in Tamil script, and comparatively little informal romanized Tamil from chats and social media, which is also messy and inconsistent. Less data, plus more variation, means weaker learning.

### 6. Tokenization Works Against It

As covered in the earlier posts on tokens, models see chunks, not letters. Tamil script has historically been split into many small pieces by tokenizers built around English, which makes it expensive and harder to process. Research on Indian-language tokenization has found large cost gaps compared with English under older tokenizers, though newer ones have improved. Romanized text tends to use fewer tokens than native script, so it can be cheaper, but cheaper isn't the same as better understood.

## What the Research Says

This is an active research area, and results change quickly as models improve, so treat these as directions rather than final answers.

**Romanized code-mixed text is a known weak spot.** A 2026 benchmark called Indi-RomCoM tested models on romanized Indic-English instructions, including Tamil-English, and reported that models consistently performed worse on them, with accuracy dropping further as the amount of mixing increased. That held for general-purpose models and for open-weight models built specifically for Indian languages, which tend to do better in native script but struggle when text is romanized.

**Script matters.** Another study of real health messages across several Indian languages found models handled romanized text noticeably worse than native-script text, a gap sometimes called the "script gap."

**But code-mixing can sometimes help.** In a study of knowledge recall across many Indian languages, prompts that mixed English words in closed much of the gap to English, while simply transliterating everything into Latin script helped less. The idea is that English words give the model familiar anchors to connect to what it already knows. Survey work on code-mixing makes a similar point: mixed or transliterated prompts can sometimes act as a "bridge" for languages with less training data.

**Transliteration itself is something LLMs can do.** A benchmark comparing general-purpose models with a specialized transliteration system found that strong general models were often competitive, and fine-tuning improved them further. Note that this tested converting romanized *words* into native script, not understanding whole conversational sentences.

**English still tends to win.** Studies of factual accuracy across Indian languages keep finding a gap between English and Indian languages, with models often more reliable when asked in English.

So the honest summary: Tanglish understanding is **often decent for simple, common requests, and gets shakier as the mixing gets heavier, the spelling gets less standard, the slang gets more local, or the task gets harder.** Different models differ a lot, and the situation is improving, which is exactly why you should measure instead of assume.

## How to Test It Yourself

Here's a simple experiment design. The key idea is to ask the **same question in three forms** and compare:

- **English**
- **Tanglish** (romanized Tamil mixed with English)
- **Tamil script**

If the answers differ in quality, you've measured the gap for *your* model and *your* task.

### Step 1: Build a Small Test Set

Use the JSONL format from the earlier post on building an eval set, with an extra `form` field. To make correctness checkable, give the model a short piece of context so the right answer is known. Here's an example around a return policy:

```json
{"id": "return-en", "form": "english", "input": "How many days do I have to return an item?", "checks": [{"type": "contains", "value": "30"}]}
{"id": "return-tanglish", "form": "tanglish", "input": "Oru item ah return panna ethana naal irukku?", "checks": [{"type": "contains", "value": "30"}]}
{"id": "return-tamil", "form": "tamil", "input": "ஒரு பொருளை திரும்பப் பெற எத்தனை நாட்கள் உள்ளன?", "checks": [{"type": "contains", "value": "30"}]}
```

And the prompt your code builds around each input:

```python
CONTEXT = "Policy: Items can be returned within 30 days of purchase."

def build_prompt(user_input: str) -> str:
    return (
        "Answer using only the context below.\n\n"
        f"Context: {CONTEXT}\n\n"
        f"Question: {user_input}"
    )
```

Aim for 20 to 40 questions, each written in all three forms. Better still, have **native speakers write the Tanglish versions**, because auto-generated Tanglish tends to look unnatural, and real users type messier than anyone expects.

### Step 2: Cover Different Kinds of Difficulty

Don't only test easy sentences. Include groups like:

- **Light mixing:** mostly English with one Tamil word. "Can you explain this error pa?"
- **Medium mixing:** balanced. "Indha error ku reason enna? Konjam simple ah explain pannunga."
- **Heavy mixing:** mostly Tamil grammar. "Naan oru Python script eludhirukken, aana adhu run aagala. Enna problem nu paathu sollunga."
- **Spelling variants:** the same sentence spelled three or four ways
- **English words with Tamil suffixes:** "Meeting ah reschedule pannidunga."
- **Slang and sentiment:** reviews or messages with expressions like "semma" or "mokka"
- **Typos and short forms:** the way people actually type on phones
- **Ambiguous requests,** where the correct behavior is to ask a clarifying question

### Step 3: Run It and Compare by Form

Reuse the `run_check` function from the eval post, and group results by form:

```python
import json
from collections import defaultdict

def run_by_form(path: str = "tanglish_eval.jsonl", runs: int = 3) -> None:
    with open(path, encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    stats = defaultdict(lambda: [0, 0])   # form -> [passes, total]

    for case in cases:
        for _ in range(runs):
            output = call_llm(build_prompt(case["input"]))
            ok = all(run_check(c, output) for c in case["checks"])
            stats[case["form"]][0] += int(ok)
            stats[case["form"]][1] += 1

    for form, (passes, total) in stats.items():
        print(f"{form:10} {passes / total:.0%}  ({passes}/{total})")

run_by_form()
```

Each case runs several times because of the randomness covered in the temperature post. A single run can mislead you.

### Step 4: Measure Token Cost Too

Since cost is part of the story, compare how many tokens each form needs. With the `tiktoken` library (it fetches its vocabulary on first use, so it needs internet once):

```python
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")

samples = {
    "english":  "How many days do I have to return an item?",
    "tanglish": "Oru item ah return panna ethana naal irukku?",
    "tamil":    "ஒரு பொருளை திரும்பப் பெற எத்தனை நாட்கள் உள்ளன?",
}

for form, text in samples.items():
    print(f"{form:10} {len(enc.encode(text)):3} tokens")
```

Different models use different tokenizers, so run this against the tokenizer for the model you actually use. You'll likely see that Tamil script costs noticeably more than the other two, which connects to the earlier post on why letter-level and language-level quirks come from tokenization.

### Step 5: Read the Results Carefully

A few patterns and what they suggest:

- **English passes, Tanglish passes, Tamil script fails:** Tanglish is fine for your model, and you may even prefer it for cost
- **English passes, Tanglish fails, Tamil script passes:** the model struggles with romanization. Consider transliterating inputs to Tamil script, or adding examples
- **Tanglish passes light mixing but fails heavy mixing:** the model needs more help on heavily Tamil sentences, so rely on clarifying questions or a stronger model
- **All three similar:** great, but test harder cases before celebrating
- **Big differences between runs:** the behavior is flaky, so it needs more guardrails

Look at the *failures*, not only the scores. Are they misunderstandings of the question, wrong answers, or answers in an unexpected language? Each has a different fix.

## Tanglish Is Also About Replies

Understanding the user is half the problem. The other half is **what language to answer in**, and models can be inconsistent here. A user writes Tanglish, and the reply might come back in English, formal Tamil script, or stilted Tanglish that no real person would write.

Decide on a policy and put it in the system prompt. For example:

```
Users may write in Tanglish: Tamil in English letters, mixed with English words.
Interpret the intent carefully. Reply in clear, simple English unless the user
asks for Tamil. If a message is ambiguous, ask a short clarifying question.
```

Then test what actually comes back. It's worth asking your real users what they prefer, since some want replies in the same casual Tanglish, while others want clean English or Tamil script for anything important.

## Practical Tips for Building With Tanglish

- **Test on real messages,** with users' consent and privacy in mind. Synthetic examples are too tidy.
- **Tell the model what Tanglish is** in the system prompt, and add a few short examples mapping Tanglish messages to their intent.
- **Try a pivot step.** Some systems first translate or normalize the user's message into clear English, then process it. This can help, but adds cost and can lose nuance, so evaluate it rather than assuming.
- **For RAG, test retrieval separately.** If users type Tanglish queries against English documents, check whether the right chunks come back. Use a multilingual embedding model, as discussed in the embeddings post, and consider rewriting the query into English before searching.
- **Prefer clarifying questions to guesses** when intent is unclear, especially before consequential actions, in line with the human-in-the-loop post.
- **Don't assume Indic-specialized models handle romanized text well.** Research suggests many do better in native script than in romanized form, so test candidates on your own data.
- **Test safety in Tanglish too.** Filters and guardrails built mainly on English may behave differently on mixed-language input, which matters for the defenses discussed in the prompt injection post.
- **Re-test regularly.** Models change often, and results from last year may not hold.
- **Consider the cost trade-off.** Romanized text generally needs fewer tokens than Tamil script, which is one practical argument for supporting it, *if* the model understands it well enough.

## What to Be Careful Not to Claim

When you write up your own results, be honest about their limits:

- A small test set tells you about *your* sample, not about "LLMs" in general
- Results depend on the specific model, version, and settings
- Your Tanglish isn't everyone's Tanglish. Dialect, age, region, and personal style vary
- Passing a test shows a model *can* handle something, not that it always will

This is the same humility that applies to any evaluation, and it's especially important for languages where there's less formal benchmarking to lean on.

## Quick Takeaways

- Tanglish combines **code-mixing** and **romanization**, and both make life harder for models
- Challenges include inconsistent spelling, English words with Tamil suffixes, local slang, and limited training data
- Research suggests romanized code-mixed text is a known weak spot, with performance usually dropping as mixing increases, but results vary by model and are improving
- Mixing English into prompts can sometimes help, since English words act as familiar anchors
- The best way to know is to test: same question in English, Tanglish, and Tamil script, run several times
- Define a reply-language policy, and test the replies as well as the understanding
- Use real user messages, native speakers, and honest caveats

## Closing Thought

Tanglish is how a huge number of people naturally type, which makes it far too important to treat as an edge case. Models are getting better at it, but "seems to work when I try it" is not the same as "works for our users." A small, honest test, with the same question asked three ways and results compared, will tell you more than any benchmark. And whatever you find, the exercise is worth doing, because the people most likely to be left behind by AI products are exactly the ones who don't write the way the training data does.