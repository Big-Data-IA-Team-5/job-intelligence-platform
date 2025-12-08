# Intelligent Conversation Context System

## Overview

The Job Intelligence Platform now features an **industry-grade conversation context manager** that makes the chat truly intelligent and context-aware, similar to ChatGPT and Claude.

## Key Features

### 1. **Entity Extraction & Tracking** 🏢
- Automatically extracts and tracks:
  - **Companies**: Google, Microsoft, Amazon, etc. (27 major tech companies)
  - **Locations**: Seattle, Boston, San Francisco, etc. (23 locations)
  - **Job Titles**: Software Engineer, Data Scientist, etc.
- Maintains last 5 unique entities of each type
- Removes duplicates automatically

### 2. **Intent Detection** 🎯
Identifies user intent across 8 categories:
- `job_search`: Finding jobs, positions, roles
- `salary`: Compensation queries
- `h1b_sponsorship`: Visa sponsorship questions
- `comparison`: Comparing companies or offers
- `contact`: Attorney/company contact information
- `resume`: Resume analysis and feedback
- `career`: Career advice and guidance
- `follow_up`: Follow-up questions

### 3. **Reference Resolution** 🔗
Intelligently resolves pronouns and references:
- **"What about Microsoft?"** → Understands previous context about Google
- **"How much do they pay?"** → Resolves "they" to last mentioned company
- **"Tell me about that company"** → References previous company discussion
- **"Jobs there?"** → Resolves "there" to last mentioned location

### 4. **Smart Context Building** 📚
- Keeps last 3-10 conversation turns in memory
- Intelligently summarizes long responses based on intent:
  - **Job searches**: Preserves job count + first 2 jobs
  - **Salary info**: Extracts salary ranges and company names
  - **H-1B data**: Keeps approval rates and safety ratings
  - **Comparisons**: Maintains comparison points
  - **Attorney contacts**: Preserves contact details
- Most recent exchange gets full detail (600 chars)
- Older exchanges get smart summarization

### 5. **Context-Aware Query Enhancement** 🚀
- Detects when context should be used:
  - Short questions (< 5 words)
  - Follow-up indicators ("what about", "also", "more")
  - Reference pronouns ("they", "it", "that")
  - Single-word questions ("Salary?", "Location?")
- Automatically enhances query with relevant conversation history
- Passes structured context to backend API

### 6. **Conversation Continuity** 🔄
- Tracks conversation flow and topic transitions
- Maintains awareness of active discussions:
  - Currently comparing companies?
  - Discussing H-1B sponsorship?
  - Analyzing resume?
- Preserves context across multiple follow-up questions

## Architecture

### Core Class: `ConversationContext`

```python
from utils.context_manager import ConversationContext

# Initialize
ctx = ConversationContext(max_turns=10)

# Enhance user query with context
enhanced_query, metadata = ctx.enhance_query(user_input)

# Update context after getting response
ctx.update_context(user_input, assistant_response)

# Get conversation summary
summary = ctx.get_summary()
```

### Integration with Frontend

**Home.py** automatically:
1. Initializes context manager in session state
2. Enhances every user query with intelligent context
3. Updates context after each response
4. Shows context awareness status in sidebar

### Metadata Structure

```python
metadata = {
    'original_query': "What about Microsoft?",
    'resolved_query': "What about Microsoft?",
    'used_context': True,
    'current_entities': {
        'companies': ['google', 'microsoft'],
        'locations': ['seattle'],
        'job_titles': ['software engineer'],
        'topics': ['job_results'],
        'last_intent': 'follow_up',
        'last_results': []
    },
    'last_intent': 'follow_up'
}
```

## Example Conversations

### Example 1: Job Search with Follow-ups

**User**: "Show me software engineer jobs at Google in Seattle"
- **Entities extracted**: companies=['google'], locations=['seattle']
- **Intent**: job_search

**Assistant**: [Returns 15 jobs with details]

**User**: "What about Microsoft?"
- **Context used**: Yes
- **Enhanced query**: Includes previous Google search context
- **Entities tracked**: companies=['google', 'microsoft'], locations=['seattle']

**User**: "Salary comparison?"
- **Context used**: Yes
- **Understands**: Compare Google vs Microsoft salaries in Seattle

### Example 2: H-1B Sponsorship

**User**: "Which companies have best H-1B approval rates?"
- **Intent**: h1b_sponsorship

**Assistant**: [Lists top companies with approval rates]

**User**: "Tell me more about their attorneys"
- **Reference resolved**: "their" → companies mentioned above
- **Context used**: Full previous conversation

### Example 3: Career Advice Flow

**User**: "Should I join a startup or big tech?"
- **Intent**: career

**Assistant**: [Provides detailed career advice]

**User**: "What if I want better work-life balance?"
- **Context used**: Maintains career advice thread
- **Understands**: This is a follow-up to career decision

## UI Features

### Sidebar Context Display

```
🧠 Context Awareness
🏢 Tracking 2 companies
📍 Tracking 1 location
💡 Last topic: H1B Sponsorship
```

### Clear Context Button
- Resets all conversation context
- Clears entity tracking
- Starts fresh conversation

## Technical Details

### Pattern Matching

**Company Detection**:
- 27 major tech companies (Amazon, Google, Microsoft, Meta, etc.)
- Word boundary matching to avoid false positives

**Location Detection**:
- 23 major tech hubs and regions
- Handles multi-word locations (San Francisco, Bay Area)

**Intent Detection**:
- Regex-based pattern matching
- Ordered by specificity (comparison before job_search)

### Context Compression

**For Recent Messages** (last turn):
- Include up to 600 characters
- Preserve full detail for immediate context

**For Older Messages**:
- Job searches: "Found X jobs at Company (e.g., first job title)"
- Salaries: "Salary information: Company - $XXX,XXX"
- H-1B: "H-1B Sponsorship: Company - 95% approval rate (safe option)"
- Comparisons: "Compared Google vs Microsoft - Salaries: $X vs $Y"

### Performance Optimization

- Entity deduplication with order preservation
- Regex compilation for pattern matching (future enhancement)
- Max turns limit (default: 10) to prevent memory bloat
- Smart truncation based on content type

## Future Enhancements

1. **Semantic Similarity**: Use embeddings to find relevant context instead of just recency
2. **Multi-turn Planning**: Detect when user has a multi-step goal
3. **Clarification Questions**: Ask for missing details when context is ambiguous
4. **Context Persistence**: Save/restore conversation context across sessions
5. **Advanced Entity Linking**: Link entities to database IDs for better tracking

## Testing

Run comprehensive tests:

```bash
cd /Users/pranavpatel/Desktop/job-intelligence-platform/frontend
python3 test_context_manager.py
```

Expected output:
- ✓ Entity extraction and tracking
- ✓ Reference resolution
- ✓ Intent detection and continuity
- ✓ Smart context building
- ✓ Intelligent summarization
- ✓ Follow-up question awareness

## API Impact

The enhanced query is sent to the backend via:

```python
enhanced_prompt = f"""Previous conversation:
{context_string}

Current question: {user_query}"""

url = f"/api/chat/ask?question={quote(enhanced_prompt)}"
```

Backend receives full context and can make better decisions based on conversation history.

## Best Practices

1. **Keep conversations focused**: Context works best within a single topic
2. **Use clear follow-ups**: "What about X?" works better than just "X?"
3. **Clear context periodically**: Use the clear button for new topics
4. **Check sidebar**: Monitor what entities are being tracked

---

**Status**: ✅ **Production Ready** - Industry-level intelligent conversation management

**Version**: 1.0.0  
**Last Updated**: December 8, 2025
