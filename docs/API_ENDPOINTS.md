# Backend API Endpoints Documentation

## Base URL
```
http://localhost:8000
```

## Available Endpoints

### 1. Health Check
```
GET /health
```
**Description**: Check if the backend service is running

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-08T..."
}
```

---

### 2. Chat Interface - Ask Question
```
POST /api/chat/ask?question={query}&resume_context={resume_text}
```

**Description**: Main chat endpoint that routes to appropriate agent based on intent

**Query Parameters**:
- `question` (required): User's query string (URL encoded)
- `resume_context` (optional): Resume text for context (URL encoded, max 2000 chars)

**Example Request**:
```bash
curl -X POST "http://localhost:8000/api/chat/ask?question=software%20engineer%20jobs%20in%20Boston"
```

**Response**:
```json
{
  "answer": "Found 15 jobs...\n\n## Senior Software Engineer\n📍 Location: Boston, MA\n💰 Salary: $150,000\n✅ H-1B Sponsor: Yes",
  "intent": "job_search",
  "processing_time": 2.34
}
```

**Supported Intents**:
1. `job_search` - Find jobs by title, company, location
2. `salary` - Get salary information
3. `h1b_sponsorship` - H-1B sponsorship details
4. `comparison` - Compare companies/offers
5. `contact` - Attorney contact information
6. `resume` - Resume analysis
7. `career` - Career advice

---

### 3. Test Endpoint
```
GET /test
```
**Description**: Test endpoint to verify API is responding

**Response**:
```json
{
  "message": "Backend is working!",
  "timestamp": "2025-12-08T..."
}
```

---

## Database Connection Details

### Snowflake Configuration
```python
{
  "account": "from secrets.json",
  "user": "from secrets.json",
  "password": "from secrets.json",
  "warehouse": "COMPUTE_WH",
  "database": "JOB_INTELLIGENCE",
  "schema": "PROCESSED_PROCESSING"
}
```

### Available Tables
1. **EMBEDDED_JOBS** (70,819 records)
   - Columns: JOB_ID, TITLE, COMPANY, LOCATION, SALARY_MIN, SALARY_MAX, DESCRIPTION, DESCRIPTION_EMBEDDING, SKILLS_EMBEDDING, etc.

2. **LCA_DISCLOSURE_DATA** (479,005 H-1B records)
   - Columns: CASE_NUMBER, EMPLOYER_NAME, JOB_TITLE, WORKSITE_CITY, WAGE_LEVEL, APPROVAL_STATUS, ATTORNEY_FIRM, etc.

---

## Frontend Integration Guide

### 1. Initialize API Client

**Python (Streamlit)**:
```python
import requests
from urllib.parse import quote

class APIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def post(self, endpoint, data=None):
        response = requests.post(f"{self.base_url}{endpoint}", json=data)
        return response.json()
```

**JavaScript (React/Next.js)**:
```javascript
const API_BASE_URL = 'http://localhost:8000';

async function askQuestion(question, resumeContext = null) {
  const params = new URLSearchParams({
    question: question
  });
  
  if (resumeContext) {
    params.append('resume_context', resumeContext.substring(0, 2000));
  }
  
  const response = await fetch(`${API_BASE_URL}/api/chat/ask?${params}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  return await response.json();
}
```

---

### 2. Example Usage Patterns

#### Job Search
```javascript
// Request
POST /api/chat/ask?question=software%20engineer%20jobs%20at%20Google%20in%20Seattle

// Response
{
  "answer": "🎯 Found 12 jobs\n\n## Senior Software Engineer - Cloud\n🏢 Company: Google\n📍 Location: Seattle, WA\n💰 Salary: $180,000 - $250,000\n✅ H-1B Sponsor: Yes (97% approval rate)\n\n## Software Engineer - ML\n...",
  "intent": "job_search"
}
```

#### Salary Query
```javascript
// Request
POST /api/chat/ask?question=what%27s%20the%20average%20salary%20for%20data%20scientist%20at%20Amazon

// Response
{
  "answer": "💰 Salary Information for Data Scientist at Amazon:\n\nAverage Salary: $145,000\nSalary Range: $120,000 - $180,000\nBased on 245 H-1B filings",
  "intent": "salary"
}
```

#### H-1B Sponsorship
```javascript
// Request
POST /api/chat/ask?question=does%20Microsoft%20sponsor%20H-1B%3F

// Response
{
  "answer": "✅ Microsoft H-1B Sponsorship Details:\n\n📈 Approval Rate: 96.8%\n📊 Total Cases: 3,245 (last 6 months)\n💰 Average Salary: $135,000\n⚖️ Risk Level: Very Safe\n\nTop Attorneys:\n1. Fragomen - 98.2% success\n2. Berry Appleman - 97.1% success",
  "intent": "h1b_sponsorship"
}
```

#### Company Comparison
```javascript
// Request
POST /api/chat/ask?question=compare%20Google%20vs%20Amazon%20for%20H-1B%20sponsorship

// Response
{
  "answer": "📊 H-1B Sponsorship Comparison\n\n🥇 1. Google\n📈 Score: 98.5/100\n✅ Approval Rate: 97.2%\n📋 Filings: 1,234\n💰 Avg Salary: $165,000\n\n🥈 2. Amazon\n📈 Score: 96.8/100\n✅ Approval Rate: 94.5%\n📋 Filings: 2,456\n💰 Avg Salary: $145,000",
  "intent": "comparison"
}
```

#### Attorney Contact
```javascript
// Request
POST /api/chat/ask?question=immigration%20attorney%20in%20Boston

// Response
{
  "answer": "⚖️ Top Immigration Attorneys in Boston:\n\n## Fragomen Law Firm\n📧 Email: boston@fragomen.com\n📞 Phone: (617) 555-0100\n📍 Location: Boston, MA\n✅ Success Rate: 98.2%\n📊 Cases: 1,234",
  "intent": "contact"
}
```

#### Resume Analysis (with context)
```javascript
// Request
POST /api/chat/ask?question=analyze%20my%20resume&resume_context=John%20Doe...Python%20developer...

// Response
{
  "answer": "📄 Resume Analysis:\n\n✅ Strengths:\n- Strong Python skills\n- 3 years experience\n- ML background\n\n⚠️ Suggestions:\n- Add more quantifiable achievements\n- Include cloud technologies\n\n🎯 Matching Jobs: 234 positions found",
  "intent": "resume"
}
```

---

### 3. Context Manager Integration

The backend accepts enhanced queries with conversation context. Format:

```
Previous conversation:
User: {previous_user_message}
Assistant: {previous_assistant_response}
User: {another_user_message}
Assistant: {another_assistant_response}

Current question: {current_user_query}
```

**Frontend should send**:
```javascript
const conversationHistory = [
  { role: "user", content: "jobs at Google" },
  { role: "assistant", content: "Found 15 jobs..." },
  { role: "user", content: "what about Microsoft?" }
];

// Build context string
let contextString = "";
for (let msg of conversationHistory.slice(-6)) {
  contextString += `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}\n`;
}

const enhancedQuery = `${contextString}\n\nCurrent question: what about Microsoft?`;

// Send to API
POST /api/chat/ask?question={encodeURIComponent(enhancedQuery)}
```

---

### 4. Error Handling

**Error Response Format**:
```json
{
  "error": "Error message here",
  "status": "error",
  "code": 500
}
```

**Common Errors**:
- 400: Bad Request (missing required parameters)
- 404: Endpoint not found
- 500: Internal server error (database connection, query execution)

**Frontend Error Handling**:
```javascript
try {
  const response = await fetch(url, options);
  const data = await response.json();
  
  if (!response.ok || data.error) {
    throw new Error(data.error || 'Request failed');
  }
  
  return data;
} catch (error) {
  console.error('API Error:', error);
  return { answer: "Sorry, something went wrong. Please try again.", intent: "error" };
}
```

---

### 5. Response Formatting

The API returns markdown-formatted responses. Frontend should render:

**Markdown Elements Used**:
- `##` - Job titles, section headers
- `**bold**` - Emphasis
- `📍`, `💰`, `✅`, etc. - Emojis for visual appeal
- `\n` - Line breaks
- Bullet points with `-` or `•`

**Rendering Libraries**:
- **React**: `react-markdown` or `marked`
- **Streamlit**: Built-in `st.markdown()`
- **Vue**: `vue-markdown`

---

### 6. Performance Considerations

**Response Times** (approximate):
- Simple queries: 0.5-1.5 seconds
- Vector search: 1.5-3 seconds
- Complex comparisons: 2-4 seconds

**Optimization Tips**:
1. Show loading spinner for queries > 1 second
2. Implement request debouncing (300ms)
3. Cache common queries client-side
4. Use optimistic UI updates where possible

---

### 7. Real-time Features

**Session Management**:
```javascript
// Store conversation in session
const sessionId = generateUUID();

// Send with each request (if implementing on backend)
headers: {
  'X-Session-ID': sessionId
}
```

**WebSocket Support** (not currently implemented, but recommended):
```javascript
// For streaming responses
const ws = new WebSocket('ws://localhost:8000/ws/chat');

ws.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  appendToResponse(chunk.text);
};
```

---

### 8. Testing Endpoints

**Quick Test Script**:
```bash
# Health check
curl http://localhost:8000/health

# Simple job search
curl -X POST "http://localhost:8000/api/chat/ask?question=software%20engineer%20jobs"

# With context
curl -X POST "http://localhost:8000/api/chat/ask?question=data%20scientist%20positions&resume_context=Python%20developer%20with%205%20years"

# H-1B query
curl -X POST "http://localhost:8000/api/chat/ask?question=Google%20H-1B%20sponsorship"

# Attorney search
curl -X POST "http://localhost:8000/api/chat/ask?question=immigration%20attorney%20Massachusetts"
```

---

### 9. Data Models

**Job Object** (from EMBEDDED_JOBS):
```typescript
interface Job {
  job_id: string;
  title: string;
  company: string;
  location: string;
  salary_min?: number;
  salary_max?: number;
  description: string;
  posted_date: string;
  visa_sponsorship: boolean;
  work_model: string; // "Remote", "Hybrid", "On-site"
}
```

**H-1B Record** (from LCA_DISCLOSURE_DATA):
```typescript
interface H1BRecord {
  case_number: string;
  employer_name: string;
  job_title: string;
  worksite_city: string;
  worksite_state: string;
  wage_level: string; // "I", "II", "III", "IV"
  prevailing_wage: number;
  approval_status: string;
  attorney_firm?: string;
  attorney_city?: string;
}
```

---

### 10. Environment Configuration

**Backend Environment Variables** (in `secrets.json`):
```json
{
  "SNOWFLAKE_ACCOUNT": "your_account",
  "SNOWFLAKE_USER": "your_user",
  "SNOWFLAKE_PASSWORD": "your_password",
  "SNOWFLAKE_WAREHOUSE": "COMPUTE_WH",
  "SNOWFLAKE_DATABASE": "JOB_INTELLIGENCE",
  "SNOWFLAKE_SCHEMA": "PROCESSED_PROCESSING",
  "OPENAI_API_KEY": "sk-...",
  "AIRTABLE_API_KEY": "key...",
  "AIRTABLE_BASE_ID": "app..."
}
```

**Frontend Environment Variables**:
```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
VITE_API_URL=http://localhost:8000  # For Vite
NEXT_PUBLIC_API_URL=http://localhost:8000  # For Next.js
```

---

## Quick Start Integration

### React/Next.js Example
```jsx
import { useState } from 'react';

export default function ChatInterface() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await fetch(
        `http://localhost:8000/api/chat/ask?question=${encodeURIComponent(query)}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setResponse(data.answer);
    } catch (error) {
      setResponse('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <input 
          value={query} 
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about jobs, salaries, H-1B..." 
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>
      {response && <div dangerouslySetInnerHTML={{__html: marked(response)}} />}
    </div>
  );
}
```

### Vue.js Example
```vue
<template>
  <div>
    <form @submit.prevent="askQuestion">
      <input v-model="query" placeholder="Ask anything..." />
      <button :disabled="loading">{{ loading ? 'Thinking...' : 'Ask' }}</button>
    </form>
    <div v-if="response" v-html="markdownToHtml(response)"></div>
  </div>
</template>

<script>
import { marked } from 'marked';

export default {
  data() {
    return {
      query: '',
      response: '',
      loading: false
    }
  },
  methods: {
    async askQuestion() {
      this.loading = true;
      try {
        const res = await fetch(
          `http://localhost:8000/api/chat/ask?question=${encodeURIComponent(this.query)}`,
          { method: 'POST' }
        );
        const data = await res.json();
        this.response = data.answer;
      } catch (error) {
        this.response = 'Error: ' + error.message;
      } finally {
        this.loading = false;
      }
    },
    markdownToHtml(md) {
      return marked(md);
    }
  }
}
</script>
```

---

## Contact & Support

- **Backend Port**: 8000
- **Frontend Port**: 8501 (Streamlit)
- **Database**: Snowflake JOB_INTELLIGENCE
- **Records Available**: 70,819 jobs + 479,005 H-1B records

---

**Last Updated**: December 8, 2025
