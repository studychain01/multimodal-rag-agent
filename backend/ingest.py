import os
import json
import base64
from pathlib import Path

import pymupdf
import anthropic
import chromadb
from dotenv import load_dotenv

load_dotenv()

# ── clients ──────────────────────────────────────────────
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

chroma_client = chromadb.PersistentClient(path="./knowledge_base")

collection = chroma_client.get_or_create_collection(
    name="vulcan_omnipro"
)

# ── config ────────────────────────────────────────────────
DOCUMENTS = {
    "owner-manual":      "files/owner-manual.pdf",
    "quick-start-guide": "files/quick-start-guide.pdf",
    "selection-chart":   "files/selection-chart.pdf",
}

PAGES_DIR = Path("files/pages")

# ── prompts ───────────────────────────────────────────────
SINGLE_PAGE_PROMPT = """
You are analyzing page {page_num} from the {source} of the 
Vulcan OmniPro 220 welder manual.

Extract all content from this page and return chunks.
Each chunk is one self-contained concept that can independently 
answer a user question.

For each chunk return:
{{
    "header": "section title",
    "content": "all text for this concept",
    "has_diagram": true/false,
    "diagram_description": "detailed semantic description of any diagrams, 
                            photos, schematics — what it shows, labels, 
                            connections, values visible",
    "has_table": true/false,
    "table_text": "table converted to readable sentences if has_table",
    "content_type": "one of: safety/specs/setup/troubleshooting/parts/tips"
}}

Also return:
{{
    "chunks": [...],
    "is_complete": true if page ends at natural section boundary,
    "is_complete": false if content clearly continues onto next page,
    "reason": "brief explanation if is_complete is false"
}}

Signs of incomplete page:
- Table starts but does not finish
- Numbered list continues beyond page
- Section header at bottom with no content below it
- Content cuts off mid-sentence or mid-paragraph
- Diagram referenced but not shown

CRITICAL: Return ONLY the JSON object.
No preamble. No explanation. No markdown code fences.
Start your response with {{ and end with }}.
Nothing before the opening brace.
Nothing after the closing brace.
"""

MULTI_PAGE_PROMPT = """
You are analyzing pages {page_nums} together from the {source} 
of the Vulcan OmniPro 220 welder manual.

These pages are being analyzed together because content runs 
across page boundaries.

Extract ALL chunks across both pages. Each chunk is one 
self-contained concept.

For each chunk return:
{{
    "header": "section title",
    "content": "all text for this concept",
    "has_diagram": true/false,
    "diagram_description": "detailed semantic description",
    "has_table": true/false,
    "table_text": "table as readable sentences",
    "content_type": "safety/specs/setup/troubleshooting/parts/tips",
    "pages": [list of page numbers this chunk spans]
}}

Important:
- If a concept spans both pages combine content from both into one chunk
- pages field must list ALL pages the chunk content comes from
- Merge cross-page tables into one coherent table_text
- A page can have multiple independent chunks

Return:
{{
    "chunks": [...],
    "is_complete": true/false,
    "reason": "explanation if still incomplete after both pages"
}}

CRITICAL: Return ONLY the JSON object.
No preamble. No explanation. No markdown code fences.
Start your response with {{ and end with }}.
Nothing before the opening brace.
Nothing after the closing brace.
"""

SLIDING_WINDOW_PROMPT = """
You are analyzing pages {page_nums} together from the {source}
of the Vulcan OmniPro 220 welder manual.

This is a sliding window over a long section. Some content from
the edges may overlap with adjacent windows — that is expected.

Extract chunks that are fully contained within these pages.
If content starts on the first page but clearly continues beyond
the last page, mark that chunk as is_complete: false.

For each chunk return:
{{
    "header": "section title",
    "content": "all text for this concept",
    "has_diagram": true/false,
    "diagram_description": "detailed semantic description",
    "has_table": true/false,
    "table_text": "table as readable sentences",
    "content_type": "safety/specs/setup/troubleshooting/parts/tips",
    "pages": [page numbers],
    "is_complete": true/false
}}

Return:
{{
    "chunks": [...],
}}

CRITICAL: Return ONLY the JSON object.
No preamble. No explanation. No markdown code fences.
Start your response with {{ and end with }}.
Nothing before the opening brace.
Nothing after the closing brace.
"""

# ── helpers ───────────────────────────────────────────────
def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def build_image_content(image_path: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": image_to_base64(image_path)
        }
    }

def call_claude(content: list) -> dict:
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

# ── extraction functions ──────────────────────────────────
def extract_single_page(page_num: int, image_path: str, source: str) -> dict:
    prompt = SINGLE_PAGE_PROMPT.format(
        page_num=page_num,
        source=source
    )
    content = [
        build_image_content(image_path),
        {"type": "text", "text": prompt}
    ]
    result = call_claude(content)
    
    for chunk in result["chunks"]:
        chunk["pages"] = chunk.get("pages", [page_num])
        chunk["source"] = source
    
    return result

def extract_multi_page(page_nums: list, image_paths: list, source: str,
                       prompt_template: str = None) -> dict:
    if prompt_template is None:
        prompt_template = MULTI_PAGE_PROMPT
    
    prompt = prompt_template.format(
        page_nums=page_nums,
        source=source
    )
    
    content = []
    for page_num, image_path in zip(page_nums, image_paths):
        content.append({"type": "text", "text": f"=== PAGE {page_num} ==="})
        content.append(build_image_content(image_path))
    
    content.append({"type": "text", "text": prompt})
    
    result = call_claude(content)
    
    for chunk in result["chunks"]:
        if "pages" not in chunk:
            chunk["pages"] = page_nums
        chunk["source"] = source
    
    return result

def sliding_window_extract(page_nums: list, image_paths: list,
                           source: str, window_size: int = 3,
                           overlap: int = 1) -> list:
    all_chunks = []
    seen_fingerprints = set()
    step = window_size - overlap
    
    for start in range(0, len(page_nums), step):
        end = min(start + window_size, len(page_nums))
        window_page_nums = page_nums[start:end]
        window_image_paths = image_paths[start:end]
        
        result = extract_multi_page(
            window_page_nums,
            window_image_paths,
            source,
            prompt_template=SLIDING_WINDOW_PROMPT
        )
        
        for chunk in result["chunks"]:
            fp_content = _norm_content(chunk)[:80]
            fingerprint = f"{chunk.get('source', '')}-{_norm_header(chunk)}-{fp_content}"
            if fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)
                all_chunks.append(chunk)
    
    return all_chunks

# ── storage ───────────────────────────────────────────────
def _norm_header(chunk: dict) -> str:
    """LLM JSON may omit header or use null; avoid crashes in ids and text."""
    h = chunk.get("header")
    if h is None:
        return "Unknown section"
    s = str(h).strip()
    return s if s else "Unknown section"


def _norm_content(chunk: dict) -> str:
    c = chunk.get("content")
    if c is None:
        return ""
    return str(c).strip()


def build_chunk_text(chunk: dict) -> str:
    header = _norm_header(chunk)
    content = _norm_content(chunk)
    parts = [
        f"Section: {header}",
        f"Source: {chunk.get('source', '')} | Pages: {chunk.get('pages', [])}",
        "",
        content,
    ]
    dd = chunk.get("diagram_description")
    if dd:
        parts.append(f"\nDiagram: {dd}")
    tt = chunk.get("table_text")
    if tt:
        parts.append(f"\nTable: {tt}")
    return "\n".join(parts).strip()


def store_chunks(chunks: list):
    ids, documents, metadatas = [], [], []
    
    for chunk in chunks:
        chunk_text = build_chunk_text(chunk)
        
        pages = chunk.get("pages", [])
        page_start = min(pages) if pages else 0
        page_end = max(pages) if pages else 0
        
        header = _norm_header(chunk)
        slug = (
            header[:40]
            .lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace("\\", "-")
        ) or "section"

        chunk_id = f"{chunk.get('source', 'unknown')}-p{page_start}-{slug}"
        
        base_id = chunk_id
        counter = 0
        while chunk_id in ids:
            counter += 1
            chunk_id = f"{base_id}-{counter}"
        
        metadata = {
            "source":       chunk.get("source", ""),
            "page_start":   page_start,
            "page_end":     page_end,
            "pages":        json.dumps(pages),
            "section":      header,
            "has_diagram":  chunk.get("has_diagram", False),
            "has_table":    chunk.get("has_table", False),
            "content_type": chunk.get("content_type") or "general",
        }
        
        ids.append(chunk_id)
        documents.append(chunk_text)
        metadatas.append(metadata)
    
    if ids:
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

# ── pdf processing ────────────────────────────────────────
def convert_pdf_to_images(pdf_path: str, source: str) -> list:
    """Rasterize PDF to PNGs via PyMuPDF (pip package `pymupdf`)."""
    output_dir = PAGES_DIR / source
    output_dir.mkdir(parents=True, exist_ok=True)

    dpi = 200
    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    image_paths = []
    doc = pymupdf.open(pdf_path)
    try:
        for i in range(len(doc)):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            path = output_dir / f"page_{i+1}.png"
            pix.save(str(path))
            image_paths.append(str(path))
    finally:
        doc.close()

    return image_paths

# ── main ingestion loop ───────────────────────────────────
def ingest_document(source: str, pdf_path: str):
    image_paths = convert_pdf_to_images(pdf_path, source)
    total_pages = len(image_paths)
    
    i = 0
    while i < total_pages:
        page_num = i + 1
        image_path = image_paths[i]
        
        result = extract_single_page(page_num, image_path, source)
        
        if result["is_complete"]:
            store_chunks(result["chunks"])
            i += 1
        
        else:
            section_page_nums = [page_num]
            section_image_paths = [image_path]
            i += 1
            
            while i < total_pages:
                next_page_num = i + 1
                next_image_path = image_paths[i]
                
                next_result = extract_single_page(
                    next_page_num, next_image_path, source
                )
                
                section_page_nums.append(next_page_num)
                section_image_paths.append(next_image_path)
                i += 1
                
                if next_result["is_complete"]:
                    break
            
            if len(section_page_nums) == 1:
                store_chunks(result["chunks"])
            
            elif len(section_page_nums) == 2:
                pair_result = extract_multi_page(
                    section_page_nums,
                    section_image_paths,
                    source
                )
                store_chunks(pair_result["chunks"])
            
            else:
                chunks = sliding_window_extract(
                    section_page_nums,
                    section_image_paths,
                    source
                )
                store_chunks(chunks)

# ── entry point ───────────────────────────────────────────
def main():
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    for source, pdf_path in DOCUMENTS.items():
        if not Path(pdf_path).exists():
            continue
        ingest_document(source, pdf_path)

if __name__ == "__main__":
    main()