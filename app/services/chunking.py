"""
PageIndex: Structural code index for LLM context retrieval.

Instead of embedding chunks into a vector DB, we maintain a searchable
in-memory index. Retrieval is done via keyword matching, file-path
filtering, and symbol lookup — then relevant pages are assembled into
a context window for the LLM.
"""

from typing import List, Dict, Optional
import re
from pathlib import Path


# Max characters to send as LLM context in one shot
MAX_CONTEXT_CHARS = 60_000  # ~15k tokens for GPT-class models


class PageIndex:
    """In-memory searchable index of code pages."""

    def __init__(self, pages: Optional[List[Dict]] = None):
        self.pages: List[Dict] = pages or []
        self._keyword_map: Dict[str, List[int]] = {}
        self._path_map: Dict[str, List[int]] = {}

        if self.pages:
            self._rebuild_indices()

    def load(self, pages: List[Dict]):
        """Load pages and rebuild search indices."""
        self.pages = pages
        self._rebuild_indices()

    def _rebuild_indices(self):
        """Build inverted indices for fast lookup."""
        self._keyword_map.clear()
        self._path_map.clear()

        for idx, page in enumerate(self.pages):
            # Keyword index
            for kw in page.get("keywords", []):
                self._keyword_map.setdefault(kw, []).append(idx)

            # Path index
            fpath = page.get("file_path", "")
            self._path_map.setdefault(fpath, []).append(idx)

    # ── Retrieval Methods ────────────────────────────────────────────

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Search pages by query string. Uses keyword + content matching."""
        query_terms = self._tokenize_query(query)
        scored: List[tuple] = []

        for idx, page in enumerate(self.pages):
            score = self._score_page(page, query_terms, query)
            if score > 0:
                scored.append((score, idx))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self.pages[idx] for _, idx in scored[:top_k]]

    def get_by_file(self, file_path: str) -> List[Dict]:
        """Get all pages belonging to a specific file."""
        indices = self._path_map.get(file_path, [])
        return [self.pages[i] for i in indices]

    def get_by_symbol(self, symbol_name: str) -> List[Dict]:
        """Find pages that define or reference a specific symbol."""
        results = []
        symbol_lower = symbol_name.lower()

        for page in self.pages:
            # Direct name match
            if page.get("name", "").lower() == symbol_lower:
                results.append(page)
                continue

            # Check in symbols list (module summary pages)
            for sym in page.get("symbols", []):
                if isinstance(sym, dict) and sym.get("name", "").lower() == symbol_lower:
                    results.append(page)
                    break

            # Check in methods list (class pages)
            for method in page.get("methods", []):
                if isinstance(method, dict) and method.get("name", "").lower() == symbol_lower:
                    results.append(page)
                    break

        return results

    def get_file_tree(self) -> List[str]:
        """Return sorted list of all unique file paths in the index."""
        paths = set()
        for page in self.pages:
            fp = page.get("file_path", "")
            if fp:
                paths.add(fp)
        return sorted(paths)

    def get_summary(self) -> Dict:
        """Return a compact summary of the entire index."""
        type_counts = {}
        languages = set()
        for page in self.pages:
            pt = page.get("page_type", "unknown")
            type_counts[pt] = type_counts.get(pt, 0) + 1
            lang = page.get("language")
            if lang:
                languages.add(lang)

        return {
            "total_pages": len(self.pages),
            "page_types": type_counts,
            "languages": sorted(languages),
            "files": self.get_file_tree(),
        }

    # ── Context Assembly ─────────────────────────────────────────────

    def build_context(self, query: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
        """Build an LLM-ready context string from the most relevant pages.

        Returns a formatted string that fits within max_chars, structured
        so the LLM can reason about file locations and code structure.
        """
        relevant = self.search(query, top_k=20)

        context_parts = []
        total_chars = 0

        for page in relevant:
            block = self._format_page_for_context(page)
            if total_chars + len(block) > max_chars:
                break
            context_parts.append(block)
            total_chars += len(block)

        if not context_parts:
            return "No relevant code found in the repository."

        header = f"## Repository Context ({len(context_parts)} pages)\n\n"
        return header + "\n---\n\n".join(context_parts)

    def _format_page_for_context(self, page: Dict) -> str:
        """Format a single page as a readable context block."""
        parts = []

        # Header
        page_type = page.get("page_type", "unknown")
        file_path = page.get("file_path", "unknown")
        name = page.get("name", "")
        lang = page.get("language", "text")

        if page_type == "module_summary":
            parts.append(f"### 📄 {file_path} (Module Overview)")
            if page.get("symbols"):
                parts.append("**Symbols:**")
                for sym in page["symbols"]:
                    if sym["type"] == "class":
                        methods_str = ", ".join(sym.get("methods", []))
                        parts.append(f"  - class `{sym['name']}` [methods: {methods_str}]")
                    elif sym["type"] == "function":
                        parts.append(f"  - `{sym.get('signature', sym['name'])}`")
                    else:
                        parts.append(f"  - {sym['type']} `{sym['name']}`")
        elif page_type == "function":
            sig = page.get("signature", name)
            parts.append(f"### ⚡ `{sig}` in {file_path}")
        elif page_type == "class":
            parts.append(f"### 🏗️ class `{name}` in {file_path}")
            if page.get("methods"):
                method_names = [m["name"] for m in page["methods"]]
                parts.append(f"**Methods:** {', '.join(method_names)}")
        else:
            parts.append(f"### 📁 {file_path}")

        # Docstring
        if page.get("docstring"):
            parts.append(f"> {page['docstring']}")

        # Content
        content = page.get("content", "")
        if content:
            parts.append(f"```{lang}\n{content}\n```")

        return "\n".join(parts)

    # ── Scoring ──────────────────────────────────────────────────────

    def _score_page(self, page: Dict, query_terms: List[str], raw_query: str) -> float:
        score = 0.0

        # Keyword matches (from prebuilt keywords)
        page_keywords = set(page.get("keywords", []))
        keyword_hits = len(page_keywords & set(query_terms))
        score += keyword_hits * 3.0

        # File path match
        file_path = page.get("file_path", "").lower()
        for term in query_terms:
            if term in file_path:
                score += 2.0

        # Symbol name match
        name = page.get("name", "").lower()
        for term in query_terms:
            if term in name:
                score += 4.0

        # Docstring match
        docstring = (page.get("docstring") or "").lower()
        for term in query_terms:
            if term in docstring:
                score += 1.5

        # Content match (lighter weight — broader)
        content = page.get("content", "").lower()
        for term in query_terms:
            if term in content:
                score += 1.0

        # Boost module summaries slightly (gives overview context)
        if page.get("page_type") == "module_summary":
            score *= 1.1

        # Boost exact phrase match in content
        if raw_query.lower() in content:
            score += 5.0

        return score

    def _tokenize_query(self, query: str) -> List[str]:
        """Break query into searchable terms."""
        # Split on non-alphanumeric, lowercase, filter short terms
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', query.lower())
        return [t for t in tokens if len(t) > 2]


def build_page_index(pages: List[Dict]) -> PageIndex:
    """Convenience factory function."""
    return PageIndex(pages)