import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Tree-sitter Python bindings
from tree_sitter import Parser, Language, Query as TSQuery, QueryCursor
# Convenience loaders for multiple languages
from tree_sitter_languages import get_language

# -----------------------------------------------------------------------------
# Configuration and setup
# -----------------------------------------------------------------------------

logger = logging.getLogger("treesitter-backend")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Root directory that the backend exposes. Default to CWD or env var WORKSPACE_DIR.
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", os.getcwd())).resolve()
if not WORKSPACE_DIR.exists() or not WORKSPACE_DIR.is_dir():
    logger.warning(f"WORKSPACE_DIR {WORKSPACE_DIR} does not exist or is not a directory. Falling back to CWD.")
    WORKSPACE_DIR = Path.cwd().resolve()

logger.info(f"Treesitter backend serving workspace: {WORKSPACE_DIR}")

# Map common file extensions to tree-sitter language identifiers
EXT_TO_LANG: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".json": "json",
    ".md": "markdown",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".swift": "swift",
    ".rb": "ruby",
    ".php": "php",
    ".css": "css",
    ".scss": "css",
    ".sql": "sql",
    ".jl": "julia",
}

# Cache parsers per language
PARSER_CACHE: Dict[str, Parser] = {}

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def safe_join(root: Path, rel_path: str) -> Path:
    """
    Safely join a relative path to the root, preventing path traversal outside the root.
    """
    candidate = (root / rel_path).resolve()
    if root not in candidate.parents and candidate != root:
        raise HTTPException(status_code=400, detail="Path traversal outside workspace is not allowed.")
    return candidate


def detect_language(path: Path, override: Optional[str] = None) -> Optional[str]:
    """
    Detect language from file extension, or use override if provided.
    """
    if override:
        return override
    lang = EXT_TO_LANG.get(path.suffix.lower())
    return lang


def get_ts_parser(lang: str) -> Parser:
    """
    Get or create a tree-sitter Parser for the given language.
    """
    if lang in PARSER_CACHE:
        return PARSER_CACHE[lang]
    try:
        if lang == "python":
            # Special-case Python grammar using tree_sitter_python
            import tree_sitter_python as tspython
            py_language = Language(tspython.language())
            parser = Parser(py_language)
        else:
            language = get_language(lang)
            parser = Parser(language)
    except Exception as e:
        logger.error(f"Failed to load parser for language '{lang}': {e}")
        raise HTTPException(status_code=400, detail=f"Unsupported language '{lang}' or parser load error.")
    PARSER_CACHE[lang] = parser
    return parser


def read_text_file(path: Path) -> str:
    """
    Read a text file as UTF-8 (fallback with errors=replace).
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.error(f"Failed to read file {path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")


def node_to_dict(node, max_depth: int = 2, depth: int = 0) -> Dict[str, Any]:
    """
    Convert a Tree-sitter node to a compact JSON dictionary, limited by max_depth.
    """
    d = {
        "type": node.type,
        "start_point": node.start_point,
        "end_point": node.end_point,
        "start_byte": node.start_byte,
        "end_byte": node.end_byte,
        "child_count": node.child_count,
    }
    if depth < max_depth and node.child_count > 0:
        children = []
        # Iterate direct children
        for i in range(node.child_count):
            try:
                child = node.child(i)
                if child is None:
                    continue
                children.append(node_to_dict(child, max_depth=max_depth, depth=depth + 1))
            except Exception:
                continue
        d["children"] = children
    return d


def parse_source(lang: str, source: str) -> Tuple[Any, Parser]:
    """
    Parse source text into a Tree-sitter tree using language parser.
    """
    parser = get_ts_parser(lang)
    # Tree-sitter expects bytes (UTF-8)
    tree = parser.parse(bytes(source, "utf-8"))
    return tree, parser


def load_language(lang: str) -> Language:
    """
    Load a Tree-sitter Language object.
    """
    try:
        if lang == "python":
            import tree_sitter_python as tspython
            return Language(tspython.language())
        return get_language(lang)
    except Exception as e:
        logger.error(f"Failed to load Language for '{lang}': {e}")
        raise HTTPException(status_code=400, detail=f"Unsupported language '{lang}' or language load error.")


# -----------------------------------------------------------------------------
# Pydantic models
# -----------------------------------------------------------------------------

class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    mtime: Optional[float] = None


class ListResponse(BaseModel):
    root: str
    path: str
    entries: List[FileEntry]


class ReadResponse(BaseModel):
    path: str
    content: str


class SaveRequest(BaseModel):
    path: str = Field(..., description="Relative file path under workspace")
    content: str = Field(..., description="UTF-8 file content")


class ParseRequest(BaseModel):
    path: Optional[str] = Field(None, description="Relative file path to parse")
    language: Optional[str] = Field(None, description="Language override (e.g., 'python')")
    content: Optional[str] = Field(None, description="Raw source content to parse if path is not provided")
    max_depth: int = Field(2, ge=0, le=6, description="Max depth of JSON tree returned")


class ParseResponse(BaseModel):
    language: str
    s_expr: str
    summary: Dict[str, Any]


class QueryRequest(BaseModel):
    path: Optional[str] = Field(None, description="Relative file path to query")
    language: Optional[str] = Field(None, description="Language override (e.g., 'python')")
    content: Optional[str] = Field(None, description="Raw source content to query if path is not provided")
    query: str = Field(..., description="Tree-sitter query pattern")
    captures_only: bool = Field(True, description="Return captures-only (True) or match groups (False)")


class CaptureRecord(BaseModel):
    name: str
    type: str
    start_point: Tuple[int, int]
    end_point: Tuple[int, int]
    start_byte: int
    end_byte: int


class QueryResponse(BaseModel):
    language: str
    captures: Optional[List[CaptureRecord]] = None
    matches: Optional[List[Dict[str, List[CaptureRecord]]]] = None


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(title="TreeSitter Backend", version="0.1.0")

# Allow local dev UIs to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "workspace": str(WORKSPACE_DIR)}


@app.get("/languages")
def languages() -> Dict[str, Any]:
    return {"supported": sorted(set(EXT_TO_LANG.values()))}


@app.get("/files", response_model=ListResponse)
def list_files(path: str = Query("", description="Relative directory path under workspace")) -> ListResponse:
    rel = path.strip()
    target = safe_join(WORKSPACE_DIR, rel)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")
    entries: List[FileEntry] = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        try:
            stat = child.stat()
            entries.append(
                FileEntry(
                    name=child.name,
                    path=str(child.relative_to(WORKSPACE_DIR)),
                    is_dir=child.is_dir(),
                    size=None if child.is_dir() else stat.st_size,
                    mtime=stat.st_mtime,
                )
            )
        except Exception:
            continue
    return ListResponse(root=str(WORKSPACE_DIR), path=str(target.relative_to(WORKSPACE_DIR)), entries=entries)


@app.get("/file", response_model=ReadResponse)
def read_file(path: str = Query(..., description="Relative file path under workspace")) -> ReadResponse:
    target = safe_join(WORKSPACE_DIR, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    content = read_text_file(target)
    return ReadResponse(path=str(target.relative_to(WORKSPACE_DIR)), content=content)


@app.post("/save")
def save_file(req: SaveRequest) -> Dict[str, Any]:
    target = safe_join(WORKSPACE_DIR, req.path)
    if not target.parent.exists():
        raise HTTPException(status_code=400, detail="Parent directory does not exist")
    try:
        target.write_text(req.content, encoding="utf-8")
        stat = target.stat()
        return {
            "path": str(target.relative_to(WORKSPACE_DIR)),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
        }
    except Exception as e:
        logger.error(f"Failed to write file {target}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")


@app.post("/parse", response_model=ParseResponse)
def parse(req: ParseRequest) -> ParseResponse:
    # Determine source
    source: Optional[str] = None
    path: Optional[Path] = None
    if req.path:
        path = safe_join(WORKSPACE_DIR, req.path)
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        source = read_text_file(path)
    else:
        source = req.content
    if not source:
        raise HTTPException(status_code=400, detail="Must provide either 'path' or 'content'")

    # Determine language
    lang = req.language or (detect_language(path) if path else None)
    if not lang:
        raise HTTPException(status_code=400, detail="Unable to detect language. Provide 'language' explicitly.")

    # Parse
    tree, _parser = parse_source(lang, source)
    root = tree.root_node

    # Build response
    s_expr = str(root)
    summary = node_to_dict(root, max_depth=req.max_depth)
    return ParseResponse(language=lang, s_expr=s_expr, summary=summary)


@app.post("/query", response_model=QueryResponse)
def query_ts(req: QueryRequest) -> QueryResponse:
    # Determine source
    source: Optional[str] = None
    path: Optional[Path] = None
    if req.path:
        path = safe_join(WORKSPACE_DIR, req.path)
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        source = read_text_file(path)
    else:
        source = req.content
    if not source:
        raise HTTPException(status_code=400, detail="Must provide either 'path' or 'content'")

    # Determine language
    lang = req.language or (detect_language(path) if path else None)
    if not lang:
        raise HTTPException(status_code=400, detail="Unable to detect language. Provide 'language' explicitly.")

    # Parse
    tree, _parser = parse_source(lang, source)
    ts_lang = load_language(lang)

    # Compile and run query
    try:
        q = TSQuery(ts_lang, req.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid query: {e}")

    qc = QueryCursor(q)

    def make_capture(name: str, node) -> CaptureRecord:
        return CaptureRecord(
            name=name,
            type=node.type,
            start_point=node.start_point,
            end_point=node.end_point,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
        )

    if req.captures_only:
        # Flat captures list
        caps = qc.captures(tree.root_node)
        captures: List[CaptureRecord] = []
        # caps is a dict-like with capture names mapping to nodes (py-tree-sitter extended API)
        # For portability, normalize to list of pairs if needed.
        if isinstance(caps, dict):
            for name, nodes in caps.items():
                for node in nodes:
                    captures.append(make_capture(name, node))
        else:
            # Fallback: list of tuples (node, capture_name, ...)
            for item in caps:
                try:
                    node, name = item
                except Exception:
                    # Different bindings may return different tuple shapes
                    node, name = item[0], item[1]
                captures.append(make_capture(name, node))
        return QueryResponse(language=lang, captures=captures)

    # Grouped matches
    matches_resp: List[Dict[str, List[CaptureRecord]]] = []
    matches = qc.matches(tree.root_node)
    # matches is a list of tuples (pattern_index, dict[capture_name] -> [nodes])
    try:
        for _, groups in matches:
            grouped: Dict[str, List[CaptureRecord]] = {}
            for name, nodes in groups.items():
                grouped[name] = [make_capture(name, n) for n in nodes]
            matches_resp.append(grouped)
    except Exception:
        # Fallback for different bindings returning alternate formats
        for m in matches:
            try:
                groups = m[1]
            except Exception:
                continue
            grouped: Dict[str, List[CaptureRecord]] = {}
            for name, nodes in groups.items():
                grouped[name] = [make_capture(name, n) for n in nodes]
            matches_resp.append(grouped)

    return QueryResponse(language=lang, matches=matches_resp)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

def main():
    """
    Run a simple development server. In production, prefer running with a process manager.
    """
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8070"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    logger.info(f"Starting TreeSitter backend on {host}:{port} (reload={reload}) workspace={WORKSPACE_DIR}")
    uvicorn.run("main:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
