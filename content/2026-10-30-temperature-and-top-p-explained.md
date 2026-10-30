Title: Temperature and Top-p Explained: Why Your AI Sounds Different Each Time
Date: 2027-04-18
Category: Beginner Guide
Tags: GenAI, LLM, temperature, top-p, sampling, beginner
Slug: temperature-and-top-p-explained

## The Question That Started This

I once asked the same question to the same model twice and got two noticeably different answers. My first thought was that something was broken. It wasn't. That variation is a feature, controlled by a couple of settings you've probably seen in every LLM API without fully understanding: **temperature** and **top-p**.

Most explanations stop at "temperature controls creativity." That's a useful starting point, but it hides what's really going on. This post goes one level deeper, without any heavy math.

## First, How an LLM Picks Its Next Word

As covered in the earlier post on what happens inside an LLM, the model generates text one token at a time. At each step, it doesn't pick a single "correct" next token. It produces a **probability for every token in its vocabulary**.

For example, after "The sky is," the model might assign:

```
blue     60%
clear    20%
grey     12%
falling   5%
purple    3%
```

Then something has to **choose** one token from that list. That choosing step is called **sampling**, and temperature and top-p are the two main dials that control it.

Two ways it could choose:

- **Always take the top option** ("blue" every time): predictable, but repetitive
- **Pick randomly, weighted by probability:** "blue" most of the time, but sometimes "clear" or "grey"

Most chat apps use something close to the second approach, which is why you get different wording on different runs.

## Temperature: Sharpening or Flattening the Odds

Temperature reshapes the probability distribution **before** a token is chosen.

- **Low temperature** makes the distribution sharper. The likely options become even more likely, and unlikely ones nearly vanish.
- **High temperature** makes it flatter. Unlikely options get a bigger share, so surprising choices become more common.

Using the same example, here's roughly what happens (illustrative numbers computed from the distribution above):

```
Original (temperature = 1):
blue 60%  | clear 20%  | grey 12%  | falling 5%   | purple 3%

Low temperature (0.5):
blue 86%  | clear 10%  | grey 3%   | falling 0.6% | purple 0.2%

High temperature (2.0):
blue 39%  | clear 23%  | grey 18%  | falling 11%  | purple 9%
```

At low temperature, "blue" dominates, so outputs are consistent. At high temperature, even "purple" has a real chance, so outputs get more varied, and sometimes stranger.

If you're curious how this works, here's a small experiment:

```python
def apply_temperature(probs, T):
    scaled = [p ** (1 / T) for p in probs]
    total = sum(scaled)
    return [s / total for s in scaled]

probs = [0.60, 0.20, 0.12, 0.05, 0.03]
print(apply_temperature(probs, 0.5))   # sharper
print(apply_temperature(probs, 2.0))   # flatter
```

(Real models apply temperature to raw scores called logits before converting them to probabilities, but the effect on the final distribution is the same idea.)

## What About Temperature = 0?

As temperature approaches zero, the model essentially always picks the single most likely token. This is called **greedy decoding**, and it makes output much more consistent.

But "consistent" isn't the same as "perfectly identical every time." Hosted APIs can still show small variations at temperature 0 because of how computations are run behind the scenes. And "consistent" definitely doesn't mean "correct": a model can confidently repeat the same wrong answer every single time. The earlier posts on hallucinations apply here. Low temperature reduces randomness, not mistakes.

## Top-p: Cutting Off the Unlikely Tail

Top-p, also called **nucleus sampling**, takes a different approach. Instead of reshaping the probabilities, it **limits which tokens are even allowed** to be chosen.

The rule: sort tokens from most to least likely, and keep adding them to a "safe list" until their combined probability reaches p. Everything outside that list is discarded, and the model samples only from what's left.

With our example and `top_p = 0.9`:

```
blue     60%   running total: 60%
clear    20%   running total: 80%
grey     12%   running total: 92%   <- reaches 90%, stop here
falling   5%   (excluded)
purple    3%   (excluded)
```

The model now samples only from blue, clear, and grey (with their probabilities rescaled to add up to 100%). The oddball options "falling" and "purple" can never be chosen.

The clever part is that top-p **adapts to the situation**:

- When the model is very confident (one token has 95%), the safe list might contain just that one token.
- When the model is uncertain (many reasonable options), the list grows to include more of them.

A fixed rule like "always keep the top 5 tokens" can't do that, which is why top-p became popular.

## A Quick Word on Top-k

You may also see **top-k** in some APIs and local tools. It's simpler: keep only the k most likely tokens (say, 40), and sample from those. It works, but unlike top-p it doesn't adjust to how confident the model is. Some tools offer both, and not every provider exposes it.

## Temperature vs Top-p: What's the Difference?

A simple way to remember it:

- **Temperature** changes **how likely** each option is (reshapes the odds)
- **Top-p** changes **which options are allowed** (trims the list)

Both reduce or increase variety, just through different mechanisms. Because they overlap in purpose, a common recommendation is to **adjust one and leave the other at its default**, rather than tuning both at once. Changing both makes it hard to tell what caused a difference. Check your provider's guidance, since it varies.

## Where These Settings Show Up in Code

Most APIs expose them as simple parameters. For example, with an OpenAI-style call:

```python
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Suggest a name for a coffee shop."}],
    temperature=0.9,
)
```

A couple of practical notes:

- **Valid ranges differ by provider.** Some allow temperature up to 2, others cap it at 1, so check the docs.
- **Some models restrict or fix these settings,** and may ignore your values. This is increasingly common with certain newer models, so don't assume every model honors them.

## Choosing Settings for Your Task

There's no universal best value, but these starting points work well in practice:

- **Extraction, classification, structured JSON output:** low (around 0 to 0.3). You want consistency. This pairs naturally with the earlier post on structured outputs.
- **Question answering over documents (RAG):** low. You want the model to stick to the retrieved facts, not improvise.
- **Code generation:** low to moderate. Correctness usually matters more than variety.
- **General chat and explanations:** moderate (often around 0.5 to 0.8).
- **Brainstorming, names, taglines, creative writing:** higher (0.8 and up), where variety is the point.

Treat these as starting points, then test. The right setting depends on your model and your task.

## Common Myths

- **"Temperature is the creativity dial."** Partly true, but really it's a randomness dial. Higher randomness can produce fresh ideas, or just nonsense.
- **"Temperature 0 means the model is always right."** No, it just means it's consistently picking its top guess.
- **"Higher temperature makes the model smarter or more thoughtful."** It doesn't. It only changes how it samples.
- **"Different answers mean the model is unreliable."** Variation is built into sampling. What matters is whether the answers are *acceptably* varied for your use case.

## Why This Matters When You Build

Understanding sampling helps with real problems:

- **Testing and evals.** Since output varies, run each test case several times, as covered in the earlier post on building an eval set. A single run can mislead you.
- **Consistency.** If your app needs repeatable behavior, lower the temperature and still validate the output.
- **Why models differ.** The earlier post on why different LLMs give different answers listed randomness as one reason, and now you know the mechanism.
- **Debugging weird outputs.** If a model produces strange or off-topic text, an overly high temperature is one of the first things worth checking.

## Closing Thought

Temperature and top-p aren't magic creativity knobs. They're two ways of controlling how a model chooses from its list of likely next tokens: one reshapes the odds, the other trims the list. Once you see that, the variation between runs stops being mysterious, and you can pick settings on purpose instead of copying defaults. And if you remember just one thing, remember this: lowering randomness makes output more consistent, but it never makes it more correct.