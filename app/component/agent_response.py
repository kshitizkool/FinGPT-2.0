import streamlit as st
import pandas as pd
from app.component.stock_charts import render_stock_charts
from app.component.report_generation import generate_pdf_report, generate_txt_report

def render_agent_response(content, metadata=None):
    """Render agent response with metadata"""
    # Only display the main content, ignore metadata and technical details
    if metadata is None:
        metadata = {}

    with st.container():
        # Normalize content to a string
        content_text = content
        if isinstance(content, dict) and "content" in content:
            content_text = content["content"]

        if not isinstance(content_text, str):
            try:
                import json as _json
                content_text = _json.dumps(content_text, indent=2)
            except Exception:
                content_text = str(content_text)

        # Ensure there's something to render
        if not content_text:
            content_text = "(no response)"

        # Render as markdown so LLM outputs show formatted text
        st.markdown(content_text)

    if "analysis_results" in metadata:
        results = metadata["analysis_results"]
        if "metrics" in results:
            st.subheader("📊 Stock Metrics")
            metrics_df = pd.DataFrame(results["metrics"])
            st.dataframe(metrics_df, use_container_width=True)
        if "price_data" in results:
            st.subheader("📈 Price Charts")
            render_stock_charts(results["price_data"])
        if "report_data" in results:
            st.subheader("📄 Download Report")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📑 Download PDF"):
                    generate_pdf_report(results["report_data"])
            with col2:
                if st.button("📝 Download TXT"):
                    generate_txt_report(results["report_data"])

    # Backward-compatible: top-level report_data in metadata (preferred)
    report_data = metadata.get("report_data") if metadata else None
    if not report_data:
        # also check inside analysis_results in case older agents placed it there
        report_data = metadata.get("analysis_results", {}).get("report_data") if metadata else None

    if report_data:
        st.subheader("📄 Download Report")
        col1, col2 = st.columns(2)
        # Generate stable keys to avoid Streamlit duplicate button state
        try:
            key_base = abs(hash(str(report_data))) % (10 ** 8)
        except Exception:
            import time
            key_base = int(time.time())

        # Use the generator functions which now return raw data
        try:
            pdf_bytes = generate_pdf_report(report_data)
        except Exception:
            pdf_bytes = None
        try:
            txt = generate_txt_report(report_data)
        except Exception:
            txt = None

        file_name_base = f"stock_analysis_{st.session_state.get('last_query', 'report')}"
        with col1:
            if pdf_bytes:
                st.download_button(
                    label="📑 Download PDF",
                    data=pdf_bytes,
                    file_name=f"{file_name_base}.pdf",
                    mime="application/pdf",
                    key=f"pdf_dl_{key_base}"
                )
            else:
                st.button("📑 Download PDF (unavailable)", disabled=True)
        with col2:
            if txt:
                st.download_button(
                    label="📝 Download TXT",
                    data=txt,
                    file_name=f"{file_name_base}.txt",
                    mime="text/plain",
                    key=f"txt_dl_{key_base}"
                )
            else:
                st.button("📝 Download TXT (unavailable)", disabled=True)

    # If a workflow graph image was provided in metadata, render it
    if metadata and metadata.get("graph_image"):
        try:
            st.subheader("🔗 Workflow Graph")
            st.image(metadata.get("graph_image"), use_container_width=True)
        except Exception:
            # Ignore image rendering failures
            pass
