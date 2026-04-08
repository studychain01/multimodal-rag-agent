import logging
import os
import json
import anthropic
from dotenv import load_dotenv
from tools import TOOL_DEFINITIONS, execute_tool

load_dotenv()

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── system prompt ─────────────────────────────────────────
SYSTEM_PROMPT = """
You are an expert technical support agent for the Vulcan OmniPro 220 
multiprocess welding system. You think like a seasoned field technician 
who has used this machine hundreds of times — not like someone reading 
a manual for the first time.

Your job is to help users set up, operate, troubleshoot, and maintain 
their Vulcan OmniPro 220. Users are typically hobbyists or small shop 
owners standing in their garage trying to get something done.

TOOLS:
You have four tools. Use them intelligently:
- search_knowledge_base: ALWAYS call this first before answering
- get_page_image: confirms page PNGs exist (no image data returned); use pages_found in manual_image blocks
- find_relevant_pages: call when you need to locate which pages cover a topic
- emit_component: call when answer needs user input to calculate or configure

RESPONSE MODALITY RULES:
Every final answer MUST include at least one "text" block with a clear explanation.
The FIRST element of "blocks" MUST be {"type": "text", "content": "..."} — never start
"blocks" with mermaid, manual_image, svg, or component only.
Put intros like "I have enough information…" or "Let me create this…" ONLY inside that
first text block's "content", never as separate prose outside the JSON.

Use get_page_image when:
- A wiring diagram, cable setup, or connection schematic is relevant
- Weld diagnosis photos would help identify the problem
- The manual page has a visual that directly answers the question
- has_diagram is true in search results
After get_page_image, put the same source and pages_found (not pages_missing) in manual_image blocks; the UI fetches pixels from the server.

Use emit_component when:
- Duty cycle question → DutyCycleCalculator
- Wire settings, material thickness, voltage → WireSettingsConfigurator  
- Polarity or cable connection question → PolarityDiagram

Do NOT use images or components when:
- Simple yes/no factual answer
- Safety warning that needs no visual
- Short answer where text is sufficient

SEARCH RULES:
- Always search before answering — never answer from memory alone
- Maximum 4 search calls per response
- Do not search for the same thing twice
- If you have enough information stop searching and answer
- Your search history is visible in the conversation

TONE:
- Direct and practical — the user wants to get welding, not read an essay
- Warn about safety issues but don't be preachy
- If a question is ambiguous ask ONE clarifying question
- Never make up specs — only use information from the manual

RESPONSE FORMAT:
Return a JSON object with this exact structure:
{
    "blocks": [
        {
            "type": "text",
            "content": "your explanation here"
        },
        {
            "type": "manual_image",
            "source": "owner-manual",
            "pages": [24],
            "caption": "TIG cable setup diagram"
        },
        {
            "type": "svg",
            "markup": "<svg>...</svg>"
        },
        {
            "type": "mermaid",
            "diagram": "flowchart TD\\n  A --> B"
        },
        {
            "type": "component",
            "name": "DutyCycleCalculator",
            "props": {"defaultProcess": "MIG", "defaultAmps": 200}
        }
    ]
}

MERMAID RULES (when you include a "mermaid" block — invalid syntax breaks rendering in the UI):
- Start the diagram with a single line: flowchart TD or flowchart LR (prefer flowchart TD).
- Use SIMPLE node IDs: letters/digits/underscore only (e.g. A, B, Q1, CHECK_GAS). No spaces or punctuation in IDs.
- Declare each ID before use. One statement per line inside the "diagram" string (separate with \\n in JSON).
- Node shapes (ID required): A[rectangle], B(rounded), C{decision?}, D([stadium]). Keep labels SHORT and ASCII-only.
- Do NOT use HTML in labels: no <br/>, no <b>, no emoji, no smart quotes. Use plain words; split long text into multiple small nodes if needed.
- Edge labels: A -->|Yes| B — keep the |label| part short; avoid nested double-quotes inside labels.
- Decision nodes: only use braces as in ID{question?} (one ID, one pair of braces). Do not put { } inside [square] or (round) labels.
- Prefer fewer than ~25 nodes; simplify or summarize rather than one giant chart.
- Test mentally: every line should look like valid Mermaid flowchart syntax for v10+.

Only include block types that are actually needed after the required leading "text" block.
You may add more "text" blocks later (e.g. a summary table after a diagram).

OUTPUT DISCIPLINE (critical — the server runs json.loads on your whole message string):
- The FIRST character of your final message MUST be `{` (opening brace). The LAST must be `}`.
- Zero characters before `{` — no blank lines, no "Based on…", no "Here is…" outside JSON.
- Do NOT wrap the JSON in markdown code fences (no ``` or ```json).
- Do NOT put any prose after the closing `}`.
- Put every explanation, disclaimer, safety note, and markdown-style table INSIDE "content"
  strings of "text" blocks (you may use multiple "text" blocks).
- Escape newlines as \\n and quotes as \\" inside JSON strings so the document is valid JSON.
- For "mermaid", put the diagram source in the "diagram" string with \\n for newlines; do not
  break out of the JSON string.
"""

# ── agent loop ────────────────────────────────────────────
MAX_ITERATIONS = 10


def _serialize_assistant_content(content) -> list | str:
    """Turn SDK assistant blocks into JSON-storable dicts for session replay."""
    if isinstance(content, str):
        return content
    blocks = []
    for block in content:
        t = getattr(block, "type", None)
        if t == "text":
            blocks.append({"type": "text", "text": block.text})
        elif t == "tool_use":
            blocks.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
        elif t == "thinking":
            continue
        else:
            logger.debug("session_serialize_skip type=%s", t)
    return blocks


def run_agent(
    user_message: str,
    conversation_history: list | None = None,
    memory_summary: str = "",
) -> tuple[dict, list]:
    """
    Run one user turn. Returns (blocks_response, messages_to_store) where messages_to_store
    is the full API message list after this turn (JSON-serializable dicts).
    """
    if conversation_history is None:
        conversation_history = []

    system = SYSTEM_PROMPT
    mem = (memory_summary or "").strip()
    if mem:
        system = SYSTEM_PROMPT + "\n\n## Earlier in this session (summary)\n" + mem

    messages = list(conversation_history) + [
        {"role": "user", "content": user_message}
    ]

    iteration = 0

    while iteration < MAX_ITERATIONS:

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=4096,
            system=system,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)
            final_text = "\n".join(text_parts).strip()
            if final_text:
                messages.append({
                    "role": "assistant",
                    "content": final_text,
                })
            return parse_final_response(response), messages

        if response.stop_reason == "tool_use":
            messages.append({
                "role": "assistant",
                "content": _serialize_assistant_content(response.content),
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({
                "role": "user",
                "content": tool_results,
            })

            iteration += 1
            continue

        break

    logger.warning("max_iterations_reached limit=%s", MAX_ITERATIONS)
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    final_text = "\n".join(text_parts).strip()
    if final_text:
        messages.append({"role": "assistant", "content": final_text})
    return parse_final_response(response), messages

# ── response parser ───────────────────────────────────────
_json_decoder = json.JSONDecoder()


def _decode_blocks_object(s: str) -> dict | None:
    """Find first JSON object in s that contains a top-level \"blocks\" key."""
    for i, c in enumerate(s):
        if c != "{":
            continue
        try:
            obj, _ = _json_decoder.raw_decode(s, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "blocks" in obj:
            return obj
    return None


def _extract_blocks_json(text: str) -> dict | None:
    """Parse {\"blocks\": [...]} from raw model text, prose/code fences allowed."""
    t = text.strip()
    if not t:
        return None

    candidates = [t]
    parts = t.split("```")
    for i in range(1, len(parts), 2):
        seg = parts[i].strip()
        if seg.lower().startswith("json"):
            seg = seg[4:].lstrip("\n").strip()
        if seg.startswith("{"):
            candidates.append(seg)

    seen: set[str] = set()
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        out = _decode_blocks_object(cand)
        if out is not None:
            return out
    return None


def parse_final_response(response) -> dict:
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    text_content = "\n".join(text_parts).strip()

    if not text_content:
        return {
            "blocks": [{
                "type": "text",
                "content": "I could not find an answer to that question."
            }]
        }

    parsed = _extract_blocks_json(text_content)
    if parsed is not None:
        return parsed

    return {
        "blocks": [{
            "type": "text",
            "content": text_content
        }]
    }

# ── test ──────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    test_questions = [
        "What's the duty cycle for MIG welding at 200A on 240V?",
        "I'm getting porosity in my flux-cored welds. What should I check?",
        "What polarity setup do I need for TIG welding?"
    ]
    
    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print(f"{'='*60}")
        
        result, _msgs = run_agent(question)

        print(f"\n{'─' * 60}")
        print("FINAL ANSWER (parsed blocks)")
        print(f"{'─' * 60}")

        for block in result["blocks"]:
            print(f"\n▸ {block['type'].upper()}")
            print("  " + "·" * 56)
            if block["type"] == "text":
                print(block["content"])
            elif block["type"] == "manual_image":
                print(f"  Source: {block['source']}, Pages: {block['pages']}")
                if block.get("caption"):
                    print(f"  Caption: {block['caption']}")
            elif block["type"] == "component":
                print(f"  Component: {block['name']}, Props: {block['props']}")
            elif block["type"] == "mermaid":
                print(block["diagram"])
            elif block["type"] == "svg":
                markup = block["markup"]
                if len(markup) > 2000:
                    print(markup[:2000] + "\n  … [SVG truncated after 2000 chars]")
                else:
                    print(markup)