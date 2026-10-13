"""veriscope/ui.py

Streamlit front-end for running audits and downloading a professional PDF report.
Features added:
- Mobile vs Desktop toggle
- Caching of results using @st.cache_data
- Generate button that produces a professional PDF and provides a download
"""

import os
import streamlit as st
from veriscope import engine, scraper, ai_summary, pdf_report
from io import BytesIO

st.set_page_config(page_title="Veriscope Audit", layout="centered")


@st.cache_data(ttl=60 * 60)
def run_audit(url: str, strategy: str):
    key = os.getenv("PAGESPEED_API_KEY")
    engine_result = engine.fetch_pagespeed(url, strategy=strategy, api_key=key)
    onpage = scraper.scrape_onpage(url)
    ai = ai_summary.generate_ai_summary(url, engine_result.get("top_failures", []), engine_result.get("core_web_vitals", {}), engine_result.get("scores", {}))

    report = {
        "url": url,
        "strategy": strategy,
        "scores": engine_result.get("scores", {}),
        "core_web_vitals": engine_result.get("core_web_vitals", {}),
        "top_failures": engine_result.get("top_failures", []),
        "onpage": onpage,
        "ai_summary": ai,
    }
    pdf_bytes = pdf_report.generate_pdf(report)
    return report, pdf_bytes


def main():
    st.title("Veriscope — Professional Site Audit")

    with st.form("audit_form"):
        url = st.text_input("Site URL", value="https://example.com")
        strategy = st.radio("Device", ["mobile", "desktop"], index=0)
        submitted = st.form_submit_button("Generate Report")

    if submitted:
        with st.spinner("Running audit — using cached results when possible"):
            try:
                report, pdf_bytes = run_audit(url, strategy)
            except Exception as e:
                st.error(f"Audit failed: {e}")
                return

        st.success("Audit complete")
        st.subheader("Scores")
        st.metric("Performance", f"{report['scores'].get('performance')}%")
        st.metric("SEO", f"{report['scores'].get('seo')}%")
        st.metric("Best Practices", f"{report['scores'].get('best-practices')}%")

        st.subheader("Top Issues")
        for f in report.get("top_failures", []):
            st.write(f"- {f.get('title')} — impact {round(f.get('impact',0)*100,1)}%")

        st.subheader("On-Page SEO Quick Checks")
        onpage = report.get("onpage", {})
        st.write(onpage)

        st.subheader("AI Summary")
        st.write(report.get("ai_summary"))

        st.download_button("Download Professional PDF", data=pdf_bytes, file_name="veriscope-report.pdf", mime="application/pdf")


if __name__ == "__main__":
    main()
