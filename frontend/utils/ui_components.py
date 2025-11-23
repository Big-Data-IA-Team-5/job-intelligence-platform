"""
UI Components
"""
import streamlit as st


def job_card(job: dict):
    """Display a job card"""
    with st.container():
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.subheader(f"{job['title']}")
            st.markdown(f"**{job['company_name']}** • {job['location']}")
            
            if job.get('salary_range'):
                st.markdown(f"💰 {job['salary_range']}")
            
            st.markdown(job['description'][:200] + "...")
        
        with col2:
            if job.get('is_remote'):
                st.success("🌐 Remote")
            if job.get('likely_sponsors_h1b'):
                st.success("✅ H1B")
            
            st.button("View Details", key=f"view_{job['job_id']}")


def metric_card(label: str, value: str, delta: str = None):
    """Display a metric card"""
    st.metric(label=label, value=value, delta=delta)


def filter_sidebar():
    """Common filter sidebar"""
    st.sidebar.header("Filters")
    
    filters = {
        'location': st.sidebar.text_input("Location"),
        'is_remote': st.sidebar.checkbox("Remote Only"),
        'sponsors_h1b': st.sidebar.checkbox("H1B Sponsors Only"),
        'job_category': st.sidebar.selectbox(
            "Category",
            ["All", "Engineering", "Data", "Product", "Design"]
        ),
        'seniority': st.sidebar.selectbox(
            "Seniority",
            ["All", "Junior", "Mid-Level", "Senior", "Principal"]
        )
    }
    
    return filters
