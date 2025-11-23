"""
Resume Matcher Page
"""
import streamlit as st
from utils.api_client import APIClient

st.set_page_config(page_title="Resume Matcher", page_icon="📄", layout="wide")

# Initialize
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

st.title("📄 Resume Matcher")
st.markdown("Upload your resume and find the best matching jobs")

# Tabs
tab1, tab2 = st.tabs(["Upload Resume", "View Matches"])

with tab1:
    st.header("Upload Your Resume")
    
    user_id = st.text_input("User ID", placeholder="Enter your user ID")
    
    # Text input
    resume_text = st.text_area(
        "Paste your resume text",
        height=300,
        placeholder="Paste your resume content here..."
    )
    
    # Or file upload
    st.markdown("**Or upload a file:**")
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['txt', 'pdf', 'docx'],
        help="Supported formats: TXT, PDF, DOCX"
    )
    
    if uploaded_file:
        # In production, you'd parse the file
        st.info("File parsing coming soon. Please use text input for now.")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("📤 Upload Resume", type="primary", use_container_width=True):
            if user_id and resume_text:
                with st.spinner("Processing resume..."):
                    try:
                        response = st.session_state.api_client.post(
                            "/resume/upload",
                            json={
                                "user_id": user_id,
                                "resume_text": resume_text
                            }
                        )
                        
                        if response:
                            st.success("Resume uploaded successfully!")
                            if response.get('extracted_skills'):
                                st.markdown("**Extracted Skills:**")
                                st.write(response['extracted_skills'])
                            
                            # Store in session
                            st.session_state.user_id = user_id
                            st.session_state.resume_uploaded = True
                    except Exception as e:
                        st.error(f"Error uploading resume: {str(e)}")
            else:
                st.warning("Please provide both User ID and resume text")

with tab2:
    st.header("Your Matching Jobs")
    
    if 'resume_uploaded' in st.session_state and st.session_state.resume_uploaded:
        col1, col2 = st.columns([2, 3])
        
        with col1:
            top_k = st.slider("Number of matches", 5, 50, 10)
            min_similarity = st.slider("Minimum similarity", 0.0, 1.0, 0.7, 0.05)
        
        if st.button("🔍 Find Matches", type="primary"):
            with st.spinner("Finding matching jobs..."):
                try:
                    # Get user's latest resume
                    resumes = st.session_state.api_client.get(
                        f"/resume/user/{st.session_state.user_id}"
                    )
                    
                    if resumes and resumes.get('resumes'):
                        resume_id = resumes['resumes'][0]['resume_id']
                        
                        # Get matches
                        matches = st.session_state.api_client.post(
                            "/resume/match",
                            json={
                                "resume_id": resume_id,
                                "top_k": top_k,
                                "min_similarity": min_similarity
                            }
                        )
                        
                        if matches and matches.get('matches'):
                            st.success(f"Found {len(matches['matches'])} matching jobs")
                            
                            # Display matches
                            for i, match in enumerate(matches['matches']):
                                job = match['job']
                                similarity = match['similarity_score']
                                
                                # Color code by similarity
                                if similarity >= 0.9:
                                    color = "🟢"
                                elif similarity >= 0.8:
                                    color = "🟡"
                                else:
                                    color = "🔵"
                                
                                with st.expander(
                                    f"{color} **{job['title']}** at {job['company_name']} - {similarity:.1%} match"
                                ):
                                    col1, col2 = st.columns([3, 1])
                                    
                                    with col1:
                                        st.markdown(f"**Location:** {job['location']}")
                                        if job.get('salary_range'):
                                            st.markdown(f"**Salary:** {job['salary_range']}")
                                        
                                        st.markdown("**Why this matches:**")
                                        if job.get('extracted_skills'):
                                            st.markdown(f"Skills: {job['extracted_skills']}")
                                        
                                        st.markdown(job['description'][:300] + "...")
                                    
                                    with col2:
                                        st.metric("Match Score", f"{similarity:.1%}")
                                        
                                        if job.get('is_remote'):
                                            st.success("🌐 Remote")
                                        if job.get('likely_sponsors_h1b'):
                                            st.success("✅ H1B")
                                        
                                        if st.button("View Job", key=f"match_{i}"):
                                            st.markdown(f"[Open]({job['url']})")
                        else:
                            st.warning("No matching jobs found. Try lowering the similarity threshold.")
                    
                except Exception as e:
                    st.error(f"Error finding matches: {str(e)}")
    else:
        st.info("👆 Upload your resume in the first tab to see matches")

# Tips
st.markdown("---")
st.subheader("💡 Tips for Better Matches")
st.markdown("""
- Include specific technical skills
- Mention years of experience
- List relevant projects and achievements
- Use industry-standard terminology
- Keep resume well-structured
""")
