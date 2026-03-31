"""
Planner Agent: Understands user intent and creates an execution plan.

Classifies queries into:
  - explanation  → user wants to understand code
  - modification → user wants to change/add/refactor code
  - debugging    → user wants to find and fix bugs
  - testing      → user wants unit tests generated
  - general      → general repo questions (what does this do, list endpoints, etc.)

Outputs a structured plan that downstream agents follow.
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from base_agent import BaseAgent


# ── Structured Output Schema ─────────────────────────────────────────

class ExecutionPlan(BaseModel):
    """Schema that the Planner must return."""

    intent: str = Field(
        description="One of: explanation, modification, debugging, testing, general"
    )
    confidence: float = Field(
        description="How confident the planner is about the classified intent (0.0-1.0)"
    )
    sub_tasks: List[str] = Field(
        description="Ordered list of sub-tasks needed to accomplish the user's goal"
    )
    target_files: List[str] = Field(
        description="File paths or patterns the query likely relates to"
    )
    target_symbols: List[str] = Field(
        description="Function/class/variable names the query likely relates to"
    )
    search_queries: List[str] = Field(
        description="2-4 keyword search queries to find relevant code in the page index"
    )
    requires_agents: List[str] = Field(
        description="Downstream agents to invoke: retriever, code_generator, debug, test_generator, validator"
    )
    summary: str = Field(
        description="One-line summary of what the user wants"
    )


# ── Prompts ──────────────────────────────────────────────────────────

PLANNER_SYSTEM_PROMPT = """\
You are a senior software architect acting as a planning agent for a code \
analysis system called RepoZen.

Your job: analyze a user's query about a code repository and produce a \
structured JSON execution plan.

## Available Information
- Repository file tree (list of all indexed files)
- Repository summary (languages, page counts, structure)

## Intent Categories
1. **explanation** — User wants to understand how code works.
   Examples: "how does auth work?", "explain the retry logic", "what does this class do?"
2. **modification** — User wants to change, add, or refactor code.
   Examples: "add input validation", "refactor into smaller functions", "add a new endpoint"
3. **debugging** — User wants to find or fix bugs.
   Examples: "why does login crash?", "find the null pointer issue", "fix the timeout"
4. **testing** — User wants tests generated.
   Examples: "write tests for the user service", "add unit tests for auth"
5. **general** — General repository questions.
   Examples: "what does this repo do?", "list all API endpoints", "show the tech stack"

## Agent Routing Rules
| Intent       | Agents to invoke                                    |
|-------------|-----------------------------------------------------|
| explanation  | retriever                                           |
| modification | retriever → code_generator → validator              |
| debugging    | retriever → debug → code_generator → validator      |
| testing      | retriever → test_generator → validator              |
| general      | retriever                                           |

## Search Query Guidelines
- Generate 2-4 focused keyword queries that will find the right code pages
- Include function/class names if the user mentions them
- Include domain terms (e.g. "authentication", "database", "routing")
- Keep queries short: 2-5 words each

## Important
- Always include "retriever" as the first agent
- Be precise about target files — use the file tree to find exact paths
- If the user mentions a specific file or function, include it in target_files / target_symbols
- If you cannot determine target files, leave the list empty (the retriever will search)

Respond with ONLY valid JSON matching the schema. No markdown fences, no explanation.
"""

PLANNER_USER_PROMPT = """\
## Repository File Tree
{file_tree}

## Repository Summary
{repo_summary}

## User Query
{query}

## Previous Conversation
{chat_history}

Produce the execution plan as JSON:
"""


# ── Agent Implementation ─────────────────────────────────────────────

class PlannerAgent(BaseAgent):
    """Classifies user intent and creates a structured execution plan."""

    def __init__(self):
        super().__init__(temperature=0.1)  # Low temp = reliable classification
        self.parser = JsonOutputParser(pydantic_object=ExecutionPlan)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", PLANNER_SYSTEM_PROMPT),
            ("human", PLANNER_USER_PROMPT),
        ])

    def run(
        self,
        query: str,
        file_tree: List[str],
        repo_summary: Dict[str, Any],
        chat_history: str = "",
    ) -> Dict[str, Any]:
        """
        Analyze the user query and produce an execution plan.

        Args:
            query:        The user's natural language question or request.
            file_tree:    List of all file paths in the repository index.
            repo_summary: Dict with total_pages, languages, page_types, files.
            chat_history: Formatted string of previous conversation turns.

        Returns:
            Dict matching the ExecutionPlan schema with keys:
              intent, confidence, sub_tasks, target_files, target_symbols,
              search_queries, requires_agents, summary
        """
        # Format file tree — cap at 200 entries to stay within context limits
        tree_str = "\n".join(f"  {f}" for f in file_tree[:200])
        if len(file_tree) > 200:
            tree_str += f"\n  ... and {len(file_tree) - 200} more files"

        # Format repo summary as readable string
        summary_str = (
            f"Languages: {', '.join(repo_summary.get('languages', []))}\n"
            f"Total pages indexed: {repo_summary.get('total_pages', 0)}\n"
            f"Page types: {repo_summary.get('page_types', {})}\n"
            f"Total files: {len(repo_summary.get('files', []))}"
        )

        # Invoke the LLM chain
        raw_result = self._invoke_chain(
            self.prompt,
            {
                "query": query,
                "file_tree": tree_str,
                "repo_summary": summary_str,
                "chat_history": chat_history or "None",
            },
            parser=self.parser,
        )

        # Normalize and validate the plan
        return self._normalize_plan(raw_result)

    def normalize_plan(self, raw: Dict) -> Dict:
        """
        Validate and clean up the LLM output.
        Ensures all fields exist and have valid values.
        """
        # ── Validate intent ──────────────────────────────────────────
        valid_intents = {"explanation", "modification", "debugging", "testing", "general"}
        intent = raw.get("intent", "general").lower().strip()
        if intent not in valid_intents:
            intent = "general"

        # ── Validate and enforce agent routing ───────────────────────
        valid_agents = {"retriever", "code_generator", "debug", "test_generator", "validator"}

        # Use the LLM's agent list but filter invalid entries
        agents = [a for a in raw.get("requires_agents", []) if a in valid_agents]

        # Enforce routing rules as fallback
        if not agents:
            agents = self._default_agents_for_intent(intent)

        # Retriever must always be first
        if "retriever" not in agents:
            agents.insert(0, "retriever")

        # ── Validate confidence ──────────────────────────────────────
        confidence = raw.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = min(max(confidence, 0.0), 1.0)

        # ── Assemble clean plan ──────────────────────────────────────
        return {
            "intent": intent,
            "confidence": confidence,
            "sub_tasks": raw.get("sub_tasks", []),
            "target_files": raw.get("target_files", []),
            "target_symbols": raw.get("target_symbols", []),
            "search_queries": raw.get("search_queries", []),
            "requires_agents": agents,
            "summary": raw.get("summary", ""),
        }

    def default_agents_for_intent(self, intent: str) -> List[str]:
        """Fallback agent routing if the LLM output is missing or invalid."""
        routing = {
            "explanation":  ["retriever"],
            "modification": ["retriever", "code_generator", "validator"],
            "debugging":    ["retriever", "debug", "code_generator", "validator"],
            "testing":      ["retriever", "test_generator", "validator"],
            "general":      ["retriever"],
        }
        return routing.get(intent, ["retriever"])