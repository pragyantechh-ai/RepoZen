"""
Test Generator Agent: Generates unit tests for code in the repository.

Receives:
  - User's test generation request
  - Execution plan from the Planner
  - Retrieved code context from the Retriever

Produces:
  - Complete, runnable test files with proper imports
  - Coverage targets (which functions/methods are tested)
  - Test descriptions and categories
  - Setup instructions if needed
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.agents.base_agent import BaseAgent


# ── Structured Output Schemas ────────────────────────────────────────

class TestCase(BaseModel):
    """A single test case within a test file."""

    name: str = Field(
        description="Test function name, e.g. 'test_login_empty_email_raises_error'"
    )
    category: str = Field(
        description="One of: happy_path, edge_case, error_case, integration, security"
    )
    description: str = Field(
        description="One-line description of what this test verifies"
    )


class TestFile(BaseModel):
    """A complete generated test file."""

    test_file_path: str = Field(
        description="Relative path for the test file, e.g. 'tests/test_auth.py'"
    )
    source_file_path: str = Field(
        description="Relative path of the file being tested"
    )
    test_framework: str = Field(
        description="Framework used: pytest, unittest, jest, vitest, junit, go_test"
    )
    test_code: str = Field(
        description="Complete test file content — imports, fixtures, all test functions"
    )
    test_cases: List[TestCase] = Field(
        description="List describing each test case in this file"
    )
    coverage_targets: List[str] = Field(
        description="Functions/methods/classes these tests cover"
    )
    requires_mocking: List[str] = Field(
        description="External dependencies that are mocked (e.g. 'database', 'http_client')"
    )


class TestGeneratorOutput(BaseModel):
    """Complete output from the Test Generator agent."""

    test_files: List[TestFile] = Field(
        description="List of generated test files"
    )
    summary: str = Field(
        description="Overview of what is tested and estimated coverage"
    )
    setup_instructions: List[str] = Field(
        description="Steps needed to run the tests (install deps, env vars, etc.)"
    )
    coverage_gaps: List[str] = Field(
        description="Functions or paths that are NOT covered and why"
    )


# ── Prompts ──────────────────────────────────────────────────────────

TESTGEN_SYSTEM_PROMPT = """\
You are an expert test engineer acting as a test generation agent for a code \
analysis system called RepoZen.

Your job: generate comprehensive, immediately runnable unit tests for the \
provided code.

## Test Framework Selection
Match the framework to the language/project:
- **Python** → pytest (preferred). Use unittest only if project already uses it.
- **JavaScript / TypeScript** → jest or vitest (check package.json if available)
- **Java** → JUnit 5
- **Go** → standard testing package
- If unsure, default to the most popular framework for the language.

## Test Structure Rules

### File Organization
- One test file per source file being tested
- Place test files in a `tests/` directory mirroring the source structure
  - Source: `app/services/auth.py` → Test: `tests/services/test_auth.py`
- Include ALL necessary imports at the top
- Group related tests in classes if there are many (pytest classes or unittest.TestCase)

### Test Naming Convention
```
test_<function_name>_<scenario>_<expected_result>
```
Examples:
- `test_login_valid_credentials_returns_token`
- `test_login_empty_email_raises_value_error`
- `test_parse_config_missing_file_returns_default`

### What to Test (Coverage Categories)
1. **happy_path** — Normal expected inputs and behavior
2. **edge_case** — Empty strings, None, zero, boundary values, unicode, very large inputs
3. **error_case** — Invalid inputs, missing required fields, exceptions
4. **integration** — Multiple functions working together (if applicable)
5. **security** — Injection attempts, unauthorized access, malformed data

### Test Quality Rules
1. Each test must have a clear docstring explaining what it verifies
2. Use descriptive assertion messages: `assert result == expected, "Login should return JWT token"`
3. One logical assertion per test (but multiple related asserts are fine)
4. Tests must be independent — no shared mutable state between tests
5. Use fixtures/setup for common test data
6. Mock ALL external dependencies:
   - Database calls → mock the repository/ORM
   - HTTP requests → mock the client
   - File I/O → mock or use tmp_path (pytest)
   - Environment variables → monkeypatch or mock.patch
7. Test code must be syntactically valid and immediately runnable
8. Include type hints in test functions if the source code uses them

### Mocking Guidelines (Python/pytest)
```python
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

@pytest.fixture
def mock_db():
    with patch("app.services.auth.database") as mock:
        yield mock

def test_example(mock_db):
    mock_db.find_user.return_value = User(id=1, email="test@test.com")
    ...
```

Respond with ONLY valid JSON matching the schema. No markdown fences, no explanation outside JSON.
"""

TESTGEN_USER_PROMPT = """\
## User Request
{query}

## Execution Plan
Target files: {target_files}
Target symbols: {target_symbols}
Sub-tasks:
{sub_tasks}

## Code to Generate Tests For
{context}

Generate comprehensive, runnable tests as JSON:
"""


# ── Agent Implementation ─────────────────────────────────────────────

class TestGeneratorAgent(BaseAgent):
    """Generates unit tests for repository code."""

    def __init__(self):
        super().__init__(temperature=0.3)  # Slight creativity for diverse test cases
        self.parser = JsonOutputParser(pydantic_object=TestGeneratorOutput)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", TESTGEN_SYSTEM_PROMPT),
            ("human", TESTGEN_USER_PROMPT),
        ])

    def run(
        self,
        query: str,
        plan: Dict[str, Any],
        context: str,
    ) -> Dict[str, Any]:
        """
        Generate unit tests for the target code.

        Args:
            query:   User's test generation request.
            plan:    Execution plan from PlannerAgent.
            context: Retrieved code context from RetrieverAgent.

        Returns:
            Dict with keys:
              test_files          – List of TestFile dicts
              summary             – Overview of coverage
              setup_instructions  – Steps to run the tests
              coverage_gaps       – What is NOT covered
        """
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
        """Validate and clean up the LLM output."""
        valid_frameworks = {
            "pytest", "unittest", "jest", "vitest",
            "junit", "go_test", "mocha", "rspec",
        }
        valid_categories = {
            "happy_path", "edge_case", "error_case",
            "integration", "security",
        }

        # ── Normalize test files ─────────────────────────────────────
        test_files: List[Dict] = []
        for tf in raw.get("test_files", []):
            framework = tf.get("test_framework", "pytest").lower().strip()
            if framework not in valid_frameworks:
                framework = "pytest"

            # Normalize test cases
            test_cases: List[Dict] = []
            for tc in tf.get("test_cases", []):
                category = tc.get("category", "happy_path").lower().strip()
                if category not in valid_categories:
                    category = "happy_path"
                test_cases.append({
                    "name": tc.get("name", "test_unnamed"),
                    "category": category,
                    "description": tc.get("description", ""),
                })

            # Normalize requires_mocking
            mocking = tf.get("requires_mocking", [])
            if isinstance(mocking, str):
                mocking = [mocking]
            mocking = [str(m) for m in mocking if m]

            test_files.append({
                "test_file_path": tf.get("test_file_path", "tests/test_generated.py"),
                "source_file_path": tf.get("source_file_path", "unknown"),
                "test_framework": framework,
                "test_code": tf.get("test_code", ""),
                "test_cases": test_cases,
                "coverage_targets": tf.get("coverage_targets", []),
                "requires_mocking": mocking,
            })

        # ── Normalize other fields ───────────────────────────────────
        setup = raw.get("setup_instructions", [])
        if isinstance(setup, str):
            setup = [setup]
        setup = [str(s) for s in setup if s]

        gaps = raw.get("coverage_gaps", [])
        if isinstance(gaps, str):
            gaps = [gaps]
        gaps = [str(g) for g in gaps if g]

        return {
            "test_files": test_files,
            "summary": raw.get("summary", "Tests generated."),
            "setup_instructions": setup,
            "coverage_gaps": gaps,
        }

    # ── Utility Methods ──────────────────────────────────────────────

    @staticmethod
    def format_tests_for_display(result: Dict) -> str:
        """
        Format test generator output as readable markdown.

        Args:
            result: The normalized output dict from run()

        Returns:
            Markdown-formatted test report
        """
        parts: List[str] = []
        parts.append(f"## 🧪 Test Generation Report\n")
        parts.append(f"{result.get('summary', '')}\n")

        for i, tf in enumerate(result.get("test_files", []), 1):
            parts.append(
                f"### Test File {i}: `{tf['test_file_path']}`"
            )
            parts.append(f"**Tests for:** `{tf['source_file_path']}`")
            parts.append(f"**Framework:** {tf['test_framework']}")
            parts.append(f"**Covers:** {', '.join(tf['coverage_targets'])}")

            if tf["requires_mocking"]:
                parts.append(f"**Mocks:** {', '.join(tf['requires_mocking'])}")

            # List test cases
            test_cases = tf.get("test_cases", [])
            if test_cases:
                category_emoji = {
                    "happy_path": "✅",
                    "edge_case": "🔶",
                    "error_case": "❌",
                    "integration": "🔗",
                    "security": "🔒",
                }
                parts.append("\n**Test Cases:**")
                for tc in test_cases:
                    emoji = category_emoji.get(tc["category"], "🔹")
                    parts.append(f"  {emoji} `{tc['name']}` — {tc['description']}")

            # Code block
            if tf["test_code"]:
                lang = "python" if tf["test_framework"] in ("pytest", "unittest") else "javascript"
                parts.append(f"\n```{lang}\n{tf['test_code']}\n```\n")

        # Coverage gaps
        gaps = result.get("coverage_gaps", [])
        if gaps:
            parts.append("### ⚠️ Coverage Gaps")
            for gap in gaps:
                parts.append(f"- {gap}")
            parts.append("")

        # Setup instructions
        setup = result.get("setup_instructions", [])
        if setup:
            parts.append("### 📋 Setup Instructions")
            for step in setup:
                parts.append(f"1. {step}")

        return "\n".join(parts)

    @staticmethod
    def extract_all_test_code(result: Dict) -> str:
        """
        Extract all generated test code as a single string.
        Used by the Validator agent.

        Args:
            result: The normalized output dict from run()

        Returns:
            Concatenated test code with file headers
        """
        blocks: List[str] = []
        for tf in result.get("test_files", []):
            code = tf.get("test_code", "")
            if code:
                blocks.append(
                    f"// File: {tf['test_file_path']}\n"
                    f"// Tests for: {tf['source_file_path']}\n"
                    f"{code}"
                )
        return "\n\n---\n\n".join(blocks)

    @staticmethod
    def get_test_stats(result: Dict) -> Dict[str, Any]:
        """
        Get summary statistics about generated tests.

        Args:
            result: The normalized output dict from run()

        Returns:
            Dict with total_files, total_tests, categories breakdown
        """
        total_tests = 0
        categories: Dict[str, int] = {}

        for tf in result.get("test_files", []):
            for tc in tf.get("test_cases", []):
                total_tests += 1
                cat = tc.get("category", "other")
                categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_files": len(result.get("test_files", [])),
            "total_tests": total_tests,
            "categories": categories,
            "coverage_targets": sum(
                len(tf.get("coverage_targets", []))
                for tf in result.get("test_files", [])
            ),
        }