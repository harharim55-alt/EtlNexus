"""AST-based parser for ETL code files.

Extracts:
- Source tables from `from etls import ...` statements
- Target table from `self.table` in __init__
- Destination tables from `self.destination_tables` in __init__
- Schedule from `self.schedule` in __init__
- Category from `self.category` in __init__
- Class name as the pipeline name
"""

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParsedETL:
    class_name: str
    source_tables: list[str] = field(default_factory=list)
    target_table: str = ""
    destination_tables: list[str] = field(default_factory=list)
    schedule: str | None = None
    category: str | None = None
    networks: list[str] = field(default_factory=list)
    code_path: str = ""


class ETLCodeParser:
    """Parse ETL Python files using AST for reliable extraction."""

    def parse_file(self, file_path: Path) -> ParsedETL | None:
        """Parse a single ETL file and return extracted metadata."""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, OSError) as e:
            logger.warning("Failed to parse %s: %s", file_path, e)
            return None

        source_tables = self._extract_etl_imports(tree)
        class_info = self._extract_class_info(tree)

        if not class_info:
            return None

        return ParsedETL(
            class_name=class_info["name"],
            source_tables=source_tables,
            target_table=class_info.get("table", ""),
            destination_tables=class_info.get("destination_tables", []),
            schedule=class_info.get("schedule"),
            category=class_info.get("category"),
            networks=class_info.get("networks", []),
            code_path=str(file_path),
        )

    def parse_directory(self, directory: Path) -> list[ParsedETL]:
        """Parse all Python files in the directory."""
        results = []
        if not directory.exists():
            logger.warning("Directory does not exist: %s", directory)
            return results

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            parsed = self.parse_file(py_file)
            if parsed:
                results.append(parsed)

        logger.info("Parsed %d ETL files from %s", len(results), directory)
        return results

    def _extract_etl_imports(self, tree: ast.Module) -> list[str]:
        """Extract source table names from `from etls import ...` statements."""
        sources = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "etls":
                for alias in node.names:
                    sources.append(alias.name)
        return sources

    def _extract_class_info(self, tree: ast.Module) -> dict | None:
        """Extract class name and __init__ assignments."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            info: dict = {"name": node.name}

            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                    continue
                for stmt in item.body:
                    self._extract_self_assign(stmt, info)

            return info
        return None

    def _extract_self_assign(self, stmt: ast.stmt, info: dict) -> None:
        """Extract self.attr = value assignments from __init__."""
        if not isinstance(stmt, ast.Assign):
            return
        if len(stmt.targets) != 1:
            return

        target = stmt.targets[0]
        if not isinstance(target, ast.Attribute):
            return
        if not isinstance(target.value, ast.Name) or target.value.id != "self":
            return

        attr = target.attr
        value = stmt.value

        if attr == "table" and isinstance(value, ast.Constant) and isinstance(value.value, str):
            info["table"] = value.value

        elif attr == "destination_tables" and isinstance(value, ast.List):
            info["destination_tables"] = [
                elt.value for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]

        elif attr == "schedule" and isinstance(value, ast.Constant) and isinstance(value.value, str):
            info["schedule"] = value.value

        elif attr == "category" and isinstance(value, ast.Constant) and isinstance(value.value, str):
            info["category"] = value.value

        elif attr == "networks" and isinstance(value, ast.List):
            info["networks"] = [
                elt.value for elt in value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]


etl_code_parser = ETLCodeParser()
