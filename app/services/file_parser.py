import ast
import os
import uuid
from typing import List, Dict
from pathlib import Path


class CodeUnitExtractor:
    """Extracts code units (functions, classes, methods) from Python files.
    For non-Python files, returns the whole file as a single unit.
    """

    # Extensions that get AST-parsed
    AST_PARSEABLE = {".py"}

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.units: List[Dict] = []

    def extract(self) -> List[Dict]:
        ext = Path(self.file_path).suffix

        if ext in self.AST_PARSEABLE:
            return self._extract_python()
        else:
            return self._extract_raw()

    # ── Python AST extraction ────────────────────────────────────────

    def _extract_python(self) -> List[Dict]:
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content)
            imports = self._extract_imports(tree)

            # Only iterate top-level body to avoid duplicating nested methods
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    self.units.append(
                        self._build_function_unit(node, content, imports)
                    )
                elif isinstance(node, ast.ClassDef):
                    self.units.append(
                        self._build_class_unit(node, content, imports)
                    )

            # If file has no classes/functions, store the whole file as a module unit
            if not self.units:
                self.units.append(self._build_module_unit(content, imports))

            return self.units

        except Exception as e:
            print(f"[ERROR] Parsing {self.file_path}: {e}")
            return self._extract_raw()

    def _extract_imports(self, tree) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                for n in node.names:
                    imports.append(f"{module}.{n.name}")
        return imports

    def _get_docstring(self, node):
        return ast.get_docstring(node)

    def _build_function_unit(self, node, content, imports) -> Dict:
        return {
            "id": str(uuid.uuid4()),
            "type": "function",
            "name": node.name,
            "file_path": self.file_path,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "content": ast.get_source_segment(content, node) or "",
            "docstring": self._get_docstring(node),
            "imports": imports,
            "parent": None,
        }

    def _build_class_unit(self, node, content, imports) -> Dict:
        class_unit = {
            "id": str(uuid.uuid4()),
            "type": "class",
            "name": node.name,
            "file_path": self.file_path,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "content": ast.get_source_segment(content, node) or "",
            "docstring": self._get_docstring(node),
            "imports": imports,
            "parent": None,
        }

        # Extract methods inside class — only direct children
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.units.append({
                    "id": str(uuid.uuid4()),
                    "type": "method",
                    "name": child.name,
                    "file_path": self.file_path,
                    "start_line": child.lineno,
                    "end_line": getattr(child, "end_lineno", child.lineno),
                    "content": ast.get_source_segment(content, child) or "",
                    "docstring": self._get_docstring(child),
                    "imports": imports,
                    "parent": node.name,
                })

        return class_unit

    def _build_module_unit(self, content: str, imports: List[str]) -> Dict:
        return {
            "id": str(uuid.uuid4()),
            "type": "module",
            "name": Path(self.file_path).stem,
            "file_path": self.file_path,
            "start_line": 1,
            "end_line": content.count("\n") + 1,
            "content": content,
            "docstring": None,
            "imports": imports,
            "parent": None,
        }

    # ── Raw text extraction (non-Python files) ──────────────────────

    def _extract_raw(self) -> List[Dict]:
        try:
            with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            if not content.strip():
                return []

            return [{
                "id": str(uuid.uuid4()),
                "type": "file",
                "name": Path(self.file_path).name,
                "file_path": self.file_path,
                "start_line": 1,
                "end_line": content.count("\n") + 1,
                "content": content,
                "docstring": None,
                "imports": [],
                "parent": None,
            }]
        except Exception as e:
            print(f"[ERROR] Reading {self.file_path}: {e}")
            return []