"""
Job Intelligence Platform - Home Page
"""
import streamlit as st
from utils.api_client import APIClient

st.set_page_config(
    page_title="Job Intelligence Platform",
    page_icon="💼",
    layout="wide"
)

# Initialize API client
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

# Main page
st.title("💼 Job Intelligence Platform")
st.markdown("---")

# Hero section
col1, col2 = st.columns([2, 1])

with col1:
    st.header("Welcome to Job Intelligence")
    st.markdown("""
    Your comprehensive platform for job search, resume matching, and market intelligence.
    
    **Features:**
    - 🔍 **Semantic Job Search**: Find jobs using natural language
    - 📄 **Resume Matching**: AI-powered resume-to-job matching
    - 📊 **Market Analytics**: Insights into job market trends
    - 🌐 **H1B Sponsorship**: Identify companies that sponsor H1B visas
    - 🏢 **Remote Jobs**: Filter for remote opportunities
    """)
    
    st.markdown("### Quick Actions")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        if st.button("🔍 Search Jobs", use_container_width=True):
            st.switch_page("pages/1_Job_Search.py")
    
    with col_b:
        if st.button("📄 Match Resume", use_container_width=True):
            st.switch_page("pages/2_Resume_Matcher.py")
    
    with col_c:
        if st.button("📊 View Analytics", use_container_width=True):
            st.switch_page("pages/3_Analytics.py")

with col2:
    st.image("https://via.placeholder.com/400x300?text=Job+Intelligence", 
             use_column_width=True)

# Statistics
st.markdown("---")
st.header("📈 Platform Statistics")

try:
    # Fetch some basic stats
    analytics = st.session_state.api_client.get("/analytics/trends?days=7")
    
    if analytics:
        metrics = st.columns(4)
        
        with metrics[0]:
            st.metric("Total Jobs", "10,000+")
        
        with metrics[1]:
            st.metric("Companies", "500+")
        
        with metrics[2]:
            st.metric("H1B Sponsors", "250+")
        
        with metrics[3]:
            st.metric("Remote Jobs", "3,000+")

except Exception as e:
    st.info("Statistics will be available once the backend is running")

# Recent updates
st.markdown("---")
st.header("📰 Recent Updates")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Latest Features")
    st.markdown("""
    - ✅ Semantic job search with Snowflake Cortex
    - ✅ AI-powered resume matching
    - ✅ H1B sponsorship data integration
    - ✅ Real-time job scraping from multiple sources
    """)

with col2:
    st.subheader("Coming Soon")
    st.markdown("""
    - 🚧 Job alerts and notifications
    - 🚧 Company reviews integration
    - 🚧 Salary predictions
    - 🚧 Interview preparation resources
    """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Built with ❤️ using Streamlit, FastAPI, and Snowflake Cortex</p>
    <p>Data updated daily | Last update: 2025-11-23</p>
</div>
""", unsafe_allow_html=True)
