Title: Why Port Numbers Under 2000 Are Not Recommended in FastAPI
Date: 2026-09-01
Category: Tutorial
Tags: FastAPI, Python, networking, uvicorn, backend, deployment
Slug: why-port-under-2000-not-recommended-fastapi
status: Published

## Why This Matters

When you're setting up a FastAPI app for the first time, it's tempting to just run `uvicorn main:app --port 80` and call it a day — no need to remember a weird port number, just hit the domain directly. But if you've tried this, you've probably already run into a `PermissionError` or had to run your app with `sudo`.

This isn't a FastAPI limitation. It's how operating systems have handled ports for decades, and understanding it will save you a lot of confusion (and some bad production decisions) down the line.

## The Real Reason: Privileged Ports

On Unix-like systems (Linux, macOS), ports **0–1023** are called **well-known** or **privileged ports**. They're reserved for core system services:

- **Port 21** — FTP
- **Port 22** — SSH
- **Port 25** — SMTP
- **Port 80** — HTTP
- **Port 443** — HTTPS

Only processes running with root/administrator privileges are allowed to bind to these ports. Any regular user process — including your FastAPI/uvicorn app — will be rejected with something like:

```
PermissionError: [Errno 13] Permission denied
```

Ports **1024–2000ish** aren't technically "privileged" in the strict OS sense, but they still fall in a zone that's commonly reserved or auto-assigned by other services, package managers, and legacy tools. Squatting on them increases your chances of silent port collisions.

## Why You Shouldn't Just Use `sudo` to Fix It

Running `sudo uvicorn main:app --port 80` "solves" the permission error, but it creates worse problems:

- **Security risk** — if your app has any vulnerability (a bad dependency, an unsafe eval, an RCE bug), it now runs with root access to the entire machine.
- **File permission chaos** — any files, logs, or cache your app creates while running as root become root-owned, breaking things later when you run as a normal user.
- **Not how production actually works** — no serious deployment runs the application server directly on port 80/443 as root.

## The Actual Best Practice

Run FastAPI on a high, unprivileged port and let a reverse proxy handle the public-facing port:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Common conventions for local dev and internal services:

- **8000** — the FastAPI/Django default
- **8080** — common alternate HTTP port
- **5000** — common Flask-era default (can conflict with macOS AirPlay)

In production, put **Nginx**, **Caddy**, or **Traefik** in front of your app. The proxy binds to port 80/443 (it's designed and hardened for that), and internally forwards traffic to your FastAPI app running on something like port 8000.

```
Client → :443 (Nginx, TLS termination) → :8000 (FastAPI/uvicorn)
```

This gives you:

- No root privileges needed for your app process
- TLS/SSL termination handled by battle-tested software
- Easy load balancing if you scale to multiple FastAPI instances
- Clean separation between "public traffic" and "your app logic"

## Quick Summary

| Port Range | Category | Can a normal user bind to it? |
|---|---|---|
| 0–1023 | Well-known / privileged | No (needs root/admin) |
| 1024–49151 | Registered ports | Yes, but may collide with other services |
| 49152–65535 | Dynamic/private ports | Yes, generally safe |

**Rule of thumb:** run FastAPI on something like `8000`, and let a reverse proxy own port `80`/`443`.

## Wrapping Up

It's a small detail, but it's one of those things every backend developer runs into eventually. Understanding *why* the OS blocks low ports — instead of just running `sudo` to make the error go away — leads to cleaner, safer deployments.