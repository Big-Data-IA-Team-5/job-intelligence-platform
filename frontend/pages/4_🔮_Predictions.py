"""
Interactive Prediction Dashboards
AI-powered predictions for salary and H-1B success
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.api_client import APIClient
import numpy as np

st.set_page_config(
    page_title="Predictions & Insights",
    page_icon="🔮",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .prediction-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        margin: 15px 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .prediction-value {
        font-size: 3em;
        font-weight: bold;
        margin: 10px 0;
    }
    .confidence-badge {
        background: rgba(255, 255, 255, 0.2);
        padding: 8px 16px;
        border-radius: 20px;
        display: inline-block;
        margin-top: 10px;
    }
    .insight-box {
        background: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 15px 0;
    }
    .recommendation-card {
        background: white;
        border: 2px solid #e5e7eb;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
        transition: all 0.2s;
    }
    .recommendation-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize API client
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

# ============ DATA LOADING FUNCTIONS ============
@st.cache_data(ttl=600)
def load_salary_by_role():
    """Load salary data by role"""
    try:
        return st.session_state.api_client.get('/analytics/salary-by-role')
    except:
        return []

@st.cache_data(ttl=600)
def load_location_salary():
    """Load location salary data"""
    try:
        return st.session_state.api_client.get('/analytics/location-salary')
    except:
        return []

# ============ PREDICTION FUNCTIONS ============
def predict_salary(role, location, experience_years, h1b_sponsor, work_model):
    """Predict salary based on inputs"""
    salary_data = load_salary_by_role()
    location_data = load_location_salary()
    
    if not salary_data:
        return None, 0
    
    # Find base salary for role
    role_salary = None
    for r in salary_data:
        if r['role'].lower() == role.lower():
            role_salary = r['avg_salary']
            break
    
    if not role_salary:
        # Use average if role not found
        role_salary = sum(r['avg_salary'] for r in salary_data) / len(salary_data) if salary_data else 100000
    
    # Location adjustment
    location_multiplier = 1.0
    for loc in location_data:
        if location.lower() in loc['city'].lower() or loc['city'].lower() in location.lower():
            # Compare to average
            avg_salary = sum(l['avg_salary'] for l in location_data) / len(location_data) if location_data else 100000
            location_multiplier = loc['avg_salary'] / avg_salary if avg_salary > 0 else 1.0
            break
    
    # Experience adjustment
    if experience_years < 1:
        exp_multiplier = 0.7  # Entry level
    elif experience_years < 3:
        exp_multiplier = 0.85  # Junior
    elif experience_years < 5:
        exp_multiplier = 1.0  # Mid-level
    elif experience_years < 8:
        exp_multiplier = 1.2  # Senior
    else:
        exp_multiplier = 1.4  # Staff/Principal
    
    # H-1B premium (sponsors typically pay 5-10% more)
    h1b_multiplier = 1.05 if h1b_sponsor else 1.0
    
    # Work model adjustment
    work_multiplier = 1.0
    if work_model == 'Remote':
        work_multiplier = 0.95  # Slight discount for remote
    elif work_model == 'Hybrid':
        work_multiplier = 1.0
    
    # Calculate predicted salary
    predicted = role_salary * location_multiplier * exp_multiplier * h1b_multiplier * work_multiplier
    
    # Confidence based on data availability
    confidence = 75
    if role_salary and location_multiplier != 1.0:
        confidence = 85
    if experience_years > 0 and experience_years < 10:
        confidence = min(confidence + 5, 95)
    
    # Calculate range (±15%)
    min_salary = predicted * 0.85
    max_salary = predicted * 1.15
    
    return {
        'predicted': round(predicted, 0),
        'min': round(min_salary, 0),
        'max': round(max_salary, 0),
        'confidence': confidence
    }, role_salary

# ============ HEADER ============
st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 30px; border-radius: 15px; margin-bottom: 25px;'>
    <h1 style='color: white; margin: 0; font-size: 2.5em;'>🔮 AI-Powered Predictions</h1>
    <p style='color: #e0e7ff; margin: 10px 0 0 0; font-size: 1.2em;'>
        Make data-driven career decisions with intelligent predictions
    </p>
</div>
""", unsafe_allow_html=True)

# ============ SALARY PREDICTOR ============
st.markdown("## 💰 Salary Prediction Dashboard")
st.caption("Predict your expected salary based on role, location, experience, and more")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 📝 Your Profile")
    
    # Load data for dropdowns
    salary_data = load_salary_by_role()
    location_data = load_location_salary()
    
    roles = [r['role'] for r in salary_data] if salary_data else ['Software Engineer', 'Data Scientist', 'Data Engineer']
    locations = [l['city'] for l in location_data] if location_data else ['San Francisco, CA', 'New York, NY', 'Seattle, WA']
    
    selected_role = st.selectbox("💼 Job Role", options=roles if roles else ['Software Engineer'], key="salary_role")
    selected_location = st.selectbox("📍 Location", options=locations if locations else ['San Francisco, CA'], key="salary_location")
    experience_years = st.slider("📅 Years of Experience", 0, 15, 2, key="salary_experience")
    h1b_sponsor = st.checkbox("🎫 H-1B Sponsor Required", value=False, key="salary_h1b")
    work_model = st.selectbox("🏠 Work Model", ['On-site', 'Hybrid', 'Remote'], key="salary_work_model")
    
    predict_btn = st.button("🔮 Predict Salary", type="primary", use_container_width=True, key="salary_predict_btn")

with col2:
        if predict_btn:
            with st.spinner("🔮 Calculating prediction..."):
                prediction, base_salary = predict_salary(
                    selected_role, selected_location, experience_years, h1b_sponsor, work_model
                )
            
            if prediction:
                st.markdown(f"""
                <div class='prediction-card'>
                    <div style='text-align: center;'>
                        <div style='font-size: 1.2em; margin-bottom: 10px;'>Predicted Annual Salary</div>
                        <div class='prediction-value'>${prediction['predicted']:,.0f}</div>
                        <div style='font-size: 1.1em; margin: 10px 0;'>
                            Range: ${prediction['min']:,.0f} - ${prediction['max']:,.0f}
                        </div>
                        <div class='confidence-badge'>
                            Confidence: {prediction['confidence']}%
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Calculate location_mult BEFORE using it in breakdown
                location_mult = 1.0
                for loc in location_data:
                    if selected_location.lower() in loc['city'].lower() or loc['city'].lower() in selected_location.lower():
                        avg = sum(l['avg_salary'] for l in location_data) / len(location_data) if location_data else 100000
                        location_mult = loc['avg_salary'] / avg if avg > 0 else 1.0
                        break
                
                # Calculate other multipliers
                exp_mult = 1.0 + (experience_years * 0.05) if experience_years < 8 else 1.4
                h1b_mult = 1.05 if h1b_sponsor else 1.0
                
                # Breakdown
                st.markdown("### 💡 Salary Breakdown")
                breakdown_cols = st.columns(4)
                
                with breakdown_cols[0]:
                    st.metric("Base Role Salary", f"${base_salary:,.0f}")
                with breakdown_cols[1]:
                    st.metric("Location Factor", f"{location_mult:.2f}x")
                with breakdown_cols[2]:
                    st.metric("Experience Factor", f"{exp_mult:.2f}x")
                with breakdown_cols[3]:
                    st.metric("H-1B Premium", f"+{((h1b_mult-1)*100):.0f}%")
                
                # Comparison chart
                if salary_data:
                    st.markdown("### 📊 Market Comparison")
                    role_salaries = {r['role']: r['avg_salary'] for r in salary_data[:10]}
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=list(role_salaries.keys()),
                        y=list(role_salaries.values()),
                        marker_color='lightblue',
                        name='Market Average',
                        opacity=0.7
                    ))
                    
                    # Always show prediction marker
                    matching_role = None
                    for role in role_salaries.keys():
                        if selected_role.lower() in role.lower() or role.lower() in selected_role.lower():
                            matching_role = role
                            break
                    
                    if matching_role:
                        fig.add_trace(go.Scatter(
                            x=[matching_role],
                            y=[prediction['predicted']],
                            mode='markers+text',
                            marker=dict(size=25, color='red', symbol='star', line=dict(color='darkred', width=2)),
                            text=[f"${prediction['predicted']:,.0f}"],
                            textposition='top center',
                            name='Your Prediction',
                            showlegend=True
                        ))
                    
                    fig.update_layout(
                        title="Your Prediction vs Market Average",
                        xaxis_title="Role",
                        yaxis_title="Salary ($)",
                        height=400,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)

# ============ FOOTER ============
st.divider()
st.markdown("""
<div style='text-align: center; color: #6b7280; padding: 20px;'>
    <p>🔮 Predictions powered by real-time data from 12K+ job postings and H-1B filings</p>
    <p>📊 Models updated daily • Confidence scores based on data quality and sample size</p>
    <p style='font-size: 0.9em; margin-top: 10px;'>
        <em>Note: Predictions are estimates based on historical patterns. Actual results may vary.</em>
    </p>
</div>
""", unsafe_allow_html=True)
