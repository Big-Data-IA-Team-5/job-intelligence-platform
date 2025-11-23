"""
Analytics Page
"""
import streamlit as st
from utils.api_client import APIClient
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")

# Initialize
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

st.title("📊 Job Market Analytics")
st.markdown("Insights into the job market trends and statistics")

# Time range selector
time_range = st.selectbox(
    "Time Range",
    ["Last 7 Days", "Last 30 Days", "Last 90 Days"],
    index=1
)

days_map = {
    "Last 7 Days": 7,
    "Last 30 Days": 30,
    "Last 90 Days": 90
}

days = days_map[time_range]

try:
    # Fetch analytics data
    with st.spinner("Loading analytics..."):
        companies = st.session_state.api_client.get("/analytics/companies?limit=20")
        trends = st.session_state.api_client.get(f"/analytics/trends?days={days}")
        categories = st.session_state.api_client.get("/analytics/categories")
        locations = st.session_state.api_client.get("/analytics/locations?limit=15")
    
    # Top companies
    st.header("🏢 Top Hiring Companies")
    if companies and companies.get('companies'):
        df_companies = pd.DataFrame(companies['companies'])
        
        fig = px.bar(
            df_companies.head(10),
            x='job_count',
            y='company_name',
            orientation='h',
            title='Top 10 Companies by Job Postings',
            labels={'job_count': 'Number of Jobs', 'company_name': 'Company'}
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
        # H1B sponsors
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("H1B Sponsorship")
            h1b_df = df_companies[df_companies['h1b_sponsor_count'] > 0].head(10)
            fig = px.pie(
                h1b_df,
                values='h1b_sponsor_count',
                names='company_name',
                title='Top H1B Sponsors'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Remote Opportunities")
            remote_df = df_companies[df_companies['remote_count'] > 0].head(10)
            fig = px.pie(
                remote_df,
                values='remote_count',
                names='company_name',
                title='Companies with Remote Jobs'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Trends over time
    st.header("📈 Job Posting Trends")
    if trends and trends.get('trends'):
        df_trends = pd.DataFrame(trends['trends'])
        df_trends['date'] = pd.to_datetime(df_trends['date'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trends['date'],
            y=df_trends['job_count'],
            mode='lines+markers',
            name='Job Postings',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title='Daily Job Postings',
            xaxis_title='Date',
            yaxis_title='Number of Jobs',
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Job categories
    st.header("📂 Job Categories Distribution")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if categories and categories.get('categories'):
            df_categories = pd.DataFrame(categories['categories'])
            
            fig = px.bar(
                df_categories,
                x='count',
                y='job_category',
                orientation='h',
                title='Jobs by Category',
                labels={'count': 'Number of Jobs', 'job_category': 'Category'},
                color='count',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if categories and categories.get('categories'):
            st.subheader("Category Stats")
            for cat in df_categories.itertuples():
                st.metric(
                    cat.job_category,
                    f"{cat.count} jobs",
                    f"{cat.h1b_rate:.0%} H1B"
                )
    
    # Top locations
    st.header("🌎 Top Locations")
    if locations and locations.get('locations'):
        df_locations = pd.DataFrame(locations['locations'])
        
        fig = px.treemap(
            df_locations,
            path=['location'],
            values='job_count',
            title='Job Distribution by Location'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Summary metrics
    st.header("📊 Summary Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_jobs = df_companies['job_count'].sum() if not df_companies.empty else 0
        st.metric("Total Jobs", f"{total_jobs:,}")
    
    with col2:
        total_companies = len(df_companies) if not df_companies.empty else 0
        st.metric("Companies Hiring", total_companies)
    
    with col3:
        h1b_sponsors = len(df_companies[df_companies['h1b_sponsor_count'] > 0]) if not df_companies.empty else 0
        st.metric("H1B Sponsors", h1b_sponsors)
    
    with col4:
        remote_companies = len(df_companies[df_companies['remote_count'] > 0]) if not df_companies.empty else 0
        st.metric("Remote Employers", remote_companies)

except Exception as e:
    st.error(f"Error loading analytics: {str(e)}")
    st.info("Make sure the backend API is running and has data")

# Export data
st.markdown("---")
if st.button("📥 Export Data"):
    st.info("Export functionality coming soon!")
