"""High-level AST parser with Morph-compatible API.

Provides multi-language AST parsing with entity extraction.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

from pheno.logging.core.logger import get_logger

logger = get_logger("pheno.analytics.ast.parser")

try:  # pragma: no cover - optional dependency
    from tree_sitter import Parser as TreeSitterParser  # type: ignore
    from tree_sitter_languages import get_language  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    TreeSitterParser = None
    get_language = None


@dataclass
class CodeEntity:
    """
    Represents a code entity (function, class, method, etc.).
    """

    type: str  # 'function', 'class', 'method'
    name: str
    signature: str
    docstring: str | None
    start_line: int
    end_line: int
    file_path: str
    parent: str | None = None  # For methods, the class name
    complexity: int = 0


class PythonASTParser:
    """
    Parser for Python files using built-in AST module.
    """

    def parse_file(self, file_path: str) -> list[CodeEntity]:
        """Extract code entities from Python file.

        Args:
            file_path: Path to Python file

        Returns:
            List of extracted code entities
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            entities = []

            # Extract top-level entities
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if it's a top-level function
                    if self._is_top_level(node, tree):
                        entities.append(self._extract_function(node, file_path, source))

                elif isinstance(node, ast.ClassDef):
                    entities.append(self._extract_class(node, file_path, source))

                    # Extract methods from class
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            entities.append(
                                self._extract_method(item, node.name, file_path, source),
                            )

            return entities

        except Exception as e:
            logger.debug("python_parse_failed", file=file_path, error=str(e))
            return []

    def _is_top_level(self, node: ast.FunctionDef, tree: ast.Module) -> bool:
        """
        Check if a function is top-level (not inside a class).
        """
        for item in tree.body:
            if item == node:
                return True
            if isinstance(item, ast.ClassDef) and node in item.body:
                return False
        return False

    def _extract_function(self, node: ast.FunctionDef, file_path: str, source: str) -> CodeEntity:
        """
        Extract function entity.
        """
        signature = self._get_signature(node, source)
        docstring = ast.get_docstring(node)

        return CodeEntity(
            type="function",
            name=node.name,
            signature=signature,
            docstring=docstring,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
        )

    def _extract_class(self, node: ast.ClassDef, file_path: str, source: str) -> CodeEntity:
        """
        Extract class entity.
        """
        bases = ", ".join(self._get_base_names(node))
        signature = f"class {node.name}({bases})" if bases else f"class {node.name}"
        docstring = ast.get_docstring(node)

        return CodeEntity(
            type="class",
            name=node.name,
            signature=signature,
            docstring=docstring,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
        )

    def _extract_method(
        self, node: ast.FunctionDef, class_name: str, file_path: str, source: str,
    ) -> CodeEntity:
        """
        Extract method entity.
        """
        signature = self._get_signature(node, source)
        docstring = ast.get_docstring(node)

        return CodeEntity(
            type="method",
            name=node.name,
            signature=signature,
            docstring=docstring,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            file_path=file_path,
            parent=class_name,
        )

    def _get_signature(self, node: ast.FunctionDef, source: str) -> str:
        """
        Get function signature from source.
        """
        try:
            lines = source.split("\n")
            start = node.lineno - 1

            # Find the end of the signature (look for ':')
            signature_lines = []
            for i in range(start, min(start + 10, len(lines))):
                line = lines[i]
                signature_lines.append(line)
                if ":" in line:
                    break

            signature = " ".join(signature_lines).strip()
            # Clean up the signature
            return re.sub(r"\s+", " ", signature)
        except Exception:
            return f"def {node.name}(...)"

    def _get_base_names(self, node: ast.ClassDef) -> list[str]:
        """
        Get base class names.
        """
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(
                    f"{base.value.id}.{base.attr}" if hasattr(base.value, "id") else base.attr,
                )
        return bases


class JavaScriptParser:
    """
    Parser for JavaScript/TypeScript files using regex patterns.
    """

    def __init__(self) -> None:
        self._ts_parser = None
        if TreeSitterParser and get_language:
            try:
                language = get_language("javascript")
                parser = TreeSitterParser()
                parser.set_language(language)
                self._ts_parser = parser
            except Exception as exc:  # pragma: no cover - optional dependency guard
                logger.debug("tree_sitter_init_failed", error=str(exc))
                self._ts_parser = None

    def parse_file(self, file_path: str) -> list[CodeEntity]:
        """Extract code entities from JS/TS file.

        Args:
            file_path: Path to JavaScript/TypeScript file

        Returns:
            List of extracted code entities
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
            if self._ts_parser:
                return self._extract_with_tree_sitter(source, file_path)

            entities = []
            entities.extend(self._extract_functions(source, file_path))
            entities.extend(self._extract_classes(source, file_path))
            entities.extend(self._extract_arrow_functions(source, file_path))
            return entities
        except Exception as e:
            logger.debug("javascript_parse_failed", file=file_path, error=str(e))
            return []

    def _extract_with_tree_sitter(self, source: str, file_path: str) -> list[CodeEntity]:
        if not self._ts_parser:  # pragma: no cover - guard
            return []

        tree = self._ts_parser.parse(bytes(source, "utf-8"))
        root = tree.root_node
        entities: list[CodeEntity] = []

        for node in _walk_tree(root):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = (
                    _slice_source(source, name_node.start_byte, name_node.end_byte)
                    if name_node
                    else "anonymous"
                )
                signature = (
                    _slice_source(source, node.start_byte, node.end_byte).split("{", 1)[0].strip()
                )
                entities.append(
                    CodeEntity(
                        type="function",
                        name=name,
                        signature=signature,
                        docstring=None,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path=file_path,
                    ),
                )
            elif node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = (
                    _slice_source(source, name_node.start_byte, name_node.end_byte)
                    if name_node
                    else "anonymous_class"
                )
                snippet = _slice_source(source, node.start_byte, node.end_byte)
                brace_index = snippet.find("{")
                signature = (snippet[:brace_index] if brace_index != -1 else snippet).strip()
                entities.append(
                    CodeEntity(
                        type="class",
                        name=name,
                        signature=signature or f"class {name}",
                        docstring=None,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path=file_path,
                    ),
                )
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                name = (
                    _slice_source(source, name_node.start_byte, name_node.end_byte)
                    if name_node
                    else "anonymous"
                )
                class_node = node.parent
                parent_name = None
                while class_node:
                    if class_node.type == "class_declaration":
                        name_child = class_node.child_by_field_name("name")
                        if name_child:
                            parent_name = source[name_child.start_byte : name_child.end_byte]
                        break
                    class_node = class_node.parent
                signature = (
                    _slice_source(source, node.start_byte, node.end_byte).split("{", 1)[0].strip()
                )
                entities.append(
                    CodeEntity(
                        type="method",
                        name=name,
                        signature=signature,
                        docstring=None,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path=file_path,
                        parent=parent_name,
                    ),
                )

        return entities


def _walk_tree(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        if hasattr(current, "children"):
            stack.extend(reversed(current.children))


def _slice_source(source: str, start_byte: int, end_byte: int) -> str:
    encoded = source.encode("utf-8")
    segment = encoded[start_byte:end_byte]
    return segment.decode("utf-8", errors="ignore")

    def _extract_functions(self, source: str, file_path: str) -> list[CodeEntity]:
        """
        Extract function declarations.
        """
        entities = []

        # Match: function name(...) { or async function name(...) {
        pattern = r"(?:async\s+)?function\s+(\w+)\s*\((.*?)\)\s*\{"

        for match in re.finditer(pattern, source):
            name = match.group(1)
            params = match.group(2)
            start_pos = match.start()

            # Find line number
            line_num = source[:start_pos].count("\n") + 1

            # Extract docstring (JSDoc)
            docstring = self._extract_jsdoc(source, start_pos)

            signature = f"function {name}({params})"

            entities.append(
                CodeEntity(
                    type="function",
                    name=name,
                    signature=signature,
                    docstring=docstring,
                    start_line=line_num,
                    end_line=line_num,  # Simplified
                    file_path=file_path,
                ),
            )

        return entities

    def _extract_classes(self, source: str, file_path: str) -> list[CodeEntity]:
        """
        Extract class declarations.
        """
        entities = []

        # Match: class Name { or class Name extends Base {
        pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{"

        for match in re.finditer(pattern, source):
            name = match.group(1)
            base = match.group(2)
            start_pos = match.start()

            line_num = source[:start_pos].count("\n") + 1
            docstring = self._extract_jsdoc(source, start_pos)

            signature = f"class {name}"
            if base:
                signature += f" extends {base}"

            entities.append(
                CodeEntity(
                    type="class",
                    name=name,
                    signature=signature,
                    docstring=docstring,
                    start_line=line_num,
                    end_line=line_num,
                    file_path=file_path,
                ),
            )

        return entities

    def _extract_arrow_functions(self, source: str, file_path: str) -> list[CodeEntity]:
        """
        Extract arrow function assignments.
        """
        entities = []

        # Match: const name = (...) => { or const name = async (...) => {
        pattern = r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\((.*?)\)\s*=>"

        for match in re.finditer(pattern, source):
            name = match.group(1)
            params = match.group(2)
            start_pos = match.start()

            line_num = source[:start_pos].count("\n") + 1
            docstring = self._extract_jsdoc(source, start_pos)

            signature = f"const {name} = ({params}) =>"

            entities.append(
                CodeEntity(
                    type="function",
                    name=name,
                    signature=signature,
                    docstring=docstring,
                    start_line=line_num,
                    end_line=line_num,
                    file_path=file_path,
                ),
            )

        return entities

    def _extract_jsdoc(self, source: str, pos: int) -> str | None:
        """
        Extract JSDoc comment before position.
        """
        # Look backwards for /** ... */
        before = source[:pos]
        match = re.search(r"/\*\*(.*?)\*/", before[::-1], re.DOTALL)
        if match:
            return match.group(1)[::-1].strip()
        return None
    return None


def get_parser_for_file(file_path: str):
    """Get appropriate parser for file type.

    Args:
        file_path: Path to file

    Returns:
        Parser instance or None if unsupported
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".py":
        return PythonASTParser()
    if ext in [".js", ".ts", ".jsx", ".tsx"]:
        return JavaScriptParser()
    return None
