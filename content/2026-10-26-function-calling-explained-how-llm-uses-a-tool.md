Title: Function Calling Explained: How an LLM Actually "Uses" a Tool
Date: 2027-04-04
Category: Beginner Guide
Tags: GenAI, LLM, function-calling, tool-use, AI-agents, Python
Slug: function-calling-explained-how-llm-uses-a-tool

## The Misconception I Had

When I first heard that an LLM can "call a function" or "use a tool," I pictured the model reaching out and running code: checking the weather, querying a database, sending an email. It sounded almost magical, and a little scary.

The reality is much simpler, and once you see it, a lot of the agent hype becomes easier to reason about. **The model never runs anything.** It only writes down a request. Your code is the one that actually does the work.

## The One-Sentence Version

Function calling means: you describe some functions to the model, and when it decides one is needed, it replies with a **structured request** ("call this function with these arguments") instead of normal text. Your program runs the function, hands the result back, and the model uses that result to write its final answer.

## Why We Need This at All

An LLM on its own has two big limits:

- **It can't know live information.** It doesn't know today's weather, your order status, or the current stock price. Its knowledge comes from training data with a cutoff.
- **It can't take actions.** Text in, text out. It can't update a database or book a meeting by itself.

Function calling is the bridge. It lets the model say "I need outside help for this" in a format your code can reliably understand.

## The Flow, Step by Step

```
1. You send: the user's question + a list of available tools (names, descriptions, parameters)
2. The model decides: answer directly, OR request a tool call
3. If it requests a tool: it returns the tool name + arguments (as structured data)
4. YOUR code runs the real function with those arguments
5. You send the result back to the model
6. The model reads the result and writes the final answer for the user
```

Let's use a simple example. The user asks: "Should I carry an umbrella in Chennai today?"

- The model can't know today's weather, so it responds with a request like: *call `get_weather` with `city = "Chennai"`*.
- Your code calls a real weather API and gets back something like `{"rain_chance": 72}`.
- You pass that back to the model.
- The model answers: "Yes, there's a high chance of rain, so carry an umbrella."

Notice who did what. The model **decided** a tool was needed and **filled in the arguments**. Your code **executed** it. The model then **explained** the result.

## Step 1: Describe Your Tools

You tell the model what tools exist using a schema, usually JSON Schema. Here's an OpenAI-style example:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city. Use this when the user asks about weather conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. Chennai"
                    }
                },
                "required": ["city"]
            }
        }
    }
]
```

Three parts matter:

- **name:** how the model refers to the tool
- **description:** how the model decides *when* to use it (this is the most important part)
- **parameters:** what inputs the tool needs, and their types

The model never sees your function's code. All it sees is this description. That means the description is effectively a prompt, and vague descriptions lead to wrong or missed tool calls.

## Step 2: Let the Model Request a Call, and Run It Yourself

```python
import json
from openai import OpenAI

client = OpenAI()

def get_weather(city: str) -> dict:
    # Replace with a real weather API call
    return {"city": city, "rain_chance": 72, "temp_c": 29}

messages = [
    {"role": "user", "content": "Should I carry an umbrella in Chennai today?"}
]

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=messages,
    tools=tools,
)

msg = response.choices[0].message

if msg.tool_calls:
    messages.append(msg)  # keep the model's tool request in the history

    for call in msg.tool_calls:
        args = json.loads(call.function.arguments)   # arguments arrive as a JSON string
        result = get_weather(**args)                 # YOUR code runs the function

        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(result),
        })

    final = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
    )
    print(final.choices[0].message.content)
else:
    print(msg.content)  # the model answered directly, no tool needed
```

Key points in this code:

- **`msg.tool_calls`** is how you detect that the model wants a tool. If it's empty, the model just answered in text.
- **Arguments arrive as a JSON string**, which you parse yourself.
- **The result goes back as a `tool` message**, linked to the original request by its ID.
- **A second model call** turns the raw result into a natural-language answer.

Claude's API follows the same idea with different field names: you define tools with an `input_schema`, the model's response contains a `tool_use` block (with an ID, tool name, and input), and you reply with a `tool_result` block referencing that ID. Different shapes, same loop.

## The Model Can Call More Than One Tool

Sometimes the model requests several tools at once, or one after another. For example: look up the user's order, then check shipping status, then answer. In practice, you wrap the steps above in a **loop**:

```
while the model keeps asking for tools:
    run the requested tools
    send the results back
until the model gives a final text answer
```

This loop is the core of what people call an **agent**, which ties back to the earlier post on the difference between an agent and a chatbot. A chatbot answers. An agent runs this loop, deciding the next step based on what each tool returns.

## Why Descriptions Matter So Much

Since the model chooses tools based only on names and descriptions, writing them well is half the job:

- **Say when to use the tool, not just what it does.** "Use this when the user asks about order status" beats "Gets order info."
- **Describe each parameter clearly,** with examples and formats (like date formats).
- **Use enums for limited choices.** If a parameter can only be "celsius" or "fahrenheit," say so in the schema.
- **Keep the tool list small and distinct.** Many overlapping tools confuse the model about which to pick.

## Things That Go Wrong

Function calling is powerful, but it fails in predictable ways:

- **Wrong tool chosen,** usually because descriptions overlap or are vague
- **Bad or invented arguments:** the model fills a parameter with a plausible guess instead of asking the user
- **Missing arguments,** because the user didn't give enough information
- **Tool errors:** the API is down, or returns something unexpected
- **Endless loops,** where the model keeps calling tools without finishing

The earlier post on why agents repeat the same wrong action applies here: return **clear, specific error messages** from your tools, so the model has something concrete to adjust to, and set a **maximum number of tool-call rounds** so a loop can't run forever.

## Safety: Treat the Model's Request as Untrusted Input

This is the part beginners often miss. The arguments the model produces are just generated text. They can be wrong, and if the conversation includes content from untrusted sources (a web page, an email, a document), that content can try to steer the model into calling tools it shouldn't.

Good habits:

- **Validate arguments** in your code, exactly as you would for user input from a web form.
- **Only expose tools you're comfortable with.** An allowlist of narrow functions is safer than a general-purpose "run any command" tool.
- **Require human confirmation for risky actions,** like sending money, deleting data, or emailing customers.
- **Give tools minimal permissions,** so a mistake has a limited blast radius.
- **Be careful with tool results,** since text returned from outside sources can contain instructions aimed at the model.

## Function Calling and Structured Outputs

These two ideas are close relatives. Both rely on the model producing data that matches a schema. Function calling uses that to request an action, while structured outputs use it to return clean, predictable data (like JSON) as the final answer. If you understand one, the other follows easily.

## A Simple Mental Model

Think of the model as a very capable assistant sitting in a room with no internet and no hands. You slide it a list of things you can do on its behalf. When it needs something, it writes a note: "Please look up the weather in Chennai." You do it, slide the result back under the door, and it writes the answer. It never touches the outside world directly. You're always the one acting.

## Closing Thought

"The LLM uses tools" is a convenient phrase, but it hides what's actually happening: the model produces a structured request, and your code decides whether and how to carry it out. That's good news. It means you stay in control of what actually happens, and it means most of the reliability and safety of a tool-using system comes from ordinary engineering: clear descriptions, validated inputs, sensible permissions, and good error handling. Once that clicks, agents stop looking like magic and start looking like a loop you can understand, build, and debug.