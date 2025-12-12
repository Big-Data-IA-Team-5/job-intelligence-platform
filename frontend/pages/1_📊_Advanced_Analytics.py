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

# Custom CSS (cleaner, lighter look)
st.markdown("""
<style>
    .metric-card { 
        background: #ffffff; 
        border: 1px solid #e5e7eb; 
        padding: 14px; 
        border-radius: 10px; 
        color: #111827; 
        text-align: center; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .insight-box { 
        background-color: #f9fafb; 
        border-left: 4px solid #6366f1; 
        padding: 12px; 
        border-radius: 6px; 
        margin: 8px 0; 
        color: #1f2937; 
    }
    .subtle { color: #6b7280; font-size: 12px; }
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
        response = st.session_state.api_client.get('/api/v1/analytics/summary')
        return response
    except Exception as e:
        st.error(f"Failed to load summary: {e}")
        return None

@st.cache_data(ttl=600)
def load_top_companies(limit=20):
    """Get top companies by job count"""
    try:
        response = st.session_state.api_client.get('/api/v1/analytics/companies', params={'limit': limit})
        return response
    except Exception as e:
        st.error(f"Failed to load companies: {e}")
        return []

@st.cache_data(ttl=600)
def load_h1b_sponsors(limit=30):
    """Get top H-1B sponsoring companies"""
    try:
        response = st.session_state.api_client.get('/api/v1/analytics/visa-sponsors', params={'limit': limit})
        return response
    except Exception as e:
        st.error(f"Failed to load H-1B sponsors: {e}")
        return []

@st.cache_data(ttl=600)
def load_locations(limit=15):
    """Get top locations by job count"""
    try:
        response = st.session_state.api_client.get('/api/v1/analytics/locations', params={'limit': limit})
        return response
    except Exception as e:
        st.error(f"Failed to load locations: {e}")
        return []

@st.cache_data(ttl=600)
def load_categories():
    """Get job distribution by visa category"""
    try:
        response = st.session_state.api_client.get('/api/v1/analytics/categories')
        return response
    except Exception as e:
        st.error(f"Failed to load categories: {e}")
        return []

@st.cache_data(ttl=600)
def load_trends(days=30):
    """Get job posting trends"""
    try:
        response = st.session_state.api_client.get('/api/v1/analytics/trends', params={'days': days})
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

# Helper: normalize ambiguous company labels
def _normalize_company(name: str) -> str:
    try:
        n = (name or '').strip()
    except Exception:
        return 'Unspecified Company'
    if n.lower() in {'unknown','n/a','na','confidential','stealth','not disclosed','unspecified','-','null','none'}:
        return 'Unspecified Company'
    return n

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
    st.metric("Total Jobs", f"{summary.get('total_jobs', 0):,}")
with col2:
    st.metric("Companies", f"{summary.get('total_companies', 0):,}")
with col3:
    st.metric("H-1B Sponsors", f"{summary.get('h1b_sponsors', 0):,}")
with col4:
    st.metric("New (7 days)", f"{summary.get('recent_postings_7d', 0):,}")
with col5:
    avg_sal = f"${summary.get('avg_salary', 0)/1000:.0f}K" if summary.get('avg_salary') else "N/A"
    st.metric("Avg Salary", avg_sal)

st.divider()

# Chart 1: Job Posting Trends
if trends_data:
    st.markdown("### 📈 Job Posting Trends (Last 30 Days)")
    trends_df = pd.DataFrame(trends_data)
    
    if not trends_df.empty:
        fig_trends = go.Figure()
        fig_trends.add_trace(go.Scatter(
            x=trends_df.get('date', []),
            y=trends_df.get('count', []),
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
        total_last_30 = trends_df['count'].sum() if 'count' in trends_df.columns else 0
        avg_daily = trends_df['count'].mean() if 'count' in trends_df.columns else 0
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
        if not companies_df.empty and 'company' in companies_df.columns:
            companies_df['company'] = companies_df['company'].apply(_normalize_company)
        
        if not companies_df.empty and 'company' in companies_df.columns and 'job_count' in companies_df.columns:
            fig_companies = go.Figure()
            fig_companies.add_trace(go.Bar(
                y=companies_df['company'],
                x=companies_df['job_count'],
                orientation='h',
                marker=dict(color='#4f46e5'),
                text=companies_df['job_count'],
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Jobs: %{x}<extra></extra>'
            ))
            
            fig_companies.update_layout(
                height=420,
                xaxis_title="Number of Jobs",
                yaxis_title="",
                showlegend=False,
                yaxis=dict(autorange="reversed")
            )
            
            st.plotly_chart(fig_companies, use_container_width=True)
        else:
            st.info("No company data available")
    else:
        st.info("No company data available")
    st.caption("Note: 'Unspecified Company' means the employer name wasn’t disclosed in the posting.")

with col_right:
    # Chart 3: Visa Category Distribution
    if categories_data:
        st.markdown("### 🎫 Jobs by Visa Category")
        categories_df = pd.DataFrame(categories_data)[:8]
        
        if not categories_df.empty and 'category' in categories_df.columns and 'count' in categories_df.columns:
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
        else:
            st.info("No category data available")
    else:
        st.info("No category data available")

st.divider()

# Chart 4: Top Locations
if locations_data:
    st.markdown("### 📍 Top Job Locations")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        locations_df = pd.DataFrame(locations_data)[:12]
        
        if not locations_df.empty and 'location' in locations_df.columns and 'job_count' in locations_df.columns:
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
        locations_df = pd.DataFrame(locations_data)[:12]
        
        if not locations_df.empty:
            top_loc = locations_df.iloc[0]
            st.markdown(f"""
            <div style='background: #f9fafb; padding: 15px; border-radius: 8px;'>
                <h3 style='margin: 0 0 10px 0; color: #667eea;'>{top_loc.get('location', 'N/A')}</h3>
                <p style='font-size: 32px; font-weight: bold; margin: 0; color: #1f2937;'>
                    {top_loc.get('job_count', 0):,}
                </p>
                <p style='color: #6b7280; margin: 5px 0 0 0;'>jobs available</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            top_5_jobs = locations_df['job_count'].head(5).sum()
            total_jobs = summary.get('total_jobs', 1)
            pct = (top_5_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
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
    st.caption("Companies actively offering visa sponsorship with approval rate data from actual USCIS filings")
    
    sponsors_df = pd.DataFrame(h1b_sponsors_data)[:20]
    
    if not sponsors_df.empty and 'company' in sponsors_df.columns:
        sponsors_df['company'] = sponsors_df['company'].apply(_normalize_company)
        # Create bubble chart
        fig_sponsors = go.Figure()

        # Scale bubble sizes (job_count determines size)
        max_jobs = sponsors_df['job_count'].max() if 'job_count' in sponsors_df.columns else 1
        sponsors_df['bubble_size'] = (sponsors_df['job_count'] / max_jobs * 50) + 10 if max_jobs > 0 else 20

        # Normalize approval rate to percentage 0-100
        if 'avg_approval_rate' in sponsors_df.columns:
            sponsors_df['approval_pct'] = sponsors_df['avg_approval_rate'].apply(lambda v: float(v) if pd.notnull(v) else None)
            sponsors_df['approval_pct'] = sponsors_df['approval_pct'].apply(lambda v: v * 100.0 if v is not None and v <= 1.0 else v)
            sponsors_df['approval_pct'] = sponsors_df['approval_pct'].clip(lower=0, upper=100)
        else:
            sponsors_df['approval_pct'] = 0.0

        # Sort by job_count and keep top 15 for readability
        sponsors_df = sponsors_df.sort_values(by='job_count', ascending=False).head(15)

        # Build hover text with breakdown if available
        hover_texts = []
        for idx, row in sponsors_df.iterrows():
            hover = f"<b>{row['company']}</b><br>Jobs: {row['job_count']}"
            
            # Show breakdown if available
            if 'h1b_certified' in row and 'h1b_applications' in row and pd.notnull(row['h1b_certified']) and pd.notnull(row['h1b_applications']):
                certified = int(row['h1b_certified'])
                total = int(row['h1b_applications'])
                hover += f"<br><br>H-1B Breakdown:"
                hover += f"<br>  ✅ Approved: {certified:,}"
                hover += f"<br>  📋 Total Filed: {total:,}"
                hover += f"<br>  📊 Rate: {row.get('approval_pct', 90.0):.1f}%"
            else:
                hover += f"<br>Approval Rate: {row.get('approval_pct', 90.0):.1f}%"
            
            hover_texts.append(hover)
        
        fig_sponsors.add_trace(go.Scatter(
            x=sponsors_df['approval_pct'].fillna(90.0),
            y=sponsors_df['company'],
            mode='markers',
            marker=dict(
                size=sponsors_df['bubble_size'],
                color=sponsors_df['approval_pct'].fillna(90.0),
                colorscale='Blues',
                showscale=True,
                colorbar=dict(title="Approval Rate (%)"),
                cmin=80,
                cmax=100,
                line=dict(color='white', width=1.5)
            ),
            customdata=hover_texts,
            hovertemplate='%{customdata}<extra></extra>'
        ))

        fig_sponsors.update_layout(
            height=500,
            xaxis_title="H-1B Approval Rate (%)",
            yaxis_title="",
            xaxis=dict(range=[80, 100]),
            showlegend=False,
        )

        # Add threshold line at 90%
        fig_sponsors.add_vline(x=90, line_dash="dash", line_color="#6b7280", annotation_text="90% Threshold")

        st.plotly_chart(fig_sponsors, use_container_width=True)
        
        # Top sponsors table
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("#### 🎯 Top 10 H-1B Sponsors")
            
            # Prepare display table with breakdown
            display_cols = ['company', 'job_count']
            if 'h1b_certified' in sponsors_df.columns and 'h1b_applications' in sponsors_df.columns:
                display_cols.extend(['h1b_certified', 'h1b_applications', 'approval_pct'])
            else:
                display_cols.append('approval_pct')
            
            display_sponsors = sponsors_df[display_cols].head(10).copy()
            
            # Format the columns
            if 'h1b_certified' in display_sponsors.columns:
                display_sponsors['h1b_certified'] = display_sponsors['h1b_certified'].apply(
                    lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A"
                )
            if 'h1b_applications' in display_sponsors.columns:
                display_sponsors['h1b_applications'] = display_sponsors['h1b_applications'].apply(
                    lambda x: f"{int(x):,}" if pd.notnull(x) else "N/A"
                )
            display_sponsors['approval_pct'] = display_sponsors['approval_pct'].apply(
                lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A"
            )
            
            # Rename columns for display
            col_names = ['Company', 'Open Jobs']
            if 'h1b_certified' in display_sponsors.columns:
                col_names.extend(['✅ Approved', '📋 Total Filed', '📊 Rate'])
            else:
                col_names.append('Approval Rate')
            display_sponsors.columns = col_names
            
            st.dataframe(display_sponsors, use_container_width=True, hide_index=True)
            st.caption("**Formula:** Approval Rate = (✅ Approved / 📋 Total Filed) × 100")
        
        with col2:
            st.markdown("#### 📊 Sponsorship Stats")
            high_approval = len(sponsors_df[sponsors_df['approval_pct'] >= 95.0]) if 'approval_pct' in sponsors_df.columns else 0
            avg_rate = sponsors_df['approval_pct'].mean() if 'approval_pct' in sponsors_df.columns else 0
            total_sponsor_jobs = sponsors_df['job_count'].sum() if 'job_count' in sponsors_df.columns else 0
            
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
        
        st.info("💡 **About 100% Approval Rates:** Companies showing 100% may have small sample sizes (e.g., 1-10 applications). Hover over chart bubbles to see actual application volumes from USCIS data.")
    else:
        st.info("No H-1B sponsor data available")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 20px;'>
    <p>📊 Data updated in real-time from Snowflake database</p>
    <p>🔄 Refresh this page to see latest statistics</p>
</div>
""", unsafe_allow_html=True)
