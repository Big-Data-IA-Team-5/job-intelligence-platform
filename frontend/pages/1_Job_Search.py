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

# Work model filters
work_model = st.sidebar.selectbox(
    "Work Model",
    ["All", "Remote", "Hybrid", "On-site"]
)

# Visa filters
st.sidebar.markdown("**Visa Sponsorship**")
sponsors_h1b = st.sidebar.checkbox("H1B Sponsors Only")
high_approval_rate = st.sidebar.checkbox("High Approval Rate (80%+)")
min_petitions = st.sidebar.slider("Min Total Petitions", 0, 100, 0, 10)

# Job filters
job_category = st.sidebar.selectbox(
    "Job Category",
    ["All", "Engineering", "Data", "Product", "Design", "Sales", "Marketing", "Operations"]
)

new_grad_only = st.sidebar.checkbox("Entry Level / New Grad Only")

# Salary filter
st.sidebar.markdown("**Salary Range**")
salary_min = st.sidebar.number_input("Min Salary ($)", min_value=0, value=0, step=10000)
salary_max = st.sidebar.number_input("Max Salary ($)", min_value=0, value=0, step=10000)

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
            # Build query string for GET request
            query_params = f"query={query}&limit=50"
            
            if location:
                query_params += f"&location={location}"
            
            if work_model != "All":
                query_params += f"&work_model={work_model}"
            
            if sponsors_h1b:
                query_params += "&h1b_sponsor=true"
            
            if high_approval_rate:
                query_params += "&min_approval_rate=0.8"
            
            if min_petitions > 0:
                query_params += f"&min_petitions={min_petitions}"
            
            if job_category != "All":
                query_params += f"&job_category={job_category}"
            
            if new_grad_only:
                query_params += "&new_grad_only=true"
            
            if salary_min > 0:
                query_params += f"&salary_min={salary_min}"
            
            if salary_max > 0:
                query_params += f"&salary_max={salary_max}"
            
            # Call the search API (GET /api/search)
            endpoint = f"/api/search?{query_params}"
            response = st.session_state.api_client.get(endpoint)
            
            if response and "jobs" in response:
                jobs = response["jobs"]
                
                st.success(f"Found {len(jobs)} jobs")
                
                # Display results
                for i, job in enumerate(jobs):
                    with st.expander(
                        f"**{job['title']}** at {job.get('company', 'N/A')} - {job.get('location', 'N/A')}"
                    ):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**Company:** {job.get('company', 'N/A')}")
                            st.markdown(f"**Location:** {job.get('location', 'N/A')}")
                            
                            # Salary display
                            salary_min = job.get('salary_min')
                            salary_max = job.get('salary_max')
                            if salary_min and salary_max:
                                st.markdown(f"**Salary:** ${salary_min:,.0f} - ${salary_max:,.0f}")
                            elif salary_min:
                                st.markdown(f"**Salary:** ${salary_min:,.0f}+")
                            
                            if job.get('job_type'):
                                st.markdown(f"**Type:** {job['job_type']}")
                            if job.get('job_category'):
                                st.markdown(f"**Category:** {job['job_category']}")
                            if job.get('department'):
                                st.markdown(f"**Department:** {job['department']}")
                            if job.get('work_model'):
                                st.markdown(f"**Work Model:** {job['work_model']}")
                            
                            # H-1B sponsorship details
                            if job.get('h1b_sponsor'):
                                h1b_details = []
                                
                                approval_rate = job.get('avg_approval_rate')
                                if approval_rate:
                                    h1b_details.append(f"✅ {approval_rate*100:.0f}% approval rate")
                                
                                petitions = job.get('total_petitions')
                                if petitions:
                                    h1b_details.append(f"📊 {petitions:,} total petitions")
                                
                                if h1b_details:
                                    st.markdown(f"**H-1B:** {' • '.join(h1b_details)}")
                            
                            # Description
                            description = job.get('description')
                            if description:
                                st.markdown("**Description:**")
                                st.markdown(description[:500] + "..." if len(description) > 500 else description)
                            
                            if job.get('visa_category'):
                                st.markdown(f"**Visa:** {job['visa_category']}")
                        
                        with col2:
                            # Work model badge
                            work_model = job.get('work_model', '')
                            if 'remote' in work_model.lower():
                                st.success("🌐 Remote")
                            
                            # H1B sponsor badge with approval rate
                            if job.get('h1b_sponsor') or job.get('h1b_sponsored_explicit'):
                                approval_rate = job.get('avg_approval_rate')
                                if approval_rate and approval_rate >= 0.8:
                                    st.success(f"✅ H1B Sponsor ({approval_rate*100:.0f}% ✨)")
                                elif approval_rate and approval_rate >= 0.6:
                                    st.info(f"✅ H1B Sponsor ({approval_rate*100:.0f}%)")
                                else:
                                    st.success("✅ H1B Sponsor")
                            
                            # New grad badge
                            if job.get('is_new_grad_role'):
                                st.info("🎓 New Grad Friendly")
                            
                            # Days since posted
                            days_posted = job.get('days_since_posted')
                            if days_posted is not None:
                                if days_posted == 0:
                                    st.markdown("Posted: **Today**")
                                elif days_posted == 1:
                                    st.markdown("Posted: **Yesterday**")
                                else:
                                    st.markdown(f"Posted: **{days_posted} days ago**")
                            
                            st.markdown("")  # Spacing
                            
                            # Apply button - opens job URL in new tab
                            job_url = job.get('url', '')
                            if job_url:
                                st.link_button("🚀 Apply Now", job_url, use_container_width=True)
                            
                            # Save job button
                            if st.button("💾 Save Job", key=f"save_{i}", use_container_width=True):
                                st.success("Saved!")
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
