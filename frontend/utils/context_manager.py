"""
Industry-Grade Conversation Context Manager
Handles intelligent context tracking, entity extraction, and conversation continuity
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re


class ConversationContext:
    """Manages conversation state and context for intelligent multi-turn interactions."""
    
    def __init__(self, max_turns: int = 10):
        """
        Initialize conversation context manager.
        
        Args:
            max_turns: Maximum conversation turns to keep in memory
        """
        self.max_turns = max_turns
        self.entities = {
            'companies': [],
            'locations': [],
            'job_titles': [],
            'topics': [],
            'last_intent': None,
            'last_results': []
        }
        self.conversation_history = []
        
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract key entities from user text using pattern matching.
        
        Args:
            text: User input text
            
        Returns:
            Dict of extracted entities by type
        """
        entities = {
            'companies': [],
            'locations': [],
            'job_titles': []
        }
        
        # Known companies (case-insensitive, word boundaries to avoid partial matches)
        known_companies = [
            'amazon', 'google', 'microsoft', 'meta', 'facebook', 'apple', 'netflix', 
            'uber', 'airbnb', 'stripe', 'salesforce', 'oracle', 'ibm', 'intel', 
            'nvidia', 'adobe', 'cisco', 'dell', 'hp', 'snowflake', 'databricks', 
            'openai', 'tesla', 'twitter', 'linkedin', 'dropbox', 'spotify',
            'servicenow', 'amgen', 'gilead', 'hdr'
        ]
        
        # First try to match with suffixes (Inc., Corp., LLC, etc.)
        company_with_suffix = r'\b(' + '|'.join(known_companies) + r')(?:,?\s*(?:inc\.?|corp\.?|llc|ltd\.?))?\b'
        matches = re.findall(company_with_suffix, text, re.IGNORECASE)
        entities['companies'] = [m.lower() for m in matches]
        
        # Known locations (cities, states, regions)
        known_locations = [
            'boston', 'seattle', 'san francisco', 'new york', 'nyc', 'bay area', 
            'austin', 'chicago', 'denver', 'los angeles', 'la', 'california', 
            'massachusetts', 'texas', 'washington', 'remote', 'portland', 'atlanta',
            'miami', 'silicon valley', 'palo alto', 'mountain view', 'sunnyvale'
        ]
        
        location_pattern = r'\b(' + '|'.join(known_locations) + r')\b'
        matches = re.findall(location_pattern, text, re.IGNORECASE)
        entities['locations'] = [m.lower() for m in matches]
        
        # Job title patterns
        job_patterns = [
            r'\b(software engineer|data scientist|data analyst|machine learning|ml engineer|'
            r'product manager|devops|frontend|backend|full stack|data engineer|'
            r'senior engineer|principal engineer|staff engineer|engineering manager)\b'
        ]
        
        for pattern in job_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities['job_titles'].extend([m.lower() for m in matches])
        
        # Remove duplicates while preserving order
        entities['companies'] = list(dict.fromkeys(entities['companies']))
        entities['locations'] = list(dict.fromkeys(entities['locations']))
        entities['job_titles'] = list(dict.fromkeys(entities['job_titles']))
        
        return entities
    
    def detect_intent(self, text: str) -> str:
        """
        Detect user intent from text.
        
        Args:
            text: User input
            
        Returns:
            Detected intent category
        """
        text_lower = text.lower()
        
        # Intent patterns (ordered by specificity)
        intent_patterns = {
            'comparison': r'\b(compare|vs|versus|difference|better|which|or)\b',
            'contact': r'\b(contact|email|phone|attorney|lawyer|reach|law firm)\b',
            'salary': r'\b(salary|pay|wage|compensation|how much|earn)\b',
            'h1b_sponsorship': r'\b(sponsor|h-?1b|h1b|visa|approval rate|safe)\b',
            'job_search': r'\b(job|jobs|position|opening|role|find|search|looking|show me|list)\b',
            'resume': r'\b(resume|cv|analyze|review|feedback|match)\b',
            'career': r'\b(career|advice|should i|transition|path|growth)\b',
            'follow_up': r'\b(what about|and|also|more|tell me more|what else)\b'
        }
        
        for intent, pattern in intent_patterns.items():
            if re.search(pattern, text_lower):
                return intent
        
        return 'general'
    
    def update_context(self, user_message: str, assistant_response: str):
        """
        Update conversation context with new exchange.
        
        Args:
            user_message: User's message
            assistant_response: Assistant's response
        """
        # Extract entities from user message
        new_entities = self.extract_entities(user_message)
        
        # Update entity tracking (keep last 5 unique of each type)
        for entity_type, values in new_entities.items():
            for value in values:
                if value not in self.entities[entity_type]:
                    self.entities[entity_type].append(value)
                    # Keep only last 5
                    if len(self.entities[entity_type]) > 5:
                        self.entities[entity_type].pop(0)
        
        # Detect and store intent
        intent = self.detect_intent(user_message)
        self.entities['last_intent'] = intent
        
        # Extract key information from assistant response
        if 'Found' in assistant_response or '##' in assistant_response:
            # Job results or structured data
            self.entities['topics'].append('job_results')
        elif '$' in assistant_response:
            self.entities['topics'].append('salary')
        elif 'approval rate' in assistant_response.lower() or 'sponsor' in assistant_response.lower():
            self.entities['topics'].append('h1b')
        
        # Add to conversation history
        self.conversation_history.append({
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'assistant': assistant_response,
            'intent': intent,
            'entities': new_entities
        })
        
        # Trim history to max_turns
        if len(self.conversation_history) > self.max_turns:
            self.conversation_history = self.conversation_history[-self.max_turns:]
    
    def resolve_references(self, text: str) -> str:
        """
        Resolve pronouns and references to entities from context.
        
        Args:
            text: User input with potential references
            
        Returns:
            Text with resolved references
        """
        resolved = text
        text_lower = text.lower()
        
        # Handle company references
        if re.search(r'\b(they|it|them|that company)\b', text, re.IGNORECASE):
            if self.entities['companies']:
                last_company = self.entities['companies'][-1]
                resolved = re.sub(
                    r'\b(they|it|them|that company)\b',
                    last_company,
                    resolved,
                    flags=re.IGNORECASE
                )
        
        # Handle location references
        if re.search(r'\b(there|that place|that city)\b', text, re.IGNORECASE):
            if self.entities['locations']:
                last_location = self.entities['locations'][-1]
                resolved = re.sub(
                    r'\b(there|that place|that city)\b',
                    last_location,
                    resolved,
                    flags=re.IGNORECASE
                )
        
        # Handle implicit job search context
        # "give me more jobs at ServiceNow" or "jobs available in ServiceNow"
        if re.search(r'\b(more jobs|jobs available|jobs at|show.*jobs|find.*jobs)\b', text_lower):
            # If asking for jobs but no job title specified, add context
            if not self.entities['job_titles']:
                # Check if this follows a job search
                if self.entities['last_intent'] in ['job_search', 'comparison']:
                    # Get job title from previous searches
                    for turn in reversed(self.conversation_history[-3:]):
                        if 'software engineer' in turn['user'].lower():
                            if 'software engineer' not in text_lower:
                                resolved = f"software engineer {resolved}"
                            break
        
        return resolved
    
    def build_context_string(self, include_last_n: int = 3) -> str:
        """
        Build intelligent context string from conversation history.
        Preserves full chat history with smart summarization for long responses.
        
        Args:
            include_last_n: Number of recent turns to include
            
        Returns:
            Formatted context string with full conversation awareness
        """
        if not self.conversation_history:
            return ""
        
        recent = self.conversation_history[-include_last_n:]
        context_parts = []
        
        for idx, turn in enumerate(recent):
            # Always include full user message - it's critical for understanding
            user_msg = turn['user']
            context_parts.append(f"User: {user_msg}")
            
            # Smart handling of assistant responses - preserve key information
            assistant_msg = turn['assistant']
            
            # For recent message (last turn), include more detail
            is_most_recent = (idx == len(recent) - 1)
            
            if is_most_recent:
                # Last exchange - include up to 600 chars to maintain context
                if len(assistant_msg) > 600:
                    # Extract key sections: results, salary, H-1B, attorney info
                    key_info = self._extract_key_info(assistant_msg, turn['intent'])
                    if key_info:
                        context_parts.append(f"Assistant: {key_info}")
                    else:
                        context_parts.append(f"Assistant: {assistant_msg[:600]}...")
                else:
                    context_parts.append(f"Assistant: {assistant_msg}")
            else:
                # Older exchanges - intelligently summarize based on intent
                if turn['intent'] == 'job_search':
                    # Preserve job search results summary
                    job_count_match = re.search(r'Found (\d+)', assistant_msg)
                    companies_mentioned = turn['entities'].get('companies', [])
                    
                    summary = f"Found {job_count_match.group(1)} jobs" if job_count_match else "Searched for jobs"
                    if companies_mentioned:
                        summary += f" at {', '.join(companies_mentioned[:3])}"
                    
                    # Include first job if available
                    first_job = re.search(r'##\s*(.+?)(?=\n|##|$)', assistant_msg)
                    if first_job:
                        summary += f" (e.g., {first_job.group(1)[:80]})"
                    
                    context_parts.append(f"Assistant: {summary}")
                
                elif turn['intent'] == 'salary':
                    # Preserve salary information
                    salary_matches = re.findall(r'\$[\d,]+', assistant_msg)
                    companies = turn['entities'].get('companies', [])
                    
                    summary = "Salary information: "
                    if companies and salary_matches:
                        summary += f"{companies[0]} - {salary_matches[0]}"
                    elif salary_matches:
                        summary += f"Range: {salary_matches[0]}"
                        if len(salary_matches) > 1:
                            summary += f" - {salary_matches[-1]}"
                    else:
                        summary += assistant_msg[:200]
                    
                    context_parts.append(f"Assistant: {summary}")
                
                elif turn['intent'] == 'h1b_sponsorship':
                    # Preserve H-1B sponsorship details
                    companies = turn['entities'].get('companies', [])
                    approval_match = re.search(r'(\d+\.?\d*)%?\s*approval', assistant_msg, re.IGNORECASE)
                    safe_match = re.search(r'(safe|moderate|risky)', assistant_msg, re.IGNORECASE)
                    
                    summary = "H-1B Sponsorship: "
                    if companies:
                        summary += f"{companies[0]} - "
                    if approval_match:
                        summary += f"{approval_match.group(1)}% approval rate"
                    if safe_match:
                        summary += f" ({safe_match.group(1)} option)"
                    
                    if not approval_match and not safe_match:
                        summary += assistant_msg[:200]
                    
                    context_parts.append(f"Assistant: {summary}")
                
                elif turn['intent'] == 'comparison':
                    # Preserve comparison insights
                    companies = turn['entities'].get('companies', [])
                    summary = f"Compared {' vs '.join(companies[:2])}" if len(companies) >= 2 else "Provided comparison"
                    
                    # Extract key comparison points
                    if 'salary' in assistant_msg.lower():
                        salary_matches = re.findall(r'\$[\d,]+', assistant_msg)
                        if len(salary_matches) >= 2:
                            summary += f" - Salaries: {salary_matches[0]} vs {salary_matches[1]}"
                    
                    context_parts.append(f"Assistant: {summary}")
                
                elif turn['intent'] == 'contact':
                    # Preserve contact information type
                    if 'attorney' in assistant_msg.lower() or 'lawyer' in assistant_msg.lower():
                        # Extract attorney name and location if available
                        location = turn['entities'].get('locations', [])
                        location_str = location[0] if location else "attorney"
                        context_parts.append(f"Assistant: Provided {location_str} attorney contact information")
                    else:
                        context_parts.append(f"Assistant: Provided contact information")
                
                elif turn['intent'] == 'resume':
                    # Preserve resume analysis summary
                    summary = "Resume analysis: "
                    if 'score' in assistant_msg.lower() or '%' in assistant_msg:
                        score_match = re.search(r'(\d+)%', assistant_msg)
                        if score_match:
                            summary += f"{score_match.group(1)}% match"
                    summary += " - Provided feedback and recommendations"
                    context_parts.append(f"Assistant: {summary}")
                
                elif turn['intent'] == 'career':
                    # Preserve career advice essence
                    summary = "Career advice: "
                    if len(assistant_msg) > 250:
                        # Extract first key point
                        first_point = assistant_msg[:250].split('.')[0]
                        summary += first_point + "..."
                    else:
                        summary += assistant_msg
                    context_parts.append(f"Assistant: {summary}")
                
                else:
                    # Generic handling - preserve first 250 chars
                    if len(assistant_msg) > 250:
                        context_parts.append(f"Assistant: {assistant_msg[:250]}...")
                    else:
                        context_parts.append(f"Assistant: {assistant_msg}")
        
        return "\n".join(context_parts)
    
    def _extract_key_info(self, text: str, intent: str) -> str:
        """
        Extract key information from long assistant responses.
        
        Args:
            text: Full assistant response
            intent: Detected intent
            
        Returns:
            Extracted key information or empty string
        """
        if intent == 'job_search':
            # Extract: Found X jobs + first 2-3 job listings
            lines = text.split('\n')
            key_lines = []
            job_count = 0
            
            for line in lines:
                if 'Found' in line or '##' in line or 'Location:' in line or 'Salary:' in line:
                    key_lines.append(line)
                    if '##' in line:
                        job_count += 1
                    if job_count >= 2:  # Include first 2 jobs
                        break
            
            return '\n'.join(key_lines[:10])  # Limit to 10 lines
        
        elif intent == 'contact':
            # Extract attorney/contact details
            lines = text.split('\n')
            key_lines = [line for line in lines if any(k in line.lower() for k in 
                         ['attorney', 'lawyer', 'email', 'phone', 'firm', '##'])]
            return '\n'.join(key_lines[:8])
        
        return ""
    
    def get_current_entities(self) -> Dict[str, List[str]]:
        """
        Get currently tracked entities.
        
        Returns:
            Dict of tracked entities
        """
        return self.entities.copy()
    
    def should_use_context(self, text: str) -> bool:
        """
        Determine if context should be included based on query type.
        
        Args:
            text: User input
            
        Returns:
            True if context should be used
        """
        text_lower = text.lower()
        
        # Follow-up indicators
        follow_up_patterns = [
            r'^(what about|and|also|more|what else|tell me more|ok so|give me more)',
            r'\b(too|as well|another|different)\b',
            r'\b(they|them|it|that|those|these)\b',
            r'^\w+\s*\?$',  # Single word questions like "Salary?"
            r'\b(which company|which is|from this|from these)\b',  # Selection from results
        ]
        
        for pattern in follow_up_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Job search follow-ups - "jobs at X", "more jobs available"
        if re.search(r'\b(jobs? (at|in|available|from)|more jobs|find.*jobs)\b', text_lower):
            # Use context if recently discussed jobs or companies
            if self.entities['companies'] or self.entities['last_intent'] == 'job_search':
                return True
        
        # Always use context if conversation history exists and query is short
        if len(self.conversation_history) > 0 and len(text.split()) < 5:
            return True
        
        return False
    
    def enhance_query(self, query: str) -> Tuple[str, Dict]:
        """
        Enhance query with context and resolved references.
        
        Args:
            query: Original user query
            
        Returns:
            Tuple of (enhanced_query, metadata)
        """
        # Resolve references
        resolved_query = self.resolve_references(query)
        
        # Build context if needed
        use_context = self.should_use_context(query)
        
        if use_context and self.conversation_history:
            context_str = self.build_context_string(include_last_n=3)
            enhanced_query = f"{context_str}\n\nCurrent question: {resolved_query}"
        else:
            enhanced_query = resolved_query
        
        # Build metadata
        metadata = {
            'original_query': query,
            'resolved_query': resolved_query,
            'used_context': use_context,
            'current_entities': self.get_current_entities(),
            'last_intent': self.entities['last_intent']
        }
        
        return enhanced_query, metadata
    
    def clear_context(self):
        """Clear all conversation context."""
        self.entities = {
            'companies': [],
            'locations': [],
            'job_titles': [],
            'topics': [],
            'last_intent': None,
            'last_results': []
        }
        self.conversation_history = []
    
    def get_summary(self) -> Dict:
        """
        Get conversation summary statistics.
        
        Returns:
            Dict with conversation statistics
        """
        return {
            'total_turns': len(self.conversation_history),
            'entities_tracked': {
                'companies': len(self.entities['companies']),
                'locations': len(self.entities['locations']),
                'job_titles': len(self.entities['job_titles'])
            },
            'intents_used': list(set(turn['intent'] for turn in self.conversation_history)),
            'last_intent': self.entities['last_intent']
        }
