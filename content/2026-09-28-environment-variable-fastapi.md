Title: Environment Variables in FastAPI — Managing Secrets the Right Way
Date: 2027-09-28
Category: Tutorial
Tags: FastAPI, Python, environment-variables, security, pydantic-settings, deployment
Slug: environment-variables-in-fastapi-managing-secrets
status: Published


## Why This Matters

Almost every FastAPI app eventually needs something it shouldn't have hardcoded in the source code: a database URL, an LLM API key, a JWT secret, a third-party service token. When you're building GenAI apps, this shows up on day one, because you can't call an LLM API without a key.

The tempting shortcut is to paste the key straight into your Python file and move on. It works, until you push that file to GitHub and a bot finds it within minutes. This article walks through how to handle secrets properly in FastAPI, from the basics to a clean, production-ready pattern.

## The Problem With Hardcoding Secrets

Here's what many beginners write at first:

```python
from fastapi import FastAPI

app = FastAPI()

OPENAI_API_KEY = "sk-abc123-my-real-secret-key"
DATABASE_URL = "postgresql://admin:password123@localhost/mydb"
```

This causes several problems at once:

- **Secrets end up in version control.** Even if you delete the line later, it stays in your Git history.
- **Different environments need different values.** Your local database isn't your production database, and hardcoding forces you to edit code for every environment.
- **Rotating a key means changing code and redeploying**, instead of just updating a setting.
- **Anyone with access to the code has access to the secrets**, including contractors, open-source contributors, or anyone who forks your repo.

## The Core Idea: Environment Variables

An **environment variable** is a value that lives outside your code, in the environment your program runs in. Your code reads it at runtime instead of containing it.

In Python, the most basic way to read one:

```python
import os

api_key = os.getenv("OPENAI_API_KEY")
```

You set the variable in your shell before running the app:

```bash
export OPENAI_API_KEY="sk-abc123-my-real-secret-key"
uvicorn main:app --port 8000
```

Now the code contains no secret, and the same code can run anywhere with different values injected from outside. That's the whole principle.

## Using a `.env` File for Local Development

Typing `export` commands every time gets old fast. The common solution for local development is a `.env` file: a plain text file in your project root that holds your variables.

```
OPENAI_API_KEY=sk-abc123-my-real-secret-key
DATABASE_URL=postgresql://admin:password123@localhost/mydb
DEBUG=true
```

The most important rule: **add `.env` to your `.gitignore` immediately, before your first commit.**

```
# .gitignore
.env
```

A good companion habit is committing a `.env.example` file with the variable names but fake values, so other developers (and future you) know what needs to be set:

```
# .env.example
OPENAI_API_KEY=your-key-here
DATABASE_URL=postgresql://user:password@localhost/dbname
DEBUG=false
```

## The Clean Way: `pydantic-settings`

You can load `.env` files manually with `python-dotenv`, but FastAPI projects usually go a step further and use **`pydantic-settings`**. Since FastAPI already relies on Pydantic, this fits naturally, and you get validation and type conversion for free.

Install it:

```bash
pip install pydantic-settings
```

Then define a settings class:

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

A few things happen here automatically:

- **Values are read from real environment variables first, then from `.env`.** So in production you can set real environment variables and skip the file entirely.
- **Types are converted and validated.** `debug: bool` will correctly turn the string `"true"` into `True`.
- **Missing required values fail loudly at startup.** If `OPENAI_API_KEY` isn't set, the app refuses to start with a clear validation error, instead of crashing mysteriously halfway through a request.

That last point is underrated. Failing fast at startup is much better than discovering a missing key when a user hits the endpoint.

## Using Settings Inside FastAPI

The recommended pattern is to load settings once and inject them with FastAPI's dependency system:

```python
# main.py
from functools import lru_cache
from fastapi import Depends, FastAPI
from config import Settings

app = FastAPI()

@lru_cache
def get_settings() -> Settings:
    return Settings()

@app.get("/info")
def info(settings: Settings = Depends(get_settings)):
    return {"debug_mode": settings.debug}
```

Two details worth noting:

- **`@lru_cache`** makes sure the `.env` file is read only once, not on every request.
- **Using `Depends`** makes testing much easier, because you can override the settings dependency in tests instead of manipulating real environment variables.

## Never Return or Log Secrets

Even with perfect storage, secrets can leak through careless code:

```python
# Don't do this
@app.get("/debug")
def debug(settings: Settings = Depends(get_settings)):
    return settings  # exposes every secret in the response
```

A few habits to avoid this:

- **Never return the whole settings object** from an endpoint.
- **Don't log full request headers or config objects**, since they may contain keys or tokens.
- **Use Pydantic's `SecretStr`** for sensitive fields, which masks the value when printed:

```python
from pydantic import SecretStr

class Settings(BaseSettings):
    openai_api_key: SecretStr

# Printing shows '**********'
# Get the real value only when you need it:
key = settings.openai_api_key.get_secret_value()
```

## Handling Secrets in Production

A `.env` file is great for local development, but it's usually not how production should work. Better options depend on where you deploy:

- **Platform environment settings.** Services like Render, Railway, Fly.io, Heroku, and most cloud platforms let you set environment variables in their dashboard or CLI. Your app reads them exactly like local ones.
- **Docker.** Pass variables at runtime with `docker run -e KEY=value` or an `--env-file`, rather than baking secrets into the image.
- **Secret managers.** For larger systems, tools like AWS Secrets Manager, Google Secret Manager, HashiCorp Vault, or Azure Key Vault store secrets centrally with access control, auditing, and rotation.

Whichever you choose, the application code barely changes, because `pydantic-settings` reads from the environment either way. That's the advantage of keeping secrets out of the code in the first place.

## What to Do If a Secret Leaks

It happens to almost everyone eventually. If you accidentally commit a key:

- **Revoke and rotate it immediately.** Generate a new key from the provider and disable the old one. This is the step that actually matters.
- **Don't rely on deleting the commit.** The secret may already be in Git history, forks, or clones, and automated scrapers find exposed keys quickly.
- **Check your provider's usage dashboard** for any activity you don't recognize, especially with LLM APIs, where stolen keys can run up a large bill fast.

## Quick Checklist

- Secrets live in environment variables, never in source code
- `.env` is in `.gitignore` before the first commit
- A `.env.example` documents which variables are needed
- Settings are loaded through `pydantic-settings` with types
- Settings are cached with `lru_cache` and injected with `Depends`
- Sensitive fields use `SecretStr`
- Production uses platform variables or a secret manager, not a committed file
- A leaked key gets rotated immediately, not just deleted

## Closing Thought

Handling secrets properly feels like boring setup work, but it's one of the highest-value habits you can build early. A few lines of `pydantic-settings` configuration protect you from the most common and most expensive beginner mistake in backend development, and it's especially important in GenAI projects, where a leaked API key can turn into a surprise bill very quickly.