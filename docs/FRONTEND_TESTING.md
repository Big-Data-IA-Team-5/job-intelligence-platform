# Frontend Testing Guide

## Start the Frontend

```bash
cd /Users/pranavpatel/Desktop/job-intelligence-platform
streamlit run frontend/Home.py
```

## Test Scenarios

### 1. Test Chat Context (Follow-up Questions)

**Steps:**
1. Open the app at http://localhost:8501
2. Type: "Tell me about Amazon"
3. Wait for response
4. Type: "What's their H-1B approval rate?"
5. **Expected**: AI should understand "their" refers to Amazon and provide Amazon's H-1B data

**Success Criteria:**
- ✅ Response mentions "Amazon" 
- ✅ Shows H-1B approval rate
- ✅ You see a toast: "🧠 Sending X context messages"

---

### 2. Test Resume Upload & Job Matching

**Steps:**
1. Click the "📎 Upload Resume" expander
2. Upload a PDF/DOCX/TXT resume with:
   - Skills like Python, AWS, SQL
   - Education (Bachelor's/Master's)
   - Work experience
3. **Expected**: After upload, you should see:
   - "✅ Resume uploaded: [filename]"
   - Years of experience
   - Education level
   - **Top 3 job matches with links!**

**Success Criteria:**
- ✅ Profile is extracted correctly
- ✅ 3 job matches shown immediately
- ✅ Each job has: title, company, location, match %
- ✅ "Apply Now" links work

---

### 3. Test Resume Context in Chat

**Steps:**
1. Upload a resume (as above)
2. Type: "Find me suitable jobs"
3. **Expected**: Jobs should be relevant to your resume skills

**Alternative:**
1. Upload resume with "Data Engineer" skills
2. Type: "Show all my job matches"
3. **Expected**: See all 10 matched jobs from the resume analysis

**Success Criteria:**
- ✅ Jobs match your skills from resume
- ✅ You see toast: "📄 Context: Resume + X messages"
- ✅ Results are personalized

---

### 4. Test Multi-Turn Conversation

**Steps:**
1. Type: "Find Python developer jobs at Google"
2. Wait for response
3. Type: "What about Microsoft?"
4. **Expected**: Shows Python jobs at Microsoft (carries over job type)

**Success Criteria:**
- ✅ Second query understands context
- ✅ Shows Microsoft jobs
- ✅ Keeps "Python developer" from first query

---

### 5. Test Message Display

**Steps:**
1. Send any message
2. **Expected**: You should see:
   - Your message in a chat bubble (user avatar)
   - AI response in a chat bubble (assistant avatar)
   - All previous messages above

**Success Criteria:**
- ✅ Messages are visible
- ✅ Markdown formatting works (bold, links, bullets)
- ✅ Scrollable chat history

---

## Sample Resume for Testing

Save this as `test_resume.txt`:

```
John Doe
Software Engineer

EDUCATION:
Master of Science in Computer Science
University of Massachusetts, Boston
GPA: 3.8/4.0

EXPERIENCE:

Data Engineering Intern | Amazon | Summer 2023
- Built ETL pipelines using Python and Airflow
- Worked with AWS services (S3, Lambda, Redshift)
- Optimized SQL queries reducing runtime by 40%

Software Developer Intern | Microsoft | Summer 2022
- Developed REST APIs using Node.js and Express
- Implemented CI/CD with Azure DevOps
- Collaborated with team of 5 engineers

SKILLS:
Programming: Python, JavaScript, Java, SQL, TypeScript
Frameworks: React, Node.js, Flask, Spring Boot
Cloud: AWS (S3, Lambda, EC2, Redshift), Azure
Databases: PostgreSQL, MongoDB, Redis, Snowflake
Tools: Git, Docker, Kubernetes, Airflow, Jenkins

WORK AUTHORIZATION: F-1 OPT

LOCATION PREFERENCE: Boston, Seattle, Remote
```

---

## Expected Behavior

### When Resume is Uploaded:
```
✅ Resume uploaded: test_resume.txt

💼 2.0 years experience
🎓 Master's in Computer Science
🔧 Python, JavaScript, Java, SQL, TypeScript

🎯 Top 3 Job Matches:

1. Data Engineer at Snowflake
   📍 Remote | Match: 87%
   [Apply Now](...)

2. Software Engineer at Microsoft
   📍 Seattle | Match: 84%
   [Apply Now](...)

3. Backend Engineer at Amazon
   📍 Boston | Match: 82%
   [Apply Now](...)

💡 Ask me 'show all jobs' to see more matches!
```

### When Asking Follow-up:
```
User: "Tell me about Google"
AI: [Info about Google's H-1B sponsorship]

User: "What's their salary for software engineers?"
AI: ### 💼 Salary Data for Software Engineer

**📍 Location:** United States
**📊 Sample Size:** 2,847 H-1B cases

**💰 Average Salary:** $142,500
**📊 Salary Range:** $80,000 - $280,000
[etc...]
```

---

## Troubleshooting

### Issue: Messages not showing
- **Check**: Scroll down - messages might be below fold
- **Fix**: Click "🔄 New" to reset
- **Debug**: Check browser console for errors

### Issue: Resume not uploading
- **Check**: File size < 5MB, format is PDF/DOCX/TXT
- **Fix**: Try a plain text (.txt) file first
- **Debug**: Check terminal logs for errors

### Issue: Context not working
- **Check**: Look for toast notification showing context being sent
- **Fix**: Clear context with sidebar button and try again
- **Debug**: Check `/tmp/backend.log` for agent logs

### Issue: Job matches not showing
- **Check**: Backend is running and healthy
- **Fix**: Wait 5-10 seconds for AI to parse resume
- **Debug**: Check response from `/api/resume/match` in Network tab

---

## Backend Logs

Watch backend logs in real-time:
```bash
tail -f /tmp/backend.log
```

Look for:
- `💬 Using chat history: X messages` - confirms context is being used
- `📄 Resume context provided` - confirms resume is sent
- `🎯 Explicit H-1B flag` - shows job classification
- `✅ LLM parsed query` - shows natural language understanding

---

## Success Checklist

- [ ] Chat messages are visible
- [ ] Resume uploads successfully
- [ ] 3 job matches shown after upload
- [ ] Follow-up questions work ("their", "them", etc.)
- [ ] Toast notifications show context being sent
- [ ] Sidebar shows "X companies tracking", "Y messages"
- [ ] "🔄 New" button clears everything
- [ ] "🔄 Clear Context" button resets conversation
- [ ] Job links are clickable
- [ ] Markdown formatting looks good

---

## Performance Notes

- Resume parsing: 3-5 seconds
- Job matching: 5-10 seconds
- Chat response: 1-3 seconds
- Context resolution: Instant

If responses are slow, check:
1. Snowflake warehouse is running
2. No network issues
3. LLM quota not exceeded
