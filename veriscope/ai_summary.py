"""veriscope/ai_summary.py

Wrapper to generate an action-oriented AI summary (Gemini) with dynamic prompting.
The function will attempt to call an external API if GEMINI_API_KEY is set; otherwise it will fallback
to a deterministic local summary for offline testing.

Output: Exactly three bullet points in plain text (primary bottleneck, business impact, first step).
"""

import os
from typing import List


def _build_prompt(site_url: str, failures: List[dict], vitals: dict, scores: dict) -> str:
    fail_lines = []
    for f in failures:
        title = f.get("title")
        disp = f.get("displayValue")
        fail_lines.append(f"- {title}: {disp if disp else 'no display value'}")

    prompt = (
        "You are a professional web performance consultant. Given the audit failures and core web vitals for"
        f" {site_url}, produce exactly three bullet points (each on its own line):\n"
        "1) The primary bottleneck for user experience and conversions.\n"
        "2) The business impact (why this matters for revenue/engagement).\n"
        "3) The precise first step the site owner should take to begin fixing it.\n\n"
        "Include context from the failures below:\n"
        f"Failures:\n{chr(10).join(fail_lines) if fail_lines else '- None'}\n\n"
        f"Core Web Vitals:\n- FCP: {vitals.get('FCP', {}).get('display')}\n- LCP: {vitals.get('LCP', {}).get('display')}\n- CLS: {vitals.get('CLS', {}).get('display')}\n\n"
        f"Scores:\n- Performance: {scores.get('performance')}\n- SEO: {scores.get('seo')}\n- Best Practices: {scores.get('best-practices')}\n\n"
        "Remember: answer with exactly three bullet points, no numbering, no additional commentary."
    )
    return prompt


def generate_ai_summary(site_url: str, failures: List[dict], vitals: dict, scores: dict) -> str:
    prompt = _build_prompt(site_url, failures, vitals, scores)
    api_key = os.getenv("GEMINI_API_KEY")

    # If there's an API key, you can plug in your Gemini/OpenAI call here.
    # The exact request shape depends on your provider — keep the prompt above as-is.
    if api_key:
        try:
            # Placeholder for actual call - adapt to your provider
            import requests
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",  # replace with your model
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 180,
                },
                timeout=20,
            )
            resp.raise_for_status()
            j = resp.json()
            # Extract text in a provider-agnostic way
            choices = j.get("choices") or []
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        except Exception:
            pass

    # Fallback deterministic summary if API not configured
    primary = "Large images and render-blocking resources delaying Largest Contentful Paint (LCP)."
    impact = "Slow LCP reduces user engagement and can lower conversions, especially on landing pages."
    first_step = "Compress/serve responsive images (WebP/AVIF), add width/height, and defer non-critical JS."
    return f"- {primary}\n- {impact}\n- {first_step}"
