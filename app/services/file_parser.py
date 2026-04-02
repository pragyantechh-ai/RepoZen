import ast
import os
import hashlib
from typing import List, Dict, Optional
from pathlib import Path


# Extensions worth indexing
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".h",
    ".md", ".txt", ".yaml", ".yml", ".json",
    ".toml", ".cfg", ".ini", ".env",
    ".html", ".css", ".scss",
    ".sh", ".bash", ".dockerfile",
}

# Files/dirs to always skip
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".cache", "env", ".idea",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    ".DS_Store", "thumbs.db",
}

MAX_FILE_SIZE_KB = 512  # Skip files larger than this


def _file_hash(content: str) -> str:
    """Short content hash for dedup / cache invalidation."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]


def _should_index(file_path: Path) -> bool:
    """Decide whether a file should be included in the page index."""
    if file_path.name in SKIP_FILES:
        return False
    if file_path.suffix not in SUPPORTED_EXTENSIONS:
        return False
    if file_path.stat().st_size > MAX_FILE_SIZE_KB * 1024:
        return False
    return True


class PageIndexBuilder:
    """Builds a structured page index from a repository directory.

    Each 'page' is a logical unit of code:
      - For Python: module-level page + individual class/function pages
      - For other files: the entire file is one page

    Every page contains rich metadata for structural retrieval.
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.pages: List[Dict] = []

    def build(self) -> List[Dict]:
        """Walk the repo and build the full page index."""
        for root, dirs, files in os.walk(self.repo_path):
            # Prune skipped directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

            for fname in sorted(files):
                fpath = Path(root) / fname
                if not _should_index(fpath):
                    continue

                rel_path = str(fpath.relative_to(self.repo_path)).replace("\\", "/")

                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                except Exception as e:
                    print(f"[SKIP] Cannot read {rel_path}: {e}")
                    continue

                if not content.strip():
                    continue

                if fpath.suffix == ".py":
                    self._index_python_file(rel_path, content)
                else:
                    self._index_raw_file(rel_path, content)

        return self.pages

    # ── Python: AST-based structural indexing ────────────────────────

    def _index_python_file(self, rel_path: str, content: str):
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Fall back to raw indexing on parse failure
            self._index_raw_file(rel_path, content)
            return

        imports = self._collect_imports(tree)
        symbols = self._collect_top_level_symbols(tree)

        # Page 1: Module overview (imports + top-level summary, NOT full content)
        module_summary = self._build_module_summary(rel_path, content, imports, symbols)
        self.pages.append(module_summary)

        # Page per top-level function/class
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.pages.append(
                    self._build_function_page(node, rel_path, content, imports)
                )
            elif isinstance(node, ast.ClassDef):
                self.pages.append(
                    self._build_class_page(node, rel_path, content, imports)
                )

    def _collect_imports(self, tree) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

    def _collect_top_level_symbols(self, tree) -> List[Dict]:
        """Quick symbol table: name, type, line number."""
        symbols = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append({
                    "name": node.name,
                    "type": "function",
                    "line": node.lineno,
                    "signature": self._get_function_signature(node),
                })
            elif isinstance(node, ast.ClassDef):
                methods = [
                    child.name for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                symbols.append({
                    "name": node.name,
                    "type": "class",
                    "line": node.lineno,
                    "methods": methods,
                })
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.append({
                            "name": target.id,
                            "type": "variable",
                            "line": node.lineno,
                        })
        return symbols

    def _get_function_signature(self, node) -> str:
        """Extract function signature string like 'def foo(a, b, c=None) -> str'."""
        args = []
        for arg in node.args.args:
            annotation = ""
            if arg.annotation:
                annotation = f": {ast.dump(arg.annotation)}"
            args.append(f"{arg.arg}{annotation}")

        returns = ""
        if node.returns:
            returns = f" -> {ast.dump(node.returns)}"

        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({', '.join(args)}){returns}"

    def _build_module_summary(self, rel_path, content, imports, symbols) -> Dict:
        """A high-level overview page for the file — no full source."""
        lines = content.split("\n")
        # Grab module-level docstring if present
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
        except Exception:
            docstring = None

        return {
            "page_id": f"mod::{rel_path}",
            "page_type": "module_summary",
            "file_path": rel_path,
            "language": "python",
            "total_lines": len(lines),
            "content_hash": _file_hash(content),
            "docstring": docstring,
            "imports": imports,
            "symbols": symbols,
            # Compact representation — NOT the full file
            "content": self._truncate(content, max_lines=30),
            "keywords": self._extract_keywords(rel_path, imports, symbols),
        }

    def _build_function_page(self, node, rel_path, content, imports) -> Dict:
        source = ast.get_source_segment(content, node) or ""
        docstring = ast.get_docstring(node)

        return {
            "page_id": f"fn::{rel_path}::{node.name}",
            "page_type": "function",
            "file_path": rel_path,
            "language": "python",
            "name": node.name,
            "signature": self._get_function_signature(node),
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "content": source,
            "content_hash": _file_hash(source),
            "docstring": docstring,
            "imports": imports,
            "parent": None,
            "keywords": self._extract_keywords(node.name, imports, []),
        }

    def _build_class_page(self, node, rel_path, content, imports) -> Dict:
        source = ast.get_source_segment(content, node) or ""
        docstring = ast.get_docstring(node)

        methods = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append({
                    "name": child.name,
                    "signature": self._get_function_signature(child),
                    "start_line": child.lineno,
                    "end_line": getattr(child, "end_lineno", child.lineno),
                    "docstring": ast.get_docstring(child),
                })

        return {
            "page_id": f"cls::{rel_path}::{node.name}",
            "page_type": "class",
            "file_path": rel_path,
            "language": "python",
            "name": node.name,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "content": source,
            "content_hash": _file_hash(source),
            "docstring": docstring,
            "imports": imports,
            "methods": methods,
            "parent": None,
            "keywords": self._extract_keywords(node.name, imports, methods),
        }

    # ── Non-Python: raw file page ────────────────────────────────────

    def _index_raw_file(self, rel_path: str, content: str):
        ext = Path(rel_path).suffix
        language = {
            ".js": "javascript", ".ts": "typescript", ".tsx": "typescript",
            ".jsx": "javascript", ".java": "java", ".go": "go",
            ".rs": "rust", ".md": "markdown", ".json": "json",
            ".yaml": "yaml", ".yml": "yaml", ".html": "html",
            ".css": "css", ".scss": "scss", ".sh": "shell",
        }.get(ext, "text")

        self.pages.append({
            "page_id": f"file::{rel_path}",
            "page_type": "file",
            "file_path": rel_path,
            "language": language,
            "total_lines": content.count("\n") + 1,
            "content": content,
            "content_hash": _file_hash(content),
            "docstring": None,
            "imports": [],
            "symbols": [],
            "keywords": self._extract_keywords(rel_path, [], []),
        })

    # ── Helpers ──────────────────────────────────────────────────────

    def _truncate(self, content: str, max_lines: int = 30) -> str:
        lines = content.split("\n")
        if len(lines) <= max_lines:
            return content
        return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"

    def _extract_keywords(self, name, imports, symbols) -> List[str]:
        """Build a keyword set for structural search."""
        keywords = set()

        # From name/path
        if isinstance(name, str):
            parts = name.replace("/", ".").replace("\\", ".").replace("_", " ").split()
            keywords.update(p.lower() for p in parts if len(p) > 2)

        # From imports
        for imp in imports:
            keywords.update(p.lower() for p in imp.split(".") if len(p) > 2)

        # From symbols
        if isinstance(symbols, list):
            for sym in symbols:
                if isinstance(sym, dict) and "name" in sym:
                    keywords.add(sym["name"].lower())

        return sorted(keywords)