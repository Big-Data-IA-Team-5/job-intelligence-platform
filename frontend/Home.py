"""
Job Intelligence AI - ChatGPT/Claude Style Interface
"""
import streamlit as st
from utils.api_client import APIClient
from utils.context_manager import ConversationContext
import io
from datetime import datetime

st.set_page_config(
    page_title="Job Intelligence AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main .block-container {
        max-width: 800px;
        padding: 1rem 2rem 8rem 2rem;
        margin: 0 auto;
    }
    .stButton button {
        border-radius: 8px;
        border: 1px solid rgba(250, 250, 250, 0.2);
        transition: all 0.2s;
        font-size: 1.2rem;
        padding: 0.5rem;
        height: 3rem;
    }
    .stButton button:hover {
        border-color: rgba(250, 250, 250, 0.4);
    }
    [data-testid="stFileUploader"] small {
        display: none !important;
    }
    /* Align upload button with chat input */
    [data-testid="column"]:has(.stButton) {
        display: flex;
        align-items: flex-end;
        padding-bottom: 0.5rem;
    }
    /* Chat input container */
    .stChatFloatingInputContainer {
        padding-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'uploaded_resume' not in st.session_state:
    st.session_state.uploaded_resume = None
    st.session_state.resume_text = None
if 'context_manager' not in st.session_state:
    st.session_state.context_manager = ConversationContext(max_turns=10)

with st.sidebar:
    st.markdown("## 🤖 Job Intelligence AI")
    st.caption("Powered by ML agents")
    st.divider()
    
    if st.session_state.resume_text:
        st.success(f"✅ Resume Active")
    else:
        st.info("💡 Upload resume")
    
    if st.session_state.messages:
        st.divider()
        st.caption(f"💬 {len(st.session_state.messages)} messages")
        
        # Show context awareness status
        summary = st.session_state.context_manager.get_summary()
        if summary['total_turns'] > 0:
            st.divider()
            st.markdown("**🧠 Context Awareness**")
            
            entities = summary['entities_tracked']
            if entities['companies'] > 0:
                st.caption(f"🏢 Tracking {entities['companies']} companies")
            if entities['locations'] > 0:
                st.caption(f"📍 Tracking {entities['locations']} locations")
            if summary['last_intent']:
                st.caption(f"💡 Last topic: {summary['last_intent'].replace('_', ' ').title()}")
            
            # Clear context button
            if st.button("🔄 Clear Context", help="Reset conversation context"):
                st.session_state.context_manager.clear_context()
                st.session_state.messages = []
                st.rerun()

if not st.session_state.messages:
    hour = datetime.now().hour
    if hour < 12:
        greeting, emoji = "Good Morning", "🌅"
    elif hour < 17:
        greeting, emoji = "Good Afternoon", "☀️"
    else:
        greeting, emoji = "Good Evening", "🌙"
    
    st.markdown(f"""
    <div style='text-align: center; padding: 5rem 2rem 3rem 2rem;'>
        <h1 style='font-size: 3.5rem; margin: 0; font-weight: 300;'>{emoji}</h1>
        <h2 style='font-size: 2.2rem; margin: 1.5rem 0 0.8rem 0; font-weight: 500;'>{greeting}</h2>
        <p style='font-size: 1.1rem; opacity: 0.7; margin: 0;'>Your AI job intelligence assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 Find jobs", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Find me Software Engineer jobs in Boston"})
            st.rerun()
        if st.button("💰 Salary info", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "What's the average salary for Data Engineers?"})
            st.rerun()
    with col2:
        if st.button("🌐 H-1B info", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Which companies sponsor H-1B?"})
            st.rerun()
        if st.button("🎯 Career advice", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "What skills for data science?"})
            st.rerun()
else:
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown("## 🤖 Job Intelligence AI")
    with col2:
        if st.button("🔄 New", use_container_width=True):
            st.session_state.messages = []
            st.session_state.uploaded_resume = None
            st.session_state.resume_text = None
            st.rerun()
    st.divider()
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Analytics Dashboard - shown at bottom after messages
    if len(st.session_state.messages) > 2:
        st.divider()
        with st.expander("📊 Session Analytics", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            user_msgs = [m for m in st.session_state.messages if m["role"] == "user"]
            assistant_msgs = [m for m in st.session_state.messages if m["role"] == "assistant"]
            
            col1.metric("Total Messages", len(st.session_state.messages))
            col2.metric("Your Questions", len(user_msgs))
            col3.metric("AI Responses", len(assistant_msgs))
            col4.metric("Resume Status", "✅ Active" if st.session_state.resume_text else "No Resume")
            
            st.caption("💡 Analytics update in real-time as you chat")

if st.session_state.get('show_upload', False):
    st.markdown("---")
    upload_file = st.file_uploader("📎 Upload Resume", type=['pdf', 'docx', 'txt'], key="upload")
    
    if upload_file and upload_file != st.session_state.uploaded_resume:
        try:
            if upload_file.type == "application/pdf":
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(upload_file.read()))
                st.session_state.resume_text = "".join([page.extract_text() for page in pdf_reader.pages])
            elif upload_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                import docx
                doc = docx.Document(io.BytesIO(upload_file.read()))
                st.session_state.resume_text = "\n".join([para.text for para in doc.paragraphs])
            else:
                st.session_state.resume_text = upload_file.read().decode('utf-8')
            
            st.session_state.uploaded_resume = upload_file
            st.session_state.messages.append({"role": "assistant", "content": "✅ Resume loaded!"})
            st.session_state.show_upload = False
            st.rerun()
        except Exception as e:
            st.error(f"❌ {str(e)}")
    
    if st.button("✕ Close"):
        st.session_state.show_upload = False
        st.rerun()

# Chat input with properly aligned upload button
input_col, btn_col = st.columns([0.95, 0.05])
with input_col:
    prompt = st.chat_input("Message Job Intelligence AI...")
with btn_col:
    if st.button("📎" if not st.session_state.resume_text else "✅", key="btn", help="Upload Resume"):
        st.session_state.show_upload = not st.session_state.get('show_upload', False)
        st.rerun()

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            from urllib.parse import quote
            
            try:
                # Use intelligent context manager to enhance the query
                enhanced_prompt, metadata = st.session_state.context_manager.enhance_query(prompt)
                
                # Build request with resume context if available
                url = f"/api/chat/ask?question={quote(enhanced_prompt)}"
                if st.session_state.resume_text:
                    url += f"&resume_context={quote(st.session_state.resume_text[:2000])}"
                
                response = st.session_state.api_client.post(url)
                
                if response and "answer" in response:
                    answer = response["answer"]
                    st.markdown(answer)
                    
                    # Update context manager with this conversation turn
                    st.session_state.context_manager.update_context(prompt, answer)
                    
                    # Add to message history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error("Couldn't process request")
                    st.session_state.messages.append({"role": "assistant", "content": "Error occurred"})
            except Exception as e:
                st.error(f"❌ {str(e)}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {str(e)}"})
    
    st.rerun()
