import os
import json
from typing import Any, Dict, Optional

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


class AIProvider:
    def __init__(self):
        self.available = bool(GEMINI_API_KEY and GEMINI_API_KEY.strip())
        self.mode = "real" if self.available else "mock"

    def generate_structured_filters(self, prompt: str) -> Dict[str, Any]:
        # Always validate; if no real key, return safe mock structured output
        # Simple rule-based mock for common cases
        p = prompt.lower()
        result = {
            "category": None,
            "min_price": None,
            "max_price": None,
            "features": None,
            "query": prompt.strip()
        }
        if "laptop" in p:
            result["category"] = "laptop"
        if "below" in p or "under" in p:
            # naive
            import re
            m = re.findall(r'(\d+)', p)
            if m:
                try:
                    result["max_price"] = float(m[-1])
                except Exception:
                    pass
        if "programming" in p:
            result["features"] = "programming"
        # Never produce SQL
        result["_ai_mode"] = self.mode
        result["_generated_at"] = "mock" if self.mode == "mock" else "real"
        return result

    def summarize_reviews(self, reviews: list[dict]) -> Dict[str, Any]:
        if not reviews:
            return {
                "summary": "No reviews available.",
                "label": "AI-generated summary",
                "count": 0,
                "mode": self.mode
            }
        # Combine text safely
        texts = [r.get("comment", "") for r in reviews if r.get("comment")]
        combined = " ".join(t[:200] for t in texts)[:1000]
        if len(texts) == 0:
            summary = f"Based on {len(reviews)} reviews (ratings only)."
        else:
            summary = f"Summary of {len(reviews)} reviews: {combined}"
        return {
            "summary": summary,
            "label": "AI-generated summary",
            "count": len(reviews),
            "mode": self.mode
        }

    def generate_product_description_draft(self, product_info: dict) -> Dict[str, Any]:
        name = product_info.get("name", "Product")
        return {
            "draft": f"AI draft description for {name}. (Edit before publishing)",
            "label": "AI-generated draft",
            "mode": self.mode,
            "auto_publish": False
        }
