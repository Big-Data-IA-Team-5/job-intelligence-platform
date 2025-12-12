"""
Jobs Database - Interactive Table with Daily Updates
Real-time job listings with advanced filtering
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.api_client import APIClient
import json

st.set_page_config(
    page_title="Jobs Database",
    page_icon="💼",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .job-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        margin: 10px 0;
        transition: all 0.2s;
    }
    .job-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #667eea;
    }
    .apply-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 10px 24px;
        border-radius: 20px;
        text-decoration: none;
        display: inline-block;
        font-weight: 600;
        transition: all 0.2s;
    }
    .apply-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    .filter-section {
        background: #f9fafb;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .new-badge {
        background: #10b981;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .hot-badge {
        background: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize API client
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_job_stats():
    """Get job statistics from backend API"""
    try:
        response = st.session_state.api_client.get('/api/jobs/stats')
        return response
    except Exception as e:
        st.error(f"Failed to load stats: {e}")
        return None

def search_jobs(filters):
    """Search jobs from backend API with filters"""
    try:
        response = st.session_state.api_client.post('/api/jobs/search', json=filters)
        # Validate response structure
        if isinstance(response, dict):
            jobs = response.get('jobs', [])
            total = response.get('total', 0)
            return jobs, total
        else:
            return [], 0
    except Exception as e:
        st.error(f"Failed to load jobs: {e}")
        return [], 0

@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_filter_options():
    """Get companies and locations for filter dropdowns"""
    try:
        companies_resp = st.session_state.api_client.get('/api/jobs/companies')
        locations_resp = st.session_state.api_client.get('/api/jobs/locations')
        return companies_resp['companies'], locations_resp['locations']
    except Exception as e:
        st.warning(f"Using cached filter options: {e}")
        return [], []

# Load filter options
companies_data, locations_data = get_filter_options()
all_companies = [c['name'] for c in companies_data] if companies_data else []
all_locations = [l['name'] for l in locations_data] if locations_data else []

# Get stats
stats = get_job_stats()
if not stats:
    st.error("Unable to connect to backend. Please ensure backend service is running.")
    st.stop()

# Ensure stats has required keys with defaults
stats = {
    'total_jobs': stats.get('total_jobs', 0),
    'h1b_sponsors': stats.get('h1b_sponsors', 0),
    'remote_jobs': stats.get('remote_jobs', 0),
    'avg_salary': stats.get('avg_salary', None)
}

# Header
st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 30px; border-radius: 10px; margin-bottom: 20px;'>
    <h1 style='color: white; margin: 0;'>💼 Jobs Database</h1>
    <p style='color: #e0e7ff; margin: 10px 0 0 0;'>
        Updated daily • {total_jobs:,} active positions • Last update: {last_update}
    </p>
</div>
""".format(
    total_jobs=stats['total_jobs'],
    last_update=datetime.now().strftime('%B %d, %Y at %I:%M %p')
), unsafe_allow_html=True)

# Stats Row
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class='stat-card'>
        <div style='font-size: 32px; font-weight: bold; color: #3b82f6;'>{stats['h1b_sponsors']:,}</div>
        <div style='color: #6b7280; font-size: 14px;'>H-1B Sponsors</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='stat-card'>
        <div style='font-size: 32px; font-weight: bold; color: #8b5cf6;'>{stats['remote_jobs']:,}</div>
        <div style='color: #6b7280; font-size: 14px;'>Remote Jobs</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg_sal = int(stats['avg_salary']/1000) if stats['avg_salary'] else 0
    st.markdown(f"""
    <div class='stat-card'>
        <div style='font-size: 32px; font-weight: bold; color: #f59e0b;'>${avg_sal}K</div>
        <div style='color: #6b7280; font-size: 14px;'>Avg Salary</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Filters Section - Clean horizontal layout
st.markdown("### 🎛️ Filter Jobs")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    job_categories = st.multiselect(
        "💼 Category",
        options=['Software Engineer', 'Data Science', 'Data Engineer', 'Machine Learning', 
                 'DevOps', 'Product Manager', 'Business Analyst', 'IT Support', 'Other'],
        default=[],
        key="category_filter"
    )

with col2:
    selected_companies = st.multiselect(
        "🏢 Company",
        options=all_companies,
        default=[],
        key="company_filter"
    )

with col3:
    selected_locations = st.multiselect(
        "📍 Location",
        options=all_locations,
        default=[],
        key="location_filter"
    )

with col4:
    selected_work_models = st.multiselect(
        "💻 Work Model",
        options=['Remote', 'Hybrid', 'On-site'],
        default=[],
        key="work_filter"
    )

with col5:
    visa_filter = st.selectbox(
        "🎫 H-1B Sponsor",
        options=['All', 'Yes', 'No'],
        index=0,
        key="visa_filter"
    )

with col6:
    posted_within = st.selectbox(
        "📅 Posted",
        options=['Any time', 'Last 24 hours', 'Last 7 days', 'Last 30 days'],
        index=0,
        key="date_filter"
    )

# Filter action buttons
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])

with col_btn1:
    apply_filters = st.button("🎯 Apply Filters", type="primary", use_container_width=True)

with col_btn2:
    clear_filters = st.button("🔄 Clear All", use_container_width=True)

# Handle clear filters
if clear_filters:
    # Clear all filter session state keys
    st.session_state.category_filter = []
    st.session_state.company_filter = []
    st.session_state.location_filter = []
    st.session_state.work_filter = []
    st.session_state.visa_filter = 'All'
    st.session_state.date_filter = 'Any time'
    st.rerun()

# Sort and Pagination options
st.markdown("---")
col_sort, col_limit = st.columns([3, 1])

with col_sort:
    sort_by = st.selectbox(
        "📊 Sort by",
        options=['Most Recent', 'Highest Salary', 'Company (A-Z)', 'Best H-1B Rate']
    )

with col_limit:
    results_limit = st.selectbox(
        "📄 Results per page",
        options=[50, 100, 200, 500],
        index=0
    )

# Map sort options to API values
sort_map = {
    'Most Recent': 'most_recent',
    'Highest Salary': 'highest_salary',
    'Company (A-Z)': 'company_az',
    'Best H-1B Rate': 'h1b_rate'
}

# Map posted_within to days
posted_days_map = {
    'Any time': None,
    'Last 24 hours': 1,
    'Last 7 days': 7,
    'Last 30 days': 30
}

# Build filter request - only include non-default values
# Use category as search term if selected
category_search = " OR ".join(job_categories) if job_categories else None

filter_request = {
    "search": category_search,  # Use categories as search terms
    "companies": selected_companies if selected_companies else None,
    "locations": selected_locations if selected_locations else None,
    "work_models": selected_work_models if selected_work_models else None,
    "experience_levels": None,
    "visa_sponsorship": visa_filter if visa_filter != 'All' else None,
    "salary_min": None,
    "salary_max": None,
    "posted_within_days": posted_days_map[posted_within],
    "sort_by": sort_map[sort_by],
    "limit": results_limit
}

# Search jobs with filters
with st.spinner("🔍 Searching jobs..."):
    jobs_data, total_jobs = search_jobs(filter_request)
    filtered_df = pd.DataFrame(jobs_data) if jobs_data else pd.DataFrame()

# Display results count
st.markdown(f"""
<div style='background: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;'>
    <strong>📊 Showing {len(filtered_df):,} jobs</strong> 
    {f'(filtered from {stats["total_jobs"]:,} total)' if len(filtered_df) < stats["total_jobs"] else ''}
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Display jobs
if len(filtered_df) == 0:
    st.warning("😔 No jobs found matching your criteria. Try adjusting the filters.")
else:
        # Table View - Clean and Interactive
        display_df = filtered_df.copy()
        
        # Create a combined salary column (only if salary exists)
        def format_salary(row):
            try:
                sal_min = float(row.get('salary_min', 0) or 0)
                sal_max = float(row.get('salary_max', 0) or 0)
                if sal_min > 0 or sal_max > 0:
                    return f"${sal_min:,.0f} - ${sal_max:,.0f}"
            except (ValueError, TypeError):
                pass
            return "Not listed"
        
        display_df['Salary'] = display_df.apply(format_salary, axis=1)
        
        # Format H-1B
        display_df['H-1B'] = display_df.apply(
            lambda row: f"✅ Yes ({row['h1b_approval_rate']*100:.0f}%)" if row.get('h1b_sponsor') and row.get('h1b_approval_rate', 0) > 0
            else "✅ Yes" if row.get('h1b_sponsor')
            else "❌ No",
            axis=1
        )
        
        # Format days - use actual posted_date if available
        def format_posted_date(row):
            days = row.get('days_since_posted', 0)
            if pd.notna(days):
                if days == 0:
                    return "Today"
                elif days == 1:
                    return "Yesterday"
                elif days < 7:
                    return f"{int(days)} days ago"
                elif days < 30:
                    weeks = int(days / 7)
                    return f"{weeks} week{'s' if weeks > 1 else ''} ago"
                else:
                    return f"{int(days)} days ago"
            return "N/A"
        
        display_df['Posted'] = display_df.apply(format_posted_date, axis=1)
        
        # Select only needed columns
        table_cols = ['title', 'company', 'location', 'Salary', 'work_model', 'H-1B', 'job_type', 'Posted', 'url']
        available_cols = [col for col in table_cols if col in display_df.columns]
        
        # Rename for display
        column_rename = {
            'title': '💼 Job Title',
            'company': '🏢 Company',
            'location': '📍 Location',
            'work_model': '🏠 Work Model',
            'job_type': '📋 Type',
            'url': '🎯 Apply'
        }
        
        final_df = display_df[available_cols].rename(columns=column_rename)
        
        # Display interactive table with clickable links
        st.dataframe(
            final_df,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config={
                "🎯 Apply": st.column_config.LinkColumn(
                    "🔗 Apply"
                )
            }
        )
        
        # Add apply buttons for selected rows
        st.markdown("---")
        st.markdown("### 📋 Bulk Actions")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("💡 Select jobs from the table above and use bulk actions")
        
        with col2:
            if st.button("📥 Export Selected", use_container_width=True):
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"jobs_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

# Footer with auto-refresh info
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #6b7280; font-size: 14px;'>
    <p>
        🔄 Data refreshes every 5 minutes • 
        💾 Jobs loaded from Snowflake JOB_INTELLIGENCE database • 
        📊 Total: {total} jobs available
    </p>
    <p style='font-size: 12px; margin-top: 5px;'>
        Last update: {timestamp}
    </p>
</div>
""".format(
    total=stats['total_jobs'],
    timestamp=datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')
), unsafe_allow_html=True)
