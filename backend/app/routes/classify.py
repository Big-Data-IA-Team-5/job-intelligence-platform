"""
Visa Classification Endpoint - Agent 3 Integration
"""
from fastapi import APIRouter, HTTPException
from app.models.job import ClassifyRequest, ClassifyResponse
from app.models.response import ErrorResponse
from app.utils.agent_wrapper import AgentManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Classification"])

@router.post("/classify",
    response_model=ClassifyResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def classify_job(request: ClassifyRequest):
    """
    Classify job visa eligibility

    Uses Agent 3 (Mixtral 8x7B) to determine:
    - CPT (internships for F-1 students)
    - OPT (entry-level for recent grads)
    - H-1B (requires sponsorship)
    - US-Only (citizenship required)

    **Example Request:**
    ```json
    {
      "title": "Software Engineer Intern",
      "company": "Microsoft",
      "description": "Summer internship for students. CPT eligible..."
    }
    ```

    **Returns:**
    - Visa category (CPT/OPT/H-1B/US-Only)
    - Confidence score (0-1)
    - Keywords/signals detected
    - AI reasoning
    - Whether human review needed
    """

    classifier = None
    try:
        # Initialize Agent 3
        classifier = AgentManager.get_classifier()

        # Classify
        result = classifier.classify_job({
            'title': request.title,
            'company': request.company,
            'description': request.description
        })

        return ClassifyResponse(
            visa_category=result['visa_category'],
            confidence=result['confidence'],
            signals=result.get('signals', []),
            reasoning=result.get('reasoning', ''),
            needs_review=result.get('needs_review', False)
        )

    except Exception as e:
        logger.error(f"Classification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Classification failed: {str(e)}"
        )

    finally:
        if classifier:
            classifier.close()