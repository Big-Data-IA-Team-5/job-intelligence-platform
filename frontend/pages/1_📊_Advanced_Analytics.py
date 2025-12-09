"""
Advanced Analytics Dashboard - Real-time Data Visualizations
Powered by 37K+ jobs and real H-1B data from Snowflake
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.api_client import APIClient

st.set_page_config(
    page_title="Advanced Analytics",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .insight-box {
        background-color: #f0f9ff;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize API client
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

# Load data functions
@st.cache_data(ttl=600)
def load_summary():
    """Get overall analytics summary"""
    try:
        response = st.session_state.api_client.get('/analytics/summary')
        return response
    except Exception as e:
        st.error(f"Failed to load summary: {e}")
        return None

@st.cache_data(ttl=600)
def load_top_companies(limit=20):
    """Get top companies by job count"""
    try:
        response = st.session_state.api_client.get('/analytics/companies', params={'limit': limit})
        return response
    except Exception as e:
        st.error(f"Failed to load companies: {e}")
        return []

@st.cache_data(ttl=600)
def load_h1b_sponsors(limit=30):
    """Get top H-1B sponsoring companies"""
    try:
        response = st.session_state.api_client.get('/analytics/visa-sponsors', params={'limit': limit})
        return response
    except Exception as e:
        st.error(f"Failed to load H-1B sponsors: {e}")
        return []

@st.cache_data(ttl=600)
def load_locations(limit=15):
    """Get top locations by job count"""
    try:
        response = st.session_state.api_client.get('/analytics/locations', params={'limit': limit})
        return response
    except Exception as e:
        st.error(f"Failed to load locations: {e}")
        return []

@st.cache_data(ttl=600)
def load_categories():
    """Get job distribution by visa category"""
    try:
        response = st.session_state.api_client.get('/analytics/categories')
        return response
    except Exception as e:
        st.error(f"Failed to load categories: {e}")
        return []

@st.cache_data(ttl=600)
def load_trends(days=30):
    """Get job posting trends"""
    try:
        response = st.session_state.api_client.get('/analytics/trends', params={'days': days})
        return response
    except Exception as e:
        st.error(f"Failed to load trends: {e}")
        return []

# Load all data
summary = load_summary()
if not summary:
    st.error("Unable to connect to backend. Please ensure backend service is running.")
    st.stop()

companies_data = load_top_companies(20)
h1b_sponsors_data = load_h1b_sponsors(30)
locations_data = load_locations(15)
categories_data = load_categories()
trends_data = load_trends(30)

# Header
st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 30px; border-radius: 10px; margin-bottom: 20px;'>
    <h1 style='color: white; margin: 0;'>🎯 Advanced Job Intelligence Analytics</h1>
    <p style='color: #e0e7ff; margin: 10px 0 0 0;'>Interactive visualizations powered by 37K+ jobs and real H-1B data</p>
</div>
""", unsafe_allow_html=True)

# Summary Cards
st.markdown("### 📊 Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Jobs", f"{summary['total_jobs']:,}")
with col2:
    st.metric("Companies", f"{summary['total_companies']:,}")
with col3:
    st.metric("H-1B Sponsors", f"{summary['h1b_sponsors']:,}")
with col4:
    st.metric("New (7 days)", f"{summary['recent_postings_7d']:,}")
with col5:
    avg_sal = f"${summary['avg_salary']/1000:.0f}K" if summary.get('avg_salary') else "N/A"
    st.metric("Avg Salary", avg_sal)

st.divider()

# Chart 1: Job Posting Trends
if trends_data:
    st.markdown("### 📈 Job Posting Trends (Last 30 Days)")
    trends_df = pd.DataFrame(trends_data)
    
    fig_trends = go.Figure()
    fig_trends.add_trace(go.Scatter(
        x=trends_df['date'],
        y=trends_df['count'],
        mode='lines+markers',
        name='Job Postings',
        line=dict(color='#667eea', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.1)'
    ))
    
    fig_trends.update_layout(
        height=350,
        xaxis_title="Date",
        yaxis_title="Number of Jobs Posted",
        hovermode='x unified',
        showlegend=False
    )
    
    st.plotly_chart(fig_trends, use_container_width=True)
    
    # Insight
    total_last_30 = trends_df['count'].sum()
    avg_daily = trends_df['count'].mean()
    st.markdown(f"""
    <div class='insight-box'>
        <strong>💡 Insight:</strong> {total_last_30:,} jobs posted in last 30 days 
        (avg: {avg_daily:.0f} jobs/day)
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Two column layout
col_left, col_right = st.columns(2)

with col_left:
    # Chart 2: Top Companies
    if companies_data:
        st.markdown("### 🏢 Top Companies by Job Count")
        companies_df = pd.DataFrame(companies_data)[:15]
        
        fig_companies = go.Figure()
        fig_companies.add_trace(go.Bar(
            y=companies_df['company'],
            x=companies_df['job_count'],
            orientation='h',
            marker=dict(
                color=companies_df['job_count'],
                colorscale='Viridis',
                showscale=False
            ),
            text=companies_df['job_count'],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Jobs: %{x}<extra></extra>'
        ))
        
        fig_companies.update_layout(
            height=500,
            xaxis_title="Number of Jobs",
            yaxis_title="",
            showlegend=False,
            yaxis=dict(autorange="reversed")
        )
        
        st.plotly_chart(fig_companies, use_container_width=True)

with col_right:
    # Chart 3: Visa Category Distribution
    if categories_data:
        st.markdown("### 🎫 Jobs by Visa Category")
        categories_df = pd.DataFrame(categories_data)[:8]
        
        fig_categories = go.Figure(data=[go.Pie(
            labels=categories_df['category'],
            values=categories_df['count'],
            hole=0.4,
            marker=dict(colors=['#667eea', '#764ba2', '#f093fb', '#4facfe', 
                                '#43e97b', '#38f9d7', '#fa709a', '#fee140']),
            textinfo='label+percent',
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>Jobs: %{value:,}<br>%{percent}<extra></extra>'
        )])
        
        fig_categories.update_layout(
            height=500,
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5)
        )
        
        st.plotly_chart(fig_categories, use_container_width=True)

st.divider()

# Chart 4: Top Locations
if locations_data:
    st.markdown("### 📍 Top Job Locations")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        locations_df = pd.DataFrame(locations_data)[:12]
        
        fig_locations = go.Figure()
        fig_locations.add_trace(go.Bar(
            x=locations_df['location'],
            y=locations_df['job_count'],
            marker=dict(
                color='#667eea',
                line=dict(color='#764ba2', width=2)
            ),
            text=locations_df['job_count'],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Jobs: %{y:,}<extra></extra>'
        ))
        
        fig_locations.update_layout(
            height=400,
            xaxis_title="",
            yaxis_title="Number of Jobs",
            showlegend=False,
            xaxis={'tickangle': -45}
        )
        
        st.plotly_chart(fig_locations, use_container_width=True)
    
    with col2:
        st.markdown("#### 🌎 Geographic Insights")
        st.markdown(f"""
        <div style='background: #f9fafb; padding: 15px; border-radius: 8px;'>
            <h3 style='margin: 0 0 10px 0; color: #667eea;'>{locations_df['location'].iloc[0]}</h3>
            <p style='font-size: 32px; font-weight: bold; margin: 0; color: #1f2937;'>
                {locations_df['job_count'].iloc[0]:,}
            </p>
            <p style='color: #6b7280; margin: 5px 0 0 0;'>jobs available</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        top_5_jobs = locations_df['job_count'].head(5).sum()
        total_jobs = summary['total_jobs']
        pct = (top_5_jobs / total_jobs * 100)
        
        st.markdown(f"""
        <div class='insight-box'>
            <strong>💡 Insight:</strong> Top 5 locations account for 
            {pct:.1f}% ({top_5_jobs:,}) of all jobs
        </div>
        """, unsafe_allow_html=True)

st.divider()

# Chart 5: H-1B Sponsors Analysis
if h1b_sponsors_data:
    st.markdown("### 🏆 Top H-1B Sponsoring Companies")
    st.caption("Companies actively offering visa sponsorship with approval rate data")
    
    sponsors_df = pd.DataFrame(h1b_sponsors_data)[:20]
    
    # Create bubble chart
    fig_sponsors = go.Figure()
    
    # Scale bubble sizes (job_count determines size)
    max_jobs = sponsors_df['job_count'].max()
    sponsors_df['bubble_size'] = (sponsors_df['job_count'] / max_jobs * 50) + 10
    
    fig_sponsors.add_trace(go.Scatter(
        x=sponsors_df.index,
        y=sponsors_df['avg_approval_rate'] * 100,
        mode='markers',
        marker=dict(
            size=sponsors_df['bubble_size'],
            color=sponsors_df['avg_approval_rate'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title="Approval<br>Rate"),
            line=dict(color='white', width=2)
        ),
        text=sponsors_df['company'],
        hovertemplate='<b>%{text}</b><br>' +
                      'Approval Rate: %{y:.1f}%<br>' +
                      'Jobs: ' + sponsors_df['job_count'].astype(str) +
                      '<extra></extra>'
    ))
    
    fig_sponsors.update_layout(
        height=450,
        xaxis_title="Company Rank",
        yaxis_title="H-1B Approval Rate (%)",
        yaxis=dict(range=[80, 105]),
        showlegend=False,
        hovermode='closest'
    )
    
    # Add threshold line at 90%
    fig_sponsors.add_hline(y=90, line_dash="dash", line_color="gray", 
                           annotation_text="90% Threshold")
    
    st.plotly_chart(fig_sponsors, use_container_width=True)
    
    # Top sponsors table
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("#### 🎯 Top 10 H-1B Sponsors")
        display_sponsors = sponsors_df[['company', 'job_count', 'avg_approval_rate']].head(10).copy()
        display_sponsors['avg_approval_rate'] = display_sponsors['avg_approval_rate'].apply(
            lambda x: f"{x*100:.1f}%" if x else "N/A"
        )
        display_sponsors.columns = ['Company', 'Open Jobs', 'Approval Rate']
        st.dataframe(display_sponsors, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("#### 📊 Sponsorship Stats")
        high_approval = len(sponsors_df[sponsors_df['avg_approval_rate'] >= 0.95])
        avg_rate = sponsors_df['avg_approval_rate'].mean() * 100
        total_sponsor_jobs = sponsors_df['job_count'].sum()
        
        st.markdown(f"""
        <div style='background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 10px;'>
            <div style='font-size: 12px; color: #6b7280;'>High Approval (≥95%)</div>
            <div style='font-size: 32px; font-weight: bold; color: #10b981;'>{high_approval}</div>
            <div style='font-size: 12px; color: #6b7280;'>companies</div>
        </div>
        
        <div style='background: #f3f4f6; padding: 15px; border-radius: 8px; margin-bottom: 10px;'>
            <div style='font-size: 12px; color: #6b7280;'>Avg Approval Rate</div>
            <div style='font-size: 32px; font-weight: bold; color: #667eea;'>{avg_rate:.1f}%</div>
        </div>
        
        <div style='background: #f3f4f6; padding: 15px; border-radius: 8px;'>
            <div style='font-size: 12px; color: #6b7280;'>Total Sponsor Jobs</div>
            <div style='font-size: 32px; font-weight: bold; color: #764ba2;'>{total_sponsor_jobs:,}</div>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 20px;'>
    <p>📊 Data updated in real-time from Snowflake database</p>
    <p>🔄 Refresh this page to see latest statistics</p>
</div>
""", unsafe_allow_html=True)
