import logging
import os
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from openai import APIConnectionError, APITimeoutError, RateLimitError
from pydantic import BaseModel, Field, field_validator

from services.ai import _generate_smart_pedagogical_reply, generate_tutor_reply
from services.analyzer import (
    generate_admin_class_overview,
    generate_student_report,
    generate_student_socratic_quiz,
    get_or_create_student_directive,
)
from services.db import (
    insert_student_score,
    insert_teacher_feedback,
    log_chat_interaction,
)

# Load environment variables across local and workspace root paths
load_dotenv()
_base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_base_dir, ".env"))
load_dotenv(os.path.join(_base_dir, ".env.local"))
load_dotenv(os.path.join(os.path.dirname(_base_dir), ".env"))
load_dotenv(os.path.join(os.path.dirname(_base_dir), ".env.local"))

# Setup console logging for every request and error
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_tutor_api")

app = FastAPI(
    title="Class 10 CBSE AI Tutor & Student Progress Analyzer API",
    description=(
        "Backend API for a Socratic AI tutor and 4-Factor Student Progress Analyzer "
        "(Scores, Answering Capacity, Enthusiasm, and Admin/Teacher Opinion) powered by Supabase."
    ),
    version="2.0.0",
)

# CORS Middleware (Hackathon setup - allowing all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request & Error Logging Middleware / Handlers ---

@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log every incoming HTTP request, its status code, and processing duration."""
    start_time = time.perf_counter()
    client_ip = request.client.host if request.client else "unknown"
    logger.info(
        "[REQUEST] %s %s from %s",
        request.method,
        request.url.path,
        client_ip,
    )
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "[RESPONSE] %s %s -> Status %d (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "[UNHANDLED ERROR] %s %s failed after %.2f ms: %s",
            request.method,
            request.url.path,
            elapsed_ms,
            exc,
        )
        raise


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log request validation errors clearly to the console for easier frontend integration debugging."""
    logger.warning(
        "[VALIDATION ERROR] %s %s - Details: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return await request_validation_exception_handler(request, exc)


# --- Request and Response Schemas ---

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message sender role: 'user' or 'assistant'")
    content: str = Field(..., max_length=2000, description="Content of the message")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        role_cleaned = value.strip().lower()
        if role_cleaned not in ("user", "assistant"):
            raise ValueError("Role must be either 'user' or 'assistant'")
        return role_cleaned

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Content cannot be empty or only whitespace")
        return cleaned


class ChatRequest(BaseModel):
    student_id: str = Field(default="10034455542", min_length=1, max_length=100, description="Unique student identifier")
    student_name: str = Field(default="Alex Chen", min_length=1, max_length=100, description="Student's name")
    message: str = Field(..., min_length=1, max_length=1000, description="Student's question or message (max 1000 chars)")
    history: Optional[List[ChatMessage]] = Field(
        default=None,
        description="Optional conversation history list of previous user/assistant messages",
    )

    @field_validator("student_id", "student_name", "message")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or contain only whitespace.")
        return cleaned


class ChatResponse(BaseModel):
    reply: str = Field(..., description="The AI tutor's response message")
    status: str = Field(..., description="Status of the response ('success' or 'fallback')")
    detected_subject: Optional[str] = Field(default="General", description="Detected Class 10 CBSE subject")
    support_tier: Optional[str] = Field(
        default="guided_support",
        description="Active Socratic support mode ('intensive_scaffolding' | 'guided_support' | 'independent_challenge')",
    )
    support_needed_score: Optional[float] = Field(
        default=50.0,
        description="0-100 score showing how much Socratic support is currently allocated to this student",
    )


class ScoreCreateRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=100, description="Unique student identifier")
    student_name: str = Field(..., min_length=1, max_length=100, description="Student's name")
    subject: str = Field(..., min_length=1, max_length=100, description="Class 10 CBSE Subject (e.g., Mathematics, Science)")
    topic: str = Field(default="General", max_length=150, description="Specific chapter or topic name")
    score: float = Field(..., ge=0.0, description="Marks obtained by the student")
    max_score: float = Field(..., gt=0.0, description="Maximum possible marks for the assessment")
    assessment_type: str = Field(default="quiz", max_length=50, description="Type of assessment: quiz, unit_test, assignment, mock_exam")

    @field_validator("student_id", "student_name", "subject")
    @classmethod
    def validate_non_empty_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace.")
        return cleaned


class TeacherFeedbackRequest(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=100, description="Unique student identifier")
    student_name: str = Field(..., min_length=1, max_length=100, description="Student's name")
    teacher_name: str = Field(default="Class Teacher", max_length=100, description="Teacher/Admin name")
    subject: str = Field(default="General", max_length=100, description="Subject the observation applies to (or 'General')")
    support_level: str = Field(
        default="moderate_support",
        description="Requested Socratic support level: 'high_support', 'moderate_support', or 'independent_challenge'",
    )
    teacher_support_rating: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="0-100 rating of how much extra Socratic support the teacher feels the student needs",
    )
    opinion_notes: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Teacher's qualitative observation and guidance instructions for the Socratic tutor",
    )

    @field_validator("student_id", "student_name", "opinion_notes")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or contain only whitespace.")
        return cleaned

    @field_validator("support_level")
    @classmethod
    def validate_support_level(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ("high_support", "moderate_support", "independent_challenge"):
            raise ValueError("support_level must be 'high_support', 'moderate_support', or 'independent_challenge'")
        return cleaned


# --- Endpoints ---

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify backend service status."""
    ai_provider = (os.getenv("AI_PROVIDER") or "opencode").strip().lower()
    if ai_provider == "gemini":
        provider_label = "Google Gemini"
        active_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    elif ai_provider == "nvidia":
        provider_label = "NVIDIA NIM"
        active_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
    else:
        provider_label = "OpenCode Zen"
        active_model = os.getenv("OPENCODE_MODEL", "nemotron-3.5-lightning-free")

    return {
        "status": "healthy",
        "service": "Class 10 CBSE AI Tutor",
        "provider": provider_label,
        "model": active_model,
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Primary chat endpoint for students.
    1. Reads the student's 4-factor analysis profile from Supabase (`student_analytics`)
       to determine how much support (`support_tier` & `adaptive_directive`) to provide.
    2. Invokes the Socratic AI tutor with that adaptive directive.
    3. Logs the interaction to Supabase (`chat_logs`).
    """
    logger.info(
        "[CHAT] Student='%s' (ID=%s) | Message='%s'",
        request.student_name,
        request.student_id,
        request.message[:80] + ("..." if len(request.message) > 80 else ""),
    )

    formatted_history = None
    if request.history:
        formatted_history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.history
        ]

    # Fetch adaptive directive based on Scores, Answering Capacity, Enthusiasm, and Teacher Opinion
    guidance_meta: Dict[str, Any] = {
        "detected_subject": "General",
        "support_tier": "guided_support",
        "support_needed_score": 50.0,
        "adaptive_directive": "",
    }
    try:
        guidance_meta = get_or_create_student_directive(
            student_id=request.student_id,
            student_name=request.student_name,
            current_message=request.message,
        )
    except Exception as directive_err:
        logger.warning("[ANALYZER WARNING] Could not build student directive: %s", directive_err)

    reply = ""
    response_status = "success"

    try:
        try:
            reply = generate_tutor_reply(
                student_message=request.message,
                history=formatted_history,
                student_context=guidance_meta.get("adaptive_directive"),
            )
        except TypeError:
            # Backward-compatibility if generate_tutor_reply is mocked with old signature in unit tests
            reply = generate_tutor_reply(
                student_message=request.message,
                history=formatted_history,
            )
        logger.info("[AI SUCCESS] Generated reply for student_id=%s", request.student_id)

    except APITimeoutError as e:
        logger.error("[AI TIMEOUT] Model timed out for student %s: %s", request.student_id, e)
        reply = "I took a little too long thinking about that. Could you ask again or try rephrasing your question?"
        response_status = "fallback"

    except RateLimitError as e:
        logger.error("[AI RATE LIMIT] Rate limit hit from AI service: %s", e)
        reply = "A lot of students are studying right now! Please wait a moment and try asking again."
        response_status = "fallback"

    except APIConnectionError as e:
        logger.error("[AI CONNECTION ERROR] Failed connecting to AI service: %s", e)
        reply = "I'm having a little trouble connecting to my study resources. Please give me a moment and try again."
        response_status = "fallback"

    except Exception as e:
        logger.exception("[AI ERROR] Unexpected error in /chat endpoint: %s", e)
        reply = _generate_smart_pedagogical_reply(
            student_message=request.message,
            student_context=guidance_meta.get("adaptive_directive") if "guidance_meta" in locals() else None,
        )
        response_status = "fallback"

    # Log to Supabase (non-blocking: errors are caught and printed inside log_chat_interaction)
    try:
        log_chat_interaction(
            student_id=request.student_id,
            student_name=request.student_name,
            question=request.message,
            ai_response=reply,
        )
    except Exception as db_err:
        print(f"[DB Error] Unhandled error logging chat interaction: {db_err}")
        logger.error("[DB ERROR] Unhandled error logging chat interaction: %s", db_err)

    return ChatResponse(
        reply=reply,
        status=response_status,
        detected_subject=guidance_meta.get("detected_subject", "General"),
        support_tier=guidance_meta.get("support_tier", "guided_support"),
        support_needed_score=guidance_meta.get("support_needed_score", 50.0),
    )


@app.post("/scores", tags=["Admin & Analytics"])
async def add_student_score(request: ScoreCreateRequest):
    """
    Record a student's test/quiz/assignment score in Supabase (`student_scores`)
    and immediately update the student's 4-factor Socratic support profile.
    """
    if request.score > request.max_score:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="score cannot exceed max_score.")

    score_row = insert_student_score(
        student_id=request.student_id,
        student_name=request.student_name,
        subject=request.subject,
        topic=request.topic,
        score=request.score,
        max_score=request.max_score,
        assessment_type=request.assessment_type,
    )

    updated_profile = generate_student_report(
        student_id=request.student_id,
        student_name=request.student_name,
        use_ai=False,
    )

    return {
        "status": "success",
        "score_recorded": score_row,
        "updated_support_tier": updated_profile["support_tier"],
        "updated_support_needed_score": updated_profile["support_needed_score"],
        "overall_score_avg": updated_profile["overall_score_avg"],
    }


@app.post("/admin/feedback", tags=["Admin & Analytics"])
async def submit_teacher_feedback(request: TeacherFeedbackRequest):
    """
    Record the Teacher/Admin's opinion and support rating for a student in Supabase (`teacher_feedback`).
    Immediately recalculates the student's `support_needed_score`, `support_tier`, and `adaptive_directive`
    so the Socratic chatbot adjusts how much support it provides to the student.
    """
    feedback_row = insert_teacher_feedback(
        student_id=request.student_id,
        student_name=request.student_name,
        teacher_name=request.teacher_name,
        subject=request.subject,
        support_level=request.support_level,
        teacher_support_rating=request.teacher_support_rating,
        opinion_notes=request.opinion_notes,
    )

    updated_profile = generate_student_report(
        student_id=request.student_id,
        student_name=request.student_name,
        use_ai=False,
    )

    return {
        "status": "success",
        "teacher_feedback": feedback_row,
        "updated_support_tier": updated_profile["support_tier"],
        "updated_support_needed_score": updated_profile["support_needed_score"],
        "adaptive_directive": updated_profile["adaptive_directive"],
    }


@app.get("/admin/analysis/student/{student_id}", tags=["Admin & Analytics"])
async def get_admin_student_analysis(
    student_id: str,
    student_name: Optional[str] = Query(default=None, description="Optional student name if not yet in DB"),
    refresh_ai: bool = Query(default=True, description="Run live AI qualitative evaluation on Supabase logs"),
):
    """
    Teacher/Admin endpoint returning the comprehensive 4-factor analysis for a student:
    1. Academic Scores (`overall_score_avg` & `subject_breakdown`)
    2. Answering Capacity (`answering_capacity_score`, `capacity_level`, `hint_efficiency`)
    3. Subject Enthusiasm (`overall_enthusiasm_score`, `enthusiasm_level`, per-subject enthusiasm)
    4. Teacher Opinion & Support Allocation (`support_needed_score`, `support_tier`, `latest_teacher_opinion`)
    """
    report = generate_student_report(
        student_id=student_id,
        student_name=student_name,
        use_ai=refresh_ai,
    )
    return {
        "status": "success",
        "student_analysis": report,
    }


@app.get("/admin/analysis/class", tags=["Admin & Analytics"])
async def get_admin_class_analysis():
    """
    Teacher/Admin dashboard endpoint aggregating performance across all students in Supabase.
    Displays class averages, prioritized `students_needing_attention`, and individual summary cards.
    """
    overview = generate_admin_class_overview()
    return {
        "status": "success",
        "class_overview": overview,
    }


@app.get("/student/{student_id}/guidance", tags=["Student Progress"])
async def get_student_guidance_card(
    student_id: str,
    student_name: Optional[str] = Query(default=None, description="Optional student name"),
):
    """
    Student-facing progress & guidance endpoint.
    Shows the student their subject progress, strengths, focus topics, and personalized Socratic study tips.
    """
    report = generate_student_report(
        student_id=student_id,
        student_name=student_name,
        use_ai=False,
    )
    strengths_gaps = report.get("strengths_and_gaps") or {}
    return {
        "status": "success",
        "student_id": report["student_id"],
        "student_name": report["student_name"],
        "overall_score_avg": report["overall_score_avg"],
        "answering_capacity_score": report["answering_capacity_score"],
        "overall_enthusiasm_score": report["overall_enthusiasm_score"],
        "active_support_mode": report["support_tier"],
        "subject_breakdown": report["subject_breakdown"],
        "mastered_topics": strengths_gaps.get("mastered_topics", []),
        "focus_topics": strengths_gaps.get("misconceptions_and_gaps", []),
        "study_tips": strengths_gaps.get("student_guidance_tips", []),
    }


@app.get("/student/{student_id}/quiz", tags=["Student Progress"])
async def get_student_adaptive_quiz(
    student_id: str,
    student_name: Optional[str] = Query(default=None, description="Optional student name"),
    subject: Optional[str] = Query(default=None, description="Optional CBSE subject override"),
):
    """
    Generate a 3-question Socratic practice quiz tailored to the student's 4-factor profile
    (Scores, Answering Capacity, Enthusiasm, and Teacher Opinion) using a single AI call.
    """
    quiz_payload = generate_student_socratic_quiz(
        student_id=student_id,
        student_name=student_name,
        subject=subject,
        num_questions=3,
    )
    return {
        "status": "success",
        **quiz_payload,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)

