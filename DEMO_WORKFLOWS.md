# Job Intelligence Platform - Demo Workflows

## 🎯 Core Demo Workflows (3-5 minutes each)

---

## 📋 Workflow 1: Smart Job Search with Context Awareness

**Scenario**: International student looking for entry-level data engineering roles with H-1B sponsorship

### Steps:

1. **Start Chat**
   ```
   "Find me data engineer jobs in Boston"
   ```
   - Shows 10 job listings with salary, visa status, location
   - Displays H-1B approval rates for companies

2. **Follow-up Question (Tests Context)**
   ```
   "Which of these sponsor H-1B visas?"
   ```
   - System remembers "these" refers to Boston data engineer jobs
   - Filters and ranks by H-1B sponsorship

3. **Deep Dive on Company**
   ```
   "Tell me about Amazon's sponsorship"
   ```
   - Displays sponsorship score: 100/100
   - Shows approval rate: **99.8%** (10,737 certified / 10,755 total)
   - Recent activity: 10,755 filings in 6 months
   - Average salary: $171,973
   - Risk assessment: Low Risk

4. **Get Contact Info**
   ```
   "Who should I contact at Amazon?"
   ```
   - Shows employer immigration email: amazonimmigration@amazon.com
   - Formatted phone: **+1 (206) 266-1000**
   - Attorney information (if available)
   - Next steps for reaching out

**Key Features Demonstrated:**
- ✅ Context-aware conversation (understands "these", "their", "that company")
- ✅ Real-time H-1B approval rate calculation
- ✅ Multi-turn dialogue with entity tracking
- ✅ Properly formatted contact information

---

## 🎓 Workflow 2: Resume-Based Job Matching

**Scenario**: Student uploads resume and gets personalized job recommendations

### Steps:

1. **Upload Resume** (Home Page)
   - Click "Upload Resume" button
   - Select PDF/DOCX file
   - System extracts:
     - Skills: Python, SQL, React, AWS, etc.
     - Experience: 2.5 years
     - Education: Master's in Computer Science
     - Visa status: F-1 OPT

2. **View Instant Matches**
   - Top 3 jobs appear immediately after upload
   - Each shows match score (e.g., 87% match)
   - Displays relevant skills overlap

3. **Chat with Resume Context**
   ```
   "Find me jobs that match my background"
   ```
   - Agent 2 uses resume context automatically
   - Returns personalized recommendations
   - Highlights skill matches

4. **Refine Search**
   ```
   "Show me remote positions only"
   ```
   - Filters results while maintaining resume context
   - Shows work model (Remote, Hybrid, Onsite)

5. **Ask Career Advice**
   ```
   "What skills should I learn to get better jobs?"
   ```
   - AI analyzes resume vs market trends
   - Suggests in-demand skills
   - Recommends career paths

**Key Features Demonstrated:**
- ✅ Resume parsing and skill extraction
- ✅ Semantic job matching (768-dim embeddings)
- ✅ Persistent resume context across chat
- ✅ Personalized career recommendations

---

## 🔍 Workflow 3: Immigration Attorney Discovery

**Scenario**: Finding qualified immigration attorneys by location

### Steps:

1. **Search by Location**
   ```
   "Tell me about immigration attorneys in Texas"
   ```
   - Returns top 10 attorneys ranked by cases handled
   - Shows approval rates (95%+ for top attorneys)
   - Displays law firm affiliations

2. **View Attorney Details**
   - **Name**: Deborah Smith
   - **Law Firm**: Berry Appleman & Leiden LLP
   - **Email**: Debsmith@bal.com
   - **Phone**: **+1 (469) 940-7682** (properly formatted)
   - **Location**: Westlake, TX
   - **Cases**: 752 total
   - **Approval Rate**: 99.7%

3. **Compare Attorneys**
   ```
   "Compare top 3 attorneys in California"
   ```
   - Side-by-side comparison
   - Success rates, case volumes
   - Specializations

4. **Get Next Steps**
   - System provides actionable advice:
     1. Contact top-rated attorneys via email
     2. Mention you need H-1B sponsorship
     3. Ask about industry experience

**Key Features Demonstrated:**
- ✅ Geographic attorney search
- ✅ Performance-based ranking
- ✅ Formatted contact information
- ✅ Actionable recommendations

---

## 📊 Workflow 4: Analytics Dashboard (Visual Demo)

**Scenario**: Exploring job market trends and H-1B sponsorship data

### Steps:

1. **Navigate to Advanced Analytics Page**
   - View total jobs: 12,122
   - Total companies: 3,221
   - H-1B sponsors: 1,155

2. **Top H-1B Sponsoring Companies**
   - Bubble chart showing approval rates vs job count
   - Real approval rates (not 100% for everyone)
   - Examples:
     - Turner Construction: 86.5%
     - Mayo Clinic: 100%
     - Navy Federal: 99.3%
     - Northwestern: 94.1%

3. **Jobs Database**
   - Search/filter 12,122 jobs
   - Sort by salary, visa status, location
   - See H-1B approval rates in table: "✅ Yes (99%)"

4. **Location Analytics**
   - Jobs by state/city
   - Average salaries by location
   - Visa sponsorship concentration

**Key Features Demonstrated:**
- ✅ Real-time analytics from Snowflake
- ✅ Accurate approval rate calculations
- ✅ Interactive visualizations (Plotly)
- ✅ Large dataset handling (12K+ jobs, 479K H-1B records)

---

## 🎬 Demo Script (5-Minute Version)

### **Minute 1: Introduction**
- "This is a Job Intelligence Platform for international students"
- "Built on Snowflake with 4 specialized AI agents"
- "Let me show you 3 powerful workflows"

### **Minute 2: Smart Search**
- Upload resume → instant matches
- Chat: "Find data engineer jobs in Boston"
- Follow-up: "Which sponsor H-1B?" (shows context awareness)
- Deep dive: "Tell me about Amazon" → 99.8% approval rate

### **Minute 3: Resume Matching**
- Already uploaded resume in previous step
- Chat: "Find jobs matching my skills"
- Shows personalized recommendations
- Demonstrates skill overlap highlighting

### **Minute 4: Contact Discovery**
- "Who should I contact at Amazon?"
- Shows formatted phone: +1 (206) 266-1000
- "Find attorneys in Texas"
- Shows top attorneys with 99%+ approval rates

### **Minute 5: Analytics**
- Navigate to dashboard
- Show H-1B sponsors bubble chart
- Browse jobs database
- Highlight accuracy of approval rates

---

## 🔑 Key Talking Points

### **Technical Stack**
- **Snowflake Cortex**: Mistral-Large2 LLM for 4 specialized agents
- **Database**: 479,005 H-1B records + 12,122 job postings
- **Vector Search**: 768-dimensional embeddings for semantic matching
- **Frontend**: Streamlit with real-time updates
- **Backend**: FastAPI with 8 API endpoints

### **AI Agents**
1. **Agent 1**: Job Search - Semantic search with filters
2. **Agent 2**: Chat Intelligence - Context-aware conversations
3. **Agent 3**: Visa Classifier - Categorizes job visa requirements
4. **Agent 4**: Resume Matcher - Extracts skills and matches jobs

### **Unique Features**
- ✅ **Real approval rates**: Certified / Total filings (not just certified/denied)
- ✅ **Context awareness**: Understands "they", "that company", "these jobs"
- ✅ **Contact formatting**: Properly formatted phone numbers (+1 (XXX) XXX-XXXX)
- ✅ **Resume persistence**: Context maintained across entire session
- ✅ **Multi-intent routing**: Single query triggers multiple specialized agents

### **Data Accuracy Fixes** (Recent Improvements)
- Fixed H-1B approval rate calculation (was showing 100% incorrectly)
- Amazon: Now shows 99.8% (10,737/10,755) instead of 100%
- Added phone number formatting for all attorney contacts
- Improved JOIN logic in analytics API for real-time accuracy

---

## 💡 Demo Tips

### **Do's:**
✅ Start with resume upload - it enables all personalized features
✅ Show follow-up questions to demonstrate context awareness
✅ Highlight the real approval rates (not inflated 100%)
✅ Show formatted phone numbers as proof of attention to detail
✅ Navigate between Home → Analytics → Jobs Database

### **Don'ts:**
❌ Don't skip resume upload - it's the killer feature
❌ Don't use generic searches like "jobs" - be specific
❌ Don't forget to show context ("What about that company?")
❌ Don't skip the analytics dashboard - it shows scale

### **Backup Demos** (if issues arise):
1. Use pre-loaded test data (see test_context_fixes.py)
2. Show architecture diagram from APPROVAL_RATE_FIX.md
3. Walk through code in agent2_chat.py to explain AI routing
4. Demo direct SQL queries in Snowflake (if DB access available)

---

## 🎯 Success Metrics to Highlight

- **Database Scale**: 479,005 H-1B records, 12,122 jobs
- **Response Time**: < 2 seconds for most queries
- **Accuracy**: 99%+ approval rates for top sponsors (real data)
- **Context Tracking**: 5-turn conversation history maintained
- **Matching Quality**: 768-dim semantic embeddings

---

## 📝 Q&A Preparation

**Q: How fresh is the data?**
A: H-1B data is FY2025 Q3 (Oct-Dec 2024), Jobs scraped weekly from 5+ sources

**Q: How do you calculate approval rates?**
A: Real rate = Certified / Total Filings (including withdrawn cases), not just certified/(certified+denied)

**Q: What makes this different from LinkedIn/Indeed?**
A: We combine job search + H-1B intelligence + AI chat + resume matching in one platform

**Q: Can it handle follow-up questions?**
A: Yes! Context manager tracks entities across 5+ conversation turns

**Q: What LLM do you use?**
A: Snowflake Cortex with Mistral-Large2 (175B parameters) for 4 specialized agents

**Q: How accurate is resume matching?**
A: Uses semantic embeddings (768-dim) not just keyword matching, validated with test resumes

---

## 🚀 Quick Start Commands

```bash
# Start Backend
cd backend
python -m uvicorn app.main:app --port 8000 --reload

# Start Frontend
cd frontend
streamlit run Home.py --server.port 8501

# Access
Frontend: http://localhost:8501
Backend API: http://localhost:8000/docs
```

---

**Last Updated**: December 8, 2025
**Demo Duration**: 5-7 minutes per workflow
**Recommended Order**: Workflow 1 → 2 → 4 (skip 3 if time limited)
