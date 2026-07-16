# MemoryRAG: Adaptive Multi-Memory Retrieval System for Agentic AI

## Project Definition

**MemoryRAG** is an adaptive Retrieval-Augmented Generation (RAG)
framework that organizes knowledge into specialized memory types instead
of storing everything in a single vector database. When a user asks a
question, the system first determines *which type of memory* is most
relevant, retrieves information only from that memory, builds an
optimized context, and finally generates a response.

Unlike traditional RAG systems that perform semantic search across one
collection, MemoryRAG introduces **Adaptive Memory Routing (AMR)**---a
routing layer that intelligently selects the appropriate knowledge
source before retrieval.

------------------------------------------------------------------------

# Core Idea

Traditional RAG

``` text
User Query
      │
      ▼
 Single Vector Database
      │
      ▼
   Top-K Retrieval
      │
      ▼
      LLM
```

MemoryRAG

``` text
User Query
      │
      ▼
Intent Classifier
      │
      ▼
Adaptive Memory Router
      │
 ┌────┼────────┬──────────┬────────────┬──────────────┐
 │    │        │          │            │
 ▼    ▼        ▼          ▼            ▼
Docs Code   Decisions  Workflows  Conversations
 │    │        │          │            │
 └────┴────────┴──────────┴────────────┘
              │
              ▼
      Context Builder
              │
              ▼
             LLM
              │
              ▼
       Memory Updater
```

------------------------------------------------------------------------

# Why It Is Different

Traditional RAG treats every document as equal.

MemoryRAG understands that different questions require different types
of knowledge.

Examples:

**Question** \> Why did we migrate from MongoDB to PostgreSQL?

Memory Selected: - Decision Memory

------------------------------------------------------------------------

**Question** \> Explain our authentication flow.

Memory Selected: - Code Memory - Document Memory

------------------------------------------------------------------------

**Question** \> How do we deploy the backend?

Memory Selected: - Workflow Memory

------------------------------------------------------------------------

# Memory Types

## 1. Document Memory

Stores: - PDFs - Documentation - Notes - Wiki Pages

Purpose: General knowledge retrieval.

------------------------------------------------------------------------

## 2. Code Memory

Stores: - Functions - Classes - APIs - README files - Git commits
(future)

Purpose: Understanding and explaining codebases.

------------------------------------------------------------------------

## 3. Decision Memory

Stores structured engineering decisions.

Example

``` text
Decision:
Move Authentication to JWT

Reason:
Reduce server-side session storage

Alternatives:
Session Authentication

Impact:
Need Refresh Tokens
```

Purpose: Retrieve historical reasoning.

------------------------------------------------------------------------

## 4. Workflow Memory

Stores business or engineering workflows.

Example

``` text
Deploy Backend

↓

Run Tests

↓

Build Docker Image

↓

Push Image

↓

Deploy

↓

Verify Health
```

Purpose: Answer process-related questions.

------------------------------------------------------------------------

## 5. Conversation Memory

Stores important discussions instead of every message.

Purpose: Long-term conversational memory.

------------------------------------------------------------------------

# Tech Stack

## Backend

-   Python 3.12
-   FastAPI

------------------------------------------------------------------------

## Database

PostgreSQL

Tables

-   Users
-   Projects
-   Chats
-   Messages
-   Memories
-   MemoryTypes
-   EmbeddingMetadata

------------------------------------------------------------------------

## Vector Database

Recommended

-   Qdrant

Alternative

-   Chroma

------------------------------------------------------------------------

## Embedding Model

Recommended

-   BAAI/bge-small-en-v1.5

Later

-   BAAI/bge-large-en-v1.5
-   jina-embeddings-v3
-   nomic-embed-text

------------------------------------------------------------------------

## LLM

Development

-   Gemini
-   Groq
-   OpenRouter

Future

-   Any OpenAI-compatible model

------------------------------------------------------------------------

## Frameworks

### LangChain

Used for

-   Document loaders
-   Chunking
-   Embeddings
-   Retrieval

------------------------------------------------------------------------

### LangGraph

Used for

-   Agent workflow
-   Routing
-   State management
-   Multi-step execution

------------------------------------------------------------------------

# Adaptive Memory Router

Initial Implementation

Use an LLM classifier.

Example Prompt

``` text
You are an intent classifier.

Classify the user query into exactly one memory type.

Choices:
- Document
- Code
- Decision
- Workflow
- Conversation

Return only the category.
```

Future Improvement

Replace with a lightweight ML classifier.

------------------------------------------------------------------------

# Context Engineering Pipeline

Instead of

``` text
Retrieve Top-K
```

MemoryRAG performs

``` text
Retrieve

↓

Rank

↓

Filter

↓

Compress

↓

Merge

↓

Generate
```

------------------------------------------------------------------------

# LangGraph Workflow

``` text
Receive Query

↓

Intent Detection

↓

Memory Routing

↓

Retriever

↓

Re-ranking

↓

Context Builder

↓

LLM Response

↓

Memory Update
```

------------------------------------------------------------------------

# Suggested Folder Structure

``` text
memoryrag/

backend/
│
├── api/
├── database/
├── embeddings/
├── graph/
├── memories/
├── models/
├── prompts/
├── retrievers/
├── routers/
├── services/
└── utils/

frontend/

tests/

docker/
```

------------------------------------------------------------------------

# Development Roadmap

## Phase 1

-   Python
-   FastAPI
-   PostgreSQL
-   CRUD APIs

Learning: - Python - FastAPI - SQL

------------------------------------------------------------------------

## Phase 2

-   Authentication
-   Projects
-   Chats

Learning: - Backend Architecture

------------------------------------------------------------------------

## Phase 3

-   Embeddings
-   Qdrant
-   Document Upload

Learning: - Embeddings - Vector Databases

------------------------------------------------------------------------

## Phase 4

-   LangChain
-   Retrieval Pipeline

Learning: - RAG Fundamentals

------------------------------------------------------------------------

## Phase 5

-   Multi-Memory Architecture

Implement: - Document Memory - Code Memory - Decision Memory - Workflow
Memory - Conversation Memory

Learning: - Memory Architecture

------------------------------------------------------------------------

## Phase 6

-   LangGraph

Workflow:

Intent Detection

↓

Memory Routing

↓

Retriever

↓

LLM

↓

Memory Update

Learning: - Agent Workflows

------------------------------------------------------------------------

## Phase 7

-   Prompt Engineering
-   Context Engineering
-   Evaluation

Learning: - Prompt Optimization - Retrieval Optimization

------------------------------------------------------------------------

## Phase 8

-   Git Integration
-   Code Memory
-   Commit Analysis

------------------------------------------------------------------------

# Learning Outcomes

By completing MemoryRAG you will gain hands-on experience with:

-   Python
-   FastAPI
-   REST APIs
-   PostgreSQL
-   Git Integration
-   LLM Fundamentals
-   Prompt Engineering
-   Context Engineering
-   LangChain
-   LangGraph
-   Agent Memory
-   Vector Embeddings
-   Vector Databases
-   Retrieval-Augmented Generation (RAG)
-   Multi-memory system design
-   AI system architecture

------------------------------------------------------------------------

# Future Research Directions

-   Adaptive Memory Routing (AMR)
-   Hybrid Retrieval (Dense + Sparse)
-   Memory Ranking Algorithms
-   Context Compression
-   Automatic Memory Consolidation
-   Retrieval Evaluation Metrics
-   Long-Term Agent Memory
-   Personalized Memory Strategies

------------------------------------------------------------------------

# Vision

MemoryRAG aims to move beyond traditional document-centric RAG by
treating different categories of knowledge as distinct memories. Through
Adaptive Memory Routing, it retrieves the most appropriate information
source before generation, producing more accurate, context-aware, and
explainable responses while remaining modular and extensible for future
research.
