# TreeSitter Backend

FastAPI backend that exposes a real filesystem over HTTP and provides Tree-sitter parsing/query capabilities for code-aware web IDEs. Agent state stays in your agent framework; this service focuses purely on the non-agentic filesystem and code analysis layer.

## Features

- Serve a workspace directory safely (prevents path traversal)
- List directories and read/write files via HTTP
- Parse files or raw content with Tree-sitter
- Run Tree-sitter queries (captures or grouped matches)
- CORS enabled for local UI development

## Requirements

- Python 3.12+
- A virtual environment tool (uv recommended)
- Dependencies defined in `pyproject.toml`:
  - `fastapi`
  - `uvicorn[standard]`
  - `tree-sitter`
  - `tree-sitter-languages`
  - `pytest` (for tests)

## Quickstart

### 1) Install dependencies

Using `uv`:

```bash
cd agentic_platform/treesitter-backend
uv sync
```

Or with pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r <generate from pyproject or install manually>
```

### 2) Choose a workspace

By default, the server uses the current working directory. Set `WORKSPACE_DIR` to point at the codebase you want to serve:

```bash
export WORKSPACE_DIR=/path/to/your/workspace
```

### 3) Run the server

```bash
# From the backend directory
uv run python main.py
# or
python main.py
```

Environment variables:
- `WORKSPACE_DIR`: Absolute path to the root directory the API exposes (default: CWD)
- `HOST`: Bind address (default: 0.0.0.0)
- `PORT`: Port (default: 8070)
- `RELOAD`: Enable dev auto-reload (default: true)
- `CORS_ALLOW_ORIGINS`: Comma-separated origins (default: *)

## API Overview

Base URL: `http://localhost:8070`

- `GET /health`
  - Returns `{ status: "ok", workspace: "<path>" }`

- `GET /languages`
  - Returns supported Tree-sitter language ids (e.g., `python`, `javascript`, ...)

- `GET /files?path=<relative_dir>`
  - List directory contents under the workspace root

- `GET /file?path=<relative_file>`
  - Read a file’s content as UTF-8

- `POST /save`
  - Save file contents
  - Body:
    ```json
    {
      "path": "relative/file.txt",
      "content": "new content"
    }
    ```

- `POST /parse`
  - Parse a file or raw content with Tree-sitter, returning s-expression and a compact JSON summary
  - Body (file path):
    ```json
    {
      "path": "src/example.py",
      "max_depth": 2
    }
    ```
  - Body (raw content):
    ```json
    {
      "language": "python",
      "content": "def foo():\n    return 1\n",
      "max_depth": 2
    }
    ```

- `POST /query`
  - Run a Tree-sitter query against a file or raw content
  - Body:
    ```json
    {
      "path": "src/example.py",
      "query": "(function_definition name: (identifier) @func.name)",
      "captures_only": true
    }
    ```
    Or:
    ```json
    {
      "language": "python",
      "content": "def foo():\n    return 1\n",
      "query": "(function_definition name: (identifier) @func.name)",
      "captures_only": false
    }
    ```

## Example usage

List root:

```bash
curl "http://localhost:8070/files?path="
```

Read file:

```bash
curl "http://localhost:8070/file?path=README.md"
```

Save file:

```bash
curl -X POST "http://localhost:8070/save" \
  -H "Content-Type: application/json" \
  -d '{"path":"notes.txt","content":"Hello, TreeSitter!"}'
```

Parse Python file:

```bash
curl -X POST "http://localhost:8070/parse" \
  -H "Content-Type: application/json" \
  -d '{"path":"src/example.py","max_depth":2}'
```

Query functions:

```bash
curl -X POST "http://localhost:8070/query" \
  -H "Content-Type: application/json" \
  -d '{
    "path":"src/example.py",
    "query":"(function_definition name: (identifier) @func.name)",
    "captures_only":true
  }'
```

## Running tests

Tests use `pytest` and FastAPI’s `TestClient`. They create a temporary workspace and exercise the endpoints.

```bash
cd agentic_platform/treesitter-backend
uv run pytest -q
# or
pytest -q
```

## Notes and tips

- Language detection is based on file extension. You can override with `language` in `parse/query` requests.
- Paths are validated to prevent traversal outside `WORKSPACE_DIR`.
- For large files or real-time editing, you can extend the backend with file watchers and WebSocket/SSE endpoints.
- If a language isn’t recognized, ensure `tree-sitter-languages` supports it or provide your own grammar binding.

## Troubleshooting

- Parser errors for a language:
  - Verify the language id is supported by `tree-sitter-languages` (e.g., `python`, `javascript`, `typescript`, `json`, etc.).
- Unicode decoding errors:
  - The backend reads as UTF-8 with `errors="replace"` fallback.
- CORS issues:
  - Set `CORS_ALLOW_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"` to match your frontend origins.

## License

MIT