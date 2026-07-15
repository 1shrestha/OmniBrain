"""
vlm_client.py

Talks to the Vision-Language Model (GPT-4o here; swap the client for
LLaVA if you're running local/open-source instead).

CHANGED FOR REAL-TIME USE:
- Uses AsyncOpenAI instead of the sync client, so many page calls can
  run at the same time instead of one after another.
- Takes a `semaphore` so the caller (extractor.py) controls exactly
  how many VLM calls run concurrently — this is what stops you from
  slamming into API rate limits while still being much faster than
  sequential.
"""

import base64
import json
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI()  # reads OPENAI_API_KEY from your environment

EXTRACTION_PROMPT = """You are looking at one page from a financial document.

If this page contains a chart, graph, or table, extract it as JSON in
exactly this shape:

{
  "type": "chart" | "table" | "none",
  "description": "one plain-English sentence describing what it shows",
  "extracted_values": [
    {"label": "string", "value": "string or number"}
  ],
  "axis_labels": {"x": "string or null", "y": "string or null"}
}

If the page has no chart or table, return:
{"type": "none", "description": "", "extracted_values": [], "axis_labels": {"x": null, "y": null}}

Rules:
- Only extract what's actually visible. Never guess or invent numbers.
- Return ONLY the JSON object. No extra text, no markdown fences.
"""


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


async def extract_from_page(image_path: str, page_number: int, semaphore: asyncio.Semaphore) -> dict:
    """
    Send one page image to GPT-4o and get back structured extraction.

    `semaphore` caps how many of these run at once across the whole
    batch — acquired here, released automatically when the call
    finishes (success or failure).
    """
    async with semaphore:
        image_b64 = encode_image(image_path)
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                            },
                        ],
                    }
                ],
                max_tokens=800,
                temperature=0,
            )
            raw_text = response.choices[0].message.content.strip()
            result = json.loads(raw_text)

        except (json.JSONDecodeError, Exception) as e:
            print(f"[vlm_client] page {page_number} failed: {e}")
            result = {
                "type": "none",
                "description": "",
                "extracted_values": [],
                "axis_labels": {"x": None, "y": None},
            }

        result["page_number"] = page_number
        return result
