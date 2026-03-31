import logging
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate

from base_agent import BaseAgent, get_llm
from app.agents.planner import PlannerAgent
from app.agents.retriever import RetrieverAgent
from app.agents.generator import CodeGeneratorAgent
from app.agents.debugger import DebugAgent
from app.agents.test_gen import TestGeneratorAgent
from app.agents.validator import ValidatorAgent
from app.services.chunking import PageIndex


logger = logging.getLogger(__name__)


# ── Explanation Prompt (used when intent is explanation / general) ────

EXPLAIN_SYSTEM_PROMPT = """\
You are a helpful code analysis assistant for RepoZen.

Your job: answer the user's question about a code repository using the \
provided code context.

## Rules
- Be specific — reference exact file paths, function names, and line numbers
- Use markdown formatting with code blocks where appropriate
- If the code context doesn't contain enough information, say so honestly
- Structure long answers with headers and bullet points
- When explaining code flow, use numbered steps
- When comparing approaches, use tables
"""

EXPLAIN_USER_PROMPT = """\
## Repository Code Context
{context}

## Previous Conversation
{chat_history}

## User Question
{query}

Provide a clear, detailed answer:
"""


class Orchestrator:
    """
    Coordinates all RepoZen agents to process a user query end-to-end.

    Usage:
        index = PageIndex(pages)
        orchestrator = Orchestrator(index)
        response = orchestrator.process("How does the auth module work?")
    """

    def __init__(self, page_index: PageIndex):
        self.page_index = page_index

        # Initialize all agents
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent(page_index)
        self.code_generator = CodeGeneratorAgent()
        self.debug_agent = DebugAgent()
        self.test_generator = TestGeneratorAgent()
        self.validator = ValidatorAgent()

        logger.info("Orchestrator initialized with all agents")

    def process(
        self,
        query: str,
        chat_history: str = "",
    ) -> Dict[str, Any]:
        """
        Process a user query through the full agent pipeline.

        Args:
            query:        Natural language query from the user.
            chat_history: Formatted string of previous conversation turns.

        Returns:
            Dict with keys:
              plan              – Execution plan from the Planner
              retrieval_stats   – Metadata about code retrieval
              files_referenced  – List of files used in context
              result            – Output from the action agent(s)
              validation        – Validation result (if code was generated)
              agent_trace       – List of agents invoked and their status
        """
        agent_trace: List[Dict[str, Any]] = []

        try:
            # ── Step 1: PLAN ─────────────────────────────────────────
            plan = self._step_plan(query, chat_history, agent_trace)

            # ── Step 2: RETRIEVE ─────────────────────────────────────
            retrieval = self._step_retrieve(query, plan, agent_trace)
            context = retrieval["context"]

            # ── Step 3: EXECUTE (based on intent) ────────────────────
            intent = plan["intent"]
            result = {}

            if intent in ("explanation", "general"):
                result = self._step_explain(query, context, chat_history, agent_trace)

            elif intent == "modification":
                result = self._step_modify(query, plan, context, chat_history, agent_trace)

            elif intent == "debugging":
                result = self._step_debug(query, plan, context, chat_history, agent_trace)

            elif intent == "testing":
                result = self._step_test(query, plan, context, agent_trace)

            else:
                # Unknown intent — fall back to explanation
                logger.warning(f"Unknown intent '{intent}', falling back to explanation")
                result = self._step_explain(query, context, chat_history, agent_trace)

            # ── Step 4: VALIDATE (if code was generated) ─────────────
            validation = self._step_validate(
                result, context, plan, agent_trace
            )

            # ── Assemble final response ──────────────────────────────
            return {
                "plan": plan,
                "retrieval_stats": retrieval["retrieval_stats"],
                "files_referenced": retrieval["files_found"],
                "result": result,
                "validation": validation,
                "agent_trace": agent_trace,
            }

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            agent_trace.append({
                "agent": "orchestrator",
                "status": "error",
                "error": str(e),
            })
            return {
                "plan": None,
                "retrieval_stats": {},
                "files_referenced": [],
                "result": {
                    "type": "error",
                    "content": f"An error occurred while processing your query: {str(e)}",
                },
                "validation": None,
                "agent_trace": agent_trace,
            }

    # ── Pipeline Steps ───────────────────────────────────────────────

    def _step_plan(
        self,
        query: str,
        chat_history: str,
        trace: List[Dict],
    ) -> Dict[str, Any]:
        """Step 1: Classify intent and build execution plan."""
        logger.info("[PLAN] Starting planner agent")

        summary = self.page_index.get_summary()
        file_tree = self.page_index.get_file_tree()

        plan = self.planner.run(
            query=query,
            file_tree=file_tree,
            repo_summary=summary,
            chat_history=chat_history,
        )

        trace.append({
            "agent": "planner",
            "status": "success",
            "intent": plan["intent"],
            "confidence": plan["confidence"],
            "agents_to_invoke": plan["requires_agents"],
            "search_queries": plan["search_queries"],
        })

        logger.info(
            f"[PLAN] Intent: {plan['intent']} "
            f"(confidence: {plan['confidence']:.0%}) | "
            f"Agents: {plan['requires_agents']}"
        )

        return plan

    def _step_retrieve(
        self,
        query: str,
        plan: Dict[str, Any],
        trace: List[Dict],
    ) -> Dict[str, Any]:
        """Step 2: Retrieve relevant code context from the PageIndex."""
        logger.info("[RETRIEVE] Starting retriever agent")

        retrieval = self.retriever.run(plan=plan, query=query)

        trace.append({
            "agent": "retriever",
            "status": "success",
            "candidates": retrieval["retrieval_stats"]["total_candidates"],
            "included": retrieval["retrieval_stats"]["included_in_context"],
            "context_chars": retrieval["retrieval_stats"]["context_chars"],
            "files_found": retrieval["files_found"],
        })

        logger.info(
            f"[RETRIEVE] {retrieval['retrieval_stats']['included_in_context']} pages "
            f"in context ({retrieval['retrieval_stats']['context_chars']:,} chars) | "
            f"Files: {retrieval['files_found']}"
        )

        return retrieval

    def _step_explain(
        self,
        query: str,
        context: str,
        chat_history: str,
        trace: List[Dict],
    ) -> Dict[str, Any]:
        """Step 3a: Answer an explanation/general question with context."""
        logger.info("[EXPLAIN] Generating explanation")

        prompt = ChatPromptTemplate.from_messages([
            ("system", EXPLAIN_SYSTEM_PROMPT),
            ("human", EXPLAIN_USER_PROMPT),
        ])

        llm = get_llm(temperature=0.3)
        chain = prompt | llm

        response = chain.invoke({
            "context": context,
            "chat_history": chat_history or "None",
            "query": query,
        })

        result = {
            "type": "explanation",
            "content": response.content,
        }

        trace.append({
            "agent": "explainer",
            "status": "success",
            "response_length": len(response.content),
        })

        logger.info(f"[EXPLAIN] Generated {len(response.content)} chars")
        return result

    def _step_modify(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str,
        chat_history: str,
        trace: List[Dict],
    ) -> Dict[str, Any]:
        """Step 3b: Generate code modifications."""
        logger.info("[CODEGEN] Starting code generator agent")

        result = self.code_generator.run(
            query=query,
            plan=plan,
            context=context,
            chat_history=chat_history,
        )

        result["type"] = "modification"

        trace.append({
            "agent": "code_generator",
            "status": "success",
            "changes_count": len(result.get("changes", [])),
            "files_changed": [c["file_path"] for c in result.get("changes", [])],
        })

        logger.info(
            f"[CODEGEN] Generated {len(result.get('changes', []))} changes"
        )

        return result

    def _step_debug(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str,
        chat_history: str,
        trace: List[Dict],
    ) -> Dict[str, Any]:
        """Step 3c: Debug → find bugs, then optionally generate fixes."""
        logger.info("[DEBUG] Starting debug agent")

        # Phase 1: Find bugs
        debug_result = self.debug_agent.run(
            query=query,
            plan=plan,
            context=context,
        )

        bug_count = len(debug_result.get("bugs", []))
        severity_counts = DebugAgent.get_severity_counts(debug_result)

        trace.append({
            "agent": "debug",
            "status": "success",
            "bugs_found": bug_count,
            "risk_level": debug_result.get("risk_level", "unknown"),
            "severity_counts": severity_counts,
        })

        logger.info(
            f"[DEBUG] Found {bug_count} bugs | "
            f"Risk: {debug_result['risk_level']} | "
            f"Critical: {severity_counts['critical']}, "
            f"Warning: {severity_counts['warning']}, "
            f"Info: {severity_counts['info']}"
        )

        result = {
            "type": "debugging",
            "debug": debug_result,
            "fixes": None,
        }

        # Phase 2: Auto-generate fixes if bugs were found
        # and code_generator is in the plan
        if bug_count > 0 and "code_generator" in plan.get("requires_agents", []):
            logger.info("[DEBUG→FIX] Generating fixes for found bugs")

            fix_query = DebugAgent.build_fix_query(query, debug_result)

            fix_result = self.code_generator.run(
                query=fix_query,
                plan=plan,
                context=context,
                chat_history=chat_history,
            )

            result["fixes"] = fix_result

            trace.append({
                "agent": "code_generator",
                "status": "success",
                "trigger": "auto_fix_from_debug",
                "changes_count": len(fix_result.get("changes", [])),
            })

            logger.info(
                f"[DEBUG→FIX] Generated {len(fix_result.get('changes', []))} "
                f"fix changes"
            )

        return result

    def _step_test(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str,
        trace: List[Dict],
    ) -> Dict[str, Any]:
        """Step 3d: Generate unit tests."""
        logger.info("[TESTGEN] Starting test generator agent")

        result = self.test_generator.run(
            query=query,
            plan=plan,
            context=context,
        )

        result["type"] = "testing"

        stats = TestGeneratorAgent.get_test_stats(result)

        trace.append({
            "agent": "test_generator",
            "status": "success",
            "test_files": stats["total_files"],
            "test_count": stats["total_tests"],
            "categories": stats["categories"],
        })

        logger.info(
            f"[TESTGEN] Generated {stats['total_tests']} tests "
            f"in {stats['total_files']} files"
        )

        return result

    def _step_validate(
        self,
        result: Dict[str, Any],
        context: str,
        plan: Dict[str, Any],
        trace: List[Dict],
    ) -> Optional[Dict[str, Any]]:
        """
        Step 4: Validate generated code (if any was produced).
        Only runs if the plan includes the validator agent.
        """
        # Check if validator is needed
        if "validator" not in plan.get("requires_agents", []):
            logger.info("[VALIDATE] Skipped — not in plan")
            return None

        # Extract generated code from the result
        generated_code = self._extract_generated_code(result)
        if not generated_code:
            logger.info("[VALIDATE] Skipped — no generated code to validate")
            return None

        logger.info("[VALIDATE] Starting validator agent")

        file_tree = self.page_index.get_file_tree()

        validation = self.validator.run(
            generated_code=generated_code,
            repo_context=context,
            change_summary=plan.get("summary", ""),
            file_tree=file_tree,
        )

        issue_counts = ValidatorAgent.get_issue_counts(validation)

        trace.append({
            "agent": "validator",
            "status": "success",
            "is_valid": validation["is_valid"],
            "confidence": validation["confidence"],
            "issue_counts": issue_counts,
        })

        logger.info(
            f"[VALIDATE] Valid: {validation['is_valid']} "
            f"(confidence: {validation['confidence']:.0%}) | "
            f"Errors: {issue_counts['error']}, "
            f"Warnings: {issue_counts['warning']}, "
            f"Suggestions: {issue_counts['suggestion']}"
        )

        return validation

    # ── Helpers ───────────────────────────────────────────────────────

    def _extract_generated_code(self, result: Dict) -> str:
        """
        Extract all generated code from any agent result so the
        Validator has something to check.

        Handles output shapes from:
          - CodeGeneratorAgent (changes list)
          - DebugAgent → CodeGeneratorAgent (fixes)
          - TestGeneratorAgent (test_files list)
        """
        blocks: List[str] = []

        result_type = result.get("type", "")

        if result_type == "modification":
            # From CodeGeneratorAgent
            blocks.append(
                CodeGeneratorAgent.extract_all_code(result)
            )

        elif result_type == "debugging":
            # From DebugAgent's auto-generated fixes
            fixes = result.get("fixes")
            if fixes:
                blocks.append(
                    CodeGeneratorAgent.extract_all_code(fixes)
                )

        elif result_type == "testing":
            # From TestGeneratorAgent
            blocks.append(
                TestGeneratorAgent.extract_all_test_code(result)
            )

        return "\n\n---\n\n".join(b for b in blocks if b)

    # ── Convenience: Format full response for display ────────────────

    @staticmethod
    def format_response(response: Dict) -> str:
        """
        Format the complete orchestrator response as a readable markdown string.
        Useful for CLI output or simple UI rendering.

        Args:
            response: The full dict returned by process()

        Returns:
            Markdown-formatted string
        """
        parts: List[str] = []

        plan = response.get("plan")
        result = response.get("result", {})
        validation = response.get("validation")
        trace = response.get("agent_trace", [])

        # ── Header ───────────────────────────────────────────────────
        if plan:
            parts.append(
                f"# 🤖 RepoZen — {plan.get('intent', 'unknown').title()}\n"
            )
            parts.append(f"> {plan.get('summary', '')}\n")
        else:
            parts.append("# 🤖 RepoZen Response\n")

        # ── Files Referenced ─────────────────────────────────────────
        files = response.get("files_referenced", [])
        if files:
            parts.append("**Files analyzed:**")
            for f in files:
                parts.append(f"  - `{f}`")
            parts.append("")

        # ── Main Result ──────────────────────────────────────────────
        result_type = result.get("type", "")

        if result_type == "explanation":
            parts.append(result.get("content", ""))

        elif result_type == "modification":
            parts.append(
                CodeGeneratorAgent.format_changes_for_display(result)
            )

        elif result_type == "debugging":
            debug_data = result.get("debug", {})
            parts.append(DebugAgent.format_bugs_for_display(debug_data))

            fixes = result.get("fixes")
            if fixes:
                parts.append("\n---\n")
                parts.append("## 🔧 Auto-Generated Fixes\n")
                parts.append(
                    CodeGeneratorAgent.format_changes_for_display(fixes)
                )

        elif result_type == "testing":
            parts.append(
                TestGeneratorAgent.format_tests_for_display(result)
            )

        elif result_type == "error":
            parts.append(f"## ⚠️ Error\n\n{result.get('content', '')}")

        # ── Validation ───────────────────────────────────────────────
        if validation:
            parts.append("\n---\n")
            parts.append(
                ValidatorAgent.format_validation_for_display(validation)
            )

        # ── Agent Trace ──────────────────────────────────────────────
        if trace:
            parts.append("\n---\n")
            parts.append("<details><summary>🔍 Agent Trace</summary>\n")
            for step in trace:
                agent = step.get("agent", "?")
                status = step.get("status", "?")
                emoji = "✅" if status == "success" else "❌"
                parts.append(f"  {emoji} **{agent}** — {status}")

                # Show interesting metadata
                for key, val in step.items():
                    if key not in ("agent", "status"):
                        parts.append(f"    - {key}: `{val}`")
            parts.append("\n</details>")

        return "\n".join(parts)