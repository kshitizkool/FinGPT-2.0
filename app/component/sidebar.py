import streamlit as st

def render_sidebar():
    """Render the sidebar with system configuration"""
    with st.sidebar:
        st.title("🤖 AI Stock Analyzer")
        st.session_state.analysis_mode = st.radio(
            "Analysis Mode",
            ["basic", "deep_research"],
            format_func=lambda x: "Basic Analysis" if x == "basic" else "Deep Research Mode",
            help="Basic: Single LLM response\nDeep Research: Multi-agent comprehensive analysis"
        )
        st.subheader("📊 Supported Sectors")
        st.info("✅ Information Technology (IT)")
        st.info("✅ Pharmaceuticals (Pharma)")
        st.warning("❌ Other sectors will be declined")
        st.subheader("🔧 System Status")
        st.success("🟢 LLM: Grok 4 Fast (Active)")
        st.success("🟢 Vector DB: Connected")
        st.success("🟢 Yahoo Finance: Active")
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.session_state.chat_history.clear()
            st.session_state.current_plan = None
            st.session_state.analysis_results = None
            st.rerun()
