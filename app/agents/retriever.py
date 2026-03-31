"""
Retriever Agent: Fetches relevant code from the PageIndex.

Uses the execution plan from the Planner to:
  1. Run search queries against the page index
  2. Look up specific files and symbols mentioned in the plan
  3. Rank all collected pages by relevance
  4. Assemble a coherent, budget-aware context window for downstream agents

This agent does NOT call the LLM — it is pure retrieval logic.
"""

from typing import Any, Dict, List, Set, Tuple

from base_agent import BaseAgent
from app.services.chunking import PageIndex, MAX_CONTEXT_CHARS


class RetrieverAgent(BaseAgent):
    """Retrieves relevant code pages based on the Planner's execution plan."""

    def __init__(self, page_index: PageIndex):
        # We inherit BaseAgent for interface consistency,
        # but we don't use the LLM — all work is local retrieval.
        super().__init__(temperature=0.0)
        self.index = page_index

    def run(
        self,
        plan: Dict[str, Any],
        query: str,
        max_chars: int = MAX_CONTEXT_CHARS,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant code context from the page index.

        Args:
            plan:      Execution plan from PlannerAgent.
            query:     Original user query (used as fallback search).
            max_chars: Maximum context size in characters (~15k tokens).

        Returns:
            Dict with:
              context          – Formatted string ready for LLM consumption
              pages            – List of raw page dicts included in context
              files_found      – Sorted list of file paths that matched
              retrieval_stats  – Metadata about the retrieval process
        """
        collected_pages, seen_ids = self._collect_pages(plan, query)

        # Rank by relevance to the plan
        ranked_pages = self._rank_pages(collected_pages, plan)

        # Assemble into a budget-aware context string
        context, included_pages = self._assemble_context(ranked_pages, max_chars)

        files_found = sorted({p.get("file_path", "") for p in included_pages})

        return {
            "context": context,
            "pages": included_pages,
            "files_found": files_found,
            "retrieval_stats": {
                "total_candidates": len(collected_pages),
                "included_in_context": len(included_pages),
                "context_chars": len(context),
                "search_queries_used": plan.get("search_queries", []),
            },
        }

    # ── Collection ───────────────────────────────────────────────────

    def _collect_pages(
        self,
        plan: Dict[str, Any],
        query: str,
    ) -> Tuple[List[Dict], Set[str]]:
        """
        Gather candidate pages from all sources in priority order:
          1. Planner's search queries
          2. Target file lookups
          3. Target symbol lookups
          4. Fallback: raw user query search
        """
        collected: List[Dict] = []
        seen_ids: Set[str] = set()

        def _add(pages: List[Dict]):
            for page in pages:
                pid = page.get("page_id", "")
                if pid and pid not in seen_ids:
                    collected.append(page)
                    seen_ids.add(pid)

        # 1 — Search queries from the planner
        for sq in plan.get("search_queries", []):
            _add(self.index.search(sq, top_k=5))

        # 2 — Specific target files
        for target_file in plan.get("target_files", []):
            # Try exact match first
            exact = self.index.get_by_file(target_file)
            if exact:
                _add(exact)
            else:
                # Fuzzy: search for the filename as a keyword
                _add(self.index.search(target_file, top_k=3))

        # 3 — Specific target symbols
        for symbol in plan.get("target_symbols", []):
            sym_pages = self.index.get_by_symbol(symbol)
            if sym_pages:
                _add(sym_pages)
            else:
                _add(self.index.search(symbol, top_k=3))

        # 4 — Fallback: search with the raw user query
        if not collected:
            _add(self.index.search(query, top_k=10))

        return collected, seen_ids

    # ── Ranking ──────────────────────────────────────────────────────

    def _rank_pages(
        self,
        pages: List[Dict],
        plan: Dict[str, Any],
    ) -> List[Dict]:
        """
        Score and sort pages by relevance to the execution plan.

        Scoring factors:
          - Target file match        (+10)
          - Target symbol match      (+8)
          - Page type boost by intent (+3 or +2)
          - Large page penalty       (-1)
        """
        target_files = set(plan.get("target_files", []))
        target_symbols = {s.lower() for s in plan.get("target_symbols", [])}
        intent = plan.get("intent", "general")

        scored: List[Tuple[float, int, Dict]] = []

        for idx, page in enumerate(pages):
            score = 0.0

            # ── File match ───────────────────────────────────────────
            file_path = page.get("file_path", "")
            if file_path in target_files:
                score += 10.0
            else:
                # Partial path match (e.g. plan says "auth.py", page is "app/services/auth.py")
                for tf in target_files:
                    if file_path.endswith(tf) or tf in file_path:
                        score += 5.0
                        break

            # ── Symbol match ─────────────────────────────────────────
            page_name = page.get("name", "").lower()
            if page_name and page_name in target_symbols:
                score += 8.0

            # Also check if any target symbol appears in the page's symbols list
            for sym in page.get("symbols", []):
                if isinstance(sym, dict) and sym.get("name", "").lower() in target_symbols:
                    score += 4.0
                    break

            # ── Page type boost based on intent ──────────────────────
            page_type = page.get("page_type", "")

            if intent in ("modification", "debugging"):
                # For code changes / debugging, prefer actual code over summaries
                if page_type in ("function", "class"):
                    score += 3.0
                elif page_type == "module_summary":
                    score += 1.0
            elif intent in ("explanation", "general"):
                # For understanding, summaries are very useful
                if page_type == "module_summary":
                    score += 3.0
                elif page_type in ("function", "class"):
                    score += 2.0
            elif intent == "testing":
                # For test generation, we need the actual implementations
                if page_type in ("function", "class"):
                    score += 4.0

            # ── Penalize very large pages (they eat context budget) ──
            content_len = len(page.get("content", ""))
            if content_len > 8000:
                score -= 2.0
            elif content_len > 5000:
                score -= 1.0

            scored.append((score, idx, page))

        # Sort by score descending, break ties by original order
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [page for _, _, page in scored]

    # ── Context Assembly ─────────────────────────────────────────────

    def _assemble_context(
        self,
        pages: List[Dict],
        max_chars: int,
    ) -> Tuple[str, List[Dict]]:
        """
        Format ranked pages into an LLM-ready context string
        that fits within the character budget.
        """
        parts: List[str] = []
        included: List[Dict] = []
        total_chars = 0

        for page in pages:
            block = self._format_page(page)
            if total_chars + len(block) > max_chars:
                # Try to fit at least a truncated version
                remaining = max_chars - total_chars
                if remaining > 500:
                    # Truncate content to fit
                    block = self._format_page(page, truncate_to=remaining - 100)
                    parts.append(block)
                    included.append(page)
                break

            parts.append(block)
            included.append(page)
            total_chars += len(block)

        if not parts:
            return "No relevant code found in the repository.", []

        header = (
            f"## Repository Context — {len(parts)} code sections "
            f"({total_chars:,} chars)\n\n"
        )
        return header + "\n\n---\n\n".join(parts), included

    # ── Page Formatting ──────────────────────────────────────────────

    def _format_page(self, page: Dict, truncate_to: int = 0) -> str:
        """
        Format a single page as a readable context block.

        Args:
            page:        The page dict from the index.
            truncate_to: If > 0, truncate the content to this many chars.
        """
        parts: List[str] = []
        page_type = page.get("page_type", "unknown")
        file_path = page.get("file_path", "unknown")
        name = page.get("name", "")
        lang = page.get("language", "text")

        # ── Header ───────────────────────────────────────────────────
        if page_type == "module_summary":
            parts.append(f"### 📄 {file_path} (Module Overview)")

            # List defined symbols
            symbols = page.get("symbols", [])
            if symbols:
                sym_lines = []
                for sym in symbols:
                    if not isinstance(sym, dict):
                        continue
                    stype = sym.get("type", "?")
                    sname = sym.get("name", "?")
                    if stype == "class":
                        methods = ", ".join(sym.get("methods", []))
                        sym_lines.append(f"  - class `{sname}` → methods: {methods}")
                    elif stype == "function":
                        sig = sym.get("signature", sname)
                        sym_lines.append(f"  - `{sig}`")
                    else:
                        sym_lines.append(f"  - {stype} `{sname}`")
                parts.append("**Defines:**\n" + "\n".join(sym_lines))

            # List imports
            imports = page.get("imports", [])
            if imports:
                parts.append(f"**Imports:** {', '.join(imports[:15])}")

        elif page_type == "function":
            sig = page.get("signature", name)
            start = page.get("start_line", "?")
            end = page.get("end_line", "?")
            parts.append(f"### ⚡ `{sig}`")
            parts.append(f"**File:** {file_path}  |  **Lines:** {start}–{end}")

        elif page_type == "class":
            start = page.get("start_line", "?")
            end = page.get("end_line", "?")
            parts.append(f"### 🏗️ class `{name}`")
            parts.append(f"**File:** {file_path}  |  **Lines:** {start}–{end}")
            methods = page.get("methods", [])
            if methods:
                m_names = [m["name"] for m in methods if isinstance(m, dict)]
                parts.append(f"**Methods:** {', '.join(m_names)}")

        else:
            lines = page.get("total_lines", "?")
            parts.append(f"### 📁 {file_path} ({lines} lines)")

        # ── Docstring ────────────────────────────────────────────────
        docstring = page.get("docstring")
        if docstring:
            # Keep docstring short
            if len(docstring) > 300:
                docstring = docstring[:300] + "…"
            parts.append(f"> {docstring}")

        # ── Code Content ─────────────────────────────────────────────
        content = page.get("content", "")
        if content:
            if truncate_to and len(content) > truncate_to:
                content = content[:truncate_to] + "\n// ... truncated ..."
            parts.append(f"```{lang}\n{content}\n```")

        return "\n".join(parts)