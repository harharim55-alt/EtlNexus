# ETLNexus Coding Standards and Conventions

This document outlines the coding standards, style guides, and conventions to be followed for the project. Adhering to these standards will help ensure code consistency, readability, and maintainability.

## 1. Python Style Guide

- **PEP 8:** All Python code should adhere to [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
- **Formatter:** We use `black` for automated code formatting. Ensure code is formatted with `black` before committing. The CI pipeline will check this.
- **Linter:** We use `flake8` and `eslint` for linting. Address linting errors reported by `flake8`. The CI pipeline will check this.
  - Max line length: 120 characters (as configured in CI).
- **Type Hinting:** All new Python code should include type hints as per [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/). Strive for comprehensive type coverage.
- **Docstrings:**
  - All modules, classes, functions, and methods should have clear, concise docstrings.
  - Follow [PEP 257 -- Docstring Conventions](https://www.python.org/dev/peps/pep-0257/).
  - Use a consistent docstring format NumPy Docstring style.
- **File and Module Length:**
  - Strive to keep Python source files (`.py`) concise and focused.
  - Ideally, files should not exceed **900 lines** of code (excluding comments and blank lines).
  - Files should be considered for refactoring if they exceed **1000 lines**.
  - This encourages modularity and makes code easier to understand, test, and maintain.

## 2. Naming Conventions

- **Modules:** `lowercase_with_underscores.py`
- **Packages:** `lowercase_with_underscores`
- **Classes:** `CapWords` (e.g., `TradingModel`, `DataConnector`)
- **Functions & Methods:** `lowercase_with_underscores()`
- **Variables:** `lowercase_with_underscores`
- **Constants:** `ALL_CAPS_WITH_UNDERSCORES`

## 3. Imports

- Imports should be grouped in the following order:
  1.  Standard library imports (e.g., `import os`, `import logging`).
  2.  Related third-party imports (e.g., `import pandas as pd`, `import yaml`).
  3.  Local application/library specific imports (e.g., `from app import config`, `from app.services import DataIngestionService`).
- Use absolute imports where possible.
- Avoid `from module import *`.

## 4. Error Handling

- Use specific exception types where possible. Avoid catching generic `Exception` unless necessary and re-raising or handling appropriately.
- Log errors effectively.
- Clean up resources in `finally` blocks where appropriate.
- Minimize the use of fallback code. Prefer to fail fast and handle errors at a higher level.

## 5. Testing

- Strive for high test coverage.
- Unit tests should be small and focused.
- Integration tests should verify interactions between components.
- Follow Arrange-Act-Assert (AAA) pattern in tests where applicable.

## 6. Security Considerations

- Never commit secrets or sensitive data to the repository. Use environment variables and a secrets management strategy (see project plan).
- Be mindful of input validation and sanitization, especially for APIs.
- (More to be added as specific security concerns arise)

---
