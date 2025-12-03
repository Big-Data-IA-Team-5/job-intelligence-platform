"""
Saved Jobs Page
"""
import streamlit as st
from utils.api_client import APIClient

st.set_page_config(page_title="Saved Jobs", page_icon="💾", layout="wide")

# Initialize
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

st.title("💾 Saved Jobs")
st.markdown("Manage your saved job postings")

# User ID input
user_id = st.text_input("User ID", placeholder="Enter your user ID")

if user_id:
    if st.button("🔄 Load Saved Jobs"):
        with st.spinner("Loading saved jobs..."):
            try:
                response = st.session_state.api_client.get(f"/jobs/saved/{user_id}")
                
                if response and response.get('saved_jobs'):
                    saved_jobs = response['saved_jobs']
                    
                    st.success(f"You have {len(saved_jobs)} saved jobs")
                    
                    # Display saved jobs
                    for i, job in enumerate(saved_jobs):
                        with st.expander(
                            f"**{job['title']}** at {job['company_name']}"
                        ):
                            col1, col2 = st.columns([3, 1])
                            
                            with col1:
                                st.markdown(f"**Location:** {job['location']}")
                                st.markdown(f"**Saved on:** {job['saved_at'][:10]}")
                                
                                if job.get('notes'):
                                    st.markdown("**Notes:**")
                                    st.write(job['notes'])
                                
                                st.markdown(f"[View Job Posting]({job['url']})")
                            
                            with col2:
                                if st.button("🗑️ Remove", key=f"remove_{i}"):
                                    try:
                                        st.session_state.api_client.delete(
                                            f"/jobs/saved/{user_id}/{job['job_id']}?source={job['source']}"
                                        )
                                        st.success("Job removed")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error removing job: {str(e)}")
                else:
                    st.info("No saved jobs yet. Start searching and save jobs you're interested in!")
                    
            except Exception as e:
                st.error(f"Error loading saved jobs: {str(e)}")
else:
    st.info("👆 Enter your User ID to view saved jobs")

# Application tracker
st.markdown("---")
st.header("📝 Application Tracker")
st.markdown("Track your job applications")

if user_id:
    st.info("Application tracking feature coming soon!")
    
    # Preview of future feature
    with st.expander("Preview: Application Tracker"):
        st.markdown("""
        **Coming Soon:**
        - Track application status
        - Set reminders for follow-ups
        - Add interview notes
        - Track offer details
        """)
