"""
Analytics Page - Connected to Snowflake Backend
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
st.markdown("Real-time insights from Snowflake database with 8,000+ jobs")

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
    with st.spinner("Loading analytics from Snowflake..."):
        summary = st.session_state.api_client.get("/analytics/summary")
        companies = st.session_state.api_client.get("/analytics/companies?limit=20")
        trends = st.session_state.api_client.get(f"/analytics/trends?days={days}")
        categories = st.session_state.api_client.get("/analytics/categories")
        locations = st.session_state.api_client.get("/analytics/locations?limit=15")
        sponsors = st.session_state.api_client.get("/analytics/visa-sponsors?limit=10")
    
    # Summary metrics at top
    st.header("📊 Platform Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Jobs", f"{summary.get('total_jobs', 0):,}")
    with col2:
        st.metric("Companies", f"{summary.get('total_companies', 0):,}")
    with col3:
        st.metric("H-1B Sponsors", f"{summary.get('h1b_sponsors', 0):,}")
    with col4:
        avg_sal = summary.get('avg_salary')
        st.metric("Avg Salary", f"${avg_sal:,.0f}" if avg_sal else "N/A")
    
    st.markdown("---")
    
    # Top companies
    st.header("🏢 Top Hiring Companies")
    if companies and isinstance(companies, list) and len(companies) > 0:
        df_companies = pd.DataFrame(companies)
        
        # Main bar chart
        fig = px.bar(
            df_companies.head(15),
            x='job_count',
            y='company',
            orientation='h',
            title='Top 15 Companies by Job Postings',
            labels={'job_count': 'Number of Jobs', 'company': 'Company'},
            color='job_count',
            color_continuous_scale='Blues'
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # H1B sponsors analysis
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("H-1B Sponsorship Distribution")
            h1b_count = df_companies['h1b_sponsor'].sum()
            non_h1b = len(df_companies) - h1b_count
            fig = px.pie(
                values=[h1b_count, non_h1b],
                names=['H-1B Sponsors', 'Non-Sponsors'],
                title='Companies Offering H-1B',
                color_discrete_sequence=['#2ecc71', '#e74c3c']
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("H-1B Approval Rates")
            # Filter companies with approval rate data
            df_with_rates = df_companies[df_companies['avg_approval_rate'].notna()].head(10)
            if not df_with_rates.empty:
                df_with_rates['approval_pct'] = df_with_rates['avg_approval_rate'] * 100
                fig = px.bar(
                    df_with_rates,
                    x='approval_pct',
                    y='company',
                    orientation='h',
                    title='Top 10 - H-1B Approval Rates',
                    labels={'approval_pct': 'Approval Rate (%)', 'company': 'Company'},
                    color='approval_pct',
                    color_continuous_scale='Greens'
                )
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No approval rate data available")
    
    # Trends over time
    st.header("📈 Job Posting Trends")
    if trends and isinstance(trends, list) and len(trends) > 0:
        df_trends = pd.DataFrame(trends)
        df_trends['date'] = pd.to_datetime(df_trends['date'])
        df_trends = df_trends.sort_values('date')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_trends['date'],
            y=df_trends['count'],
            mode='lines+markers',
            name='Job Postings',
            line=dict(color='#3498db', width=3),
            marker=dict(size=10)
        ))
        
        fig.update_layout(
            title=f'Job Postings Trend - {time_range}',
            xaxis_title='Date',
            yaxis_title='Number of Jobs',
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No trend data available for {time_range}")
    
    # Visa categories
    st.header("📂 Visa Category Distribution")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if categories and isinstance(categories, list) and len(categories) > 0:
            df_categories = pd.DataFrame(categories)
            
            # Pie chart for visa categories
            fig = px.pie(
                df_categories,
                values='count',
                names='category',
                title='Visa Category Breakdown',
                color_discrete_sequence=['#3498db', '#e74c3c'],
                hole=0.4
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if categories and isinstance(categories, list) and len(categories) > 0:
            st.subheader("Category Details")
            for cat in df_categories.itertuples():
                st.metric(
                    cat.category,
                    f"{cat.count:,} jobs",
                    f"{cat.percentage:.1f}%"
                )
    
    # Top locations
    st.header("🌎 Top Locations")
    if locations and isinstance(locations, list) and len(locations) > 0:
        df_locations = pd.DataFrame(locations)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Bar chart
            fig = px.bar(
                df_locations.head(10),
                x='job_count',
                y='location',
                orientation='h',
                title='Top 10 Locations by Job Count',
                labels={'job_count': 'Number of Jobs', 'location': 'Location'},
                color='job_count',
                color_continuous_scale='Oranges'
            )
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Treemap
            fig = px.treemap(
                df_locations.head(15),
                path=['location'],
                values='job_count',
                title='Location Distribution (Top 15)',
                color='job_count',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # H-1B Sponsors deep dive
    st.header("🎯 Top H-1B Sponsors")
    if sponsors and isinstance(sponsors, list) and len(sponsors) > 0:
        df_sponsors = pd.DataFrame(sponsors)
        df_sponsors['approval_pct'] = df_sponsors['avg_approval_rate'] * 100
        
        # Create a detailed table
        st.dataframe(
            df_sponsors[['company', 'job_count', 'approval_pct']].rename(columns={
                'company': 'Company',
                'job_count': 'Job Openings',
                'approval_pct': 'H-1B Approval Rate (%)'
            }),
            use_container_width=True,
            hide_index=True
        )

except Exception as e:
    st.error(f"❌ Error loading analytics: {str(e)}")
    st.info("🔍 **Troubleshooting:**")
    st.markdown("""
    - Check if backend API is running on port 8000
    - Verify Snowflake connection in backend
    - Check if jobs_processed table has data
    """)
    
    # Show connection status
    with st.expander("🔧 Debug Info"):
        try:
            health = st.session_state.api_client.get("/health")
            st.json(health)
        except:
            st.error("Backend API is not responding")

# Export and refresh
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Refresh Data"):
        st.rerun()

with col2:
    if st.button("📥 Export Analytics"):
        try:
            # Prepare export data
            export_data = {
                "summary": summary,
                "companies": companies[:10] if companies else [],
                "categories": categories,
                "locations": locations[:10] if locations else []
            }
            st.download_button(
                label="Download JSON",
                data=str(export_data),
                file_name=f"analytics_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        except:
            st.error("Export failed")
