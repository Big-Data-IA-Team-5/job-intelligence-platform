"""
Unified AI Assistant - Your complete job intelligence companion
Handles: Job Search, Resume Analysis, Salary Info, H-1B Sponsorship, Career Guidance
"""
import streamlit as st
from utils.api_client import APIClient
import time
import io
import base64

# Page config - session clears when browser closes
st.set_page_config(
    page_title="Job Intelligence AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize API client (session-based - clears when browser closes)
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

# Initialize chat history (session-based - auto clears)
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Initialize uploaded resume (session-based - auto clears)
if 'uploaded_resume' not in st.session_state:
    st.session_state.uploaded_resume = None
    st.session_state.resume_text = None

# Header - Only show title if there are messages
if st.session_state.messages:
    col1, col2, col3 = st.columns([5, 1, 1])
    with col1:
        st.markdown("### 🤖 AI Job Intelligence")
    with col2:
        # Resume upload button
        if st.button("➕ Resume" if not st.session_state.resume_text else "📄 Resume", use_container_width=True):
            st.session_state.show_upload = not st.session_state.get('show_upload', False)
            st.rerun()
    with col3:
        if st.button("🔄 New", use_container_width=True):
            st.session_state.messages = []
            st.session_state.uploaded_resume = None
            st.session_state.resume_text = None
            st.session_state.show_upload = False
            st.rerun()

# Sidebar - minimal and clean
with st.sidebar:
    # Show resume status only if uploaded
    if st.session_state.resume_text:
        st.markdown("### 📄 Resume")
        st.success(f"✓ {st.session_state.uploaded_resume.name if st.session_state.uploaded_resume else 'Active'}")
        st.divider()
    
    # Session stats (only show if there are messages)
    if st.session_state.messages:
        st.markdown("### 📊 This chat")
        col1, col2 = st.columns(2)
        col1.metric("Messages", len(st.session_state.messages))
        col2.metric("Questions", len([m for m in st.session_state.messages if m["role"] == "user"]))
        st.divider()
    
    # Capabilities
    st.markdown("### ✨ Capabilities")
    st.markdown("""
    🔍 Job search  
    💰 Salary insights  
    📄 Resume analysis  
    🌐 H-1B sponsorship  
    🎯 Career advice  
    """)
    
    if st.session_state.messages:
        st.divider()
        st.caption("💡 Session clears on browser close")
