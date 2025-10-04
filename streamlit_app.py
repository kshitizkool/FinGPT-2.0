import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO

# Import custom modules (these would be implemented separately)
from src.workflow.graph_builder import create_stock_analysis_graph
from src.utils.config_loader import load_config
from src.utils.logging_setup import setup_logging
from src.agents.router_agent import RouterAgent
from langchain_community.chat_message_histories import StreamlitChatMessageHistory

# Import components
from app.component.sidebar import render_sidebar
from app.component.chat_interface import render_chat_interface
from app.component.agent_response import render_agent_response
from app.component.stock_charts import render_stock_charts
from app.component.query_processing import process_user_query, process_basic_mode, process_deep_research_mode
from app.component.report_generation import generate_pdf_report, generate_txt_report
from app.component.planning_interface import render_planning_interface

# Configure Streamlit page
st.set_page_config(
    page_title="AI Stock Analysis System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize logging
logger = setup_logging()

# Load configuration
@st.cache_resource
def load_system_config():
    return load_config("config/config.yaml")

config = load_system_config()

# Initialize session state
def init_session_state():
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
    
    if "config" not in st.session_state:
        st.session_state.config = config
    
    if "logger" not in st.session_state:
        st.session_state.logger = logger

