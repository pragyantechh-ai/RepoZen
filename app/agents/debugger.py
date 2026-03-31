"""
Debug Agent: Finds bugs, issues, and suggests fixes.

Receives:
  - User's bug report or debugging question
  - Execution plan from the Planner
  - Retrieved code context from the Retriever

Performs:
  - Logic error detection (wrong conditions, off-by-one, bad return values)
  - Type safety analysis (missing checks, unsafe casts)
  - Null/None reference detection (unhandled None, missing guards)
  - Edge case analysis (empty inputs, boundaries, error paths)
  - Security issue detection (injection, hardcoded secrets, unsafe ops)
  - Import/dependency validation (missing imports, circular deps)
  - Performance issue detection (N+1 queries, unnecessary loops)

Produces:
  - List of categorized bug reports with severity
  - Concrete suggested fix for each bug
  - Overall risk assessment
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from base_agent import BaseAgent


# ── Structured Output Schemas ────────────────────────────────────────

class BugReport(BaseModel):
    """A single identified issue."""

    file_path: str = Field(
        description="Relative path of the file where the issue exists"
    )
    line_range: str = Field(
        description="Approximate line range of the issue, e.g. '45-52' or '12'"
    )
    severity: str = Field(
        description="One of: critical, warning, info"
    )
    category: str = Field(
        description=(
            "One of: logic_error, type_error, null_reference, "
            "race_condition, security, performance, style, "
            "import_error, edge_case, error_handling, other"
        )
    )
    title: str = Field(
        description="Short one-line title for the issue"
    )
    description: str = Field(
        description="Detailed description of the bug and why it is a problem"
    )
    code_snippet: str = Field(
        description="The exact problematic code from the context"
    )
    suggested_fix: str = Field(
        description="The corrected code that resolves the issue"
    )
    explanation: str = Field(
        description="Why the suggested fix resolves the issue"
    )


class DebugOutput(BaseModel):
    """Complete output from the Debug Agent."""

    bugs: List[BugReport] = Field(
        description="List of identified issues, ordered by severity (critical first)"
    )
    overall_assessment: str = Field(
        description="Summary paragraph of the code's health and main concerns"
    )
    risk_level: str = Field(
        description="One of: low, medium, high, critical"
    )
    positive_observations: List[str] = Field(
        description="Things the code does well (good patterns, proper error handling, etc.)"
    )


# ── Prompts ──────────────────────────────────────────────────────────

DEBUG_SYSTEM_PROMPT = """\
You are a senior debugging specialist acting as a debug agent for a code \
analysis system called RepoZen.

Your job: carefully analyze the provided code and find real, actionable bugs.

## What to Look For

### 🔴 Critical Issues
- **Logic errors**: wrong conditions, inverted booleans, off-by-one, incorrect return values
- **Null/None references**: accessing attributes on potentially None values without guards
- **Security vulnerabilities**: SQL injection, command injection, hardcoded secrets/keys, \
  path traversal, unsafe deserialization
- **Data loss risks**: silent exception swallowing, missing transaction rollbacks
- **Race conditions**: shared mutable state without synchronization

### 🟡 Warnings
- **Type errors**: wrong argument types, unsafe casts, missing type checks
- **Edge cases**: unhandled empty inputs, boundary values, negative numbers, unicode
- **Error handling**: bare except clauses, catching too broadly, missing error propagation
- **Import errors**: missing imports, importing from wrong module, circular dependencies
- **Resource leaks**: unclosed files/connections, missing context managers

### 🔵 Info
- **Performance**: N+1 queries, unnecessary loops, redundant computations, large memory usage
- **Style**: inconsistent naming, dead code, overly complex logic that could be simplified
- **Best practices**: missing docstrings on public APIs, magic numbers, god functions

## Rules
1. **Be precise** — reference exact line numbers and copy the exact code snippet
2. **Be actionable** — every bug MUST have a concrete, working suggested_fix
3. **Be honest** — if the code looks correct, say so. Don't invent phantom bugs.
4. **Prioritize** — order bugs by severity (critical → warning → info)
5. **Don't nitpick** — don't report style preferences as critical issues
6. **Focus on user's concern** — if the user asked about a specific issue, analyze that first
7. **Include positive observations** — note good patterns you see in the code

For the suggested_fix field, provide the COMPLETE corrected code snippet \
(not just the changed line). It should be a drop-in replacement.

Respond with ONLY valid JSON matching the schema. No markdown fences, no explanation outside JSON.
"""

DEBUG_USER_PROMPT = """\
## User's Bug Report / Debugging Question
{query}

## Execution Plan Context
Intent: debugging
Target files: {target_files}
Target symbols: {target_symbols}
Sub-tasks:
{sub_tasks}

## Retrieved Code to Analyze
{context}

Analyze the code thoroughly and report all findings as JSON:
"""


# ── Agent Implementation ─────────────────────────────────────────────

class DebugAgent(BaseAgent):
    """Analyzes code for bugs, issues, and anti-patterns."""

    def __init__(self):
        super().__init__(temperature=0.1)  # Low temp = precise, consistent analysis
        self.parser = JsonOutputParser(pydantic_object=DebugOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", DEBUG_SYSTEM_PROMPT),
            ("human", DEBUG_USER_PROMPT),
        ])

    def run(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str,
    ) -> Dict[str, Any]:
        """
        Analyze code for bugs and issues.

        Args:
            query:   User's bug report or debugging question.
            plan:    Execution plan from PlannerAgent.
            context: Retrieved code context from RetrieverAgent.

        Returns:
            Dict with keys:
              bugs                  – List of BugReport dicts
              overall_assessment    – Summary of code health
              risk_level            – low / medium / high / critical
              positive_observations – Good things about the code
        """
        # Format plan details for the prompt
        target_files_str = ", ".join(plan.get("target_files", [])) or "(not specified)"
        target_symbols_str = ", ".join(plan.get("target_symbols", [])) or "(not specified)"

        sub_tasks = plan.get("sub_tasks", [])
        sub_tasks_str = "\n".join(
            f"  {i + 1}. {task}" for i, task in enumerate(sub_tasks)
        )

        raw_result = self._invoke_chain(
            self.prompt,
            {
                "query": query,
                "target_files": target_files_str,
                "target_symbols": target_symbols_str,
                "sub_tasks": sub_tasks_str or "  (none specified)",
                "context": context,
            },
            parser=self.parser,
        )

        return self._normalize_output(raw_result)

    def _normalize_output(self, raw: Dict) -> Dict:
        """
        Validate and clean up the LLM output.
        Ensures all fields exist with valid values and bugs are properly sorted.
        """
        valid_severities = {"critical", "warning", "info"}
        valid_categories = {
            "logic_error", "type_error", "null_reference",
            "race_condition", "security", "performance",
            "style", "import_error", "edge_case",
            "error_handling", "other",
        }
        valid_risk_levels = {"low", "medium", "high", "critical"}

        # Severity sort order for prioritization
        severity_order = {"critical": 0, "warning": 1, "info": 2}

        # ── Normalize bugs ───────────────────────────────────────────
        bugs: List[Dict] = []
        for bug in raw.get("bugs", []):
            severity = bug.get("severity", "info").lower().strip()
            if severity not in valid_severities:
                severity = "info"

            category = bug.get("category", "other").lower().strip()
            if category not in valid_categories:
                category = "other"

            bugs.append({
                "file_path": bug.get("file_path", "unknown"),
                "line_range": str(bug.get("line_range", "?")),
                "severity": severity,
                "category": category,
                "title": bug.get("title", "Untitled issue"),
                "description": bug.get("description", ""),
                "code_snippet": bug.get("code_snippet", ""),
                "suggested_fix": bug.get("suggested_fix", ""),
                "explanation": bug.get("explanation", ""),
            })

        # Sort by severity: critical first, then warning, then info
        bugs.sort(key=lambda b: severity_order.get(b["severity"], 99))

        # ── Normalize risk level ─────────────────────────────────────
        risk_level = raw.get("risk_level", "low").lower().strip()
        if risk_level not in valid_risk_levels:
            # Infer from bugs if LLM gave invalid value
            risk_level = self._infer_risk_level(bugs)

        # ── Normalize positive observations ──────────────────────────
        positives = raw.get("positive_observations", [])
        if isinstance(positives, str):
            positives = [positives]
        positives = [str(p) for p in positives if p]

        return {
            "bugs": bugs,
            "overall_assessment": raw.get("overall_assessment", "Analysis complete."),
            "risk_level": risk_level,
            "positive_observations": positives,
        }

    def _infer_risk_level(self, bugs: List[Dict]) -> str:
        """Infer overall risk level from the severity distribution of bugs."""
        if not bugs:
            return "low"

        severities = [b["severity"] for b in bugs]
        critical_count = severities.count("critical")
        warning_count = severities.count("warning")

        if critical_count >= 2:
            return "critical"
        elif critical_count == 1:
            return "high"
        elif warning_count >= 3:
            return "high"
        elif warning_count >= 1:
            return "medium"
        else:
            return "low"

    # ── Utility Methods ──────────────────────────────────────────────

    @staticmethod
    def format_bugs_for_display(result: Dict) -> str:
        """
        Format debug output as a readable markdown report.
        Useful for showing results in the UI.

        Args:
            result: The normalized output dict from run()

        Returns:
            Markdown-formatted bug report
        """
        parts: List[str] = []

        risk = result.get("risk_level", "unknown").upper()
        risk_emoji = {
            "LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"
        }.get(risk, "⚪")

        parts.append(f"## {risk_emoji} Debug Report — Risk: {risk}\n")
        parts.append(f"{result.get('overall_assessment', '')}\n")

        # Positive observations
        positives = result.get("positive_observations", [])
        if positives:
            parts.append("### ✅ Positive Observations")
            for p in positives:
                parts.append(f"- {p}")
            parts.append("")

        # Bug reports
        bugs = result.get("bugs", [])
        if not bugs:
            parts.append("### 🎉 No issues found!")
            return "\n".join(parts)

        severity_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}

        for i, bug in enumerate(bugs, 1):
            emoji = severity_emoji.get(bug["severity"], "⚪")
            parts.append(
                f"### {emoji} Bug {i}: {bug['title']}"
            )
            parts.append(f"**File:** `{bug['file_path']}` | "
                         f"**Lines:** {bug['line_range']} | "
                         f"**Category:** {bug['category']}")
            parts.append(f"\n{bug['description']}\n")

            if bug["code_snippet"]:
                parts.append("**Problematic code:**")
                parts.append(f"```\n{bug['code_snippet']}\n```\n")

            if bug["suggested_fix"]:
                parts.append("**Suggested fix:**")
                parts.append(f"```\n{bug['suggested_fix']}\n```\n")

            if bug["explanation"]:
                parts.append(f"**Why:** {bug['explanation']}\n")

        return "\n".join(parts)

    @staticmethod
    def build_fix_query(original_query: str, result: Dict) -> str:
        """
        Build a query string for the CodeGeneratorAgent based on debug findings.
        Used by the Orchestrator when auto-fixing bugs.

        Args:
            original_query: The user's original question
            result:         The normalized output dict from run()

        Returns:
            A detailed query string the CodeGenerator can act on
        """
        bugs = result.get("bugs", [])
        if not bugs:
            return original_query

        bug_lines: List[str] = []
        for bug in bugs:
            bug_lines.append(
                f"- [{bug['severity'].upper()}] {bug['file_path']} "
                f"(lines {bug['line_range']}): {bug['title']} — {bug['description']}"
            )

        return (
            f"Fix the following bugs found during analysis:\n\n"
            f"{'chr(10)'.join(bug_lines)}\n\n"
            f"For each bug, apply the suggested fix. "
            f"Ensure all fixes are compatible with each other.\n\n"
            f"Original user request: {original_query}"
        )

    @staticmethod
    def get_severity_counts(result: Dict) -> Dict[str, int]:
        """
        Get a count of bugs by severity.

        Args:
            result: The normalized output dict from run()

        Returns:
            Dict like {"critical": 1, "warning": 3, "info": 2}
        """
        counts = {"critical": 0, "warning": 0, "info": 0}
        for bug in result.get("bugs", []):
            sev = bug.get("severity", "info")
            if sev in counts:
                counts[sev] += 1
        return counts