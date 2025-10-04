# Initialize session state for Streamlit
import streamlit as st
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

def init_session_state(config=None, logger=None):
	"""Initialize Streamlit session state variables"""
	if "messages" not in st.session_state:
		st.session_state.messages = []
	if "analysis_mode" not in st.session_state:
		st.session_state.analysis_mode = "basic"
	if "chat_history" not in st.session_state:
		st.session_state.chat_history = StreamlitChatMessageHistory(key="chat_messages")
	if "current_plan" not in st.session_state:
		st.session_state.current_plan = None
	if "analysis_results" not in st.session_state:
		st.session_state.analysis_results = None
	if config is not None and "config" not in st.session_state:
		st.session_state.config = config
	if logger is not None and "logger" not in st.session_state:
		st.session_state.logger = logger
