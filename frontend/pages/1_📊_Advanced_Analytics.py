"""
Advanced Analytics Dashboard - Meaningful Insights for International Students
Powered by 47K+ jobs and real H-1B data from Snowflake
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.api_client import APIClient

st.set_page_config(
    page_title="Job Market Intelligence",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .insight-box {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-left: 4px solid #0ea5e9;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
    }
    .metric-highlight {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .warning-box {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border-left: 4px solid #f59e0b;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
    }
    .success-box {
        background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
        border-left: 4px solid #10b981;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize API client
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

# ============ DATA LOADING FUNCTIONS ============
@st.cache_data(ttl=600)
def load_summary():
    try:
        return st.session_state.api_client.get('/analytics/summary')
    except Exception as e:
        st.error(f"Failed to load summary: {e}")
        return None

@st.cache_data(ttl=600)
def load_salary_by_role():
    try:
        return st.session_state.api_client.get('/analytics/salary-by-role')
    except:
        return []

@st.cache_data(ttl=600)
def load_work_models():
    try:
        return st.session_state.api_client.get('/analytics/work-models')
    except:
        return []

@st.cache_data(ttl=600)
def load_h1b_comparison():
    try:
        return st.session_state.api_client.get('/analytics/h1b-vs-non-sponsor')
    except:
        return {}

@st.cache_data(ttl=600)
def load_location_salary():
    try:
        return st.session_state.api_client.get('/analytics/location-salary')
    except:
        return []

@st.cache_data(ttl=600)
def load_experience_levels():
    try:
        return st.session_state.api_client.get('/analytics/experience-level')
    except:
        return []

@st.cache_data(ttl=600)
def load_job_types():
    try:
        return st.session_state.api_client.get('/analytics/job-type-breakdown')
    except:
        return []

@st.cache_data(ttl=600)
def load_top_skills():
    try:
        return st.session_state.api_client.get('/analytics/top-skills')
    except:
        return []

@st.cache_data(ttl=600)
def load_h1b_risk():
    try:
        return st.session_state.api_client.get('/analytics/h1b-risk-analysis')
    except:
        return {}

@st.cache_data(ttl=600)
def load_h1b_sponsors(limit=25):
    try:
        return st.session_state.api_client.get('/analytics/visa-sponsors', params={'limit': limit})
    except:
        return []

@st.cache_data(ttl=600)
def load_trends(days=30):
    try:
        return st.session_state.api_client.get('/analytics/trends', params={'days': days})
    except:
        return []

# Load all data
summary = load_summary()
if not summary:
    st.error("⚠️ Unable to connect to backend. Please ensure the backend service is running.")
    st.stop()

# ============ HEADER ============
st.markdown("""
<div style='background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); 
            padding: 30px; border-radius: 15px; margin-bottom: 25px;'>
    <h1 style='color: white; margin: 0; font-size: 2.2em;'>🎯 Job Market Intelligence for International Students</h1>
    <p style='color: #93c5fd; margin: 10px 0 0 0; font-size: 1.1em;'>
        Data-driven insights from {total_jobs:,} jobs • Updated in real-time
    </p>
</div>
""".format(total_jobs=summary['total_jobs']), unsafe_allow_html=True)

# ============ KEY METRICS ROW ============
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📋 Total Jobs", f"{summary['total_jobs']:,}", 
              delta=f"+{summary['recent_postings_7d']:,} this week")
with col2:
    st.metric("🏢 Companies Hiring", f"{summary['total_companies']:,}")
with col3:
    h1b_pct = round(summary['h1b_sponsors'] / summary['total_companies'] * 100, 1)
    st.metric("🎫 H-1B Sponsors", f"{summary['h1b_sponsors']:,}", 
              delta=f"{h1b_pct}% of companies")
with col4:
    avg_sal = f"${summary['avg_salary']/1000:.0f}K" if summary.get('avg_salary') else "N/A"
    st.metric("💰 Avg Salary", avg_sal)

st.divider()

# ============ SECTION 1: H-1B SPONSORSHIP REALITY CHECK ============
st.markdown("## 🎫 H-1B Sponsorship: The Reality")
st.caption("Understanding your job market as an international student")

h1b_data = load_h1b_comparison()

if h1b_data and h1b_data.get('sponsors') and h1b_data.get('non_sponsors'):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create comparison bar chart
        categories = ['H-1B Sponsors', 'Non-Sponsors']
        job_counts = [h1b_data['sponsors']['job_count'], h1b_data['non_sponsors']['job_count']]
        salaries = [h1b_data['sponsors'].get('avg_salary', 0) or 0, h1b_data['non_sponsors'].get('avg_salary', 0) or 0]
        
        fig = go.Figure()
        
        # Job count bars
        fig.add_trace(go.Bar(
            name='Jobs Available',
            x=categories,
            y=job_counts,
            marker_color=['#10b981', '#94a3b8'],
            text=[f"{x:,}" for x in job_counts],
            textposition='outside',
            yaxis='y'
        ))
        
        # Salary line
        fig.add_trace(go.Scatter(
            name='Avg Salary',
            x=categories,
            y=salaries,
            mode='lines+markers+text',
            marker=dict(size=15, color='#f59e0b'),
            line=dict(width=3, color='#f59e0b'),
            text=[f"${x/1000:.0f}K" if x else "N/A" for x in salaries],
            textposition='top center',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="Jobs & Salary: H-1B Sponsors vs Non-Sponsors",
            yaxis=dict(title="Number of Jobs", showgrid=False),
            yaxis2=dict(title="Average Salary", overlaying='y', side='right', showgrid=False, range=[0, max(salaries)*1.3] if salaries else [0, 200000]),
            height=400,
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            bargap=0.4
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        sponsor_pct = h1b_data['sponsors']['percentage']
        st.markdown(f"""
        <div class='success-box'>
            <h3 style='margin: 0 0 10px 0; color: #065f46;'>✅ Good News!</h3>
            <p style='font-size: 2.5em; font-weight: bold; color: #047857; margin: 0;'>{sponsor_pct:.1f}%</p>
            <p style='color: #065f46;'>of jobs offer H-1B sponsorship</p>
        </div>
        """, unsafe_allow_html=True)
        
        if h1b_data.get('salary_premium'):
            premium = h1b_data['salary_premium']
            premium_pct = h1b_data.get('salary_premium_pct', 0)
            if premium > 0:
                st.markdown(f"""
                <div class='insight-box'>
                    <strong>💰 Salary Premium</strong><br>
                    H-1B sponsors pay <strong>${premium/1000:.0f}K more</strong> on average 
                    ({premium_pct:.1f}% higher)
                </div>
                """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 2: SALARY BY ROLE ============
st.markdown("## 💰 Salary by Role: Where's the Money?")
st.caption("Know your worth - salary ranges by job category")

salary_data = load_salary_by_role()

if salary_data:
    df = pd.DataFrame(salary_data)
    
    # Horizontal bar chart with salary ranges
    fig = go.Figure()
    
    # Add bars for average salary
    fig.add_trace(go.Bar(
        y=df['role'],
        x=df['avg_salary'],
        orientation='h',
        name='Average Salary',
        marker=dict(
            color=df['avg_salary'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Salary")
        ),
        text=[f"${x/1000:.0f}K" for x in df['avg_salary']],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>Avg: $%{x:,.0f}<br>Jobs: ' + df['job_count'].astype(str) + '<extra></extra>'
    ))
    
    fig.update_layout(
        title="Average Salary by Tech Role",
        xaxis_title="Average Salary ($)",
        yaxis_title="",
        height=500,
        yaxis=dict(autorange="reversed"),
        xaxis=dict(tickformat="$,.0f"),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Key insight
    top_role = df.iloc[0]
    bottom_role = df.iloc[-1]
    diff = top_role['avg_salary'] - bottom_role['avg_salary']
    
    st.markdown(f"""
    <div class='insight-box'>
        <strong>💡 Key Insight:</strong> <strong>{top_role['role']}</strong> roles pay 
        <strong>${diff/1000:.0f}K more</strong> on average than {bottom_role['role']} roles.
        Focus on high-demand skills to maximize earning potential!
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 3: REMOTE WORK OPPORTUNITY ============
st.markdown("## 🏠 Remote Work: Flexibility Trends")
st.caption("Understanding the new normal in tech jobs")

work_data = load_work_models()

if work_data:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        df = pd.DataFrame(work_data)
        
        colors = {'Remote': '#10b981', 'Hybrid': '#3b82f6', 'On-site': '#94a3b8'}
        
        fig = go.Figure(data=[go.Pie(
            labels=df['work_model'],
            values=df['count'],
            hole=0.5,
            marker=dict(colors=[colors.get(m, '#94a3b8') for m in df['work_model']]),
            textinfo='label+percent',
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>Jobs: %{value:,}<br>%{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title="Work Model Distribution",
            height=400,
            showlegend=True,
            annotations=[dict(text='Work<br>Model', x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📊 Work Model Breakdown")
        
        for _, row in df.iterrows():
            model = row['work_model']
            pct = row['percentage']
            count = row['count']
            salary = row.get('avg_salary')
            
            emoji = "🏠" if model == "Remote" else "🔄" if model == "Hybrid" else "🏢"
            color = colors.get(model, '#94a3b8')
            
            salary_str = f"${salary/1000:.0f}K avg" if salary else "Salary varies"
            
            st.markdown(f"""
            <div style='background: white; border: 2px solid {color}; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <div>
                        <span style='font-size: 1.5em;'>{emoji}</span>
                        <strong style='font-size: 1.2em; margin-left: 10px;'>{model}</strong>
                    </div>
                    <div style='text-align: right;'>
                        <div style='font-size: 1.5em; font-weight: bold; color: {color};'>{pct:.1f}%</div>
                        <div style='font-size: 0.9em; color: #6b7280;'>{count:,} jobs</div>
                    </div>
                </div>
                <div style='color: #6b7280; margin-top: 5px;'>{salary_str}</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 4: BEST CITIES FOR SALARY ============
st.markdown("## 📍 Best Cities for Tech Salaries")
st.caption("Where should you target your job search?")

location_data = load_location_salary()

if location_data:
    df = pd.DataFrame(location_data)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = go.Figure()
        
        # Bar chart with dual coloring based on salary
        fig.add_trace(go.Bar(
            x=df['city'],
            y=df['avg_salary'],
            marker=dict(
                color=df['avg_salary'],
                colorscale='YlOrRd',
                showscale=True,
                colorbar=dict(title="Salary")
            ),
            text=[f"${x/1000:.0f}K" for x in df['avg_salary']],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Avg Salary: $%{y:,.0f}<br>H-1B Friendly: ' + df['h1b_friendly_pct'].astype(str) + '%<extra></extra>'
        ))
        
        fig.update_layout(
            title="Average Salary by City (Tech Jobs)",
            xaxis_title="",
            yaxis_title="Average Salary ($)",
            height=450,
            xaxis={'tickangle': -45},
            yaxis=dict(tickformat="$,.0f")
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🎯 Top 5 Highest Paying")
        
        for i, row in df.head(5).iterrows():
            city = row['city']
            salary = row['avg_salary']
            h1b_pct = row['h1b_friendly_pct']
            
            h1b_color = '#10b981' if h1b_pct >= 70 else '#f59e0b' if h1b_pct >= 50 else '#ef4444'
            
            st.markdown(f"""
            <div style='background: #f9fafb; padding: 12px; border-radius: 8px; margin: 8px 0;'>
                <div style='font-weight: bold; color: #1f2937;'>{i+1}. {city}</div>
                <div style='display: flex; justify-content: space-between; margin-top: 5px;'>
                    <span style='color: #667eea; font-weight: bold;'>${salary/1000:.0f}K</span>
                    <span style='color: {h1b_color};'>🎫 {h1b_pct:.0f}% H-1B</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class='warning-box' style='margin-top: 20px;'>
            <strong>⚠️ Consider Cost of Living!</strong><br>
            Higher salaries in SF/NYC may not go as far due to housing costs.
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 5: EXPERIENCE LEVEL OPPORTUNITIES ============
st.markdown("## 👔 Jobs by Experience Level")
st.caption("Where do you fit in the job market?")

exp_data = load_experience_levels()

if exp_data:
    df = pd.DataFrame(exp_data)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Funnel chart for experience levels
        colors = ['#22c55e', '#3b82f6', '#8b5cf6', '#f59e0b']
        
        fig = go.Figure(go.Funnel(
            y=df['level'],
            x=df['job_count'],
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(color=colors[:len(df)]),
            connector=dict(line=dict(color="royalblue", width=1))
        ))
        
        fig.update_layout(
            title="Job Availability by Experience Level",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 Salary & H-1B by Level")
        
        for i, row in df.iterrows():
            level = row['level']
            job_count = row['job_count']
            pct = row['percentage']
            salary = row.get('avg_salary')
            h1b_pct = row.get('h1b_friendly_pct', 0)
            
            salary_str = f"${salary/1000:.0f}K" if salary else "Varies"
            
            st.markdown(f"""
            <div style='background: #f3f4f6; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <div style='font-weight: bold; font-size: 1.1em; color: #1f2937;'>{level}</div>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;'>
                    <div>
                        <div style='color: #6b7280; font-size: 0.8em;'>Jobs</div>
                        <div style='font-weight: bold; color: #3b82f6;'>{job_count:,} ({pct:.0f}%)</div>
                    </div>
                    <div>
                        <div style='color: #6b7280; font-size: 0.8em;'>Avg Salary</div>
                        <div style='font-weight: bold; color: #10b981;'>{salary_str}</div>
                    </div>
                </div>
                <div style='margin-top: 8px;'>
                    <div style='color: #6b7280; font-size: 0.8em;'>H-1B Friendly</div>
                    <div style='background: #e5e7eb; border-radius: 4px; height: 8px; margin-top: 4px;'>
                        <div style='background: #667eea; border-radius: 4px; height: 100%; width: {h1b_pct}%;'></div>
                    </div>
                    <div style='font-size: 0.8em; color: #667eea; text-align: right;'>{h1b_pct:.0f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Insight for new grads
    new_grad_row = df[df['level'].str.contains('Entry|New Grad', case=False, na=False)]
    if not new_grad_row.empty:
        ng_count = new_grad_row.iloc[0]['job_count']
        ng_pct = new_grad_row.iloc[0]['percentage']
        st.markdown(f"""
        <div class='success-box'>
            <strong>🎓 Good News for New Grads!</strong><br>
            There are <strong>{ng_count:,} entry-level positions</strong> ({ng_pct:.0f}% of market) currently available.
            Focus on building skills and getting internship experience!
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 6: TOP H-1B SPONSORS ============
st.markdown("## 🏆 Top H-1B Sponsoring Companies")
st.caption("Companies most likely to sponsor your visa")

sponsors_data = load_h1b_sponsors(25)

if sponsors_data:
    df = pd.DataFrame(sponsors_data)
    
    # Filter to only show companies with approval rates
    df = df[df['avg_approval_rate'].notna()][:15]
    
    if not df.empty:
        fig = go.Figure()
        
        # Bubble chart: x=rank, y=approval rate, size=job count
        max_jobs = df['job_count'].max()
        df['bubble_size'] = (df['job_count'] / max_jobs * 40) + 15
        
        fig.add_trace(go.Scatter(
            x=list(range(1, len(df)+1)),
            y=df['avg_approval_rate'],
            mode='markers+text',
            marker=dict(
                size=df['bubble_size'],
                color=df['avg_approval_rate'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Approval<br>Rate %"),
                line=dict(color='white', width=2)
            ),
            text=df['company'].apply(lambda x: x[:15] + '...' if len(x) > 15 else x),
            textposition='top center',
            hovertemplate='<b>%{text}</b><br>Approval Rate: %{y:.1f}%<br>Open Jobs: ' + df['job_count'].astype(str) + '<extra></extra>'
        ))
        
        # Add 90% threshold line
        fig.add_hline(y=90, line_dash="dash", line_color="gray", 
                      annotation_text="90% Safe Threshold", annotation_position="bottom right")
        
        fig.update_layout(
            title="H-1B Sponsors: Approval Rate vs Open Positions",
            xaxis_title="Company Rank (by job count)",
            yaxis_title="H-1B Approval Rate (%)",
            height=500,
            yaxis=dict(range=[min(df['avg_approval_rate'].min()-5, 80), 105]),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Top sponsors table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 🎯 Top 10 Safest H-1B Sponsors")
            display_df = df.nlargest(10, 'avg_approval_rate')[['company', 'job_count', 'avg_approval_rate']].copy()
            display_df['avg_approval_rate'] = display_df['avg_approval_rate'].apply(lambda x: f"{x:.1f}%")
            display_df.columns = ['Company', 'Open Jobs', 'Approval Rate']
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        with col2:
            high_approval = len(df[df['avg_approval_rate'] >= 95])
            avg_rate = df['avg_approval_rate'].mean()
            
            st.markdown(f"""
            <div style='background: #f3f4f6; padding: 20px; border-radius: 12px; text-align: center;'>
                <div style='font-size: 3em; font-weight: bold; color: #10b981;'>{high_approval}</div>
                <div style='color: #6b7280;'>companies with 95%+ approval rate</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style='background: #f3f4f6; padding: 20px; border-radius: 12px; text-align: center; margin-top: 15px;'>
                <div style='font-size: 3em; font-weight: bold; color: #667eea;'>{avg_rate:.1f}%</div>
                <div style='color: #6b7280;'>average approval rate</div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 7: TOP SKILLS IN DEMAND ============
st.markdown("## 🛠️ Top Skills in Demand")
st.caption("Skills employers are looking for - focus your learning here!")

skills_data = load_top_skills()

if skills_data:
    df = pd.DataFrame(skills_data)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Horizontal bar chart for skills
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=df['skill'][:15],
            x=df['count'][:15],
            orientation='h',
            marker=dict(
                color=df['count'][:15],
                colorscale='Plasma',
                showscale=False
            ),
            text=df['count'][:15].apply(lambda x: f"{x:,}"),
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Mentioned in: %{x:,} jobs<extra></extra>'
        ))
        
        fig.update_layout(
            title="Most In-Demand Skills (by job mentions)",
            xaxis_title="Number of Job Postings",
            yaxis_title="",
            height=500,
            yaxis=dict(autorange="reversed"),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### 🎯 Skill Categories")
        
        # Categorize skills
        tech_skills = ['Python', 'SQL', 'Java', 'JavaScript', 'AWS', 'React', 'Docker']
        data_skills = ['Analytics', 'Data Science', 'Data Engineering', 'Machine Learning', 'AI']
        
        tech_count = sum(row['count'] for _, row in df.iterrows() if row['skill'] in tech_skills)
        data_count = sum(row['count'] for _, row in df.iterrows() if row['skill'] in data_skills)
        
        st.markdown(f"""
        <div style='background: #dbeafe; padding: 15px; border-radius: 10px; margin: 10px 0;'>
            <div style='font-weight: bold; color: #1e40af;'>💻 Technical Skills</div>
            <div style='font-size: 1.3em; color: #3b82f6;'>{tech_count:,} job mentions</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style='background: #dcfce7; padding: 15px; border-radius: 10px; margin: 10px 0;'>
            <div style='font-weight: bold; color: #166534;'>📊 Data/ML Skills</div>
            <div style='font-size: 1.3em; color: #22c55e;'>{data_count:,} job mentions</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Top 3 skills callout
        top3 = df.head(3)['skill'].tolist()
        st.markdown(f"""
        <div class='insight-box'>
            <strong>🔥 Hot Skills Right Now:</strong><br>
            {', '.join(top3)}<br><br>
            <em>These skills appear in the most job postings!</em>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ============ SECTION 8: H-1B RISK ANALYSIS & BACKUP PLANS ============
st.markdown("## ⚠️ H-1B Risk Analysis & Backup Plans")
st.caption("Prepare for all scenarios - smart planning for international students")

risk_data = load_h1b_risk()

if risk_data:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #fef3c7 0%, #fcd34d 100%); padding: 25px; border-radius: 15px; text-align: center;'>
            <div style='font-size: 3em; font-weight: bold; color: #b45309;'>{risk_data.get('lottery_success_rate', 30):.0f}%</div>
            <div style='color: #92400e; font-weight: bold;'>H-1B Lottery Success Rate</div>
            <div style='color: #a16207; font-size: 0.9em; margin-top: 5px;'>Historical average</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #d1fae5 0%, #6ee7b7 100%); padding: 25px; border-radius: 15px; text-align: center;'>
            <div style='font-size: 3em; font-weight: bold; color: #047857;'>{risk_data.get('h1b_friendly_pct', 0):.0f}%</div>
            <div style='color: #065f46; font-weight: bold;'>H-1B Sponsor Jobs</div>
            <div style='color: #047857; font-size: 0.9em; margin-top: 5px;'>{risk_data.get('h1b_friendly_jobs', 0):,} positions</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #dbeafe 0%, #93c5fd 100%); padding: 25px; border-radius: 15px; text-align: center;'>
            <div style='font-size: 3em; font-weight: bold; color: #1e40af;'>{risk_data.get('internship_opportunities', 0):,}</div>
            <div style='color: #1e3a8a; font-weight: bold;'>Internship Opportunities</div>
            <div style='color: #2563eb; font-size: 0.9em; margin-top: 5px;'>For CPT experience</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Recommendations
    st.markdown("### 📋 Strategic Recommendations")
    
    recommendations = risk_data.get('recommendations', [])
    
    rec_col1, rec_col2 = st.columns(2)
    
    with rec_col1:
        for i, rec in enumerate(recommendations[:3]):
            icon = ['🎯', '📝', '🏫'][i] if i < 3 else '✅'
            st.markdown(f"""
            <div style='background: white; border: 1px solid #e5e7eb; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <span style='font-size: 1.3em;'>{icon}</span>
                <span style='margin-left: 10px;'>{rec}</span>
            </div>
            """, unsafe_allow_html=True)
    
    with rec_col2:
        for i, rec in enumerate(recommendations[3:]):
            icon = ['🌐', '📚'][i] if i < 2 else '✅'
            st.markdown(f"""
            <div style='background: white; border: 1px solid #e5e7eb; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <span style='font-size: 1.3em;'>{icon}</span>
                <span style='margin-left: 10px;'>{rec}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Key insight
    st.markdown(f"""
    <div class='warning-box'>
        <strong>💡 Key Insight:</strong> {risk_data.get('key_insight', 'Plan ahead and have multiple backup options!')}
    </div>
    """, unsafe_allow_html=True)

# ============ FOOTER ============
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 20px;'>
    <p>📊 Data sourced from 47K+ real job postings and USCIS H-1B filings</p>
    <p>🔄 Analytics update automatically • Last refresh: Real-time</p>
</div>
""", unsafe_allow_html=True)
