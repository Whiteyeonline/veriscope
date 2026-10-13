import streamlit as st
import requests
import ssl
import socket
from datetime import datetime
import google.generativeai as genai
from io import BytesIO
from urllib.parse import urlparse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# --- Initialization & API Keys ---
st.set_page_config(page_title="Free SEO Auditor", page_icon="📈", layout="centered")

try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
    pagespeed_key = st.secrets["PAGESPEED_API_KEY"]
    genai.configure(api_key=gemini_key)
except KeyError:
    st.error("Missing API Keys! Please add GEMINI_API_KEY and PAGESPEED_API_KEY to Streamlit secrets.")
    st.stop()

# --- Functions ---
def check_ssl(url):
    domain = urlparse(url).netloc or url
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                expire_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                days_left = (expire_date - datetime.now()).days
                return True, days_left
    except Exception:
        return False, 0

def get_pagespeed_data(url):
    api_url = f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={url}&strategy=mobile&key={pagespeed_key}"
    response = requests.get(api_url)
    if response.status_code != 200:
        return None
    
    data = response.json()
    lighthouse = data.get('lighthouseResult', {})
    categories = lighthouse.get('categories', {})
    audits = lighthouse.get('audits', {})
    
    # Extract specific fixes if they exist and failed the audit (score < 1)
    fixes = []
    for audit_key in ['modern-image-formats', 'unminified-javascript', 'uses-text-compression', 'render-blocking-resources']:
        audit_item = audits.get(audit_key, {})
        if audit_item.get('score', 1) < 1:
            fixes.append(audit_item.get('title', ''))
            
    return {
        "Scores": {
            "Performance": int(categories.get('performance', {}).get('score', 0) * 100),
            "SEO": int(categories.get('seo', {}).get('score', 0) * 100),
            "Best Practices": int(categories.get('best-practices', {}).get('score', 0) * 100)
        },
        "Fixes": [f for f in fixes if f] # Remove empty strings
    }

def generate_ai_summary(url, scores):
    prompt = f"""Act as a strict technical SEO auditor. I just audited {url}. 
    Scores out of 100: Performance ({scores['Performance']}), SEO ({scores['SEO']}), Best Practices ({scores['Best Practices']}). 
    Write a short, professional, 3-sentence executive summary for the business owner explaining what these scores mean, the business impact of a slow site, and the urgency to fix it. No fluff."""
    
    try:
        # Try the latest Flash model first
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        # If the API key lacks access to 1.5 Flash, fallback to the guaranteed base model
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text

def create_pdf(url, data, ssl_status, ai_summary):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Header
    elements.append(Paragraph("Technical SEO & Security Audit", styles['Title']))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"<b>Target URL:</b> {url}", styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # AI Summary Section
    elements.append(Paragraph("<b>Executive Summary</b>", styles['Heading2']))
    elements.append(Paragraph(ai_summary, styles['Normal']))
    elements.append(Spacer(1, 24))
    
    # Data Table Section
    elements.append(Paragraph("<b>Diagnostic Scores</b>", styles['Heading2']))
    table_data = [['Metric', 'Score (0-100)', 'Status']]
    
    for key, val in data['Scores'].items():
        status = "Good" if val >= 80 else "Needs Fix"
        table_data.append([key, str(val), status])
        
    ssl_text = f"Valid ({ssl_status[1]} days)" if ssl_status[0] else "Missing/Invalid"
    table_data.append(['SSL Security', ssl_text, "Good" if ssl_status[0] else "Critical"])
    
    t = Table(table_data, colWidths=[150, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A202C")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F7FAFC")),
        ('GRID', (0,0), (-1,-1), 1, colors.silver)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))
    
    # Specific Fixes Section
    if data['Fixes']:
        elements.append(Paragraph("<b>Identified Technical Errors</b>", styles['Heading2']))
        for fix in data['Fixes']:
            elements.append(Paragraph(f"• {fix}", styles['Normal']))
            elements.append(Spacer(1, 6))
        elements.append(Spacer(1, 24))
    
    # Affiliate / CTA Section
    cta = """<b>Need these fixed?</b> Don't lose customers to slow load times. 
    <link href="https://your-affiliate-link.com" color="blue">Click here to hire a vetted technical SEO specialist for under $50.</link>"""
    elements.append(Paragraph(cta, styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- User Interface ---
st.title("Automated Site Auditor")
st.markdown("Enter a website URL to generate a comprehensive PDF report outlining technical SEO and performance errors.")

target_url = st.text_input("Website URL", placeholder="https://example.com")

if st.button("Generate Free PDF Audit", type="primary"):
    if not target_url.startswith("http"):
        st.error("Please include http:// or https:// in the URL.")
    else:
        with st.status("Running automated diagnostics...", expanded=True) as status:
            st.write("Checking SSL Certificate...")
            ssl_status = check_ssl(target_url)
            
            st.write("Running Google Lighthouse Audit...")
            audit_data = get_pagespeed_data(target_url)
            
            if audit_data:
                st.write("Analyzing data with AI...")
                summary = generate_ai_summary(target_url, audit_data['Scores'])
                
                st.write("Compiling PDF...")
                pdf_buffer = create_pdf(target_url, audit_data, ssl_status, summary)
                
                status.update(label="Audit Complete!", state="complete", expanded=False)
                
                st.success("Report generated successfully.")
                st.download_button(
                    label="📄 Download Professional Report",
                    data=pdf_buffer,
                    file_name="Website_Audit_Report.pdf",
                    mime="application/pdf"
                )
            else:
                status.update(label="Failed to fetch data.", state="error", expanded=False)
                st.error("Could not fetch data. Ensure the site is live and allows bots.")
    
