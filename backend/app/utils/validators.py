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


def validate_file_upload(filename: str, file_content: bytes, allowed_extensions: list = None) -> tuple[bool, str]:
    """Validate uploaded file for resume processing.
    
    Args:
        filename: Name of the uploaded file
        file_content: Binary content of the file
        allowed_extensions: List of allowed file extensions (default: ['pdf', 'docx', 'txt'])
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if allowed_extensions is None:
        allowed_extensions = ['pdf', 'docx', 'txt']
    
    # Check file size (5MB limit)
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if len(file_content) > max_size:
        return False, f"File size exceeds 5MB limit (current: {len(file_content) / (1024*1024):.2f}MB)"
    
    # Check minimum size (100 bytes)
    if len(file_content) < 100:
        return False, "File is too small or empty"
    
    # Check file extension
    if not filename or '.' not in filename:
        return False, "Invalid filename: no extension found"
    
    extension = filename.lower().split('.')[-1]
    if extension not in allowed_extensions:
        return False, f"Invalid file type '.{extension}'. Allowed: {', '.join(allowed_extensions)}"
    
    # MIME type validation based on file signature (magic numbers)
    file_signatures = {
        'pdf': [b'%PDF'],
        'docx': [b'PK\x03\x04'],  # DOCX is a ZIP file
        'txt': []  # Text files have no specific signature
    }
    
    if extension in file_signatures and file_signatures[extension]:
        valid_signature = any(
            file_content.startswith(sig) 
            for sig in file_signatures[extension]
        )
        if not valid_signature:
            return False, f"File content doesn't match .{extension} format (possible file corruption or wrong extension)"
    
    return True, ""


def validate_resume_text(text: str) -> tuple[bool, str]:
    """Validate extracted resume text.
    
    Args:
        text: Extracted text from resume
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Resume text is empty"
    
    if len(text) < 100:
        return False, f"Resume text too short ({len(text)} chars). Minimum: 100 characters"
    
    if len(text) > 50000:
        return False, f"Resume text too long ({len(text)} chars). Maximum: 50,000 characters"
    
    return True, ""


def validate_resume_content(text: str) -> tuple[bool, str]:
    """Validate that content appears to be an actual resume using AI.
    
    Uses Snowflake Cortex LLM to intelligently determine if the document
    is a resume or some other type of document (bill, procedure, etc).
    
    Args:
        text: Extracted text from document
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or len(text.strip()) < 100:
        return False, "Content is too short to be a resume"
    
    # Use LLM for intelligent validation
    try:
        import snowflake.connector
        import os
        import json
        import re
        
        # Get Snowflake credentials
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            database='job_intelligence',
            schema='processed',
            warehouse='compute_wh'
        )
        
        cursor = conn.cursor()
        
        # Truncate text to first 2000 chars for efficiency
        text_sample = text[:2000]
        
        # Build AI validation prompt
        prompt = f"""Analyze this document and determine if it is a professional resume/CV.

DOCUMENT TEXT:
{text_sample}

INSTRUCTIONS:
1. A resume/CV contains: work experience, education, skills, and contact information about a person's professional background
2. NOT a resume: bills, invoices, statements, procedures, guidelines, manuals, forms, applications, instructions, letters

Respond with ONLY a JSON object:
{{
  "is_resume": true or false,
  "document_type": "resume" or "bill" or "procedure" or "statement" or "form" or "other",
  "confidence": 0.0 to 1.0,
  "reason": "brief explanation"
}}"""
        
        # Escape for SQL
        prompt_escaped = prompt.replace("'", "''")
        
        # Call Mixtral LLM
        sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mixtral-8x7b',
                '{prompt_escaped}'
            )
        """
        
        cursor.execute(sql)
        response = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        # Parse response
        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            
            is_resume = result.get('is_resume', False)
            doc_type = result.get('document_type', 'unknown')
            confidence = result.get('confidence', 0.0)
            reason = result.get('reason', 'Unknown')
            
            if not is_resume:
                return False, (
                    f"This appears to be a {doc_type}, not a resume. "
                    f"{reason}. Please upload a professional resume/CV with your work experience, "
                    "education, skills, and contact information."
                )
            
            if confidence < 0.7:
                return False, (
                    f"Document validation uncertain (confidence: {confidence:.0%}). "
                    "Please upload a clearly formatted resume with work experience, education, and skills."
                )
            
            return True, ""
        
        # Fallback to keyword validation if LLM fails
        return _fallback_keyword_validation(text)
        
    except Exception as e:
        # If AI validation fails, use fallback
        import logging
        logging.warning(f"AI resume validation failed: {e}, using fallback")
        return _fallback_keyword_validation(text)


def _fallback_keyword_validation(text: str) -> tuple[bool, str]:
    """Fallback keyword-based validation if AI fails."""
    text_lower = text.lower()
    
    # Quick check for obvious non-resume documents
    non_resume_indicators = [
        'invoice', 'bill', 'statement', 'payment', 'account number',
        'procedure', 'guideline', 'policy', 'manual', 'instructions',
        'total amount', 'balance due', 'transaction', 'form w-', 'tax form'
    ]
    
    if any(indicator in text_lower for indicator in non_resume_indicators):
        return False, (
            "This appears to be a billing/procedural document, not a resume. "
            "Please upload a professional resume with your work experience and skills."
        )
    
    # Check for resume indicators
    resume_indicators = [
        'experience', 'education', 'skills', 'work history',
        'employment', 'degree', 'university', 'projects'
    ]
    
    has_resume_content = sum(1 for indicator in resume_indicators if indicator in text_lower) >= 3
    
    if not has_resume_content:
        return False, (
            "This doesn't appear to be a resume. "
            "Please upload a document with your work experience, education, and skills."
        )
    
    return True, ""
