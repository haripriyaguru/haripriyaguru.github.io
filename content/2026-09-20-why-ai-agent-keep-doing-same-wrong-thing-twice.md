Title: Why The AI Agent Keeps Doing the Same Wrong Thing Twice
Date: 2026-09-20
Category: GenAI
Tags: GenAI, AI-agents, debugging, memory, beginner
Slug: why-the-ai-agent-keeps-doing-the-same-wrong-thing-twice
status: Published

## Why This Happens to Almost Everyone

If you've built or even just used an AI agent for anything beyond a single simple task, you've probably watched it fail at something, then immediately try the exact same failed approach again — sometimes two or three times in a row — instead of learning from the mistake it just made. It's one of the most frustrating and most common agent failure patterns, and understanding why it happens makes it a lot easier to actually fix.

## First, What's Actually Happening Under the Hood

An agent works in a loop: reason about what to do, take an action (like calling a tool), observe the result, then reason again about the next step. In theory, "observe the result" should include noticing that the last action failed. In practice, several things can break that feedback loop:

```
Agent tries Action A → Action A fails → Agent should notice the failure and adjust →
Instead, Agent tries Action A again → fails again → repeat
```

The agent isn't being "stupid" in some general sense — it's a very specific breakdown in how failure information gets fed back into its next decision.

## Reason 1: The Failure Isn't Actually Reaching the Model Clearly

A huge number of these loops come down to something surprisingly mundane: the error message returned by a failed tool call is vague, generic, or buried in a format the model doesn't parse well. If a tool just returns `"Error: 400"` with no explanation, the model has almost nothing useful to reason about — it doesn't know *why* it failed, so it can't meaningfully adjust its next attempt.

Compare that to a tool returning `"Error: missing required field 'user_id' in request"` — now the model has something concrete to correct on the next try.

## Reason 2: The Context Window Pushed the Failure Out

In longer agent runs, older parts of the conversation — including the record of a previous failed attempt — can get pushed out of the context window entirely, especially if the agent has been chugging along through many steps. If the model literally can't "see" that it already tried and failed at something, it has no way to know it's repeating itself.

This ties directly into how context windows work — everything the model reasons over has to actually be present in what it's currently looking at. No hidden memory of earlier steps exists beyond what's explicitly kept in context.

## Reason 3: No Explicit Tracking of "Things Already Tried"

Even when failure information is technically present in the context, the agent's reasoning process might not be structured to actively check "have I tried this exact thing before?" before choosing its next action. Without an explicit mechanism nudging it to compare its next move against its history of attempts, it can default back to whatever seemed like the most statistically reasonable next step — even if that's the same thing it just tried.

## Reason 4: The Model Is Pattern-Matching, Not Truly "Reasoning" About Failure

This connects back to something fundamental about how LLMs work: they're predicting likely next steps based on patterns, not running a genuine causal analysis of "why did this fail and what does that imply." If the failed action still looks like the most plausible next step based on the overall pattern of the conversation, the model can gravitate back toward it — even right after that same action just failed.

## How to Actually Fix This

A few practical techniques that meaningfully reduce this failure pattern:

- **Make tool errors specific and actionable.** Invest in clear, structured error messages from your tools — not just status codes, but enough detail for the model to understand what specifically needs to change.
- **Explicitly track attempt history in the prompt.** Maintain a running list of "actions already tried and their outcomes" and feed that back into the agent's context on every step, rather than relying on it staying visible naturally in a long conversation.
- **Add a repetition check as a guardrail.** Before executing an action, compare it against recent past actions. If the agent is about to repeat something that already failed, force a different reasoning step — explicitly ask it to try a different approach instead of letting it proceed.
- **Set a retry limit with escalation.** After a fixed number of failed attempts at the same action, stop the loop automatically and either ask a human for input or force the agent into a different strategy, rather than letting it spin indefinitely.
- **Summarize failures instead of just logging them.** Instead of dumping raw error logs into context, have the system generate a short, clear summary like "Attempted X twice, both failed due to missing permissions — do not retry X without first checking permissions." This gives the model a much stronger signal than raw logs buried in a long history.

## Why This Matters More Than It Seems

This isn't just an annoying edge case — it's one of the clearest signs of the gap between "looks intelligent in a demo" and "reliable enough for production." A system that can't reliably learn from its own immediate failure, even within a single task, isn't ready to be trusted with anything high-stakes without strong guardrails around it. This is exactly why careful agent design — not just a capable underlying model — determines whether an agent is actually usable in practice.

## Closing Thought

Watching an agent repeat the same failed action feels like watching it "not learn," but it's really a much more specific, fixable problem: failure information not being clear enough, not staying visible in context, or not being explicitly checked against before the next action. Fix those three things, and a huge share of these frustrating loops disappear — not because the model suddenly got smarter, but because it's finally being given the information it needed to not repeat itself in the first place.