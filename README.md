# RepoZen
An AI system that digests repo's and uses agents to explain modules, generate features, write tests and detect bugs. Making easy the struggle to understand large, legacy and unfamiliar codebases.

Frontend (Vercel + React)
   ↓
FastAPI (Async APIs)
   ↓
Clerk (Auth)
   ↓
-----------------------------
|  Agent Layer (LangGraph)  |
-----------------------------
   ↓
Memory (Redis)
   ↓
RAG Pipeline (PageIndexing)
   ↓
LLM (OpenRouter)
   ↓
-----------------------------
| Observability Layer       |
| Langfuse + PostHog        |
-----------------------------
   ↓
Caching Layer (Redis)