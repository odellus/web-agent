
import sys

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def build_app(tmp_path: Path, monkeypatch) -> TestClient:
    """
    Configure environment for the backend to serve from tmp_path and return a TestClient
    for the FastAPI app defined in treesitter-backend/main.py.
    """
    # Ensure module import path contains the backend directory
    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_dir))

    # Point workspace to the test directory
    monkeypatch.setenv("WORKSPACE_DIR", str(tmp_path))

    # Import (or reload) the backend module so it picks up the env var
    if "main" in sys.modules:
        del sys.modules["main"]


    # Build client
    from main import app  # noqa: E402
    client = TestClient(app)
    return client


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    return build_app(tmp_path, monkeypatch)


def test_health_returns_workspace(client: TestClient, tmp_path: Path):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert Path(data["workspace"]).resolve() == tmp_path.resolve()


def test_list_and_read_files(client: TestClient, tmp_path: Path):
    # Create a directory and a couple of files
    subdir = tmp_path / "src"
    subdir.mkdir()
    f1 = tmp_path / "README.md"
    f1.write_text("# Test Workspace\n", encoding="utf-8")
    f2 = subdir / "example.py"
    f2.write_text(
        "def foo(x: int) -> int:\n"
        "    return x + 1\n",
        encoding="utf-8",
    )

    # List root directory
    resp = client.get("/files", params={"path": ""})
    assert resp.status_code == 200
    data = resp.json()
    names = [e["name"] for e in data["entries"]]
    assert "README.md" in names
    assert "src" in names

    # List subdir
    resp = client.get("/files", params={"path": "src"})
    assert resp.status_code == 200
    data = resp.json()
    assert [e["name"] for e in data["entries"]] == ["example.py"]

    # Read file
    resp = client.get("/file", params={"path": "README.md"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == "README.md"
    assert data["content"].startswith("# Test Workspace")


def test_save_file_and_read_back(client: TestClient, tmp_path: Path):

    # Save content
    content = "Hello, TreeSitter backend!\n"
    resp = client.post("/save", json={"path": "notes.txt", "content": content})
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["path"] == "notes.txt"
    assert meta["size"] == len(content)

    # Read back
    resp = client.get("/file", params={"path": "notes.txt"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == content


def test_languages_endpoint(client: TestClient):
    resp = client.get("/languages")
    assert resp.status_code == 200
    data = resp.json()
    assert "supported" in data
    # At least Python should be supported via tree-sitter-languages
    assert "python" in data["supported"]


def test_parse_python_file(client: TestClient, tmp_path: Path):
    py_file = tmp_path / "calc.py"
    py_file.write_text(
        "def add(a, b):\n"
        "    return a + b\n",
        encoding="utf-8",
    )
    # Parse by path (auto-detect language)
    resp = client.post("/parse", json={"path": "calc.py"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "python"
    assert isinstance(data["s_expr"], str)
    # Tree-sitter Python grammar should produce a function_definition node
    assert "function_definition" in data["s_expr"] or "function_def" in data["s_expr"]
    # Summary tree limited by max_depth
    assert "summary" in data
    assert data["summary"]["type"] in ("module", "file_input")


def test_query_python_functions(client: TestClient, tmp_path: Path):
    src = tmp_path / "mathops.py"
    src.write_text(
        "def square(x):\n"
        "    return x*x\n"
        "\n"
        "def cube(y):\n"
        "    return y*y*y\n",
        encoding="utf-8",
    )

    # Query for function definitions and their identifiers using Tree-sitter query syntax
    query = """
    (function_definition
      name: (identifier) @func.name
      parameters: (parameters) @func.params)
    """

    resp = client.post(
        "/query",
        json={
            "path": "mathops.py",
            "query": query,
            "captures_only": True,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["language"] == "python"
    captures = data.get("captures")
    assert isinstance(captures, list)
    # Expect at least two function names captured: square and cube
    names = []
    for cap in captures:
        if cap["name"] == "func.name":
            # Extract substring using byte offsets to verify names
            start = cap["start_byte"]
            end = cap["end_byte"]
            # Read file content to slice by byte range
            buf = src.read_bytes()
            names.append(buf[start:end].decode("utf-8"))
    assert set(names) >= {"square", "cube"}


def test_query_matches_grouping(client: TestClient, tmp_path: Path):
    src = tmp_path / "use.py"
    src.write_text(
        "def bar():\n"
        "    baz()\n",
        encoding="utf-8",
    )

    query = """
    (function_definition
      name: (identifier) @function.def
      body: (block) @function.block)

    (call
      function: (identifier) @function.call
      arguments: (argument_list)? @function.args)
    """

    resp = client.post(
        "/query",
        json={
            "path": "use.py",
            "query": query,
            "captures_only": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    matches = data.get("matches")
    assert isinstance(matches, list)
    # We should have grouped captures for function.def and function.call across matches
    # Flatten capture names across matches
    seen_capture_names = set()
    for m in matches:
        for k in m.keys():
            seen_capture_names.add(k)
    assert "function.def" in seen_capture_names
    assert "function.call" in seen_capture_names
