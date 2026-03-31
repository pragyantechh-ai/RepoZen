"""
Validator Agent: Ensures generated code is correct and consistent.

Receives:
  - Generated/modified code from CodeGenerator, DebugAgent, or TestGenerator
  - Existing repository context from the Retriever
  - Repository file tree

Validates:
  1. Syntax correctness — valid language constructs, bracket matching
  2. Import validity — referenced modules exist in repo or are standard/third-party
  3. Style consistency — naming conventions, patterns match existing code
  4. Non-regression — existing functionality is not accidentally removed
  5. Type safety — basic type consistency checks
  6. Completeness — no placeholder code, no unfinished implementations
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from base_agent import BaseAgent


# ── Structured Output Schemas ────────────────────────────────────────

class ValidationIssue(BaseModel):
    """A single validation finding."""

    file_path: str = Field(
        description="File where the issue was found"
    )
    issue_type: str = Field(
        description=(
            "One of: syntax_error, import_error, style_mismatch, "
            "regression, type_error, missing_dependency, "
            "incomplete_code, logic_concern, naming_issue"
        )
    )
    severity: str = Field(
        description="One of: error, warning, suggestion"
    )
    line_reference: str = Field(
        description="Approximate line number or range in the generated code"
    )
    description: str = Field(
        description="Clear description of the validation issue"
    )
    suggested_fix: str = Field(
        description="How to fix it. Empty string if just informational"
    )


class ValidatorOutput(BaseModel):
    """Complete output from the Validator agent."""

    is_valid: bool = Field(
        description="True if code passes all critical checks (no 'error' severity issues)"
    )
    issues: List[ValidationIssue] = Field(
        description="List of all validation findings, ordered by severity"
    )
    summary: str = Field(
        description="Overall validation summary — one paragraph"
    )
    confidence: float = Field(
        description="Confidence in the validation result (0.0-1.0)"
    )
    checks_performed: List[str] = Field(
        description="List of validation checks that were performed"
    )


# ── Prompts ──────────────────────────────────────────────────────────

VALIDATOR_SYSTEM_PROMPT = """\
You are a meticulous code reviewer acting as a validation agent for a code \
analysis system called RepoZen.

Your job: validate generated or modified code against the existing repository \
to ensure it is correct, consistent, and safe to apply.

## Validation Checks (perform ALL of these)

### 1. Syntax Correctness [CRITICAL]
- Valid language syntax — brackets, parentheses, quotes all balanced
- Proper indentation (especially Python)
- No truncated or incomplete statements
- Valid string formatting and f-strings

### 2. Import Validity [CRITICAL]
- All imported modules exist either:
  - In the repository (check file tree)
  - As Python standard library modules
  - As common third-party packages (requests, fastapi, pydantic, etc.)
- Import paths match the project structure
- No circular imports introduced

### 3. Style Consistency [WARNING]
- Variable/function naming matches repo conventions (snake_case vs camelCase)
- Indentation style matches (spaces vs tabs, 2 vs 4 spaces)
- Docstring style matches (Google, NumPy, or Sphinx)
- File organization matches existing patterns

### 4. Non-Regression [CRITICAL]
- Existing public functions/classes are not accidentally removed
- Function signatures are not changed in breaking ways
- Return types remain compatible
- Error handling is not weakened

### 5. Type Safety [WARNING]
- Function arguments match expected types from call sites
- Return values match declared return types
- No obvious type mismatches in assignments

### 6. Completeness [ERROR]
- No placeholder comments like "TODO: implement", "pass", "..."
- No incomplete function bodies
- All referenced helper functions/classes exist or are being created

## Severity Rules
- **error**: Blocks deployment. Syntax errors, missing imports, broken functionality.
- **warning**: Should be fixed. Style issues, potential type problems, weak patterns.
- **suggestion**: Nice to have. Alternative approaches, minor improvements.

## Decision Rule for is_valid
- `true` → Zero "error" severity issues. Warnings and suggestions are OK.
- `false` → One or more "error" severity issues found.

## Important
- Be practical — don't fail code for minor style preferences
- If you're uncertain, use "warning" not "error"
- Check imports carefully against the file tree
- Note what checks you performed in checks_performed

Respond with ONLY valid JSON matching the schema. No markdown fences, no explanation outside JSON.
"""

VALIDATOR_USER_PROMPT = """\
## Existing Repository Context (surrounding code)
{repo_context}

## Generated / Modified Code to Validate
{generated_code}

## What Was Changed
{change_summary}

## Repository File Tree
{file_tree}

Validate the generated code thoroughly and respond as JSON:
"""


# ── Agent Implementation ─────────────────────────────────────────────

class ValidatorAgent(BaseAgent):
    """Validates generated code for correctness and repo consistency."""

    def __init__(self):
        super().__init__(temperature=0.0)  # Fully deterministic for validation
        self.parser = JsonOutputParser(pydantic_object=ValidatorOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", VALIDATOR_SYSTEM_PROMPT),
            ("human", VALIDATOR_USER_PROMPT),
        ])

    def run(
        self,
        generated_code: str,
        repo_context: str,
        change_summary: str,
        file_tree: List[str],
    ) -> Dict[str, Any]:
        """
        Validate generated code against the repository.

        Args:
            generated_code: Code produced by CodeGenerator / TestGenerator / DebugAgent.
            repo_context:   Existing code context retrieved from the repo.
            change_summary: Description of what was changed (from the plan or generator).
            file_tree:      List of file paths in the repository.

        Returns:
            Dict with keys:
              is_valid          – True if no critical errors found
              issues            – List of ValidationIssue dicts
              summary           – Overall validation summary
              confidence        – 0.0-1.0 confidence score
              checks_performed  – List of checks that were run
        """
        # Cap file tree to avoid token overflow
        tree_str = "\n".join(f"  {f}" for f in file_tree[:150])
        if len(file_tree) > 150:
            tree_str += f"\n  ... and {len(file_tree) - 150} more files"

        raw_result = self._invoke_chain(
            self.prompt,
            {
                "repo_context": repo_context,
                "generated_code": generated_code,
                "change_summary": change_summary or "(no summary provided)",
                "file_tree": tree_str,
            },
            parser=self.parser,
        )

        return self._normalize_output(raw_result)

    def _normalize_output(self, raw: Dict) -> Dict:
        """Validate and clean up the LLM output."""
        valid_issue_types = {
            "syntax_error", "import_error", "style_mismatch",
            "regression", "type_error", "missing_dependency",
            "incomplete_code", "logic_concern", "naming_issue",
        }
        valid_severities = {"error", "warning", "suggestion"}
        severity_order = {"error": 0, "warning": 1, "suggestion": 2}

        # ── Normalize issues ─────────────────────────────────────────
        issues: List[Dict] = []
        has_errors = False

        for issue in raw.get("issues", []):
            severity = issue.get("severity", "warning").lower().strip()
            if severity not in valid_severities:
                severity = "warning"
            if severity == "error":
                has_errors = True

            issue_type = issue.get("issue_type", "logic_concern").lower().strip()
            if issue_type not in valid_issue_types:
                issue_type = "logic_concern"

            issues.append({
                "file_path": issue.get("file_path", "unknown"),
                "issue_type": issue_type,
                "severity": severity,
                "line_reference": str(issue.get("line_reference", "?")),
                "description": issue.get("description", ""),
                "suggested_fix": issue.get("suggested_fix", ""),
            })

        # Sort: errors first, then warnings, then suggestions
        issues.sort(key=lambda i: severity_order.get(i["severity"], 99))

        # ── Determine is_valid ───────────────────────────────────────
        # LLM's opinion, but override if it contradicts the issues
        llm_valid = raw.get("is_valid", True)
        actual_valid = not has_errors

        # Trust the issue analysis over the LLM's boolean
        is_valid = actual_valid

        # ── Normalize confidence ─────────────────────────────────────
        confidence = raw.get("confidence", 0.7)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.7
        confidence = min(max(confidence, 0.0), 1.0)

        # ── Normalize checks performed ───────────────────────────────
        checks = raw.get("checks_performed", [])
        if isinstance(checks, str):
            checks = [checks]
        checks = [str(c) for c in checks if c]

        # Default checks if LLM didn't list them
        if not checks:
            checks = [
                "syntax_check",
                "import_validation",
                "style_consistency",
                "regression_check",
                "type_safety",
                "completeness_check",
            ]

        return {
            "is_valid": is_valid,
            "issues": issues,
            "summary": raw.get("summary", "Validation complete."),
            "confidence": confidence,
            "checks_performed": checks,
        }

    # ── Utility Methods ──────────────────────────────────────────────

    @staticmethod
    def format_validation_for_display(result: Dict) -> str:
        """
        Format validation output as a readable markdown report.

        Args:
            result: The normalized output dict from run()

        Returns:
            Markdown-formatted validation report
        """
        parts: List[str] = []

        is_valid = result.get("is_valid", False)
        confidence = result.get("confidence", 0.0)

        if is_valid:
            parts.append(f"## ✅ Validation Passed (confidence: {confidence:.0%})\n")
        else:
            parts.append(f"## ❌ Validation Failed (confidence: {confidence:.0%})\n")

        parts.append(f"{result.get('summary', '')}\n")

        # Checks performed
        checks = result.get("checks_performed", [])
        if checks:
            parts.append("**Checks performed:**")
            for check in checks:
                parts.append(f"  ✓ {check}")
            parts.append("")

        # Issues
        issues = result.get("issues", [])
        if not issues:
            parts.append("### 🎉 No issues found!")
            return "\n".join(parts)

        severity_emoji = {"error": "🔴", "warning": "🟡", "suggestion": "💡"}

        for i, issue in enumerate(issues, 1):
            emoji = severity_emoji.get(issue["severity"], "⚪")
            parts.append(
                f"### {emoji} Issue {i}: {issue['issue_type']}"
            )
            parts.append(
                f"**File:** `{issue['file_path']}` | "
                f"**Line:** {issue['line_reference']} | "
                f"**Severity:** {issue['severity']}"
            )
            parts.append(f"\n{issue['description']}\n")

            if issue["suggested_fix"]:
                parts.append(f"**Fix:** {issue['suggested_fix']}\n")

        return "\n".join(parts)

    @staticmethod
    def get_issue_counts(result: Dict) -> Dict[str, int]:
        """
        Get a count of issues by severity.

        Args:
            result: The normalized output dict from run()

        Returns:
            Dict like {"error": 1, "warning": 2, "suggestion": 3}
        """
        counts = {"error": 0, "warning": 0, "suggestion": 0}
        for issue in result.get("issues", []):
            sev = issue.get("severity", "warning")
            if sev in counts:
                counts[sev] += 1
        return counts

    @staticmethod
    def has_blocking_issues(result: Dict) -> bool:
        """
        Check if there are any error-severity issues that block deployment.

        Args:
            result: The normalized output dict from run()

        Returns:
            True if any error-severity issues exist
        """
        return any(
            issue.get("severity") == "error"
            for issue in result.get("issues", [])
        )