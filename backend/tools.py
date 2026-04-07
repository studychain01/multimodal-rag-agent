import json
import logging
from pathlib import Path
import chromadb

logger = logging.getLogger(__name__)

# ── clients ──────────────────────────────────────────────
chroma_client = chromadb.PersistentClient(path="./knowledge_base")

collection = chroma_client.get_or_create_collection(
    name="vulcan_omnipro"
)

PAGES_DIR = Path("files/pages")

# ── tool definitions (JSON schema for Claude) ─────────────
TOOL_DEFINITIONS = [
    {
        "name": "search_knowledge_base",
        "description": """Search the Vulcan OmniPro 220 manual for relevant 
        information. Use this to find technical specs, procedures, 
        troubleshooting steps, safety information, or any content 
        from the manual. Call this first before answering any question.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — be specific and technical"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["safety", "specs", "setup", "troubleshooting", 
                             "parts", "tips", "any"],
                    "description": "Filter by content type. Use any if unsure."
                },
                "n_results": {
                    "type": "integer",
                    "description": "Number of results to return. Default 3.",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_page_image",
        "description": """Confirm which manual page PNGs exist on disk and attach a caption.
        Does not return image bytes — the client loads images via GET /page/{source}/{page}.
        Use when a diagram, schematic, or photo should appear in the UI; then include
        manual_image blocks with the same source and pages (use pages_found from the result).
        Call after search_knowledge_base when has_diagram is true or a visual is needed.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["owner-manual", "quick-start-guide", "selection-chart"],
                    "description": "Which document the page is from"
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Page numbers to retrieve. Can be multiple for cross-page sections."
                },
                "caption": {
                    "type": "string",
                    "description": "Caption to show under the image"
                }
            },
            "required": ["source", "pages", "caption"]
        }
    },
    {
        "name": "find_relevant_pages",
        "description": """Find which manual pages are most relevant to a topic.
        Use this when you need to know which pages cover a specific subject
        before deciding whether to retrieve images.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic to find pages for"
                },
                "has_diagram": {
                    "type": "boolean",
                    "description": "Filter to only pages with diagrams. Default false."
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "emit_component",
        "description": """Emit an interactive React component for the user.
        Use this when the answer requires user input to calculate or configure.
        Available components:
        - DutyCycleCalculator: for duty cycle questions (needs process, amps, voltage)
        - WireSettingsConfigurator: for wire/material setup questions
        - PolarityDiagram: for polarity/cable connection questions""",
        "input_schema": {
            "type": "object",
            "properties": {
                "component": {
                    "type": "string",
                    "enum": ["DutyCycleCalculator", "WireSettingsConfigurator", 
                             "PolarityDiagram"],
                    "description": "Which component to render"
                },
                "props": {
                    "type": "object",
                    "description": "Props to pass to the component based on context"
                }
            },
            "required": ["component", "props"]
        }
    }
]

# ── tool implementations ──────────────────────────────────
def search_knowledge_base(query: str, content_type: str = "any", 
                          n_results: int = 3) -> dict:
    where = None
    if content_type != "any":
        where = {"content_type": content_type}
    
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"]
    )
    
    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "content":      results["documents"][0][i],
            "source":       results["metadatas"][0][i]["source"],
            "section":      results["metadatas"][0][i]["section"],
            "page_start":   results["metadatas"][0][i]["page_start"],
            "page_end":     results["metadatas"][0][i]["page_end"],
            "pages":        json.loads(results["metadatas"][0][i]["pages"]),
            "has_diagram":  results["metadatas"][0][i]["has_diagram"],
            "has_table":    results["metadatas"][0][i]["has_table"],
            "relevance":    round(1 - results["distances"][0][i], 3)
        })
    
    return {
        "query": query,
        "results": chunks,
        "hint": "If has_diagram is true on a result, consider calling get_page_image"
    }

def get_page_image(source: str, pages: list, caption: str) -> dict:
    """Check page files only; never embed base64 (keeps tool_result small for the API)."""
    pages_found = []
    pages_missing = []
    for page in pages:
        image_path = PAGES_DIR / source / f"page_{page}.png"
        if image_path.exists():
            pages_found.append(page)
        else:
            pages_missing.append(page)

    return {
        "source": source,
        "pages_requested": list(pages),
        "pages_found": pages_found,
        "pages_missing": pages_missing,
        "caption": caption,
        "note": (
            "Images are served to the user by the app, not in this result. "
            "Use manual_image blocks with source and pages_found (omit missing pages)."
        ),
    }

def find_relevant_pages(topic: str, has_diagram: bool = False) -> dict:
    where = {"has_diagram": True} if has_diagram else None
    
    results = collection.query(
        query_texts=[topic],
        n_results=5,
        where=where,
        include=["metadatas", "distances"]
    )
    
    pages = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        pages.append({
            "source":      meta["source"],
            "page_start":  meta["page_start"],
            "page_end":    meta["page_end"],
            "section":     meta["section"],
            "has_diagram": meta["has_diagram"],
            "relevance":   round(1 - results["distances"][0][i], 3)
        })
    
    return {
        "topic": topic,
        "pages": pages
    }

def emit_component(component: str, props: dict) -> dict:
    return {
        "component": component,
        "props":     props
    }


# ── tool router ───────────────────────────────────────────
def execute_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name == "search_knowledge_base":
        out = search_knowledge_base(**tool_input)
    elif tool_name == "get_page_image":
        out = get_page_image(**tool_input)
    elif tool_name == "find_relevant_pages":
        out = find_relevant_pages(**tool_input)
    elif tool_name == "emit_component":
        out = emit_component(**tool_input)
    else:
        logger.warning("unknown_tool name=%s", tool_name)
        return {"error": f"Unknown tool: {tool_name}"}

    return out