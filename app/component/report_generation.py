import streamlit as st
import json
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO

def generate_pdf_report(report_data: dict):
    """Generate and download PDF report"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title="Stock Analysis Report"
        )
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("📊 Stock Analysis Report", styles["Title"]))
        story.append(Spacer(1, 12))

        # If report_data is a string, render as a single paragraph
        if isinstance(report_data, str):
            story.append(Paragraph(report_data, styles["BodyText"]))
        else:
            for key, value in report_data.items():
                story.append(Paragraph(f"<b>{key}:</b>", styles["Heading3"]))
                if isinstance(value, (dict, list)):
                    pretty_val = json.dumps(value, indent=2)
                    story.append(Paragraph(pretty_val.replace("\n", "<br/>"), styles["BodyText"]))
                else:
                    story.append(Paragraph(str(value), styles["BodyText"]))
                story.append(Spacer(1, 12))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    except Exception as e:
        # Return None on failure so caller can handle it
        return None

def generate_txt_report(report_data: dict):
    """Generate and download TXT report"""
    try:
        # If report_data is already a string, use it directly
        if isinstance(report_data, str):
            report_text = report_data
        else:
            report_text = json.dumps(report_data, indent=2)
        return report_text
    except Exception:
        return None
