import streamlit as st
from app.component.agent_response import render_agent_response
from app.component.query_processing import process_user_query

def render_chat_interface():
    """Render the main chat interface"""
    st.title("💬 Stock Analysis Chat")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                # Always use render_agent_response for assistant messages
                render_agent_response(message["content"], message.get("metadata", {}))
            else:
                st.markdown(message["content"])
    if prompt := st.chat_input("Ask about IT or Pharma stocks..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            response_placeholder = st.container()
            process_user_query(prompt, response_placeholder)
