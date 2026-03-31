"""
Code Generator Agent: Writes new code or patches existing code.

Receives:
  - User's request
  - Execution plan from the Planner
  - Retrieved code context from the Retriever

Produces structured output with:
  - File path for each change
  - Action type (create / modify / delete)
  - Original code snippet being replaced (for modifications)
  - New code
  - Explanation of why the change was made
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from base_agent import BaseAgent


# ── Structured Output Schemas ────────────────────────────────────────

class CodeChange(BaseModel):
    """A single file change produced by the generator."""

    file_path: str = Field(
        description="Relative path of the file to create or modify"
    )
    action: str = Field(
        description="One of: create, modify, delete"
    )
    original_snippet: str = Field(
        description="The original code being replaced. Empty string for 'create' or 'delete' actions"
    )
    new_code: str = Field(
        description="The new or modified code. Empty string for 'delete' action"
    )
    explanation: str = Field(
        description="Brief explanation of why this change is being made"
    )
    start_line: int = Field(
        description="Approximate start line of the change. 0 for new files"
    )
    end_line: int = Field(
        description="Approximate end line of the change. 0 for new files"
    )


class CodeGeneratorOutput(BaseModel):
    """Complete output from the Code Generator agent."""

    changes: List[CodeChange] = Field(
        description="Ordered list of code changes to apply"
    )
    summary: str = Field(
        description="High-level summary of all changes made"
    )
    notes: List[str] = Field(
        description="Important warnings, assumptions, or follow-up actions"
    )


# ── Prompts ──────────────────────────────────────────────────────────

CODEGEN_SYSTEM_PROMPT = """\
You are an expert software engineer acting as a code generation agent for \
a system called RepoZen.

Your job: produce precise, production-quality code changes based on the \
user's request, the execution plan, and the retrieved repository context.

## Output Rules

### For each change you MUST specify:
- **file_path**: exact relative path (match the paths in the context)
- **action**: "create" (new file), "modify" (change existing), or "delete" (remove file)
- **original_snippet**: for "modify" — include the exact original code being replaced \
  so a diff can be generated. Leave empty ("") for "create" or "delete".
- **new_code**: the replacement / new code. Leave empty ("") for "delete".
- **explanation**: one sentence — why this change is needed.
- **start_line** / **end_line**: approximate line numbers for modifications. 0 for new files.

### Code Quality Rules
1. Match the existing repo style — naming conventions, indentation, patterns
2. Preserve all existing imports unless replacing them
3. Add necessary new imports at the top of the change
4. Include type hints if the repo uses them
5. Add docstrings for new functions and classes
6. Handle edge cases and errors appropriately
7. Never introduce placeholder code like "# TODO: implement"
8. Each change must be syntactically valid and self-contained
9. If modifying a function, include the COMPLETE modified function — not just the changed lines
10. Keep changes minimal — don't rewrite code that doesn't need changing

### When creating new files
- Include all necessary imports
- Match the module structure of the existing project
- Add a module-level docstring

### When modifying existing files
- The original_snippet MUST match the existing code exactly — do not paraphrase it
- Include enough surrounding context so the change can be located unambiguously
- If multiple changes are needed in the same file, list them as separate changes in order

Respond with ONLY valid JSON matching the schema. No markdown fences, no explanation outside JSON.
"""

CODEGEN_USER_PROMPT = """\
## Execution Plan
Intent: {intent}
Summary: {plan_summary}

Sub-tasks:
{sub_tasks}

Target files: {target_files}
Target symbols: {target_symbols}

## Retrieved Code Context
{context}

## User Request
{query}

## Previous Conversation
{chat_history}

Generate the code changes as JSON:
"""


# ── Agent Implementation ─────────────────────────────────────────────

class CodeGeneratorAgent(BaseAgent):
    """Generates new code or modifications based on plan and context."""

    def __init__(self):
        super().__init__(temperature=0.3)  # Slightly creative for code generation
        self.parser = JsonOutputParser(pydantic_object=CodeGeneratorOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CODEGEN_SYSTEM_PROMPT),
            ("human", CODEGEN_USER_PROMPT),
        ])

    def run(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str,
        chat_history: str = "",
    ) -> Dict[str, Any]:
        """
        Generate code changes based on the user's request and repo context.

        Args:
            query:        Original user request.
            plan:         Execution plan from PlannerAgent.
            context:      Retrieved code context from RetrieverAgent.
            chat_history: Formatted previous conversation turns.

        Returns:
            Dict with keys:
              changes  – List of CodeChange dicts
              summary  – High-level summary of all changes
              notes    – Warnings, assumptions, follow-up actions
        """
        # Format sub-tasks as a numbered list
        sub_tasks = plan.get("sub_tasks", [])
        sub_tasks_str = "\n".join(
            f"  {i + 1}. {task}" for i, task in enumerate(sub_tasks)
        )

        # Format target files and symbols
        target_files_str = ", ".join(plan.get("target_files", [])) or "(not specified)"
        target_symbols_str = ", ".join(plan.get("target_symbols", [])) or "(not specified)"

        raw_result = self._invoke_chain(
            self.prompt,
            {
                "intent": plan.get("intent", "modification"),
                "plan_summary": plan.get("summary", ""),
                "sub_tasks": sub_tasks_str or "  (none specified)",
                "target_files": target_files_str,
                "target_symbols": target_symbols_str,
                "context": context,
                "query": query,
                "chat_history": chat_history or "None",
            },
            parser=self.parser,
        )

        return self._normalize_output(raw_result)

    def _normalize_output(self, raw: Dict) -> Dict:
        """
        Validate and clean up the LLM output.
        Ensures every change has all required fields with valid values.
        """
        valid_actions = {"create", "modify", "delete"}

        changes: List[Dict] = []
        for change in raw.get("changes", []):
            action = change.get("action", "modify").lower().strip()
            if action not in valid_actions:
                action = "modify"

            file_path = change.get("file_path", "unknown")
            original_snippet = change.get("original_snippet", "")
            new_code = change.get("new_code", "")
            explanation = change.get("explanation", "")
            start_line = change.get("start_line", 0)
            end_line = change.get("end_line", 0)

            # Sanity checks per action type
            if action == "create":
                original_snippet = ""
                start_line = 0
                end_line = 0
            elif action == "delete":
                new_code = ""
            elif action == "modify":
                # Ensure line range is valid
                if isinstance(start_line, int) and isinstance(end_line, int):
                    if end_line < start_line:
                        end_line = start_line

            changes.append({
                "file_path": file_path,
                "action": action,
                "original_snippet": original_snippet,
                "new_code": new_code,
                "explanation": explanation,
                "start_line": start_line if isinstance(start_line, int) else 0,
                "end_line": end_line if isinstance(end_line, int) else 0,
            })

        # Build notes list — ensure it's always a list of strings
        notes = raw.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        notes = [str(n) for n in notes if n]

        return {
            "changes": changes,
            "summary": raw.get("summary", "Code changes generated."),
            "notes": notes,
        }

    # ── Utility: format changes for display ──────────────────────────

    @staticmethod
    def format_changes_for_display(result: Dict) -> str:
        """
        Format the code generator output as a readable markdown string.
        Useful for showing results in the UI or passing to the Validator.

        Args:
            result: The normalized output dict from run()

        Returns:
            Markdown-formatted string of all changes
        """
        parts: List[str] = []

        parts.append(f"## {result.get('summary', 'Code Changes')}\n")

        for i, change in enumerate(result.get("changes", []), 1):
            action = change["action"].upper()
            file_path = change["file_path"]
            explanation = change["explanation"]

            parts.append(f"### Change {i}: {action} `{file_path}`")
            parts.append(f"> {explanation}\n")

            if change["action"] == "modify" and change["original_snippet"]:
                parts.append("**Original:**")
                parts.append(f"```\n{change['original_snippet']}\n```\n")

            if change["new_code"]:
                parts.append("**New:**")
                parts.append(f"```\n{change['new_code']}\n```\n")

        # Append notes if any
        notes = result.get("notes", [])
        if notes:
            parts.append("### ⚠️ Notes")
            for note in notes:
                parts.append(f"- {note}")

        return "\n".join(parts)

    @staticmethod
    def extract_all_code(result: Dict) -> str:
        """
        Extract all generated/modified code as a single string.
        Used by the Validator agent.

        Args:
            result: The normalized output dict from run()

        Returns:
            Concatenated code string with file headers
        """
        blocks: List[str] = []
        for change in result.get("changes", []):
            code = change.get("new_code", "")
            if code:
                blocks.append(
                    f"// File: {change['file_path']} ({change['action']})\n{code}"
                )
        return "\n\n---\n\n".join(blocks)