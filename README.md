# RepoZen
An AI system that digests repo's and uses agents to explain modules, generate features, write tests and detect bugs. Making easy the struggle to understand large, legacy and unfamiliar codebases.


## Backend Architecture

POST /api/upload/url  ──→  session_manager.create_session()
                            ──→  BackgroundTask: analyze_repo_background()
                                   ├── clone_repo()
                                   ├── FileParser → parse all files
                                   ├── Chunker → chunk into pages
                                   ├── PageIndex(pages)
                                   └── session.mark_ready(page_index)

GET /api/status/{id}  ──→  session.status  (poll until "ready")

POST /api/chat        ──→  session.orchestrator.process(query)
                              │
                              ├── PlannerAgent.run()
                              │     └── intent + search_queries + agent routing
                              │
                              ├── RetrieverAgent.run()
                              │     └── search PageIndex → build context string
                              │
                              ├── (based on intent)
                              │     ├── explanation → LLM explain with context
                              │     ├── modification → CodeGeneratorAgent.run()
                              │     ├── debugging → DebugAgent.run() → CodeGeneratorAgent.run()
                              │     └── testing → TestGeneratorAgent.run()
                              │
                              └── ValidatorAgent.run()  (if code was generated)

DELETE /api/session/{id}  ──→  cleanup


![Image Alt text](/RepoZen/UI_images/UI_interface.png "UI Interface"))