import streamlit as st
from app.component.sidebar import render_sidebar
from app.component.chat_interface import render_chat_interface
from app.component.planning_interface import render_planning_interface
from app.utils.session_state import init_session_state
from src.utils.config_loader import load_config
from src.utils.logging_setup import setup_logging

def main():
    """Main application entry point"""
    # Initialize logging and config
    logger = setup_logging()
    config = load_config("config/config.yaml")
    # Initialize session state with config and logger
    init_session_state(config=config, logger=logger)
    
    # Render sidebar
    render_sidebar()
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        render_chat_interface()
        render_planning_interface()
    
    with col2:
        # Additional information panel
        st.subheader("ℹ️ System Info")
        st.caption(f"Mode: {st.session_state.analysis_mode.title()}")
        st.caption(f"Messages: {len(st.session_state.messages)}")
        
        # Show current plan if available
        if st.session_state.current_plan:
            st.subheader("📋 Current Plan")
            with st.expander("View Details"):
                st.json(st.session_state.current_plan)

if __name__ == "__main__":
    main()