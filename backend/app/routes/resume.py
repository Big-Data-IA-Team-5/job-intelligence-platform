"""
Resume Matching Endpoint - Agent 4 Integration
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models.resume import (
    MatchRequest, MatchResponse, UploadRequest, UploadResponse,
    ResumeProfile, JobMatch
)
from app.models.response import ErrorResponse
from app.utils.agent_wrapper import AgentManager
from app.utils.validators import validate_file_upload, validate_resume_text, validate_resume_content
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resume", tags=["Resume Matching"])

@router.post("/match",
    response_model=MatchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def match_resume(request: MatchRequest):
    """
    Match resume to top jobs

    Uses Agent 4 to:
    1. Extract skills, experience, preferences from resume
    2. Find matching jobs in database using semantic search
    3. Score and rank top 10 matches by relevance and recency

    **Example Request:**
    ```json
    {
      "resume_text": "John Doe\\n5 years Python experience...\\nMaster's CS...",
      "user_id": "user_123"
    }
    ```

    **Returns:**
    - Extracted profile (skills, experience, education)
    - Top 10 job matches with scores
    - Match reasoning for each job
    """

    matcher = None
    try:
        # Validate resume text length
        is_valid, error_msg = validate_resume_text(request.resume_text)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resume text: {error_msg}"
            )

        # Validate resume content (CRITICAL: Check if it's actually a resume)
        is_valid_content, content_error = validate_resume_content(request.resume_text)
        if not is_valid_content:
            logger.warning(f"Resume content validation failed: {content_error}")
            raise HTTPException(
                status_code=400,
                detail=content_error
            )

        # Generate resume ID
        resume_id = f"resume_{uuid.uuid4().hex[:8]}"

        # Initialize Agent 4
        matcher = AgentManager.get_matcher()

        # Match
        result = matcher.match_resume(
            resume_id=resume_id,
            resume_text=request.resume_text
        )

        # Convert to response model - handle skills structure
        profile_data = result['profile']

        # If technical_skills is a dict, flatten it to a list
        if isinstance(profile_data.get('technical_skills'), dict):
            tech_skills = []
            for category, skills in profile_data['technical_skills'].items():
                if isinstance(skills, list):
                    tech_skills.extend(skills)
                else:
                    tech_skills.append(str(skills))
            profile_data['technical_skills'] = tech_skills

        # Same for soft_skills if it's a dict
        if isinstance(profile_data.get('soft_skills'), dict):
            soft_skills = []
            for category, skills in profile_data['soft_skills'].items():
                if isinstance(skills, list):
                    soft_skills.extend(skills)
                else:
                    soft_skills.append(str(skills))
            profile_data['soft_skills'] = soft_skills

        profile = ResumeProfile(**profile_data)

        # Build matches with deduplication
        seen_jobs = set()
        matches = []

        for m in result['top_matches']:
            job_id = m.get('job_id') or m.get('JOB_ID', '')
            title = m.get('title') or m.get('TITLE', '')
            company = m.get('company') or m.get('COMPANY', '')
            location = m.get('location') or m.get('LOCATION', '')

            # Create unique key based on title+company+location (more reliable than job_id)
            # Many job boards have duplicate postings with different IDs
            unique_key = f"{title}|{company}|{location}".lower().strip()

            # Skip duplicates
            if unique_key in seen_jobs:
                logger.info(f"Skipping duplicate job: {title} at {company} (ID: {job_id})")
                continue

            seen_jobs.add(unique_key)

            # Also track by job_id as secondary check
            if job_id:
                job_id_key = f"id:{job_id}"
                if job_id_key in seen_jobs:
                    logger.info(f"Skipping duplicate job_id: {job_id}")
                    continue
                seen_jobs.add(job_id_key)

            matches.append(JobMatch(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                overall_score=m.get('overall_score', 0.0) / 100.0,  # Normalize from percentage
                skills_score=m.get('skills_score', 0.0) / 100.0,
                experience_score=m.get('experience_score', 0.0) / 100.0,
                visa_score=m.get('visa_score', 0.0) / 100.0,
                location_score=m.get('location_score', 0.0) / 100.0,
                match_reasoning=m.get('match_reasoning', ''),
                url=m.get('url') or m.get('URL', ''),
                visa_category=m.get('visa_category') or m.get('VISA_CATEGORY')
            ))

        return MatchResponse(
            status="success",
            profile=profile,
            top_matches=matches,
            total_candidates=result['total_candidates'],
            resume_id=resume_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Matching error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume matching failed: {str(e)}"
        )

    finally:
        if matcher:
            matcher.close()

@router.post("/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def upload_resume(request: UploadRequest):
    """
    Upload resume text (stores in Snowflake)

    **Example Request:**
    ```json
    {
      "resume_text": "Full resume text...",
      "file_name": "john_doe_resume.pdf",
      "user_id": "user_123"
    }
    ```

    **Returns:**
    - Resume ID
    - Upload status
    """

    matcher = None
    try:
        # Validate resume text length
        is_valid, error_msg = validate_resume_text(request.resume_text)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resume text: {error_msg}"
            )

        # Validate resume content (check if it's actually a resume)
        is_valid_content, content_error = validate_resume_content(request.resume_text)
        if not is_valid_content:
            raise HTTPException(
                status_code=400,
                detail=content_error
            )

        # Generate resume ID
        resume_id = f"resume_{uuid.uuid4().hex[:8]}"

        # Initialize Agent 4
        matcher = AgentManager.get_matcher()

        # Store resume (simplified - just extract profile)
        result = matcher.match_resume(
            resume_id=resume_id,
            resume_text=request.resume_text
        )

        return UploadResponse(
            status="success",
            resume_id=resume_id,
            message="Resume uploaded and processed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume upload failed: {str(e)}"
        )

    finally:
        if matcher:
            matcher.close()


@router.post("/upload-file",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def upload_resume_file(
    file: UploadFile = File(...),
    user_id: str = ""
):
    """
    Upload resume file with validation (PDF, DOCX, TXT only, max 5MB)

    **Guardrails:**
    - Only PDF, DOCX, TXT files accepted
    - Maximum file size: 5MB
    - MIME type validation
    - Content extraction validation

    **Returns:**
    - Resume ID
    - Upload status
    - Extracted text preview
    """

    matcher = None
    try:
        # Read file content
        file_content = await file.read()

        # Validate file
        is_valid, error_msg = validate_file_upload(
            filename=file.filename,
            file_content=file_content,
            allowed_extensions=['pdf', 'docx', 'txt']
        )

        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )

        # Extract text based on file type
        resume_text = ""
        extension = file.filename.lower().split('.')[-1]

        if extension == 'txt':
            try:
                resume_text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Unable to decode text file. Please ensure it's UTF-8 encoded."
                )

        elif extension == 'pdf':
            try:
                import PyPDF2
                from io import BytesIO

                pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
                resume_text = ""

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        resume_text += text + "\n"

                if not resume_text.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Could not extract text from PDF. File may be image-based or corrupted."
                    )
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="PDF processing not available. Please upload TXT or DOCX."
                )

        elif extension == 'docx':
            try:
                import docx
                from io import BytesIO

                doc = docx.Document(BytesIO(file_content))
                resume_text = "\n".join([
                    para.text for para in doc.paragraphs
                    if para.text.strip()
                ])

                if not resume_text.strip():
                    raise HTTPException(
                        status_code=400,
                        detail="DOCX file appears to be empty"
                    )
            except ImportError:
                raise HTTPException(
                    status_code=500,
                    detail="DOCX processing not available. Please upload TXT or PDF."
                )

        # Validate extracted text length
        is_valid, error_msg = validate_resume_text(resume_text)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid resume content: {error_msg}"
            )

        # Validate resume content (check if it's actually a resume)
        is_valid_content, content_error = validate_resume_content(resume_text)
        if not is_valid_content:
            raise HTTPException(
                status_code=400,
                detail=content_error
            )

        # Generate resume ID
        resume_id = f"resume_{uuid.uuid4().hex[:8]}"

        # Initialize Agent 4 and process
        matcher = AgentManager.get_matcher()

        result = matcher.match_resume(
            resume_id=resume_id,
            resume_text=resume_text
        )

        return UploadResponse(
            status="success",
            resume_id=resume_id,
            message=f"Resume file '{file.filename}' uploaded and processed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume file upload failed: {str(e)}"
        )

    finally:
        if matcher:
            matcher.close()