"""
Validation Utilities
"""
from typing import Optional
import re


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_user_id(user_id: str) -> bool:
    """Validate user ID format"""
    return len(user_id) > 0 and len(user_id) <= 100


def sanitize_sql_input(input_str: str) -> str:
    """Sanitize SQL input to prevent injection"""
    # Remove potentially dangerous characters
    dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'sp_']
    
    for char in dangerous_chars:
        input_str = input_str.replace(char, '')
    
    return input_str.strip()


def validate_search_query(query: Optional[str]) -> bool:
    """Validate search query"""
    if not query:
        return False
    
    if len(query) > 500:
        return False
    
    return True
