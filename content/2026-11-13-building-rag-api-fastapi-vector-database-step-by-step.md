Title: Building a RAG API with FastAPI and a Vector Database: Step by Step
Date: 2026-11-13
Category: Tutorial
Tags: GenAI, RAG, FastAPI, vector-database, Python, API, ChromaDB, production
Slug: building-rag-api-fastapi-vector-database-step-by-step

## What We're Building

Retrieval-Augmented Generation (RAG) is the pattern where an LLM answers questions using documents you provide, rather than relying only on what it learned during training. It's the foundation of most real-world AI apps: document Q&A, support bots, knowledge assistants.

This post builds a working RAG API end to end with FastAPI as the server and ChromaDB as the vector database. By the end you'll have a `/ingest` endpoint to load documents and a `/ask` endpoint to query them, with the LLM grounding its answers in what you ingested.

## How RAG Works at a High Level

Before writing any code, the data flow:

**Ingestion (one-time or periodic):**
1. Take your documents (PDFs, text files, web pages, whatever)
2. Split them into chunks
3. Embed each chunk into a vector using an embedding model
4. Store those vectors in a vector database alongside the original text

**Query (every user request):**
1. Embed the user's question using the same embedding model
2. Search the vector database for the chunks whose vectors are closest to the question vector
3. Pass the retrieved chunks + the question to an LLM
4. Return the LLM's answer

The vector search finds semantically similar content, not just keyword matches. That's the key advantage over a plain text search.

## Project Structure

```
rag-api/
  app.py
  prompts/
    rag_answer.txt
  requirements.txt
```

## Dependencies

```
fastapi==0.115.0
uvicorn==0.30.6
chromadb==0.5.15
openai==1.51.0
python-dotenv==1.0.1
```

## The Answer Prompt

Following the rule of keeping prompts in separate files:

```
# prompts/rag_answer.txt

You are a helpful assistant. Answer the user's question using ONLY the context provided below.
If the answer is not in the context, say "I don't have enough information to answer that."
Do not make up facts or use knowledge outside the provided context.

Context:
$context

Question:
$question
```

## The Full API

```python
# app.py

import os
import uuid
from pathlib import Path
from string import Template

import chromadb
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="RAG API")

# --- Clients ---
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="documents",
    metadata={"hnsw:space": "cosine"},
)

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
TOP_K = 5

# --- Load prompt template ---
PROMPT_TEMPLATE = Template(
    Path("prompts/rag_answer.txt").read_text()
)


# --- Request / Response models ---
class IngestRequest(BaseModel):
    documents: list[str]
    ids: list[str] | None = None


class IngestResponse(BaseModel):
    ingested: int
    ids: list[str]


class AskRequest(BaseModel):
    question: str
    top_k: int = TOP_K


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


# --- Embedding helper ---
def embed(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        input=texts,
        model=EMBED_MODEL,
    )
    return [item.embedding for item in response.data]


# --- Routes ---
@app.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest):
    if not request.documents:
        raise HTTPException(status_code=400, detail="No documents provided.")

    ids = request.ids or [str(uuid.uuid4()) for _ in request.documents]

    if len(ids) != len(request.documents):
        raise HTTPException(
            status_code=400,
            detail="Length of ids must match length of documents.",
        )

    vectors = embed(request.documents)
    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=request.documents,
    )
    return IngestResponse(ingested=len(request.documents), ids=ids)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Embed the question and retrieve closest chunks
    question_vector = embed([request.question])[0]
    results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(request.top_k, collection.count() or 1),
        include=["documents"],
    )

    retrieved_docs: list[str] = results["documents"][0] if results["documents"] else []
    if not retrieved_docs:
        raise HTTPException(
            status_code=404,
            detail="No documents found in the database. Ingest some first.",
        )

    context = "\n\n---\n\n".join(retrieved_docs)
    prompt = PROMPT_TEMPLATE.substitute(
        context=context,
        question=request.question,
    )

    response = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    answer = response.choices[0].message.content

    return AskResponse(answer=answer, sources=retrieved_docs)


@app.get("/health")
def health():
    return {"status": "ok", "documents_in_db": collection.count()}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
```

## Trying It Out

Start the server:
```bash
python app.py
```

Ingest a few documents:
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      "FastAPI is a modern Python web framework for building APIs. It uses type hints for validation.",
      "ChromaDB is an open-source vector database designed for AI applications.",
      "RAG stands for Retrieval-Augmented Generation. It combines retrieval with language model generation."
    ]
  }'
```

Ask a question:
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RAG?"}'
```

You'll get back the answer plus the source chunks the LLM used — which is useful both for transparency and for debugging when answers go wrong.

## A Few Things Worth Knowing

**Chunk size matters.** This example ingests each document string as one chunk. In a real pipeline, you'd split larger documents into smaller overlapping chunks (300–500 tokens each is a common range). Too large and the retrieved context is noisy; too small and you lose context around the answer.

**The embedding model must stay consistent.** The model used at ingest time and at query time must be identical. Switching embedding models means re-ingesting everything.

**ChromaDB is local by default.** `PersistentClient` stores data on disk in `./chroma_db`. For production, look at hosted options like Pinecone, Weaviate, or Qdrant — or the Chroma cloud offering.

**Temperature should be low for factual Q&A.** `temperature=0.2` keeps the answer close to what the retrieved context actually says. Higher temperature risks the model getting creative where you want it to be literal.

**`sources` in the response is not just for show.** Returning the source chunks lets callers verify the answer against the original text. This is important for trust in production, and it's the starting point for citation features.

## What to Add Next

A minimal RAG API is a foundation. Things you'd add before going to production:

- Document chunking and overlap (using `langchain` or plain Python)
- Metadata filters on ingestion and retrieval (by source file, date, category)
- Authentication on the `/ingest` endpoint so only trusted callers can add documents
- A deletion endpoint to remove stale documents
- Logging prompt name, version, model, and retrieved chunk IDs on every `/ask` call, as covered in the prompt versioning post

The core loop — embed, store, retrieve, generate — stays the same regardless of how much you build around it.
