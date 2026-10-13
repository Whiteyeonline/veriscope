# Veriscope — Professional Audit (Micro-SaaS)

This branch upgrades the basic script into a professional-tier audit tool suitable for agency delivery. It adds:

- Engine: dynamic PageSpeed Insights parsing and top-5 failure extraction
- On-page scraper: title, meta description, primary H1 checks
- AI summary injection: dynamic prompt with failures and vitals (Gemini/OpenAI wrapper)
- Premium PDF generation with ReportLab (cover, bar chart, color-coded tables)
- Streamlit UI with caching and mobile/desktop toggle

Quick start

1. Create a virtualenv and install dependencies:

   pip install -r requirements.txt

2. Set environment variables:

   - PAGESPEED_API_KEY: (recommended) Google PageSpeed Insights API key
   - GEMINI_API_KEY: (optional) your AI key

3. Run the Streamlit app:

   streamlit run veriscope/ui.py

Notes

- The AI wrapper contains a placeholder API call; adapt it to your chosen provider's API shape (Gemini/Google or OpenAI).
- ReportLab is used to create an agency-style PDF — tweak colors and layout in veriscope/pdf_report.py
