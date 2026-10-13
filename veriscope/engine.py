"""veriscope/engine.py

Core engine to call PageSpeed Insights and extract actionable metrics:
- Core Web Vitals (FCP, LCP, CLS)
- Category scores (performance, seo, best-practices)
- Top 5 highest-impact audit failures (dynamically determined)
"""

import os
import requests

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def fetch_pagespeed(url: str, strategy: str = "mobile", api_key: str | None = None) -> dict:
    """Call PageSpeed Insights API and return parsed results.

    strategy: 'mobile' or 'desktop'
    api_key: optional API key (recommended to set via env)
    """
    params = {"url": url, "strategy": strategy}
    if api_key:
        params["key"] = api_key

    resp = requests.get(PAGESPEED_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Categories
    categories = data.get("lighthouseResult", {}).get("categories", {})
    scores = {}
    for k in ("performance", "seo", "best-practices"):
        cat = categories.get(k)
        if cat and "score" in cat:
            # Lighthouse returns score in 0..1
            scores[k] = round(cat["score"] * 100, 1)
        else:
            scores[k] = None

    audits = data.get("lighthouseResult", {}).get("audits", {})

    # Core Web Vitals extraction
    def _get_numeric(audit_keys):
        for key in audit_keys:
            a = audits.get(key)
            if not a:
                continue
            # numericValue is usually present
            val = a.get("numericValue")
            if val is not None:
                return val, a.get("displayValue") or str(val)
            # sometimes displayValue has readable string
            if a.get("displayValue"):
                return None, a.get("displayValue")
        return None, None

    fcp_val, fcp_display = _get_numeric(["first-contentful-paint", "first-contentful-paint-3g"]) 
    lcp_val, lcp_display = _get_numeric(["largest-contentful-paint"]) 
    cls_val, cls_display = _get_numeric(["cumulative-layout-shift"]) 

    # Dynamic top-5 failures by impact (score-based)
    failures = []
    for key, audit in audits.items():
        score = audit.get("score")
        # Some audits have score 0..1, some have True/False or scoreDisplayMode
        if score is None:
            # treat failing boolean audits as score 0 if not passed
            if audit.get("scoreDisplayMode") == "binary":
                passed = audit.get("passed")
                score_val = 1.0 if passed else 0.0
            else:
                # fallback: skip if no score info
                continue
        else:
            try:
                score_val = float(score)
            except Exception:
                continue

        # compute impact: lower score -> higher impact
        impact = 1.0 - score_val
        failures.append({
            "id": key,
            "title": audit.get("title") or key,
            "description": audit.get("description") or audit.get("explanation") or "",
            "score": score_val,
            "displayValue": audit.get("displayValue"),
            "impact": impact,
        })

    # Sort by impact desc, pick top 5 with impact>0
    failures_sorted = sorted([f for f in failures if f["impact"] > 0], key=lambda x: x["impact"], reverse=True)[:5]

    result = {
        "url": url,
        "strategy": strategy,
        "scores": scores,
        "core_web_vitals": {
            "FCP": {"numeric": fcp_val, "display": fcp_display},
            "LCP": {"numeric": lcp_val, "display": lcp_display},
            "CLS": {"numeric": cls_val, "display": cls_display},
        },
        "top_failures": failures_sorted,
        "raw_audits_count": len(audits),
        "raw": data,
    }
    return result


if __name__ == "__main__":
    import json
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    key = os.getenv("PAGESPEED_API_KEY")
    out = fetch_pagespeed(url, strategy="mobile", api_key=key)
    print(json.dumps(out, indent=2))
