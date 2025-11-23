"""
Job Search Page
"""
import streamlit as st
from utils.api_client import APIClient
import pandas as pd

st.set_page_config(page_title="Job Search", page_icon="🔍", layout="wide")

# Initialize
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

st.title("🔍 Job Search")
st.markdown("Search for jobs using keywords or semantic search")

# Sidebar filters
st.sidebar.header("Filters")

search_mode = st.sidebar.radio(
    "Search Mode",
    ["Keyword Search", "Semantic Search"]
)

location = st.sidebar.text_input("Location", placeholder="e.g., San Francisco, Remote")

is_remote = st.sidebar.checkbox("Remote Only")
sponsors_h1b = st.sidebar.checkbox("H1B Sponsors Only")

job_category = st.sidebar.selectbox(
    "Job Category",
    ["All", "Engineering", "Data", "Product", "Design", "Sales", "Marketing", "Operations"]
)

seniority_level = st.sidebar.selectbox(
    "Seniority Level",
    ["All", "Junior", "Mid-Level", "Senior", "Principal", "Management"]
)

# Main search
query = st.text_input(
    "Search for jobs",
    placeholder="e.g., machine learning engineer with Python experience"
)

col1, col2 = st.columns([1, 4])
with col1:
    search_button = st.button("🔍 Search", type="primary", use_container_width=True)

# Search results
if search_button and query:
    with st.spinner("Searching for jobs..."):
        try:
            # Build request
            params = {
                "query": query,
                "limit": 50
            }
            
            if location:
                params["location"] = location
            if is_remote:
                params["is_remote"] = True
            if sponsors_h1b:
                params["sponsors_h1b"] = True
            if job_category != "All":
                params["job_category"] = job_category
            if seniority_level != "All":
                params["seniority_level"] = seniority_level
            
            # Choose endpoint based on search mode
            if search_mode == "Semantic Search":
                endpoint = f"/search/semantic?query={query}&limit=50"
                response = st.session_state.api_client.get(endpoint)
            else:
                response = st.session_state.api_client.post("/search/", json=params)
            
            if response and "jobs" in response:
                jobs = response["jobs"]
                
                st.success(f"Found {len(jobs)} jobs")
                
                # Display results
                for i, job in enumerate(jobs):
                    with st.expander(
                        f"**{job['title']}** at {job['company_name']} - {job['location']}"
                    ):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**Company:** {job['company_name']}")
                            st.markdown(f"**Location:** {job['location']}")
                            if job.get('salary_range'):
                                st.markdown(f"**Salary:** {job['salary_range']}")
                            if job.get('job_type'):
                                st.markdown(f"**Type:** {job['job_type']}")
                            if job.get('seniority_level'):
                                st.markdown(f"**Level:** {job['seniority_level']}")
                            
                            st.markdown("**Description:**")
                            st.markdown(job['description'][:500] + "...")
                            
                            if job.get('extracted_skills'):
                                st.markdown(f"**Skills:** {job['extracted_skills']}")
                        
                        with col2:
                            if job.get('is_remote'):
                                st.success("🌐 Remote")
                            if job.get('likely_sponsors_h1b'):
                                st.success("✅ H1B Sponsor")
                            
                            st.markdown(f"Posted: {job['posted_date'][:10]}")
                            
                            if st.button("🔗 View Job", key=f"view_{i}"):
                                st.markdown(f"[Open Job Posting]({job['url']})")
                            
                            if st.button("💾 Save Job", key=f"save_{i}"):
                                st.success("Job saved!")
            else:
                st.warning("No jobs found. Try adjusting your search criteria.")
                
        except Exception as e:
            st.error(f"Error searching jobs: {str(e)}")
            st.info("Make sure the backend API is running")

# Tips
with st.sidebar:
    st.markdown("---")
    st.subheader("💡 Search Tips")
    st.markdown("""
    **Keyword Search:**
    - Use specific job titles
    - Include key skills
    
    **Semantic Search:**
    - Use natural language
    - Describe what you're looking for
    - Example: "remote data engineering role with cloud experience"
    """)
