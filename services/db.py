import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

logger = logging.getLogger("ai_tutor_db")

_SUPABASE_CLIENT: Optional[Client] = None

PLACEHOLDER_URLS = {
    "",
    "your_supabase_url_here",
    "https://your-project-ref.supabase.co",
}
PLACEHOLDER_KEYS = {
    "",
    "your_supabase_service_role_key_here",
}

# Fail-safe in-memory store so local testing / hackathon demos still work
# even if a Supabase table hasn't been migrated yet or network is unreachable.
_MEMORY_CHAT_LOGS: List[Dict[str, Any]] = []
_MEMORY_SCORES: List[Dict[str, Any]] = []
_MEMORY_TEACHER_FEEDBACK: List[Dict[str, Any]] = []
_MEMORY_ANALYTICS: Dict[str, Dict[str, Any]] = {}


def get_supabase_client() -> Optional[Client]:
    """
    Initialize and return the Supabase client using SUPABASE_URL and SUPABASE_SERVICE_KEY.
    Returns None if credentials are not configured or are still placeholders.
    """
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    supabase_url = (os.getenv("SUPABASE_URL") or "").strip()
    supabase_key = (os.getenv("SUPABASE_SERVICE_KEY") or "").strip()

    if supabase_url in PLACEHOLDER_URLS or supabase_key in PLACEHOLDER_KEYS:
        return None

    _SUPABASE_CLIENT = create_client(supabase_url, supabase_key)
    return _SUPABASE_CLIENT


def log_chat_interaction(
    student_id: str,
    student_name: str,
    question: str,
    ai_response: str,
) -> bool:
    """
    Insert a chat interaction record into the Supabase `chat_logs` table.
    Guaranteed never to raise an exception so chat replies are never broken by DB issues.

    Columns inserted:
    - student_id
    - student_name
    - question
    - ai_response
    - created_at
    """
    row = {
        "student_id": student_id,
        "student_name": student_name,
        "question": question,
        "ai_response": ai_response,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEMORY_CHAT_LOGS.append(row)

    try:
        client = get_supabase_client()
        if client is None:
            msg = "[DB Warning] SUPABASE_URL or SUPABASE_SERVICE_KEY is not configured. Skipping chat_logs insert."
            print(msg)
            logger.warning(msg)
            return False

        client.table("chat_logs").insert(row).execute()
        logger.info("Logged chat interaction to Supabase for student_id=%s", student_id)
        return True

    except Exception as e:
        error_msg = f"[DB Error] Failed to insert chat log into Supabase: {e}"
        print(error_msg)
        logger.error(error_msg)
        return False


def get_student_chat_logs(student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch recent Socratic chat interactions for a student from the Supabase `chat_logs` table.
    Falls back to in-memory logs if Supabase is unconfigured or unreachable.
    """
    try:
        client = get_supabase_client()
        if client is not None:
            response = (
                client.table("chat_logs")
                .select("*")
                .eq("student_id", student_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            if response and getattr(response, "data", None) is not None:
                return list(response.data)
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching chat_logs from Supabase for %s: %s", student_id, e)

    matching = [row for row in _MEMORY_CHAT_LOGS if row.get("student_id") == student_id]
    return list(reversed(matching))[:limit]


def insert_student_score(
    student_id: str,
    student_name: str,
    subject: str,
    topic: str,
    score: float,
    max_score: float,
    assessment_type: str = "quiz",
) -> Dict[str, Any]:
    """
    Insert a student's academic score into the Supabase `student_scores` table.

    Columns inserted:
    - student_id
    - student_name
    - subject
    - topic
    - score
    - max_score
    - percentage
    - assessment_type
    - created_at
    """
    percentage = round((score / max_score) * 100.0, 2) if max_score > 0 else 0.0
    row = {
        "student_id": student_id,
        "student_name": student_name,
        "subject": subject,
        "topic": topic or "General",
        "score": float(score),
        "max_score": float(max_score),
        "percentage": percentage,
        "assessment_type": assessment_type or "quiz",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEMORY_SCORES.append(row)

    try:
        client = get_supabase_client()
        if client is not None:
            client.table("student_scores").insert(row).execute()
            logger.info("Logged score to Supabase `student_scores` for student_id=%s", student_id)
    except Exception as e:
        logger.warning("[DB Warning] Failed to insert score into Supabase `student_scores`: %s", e)

    return row


def get_student_scores(student_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all academic test/quiz scores for a student from the Supabase `student_scores` table.
    Ordered chronologically (oldest to newest) to calculate score improvement trends.
    """
    try:
        client = get_supabase_client()
        if client is not None:
            response = (
                client.table("student_scores")
                .select("*")
                .eq("student_id", student_id)
                .order("created_at", desc=False)
                .execute()
            )
            if response and getattr(response, "data", None) is not None:
                return list(response.data)
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching student_scores from Supabase for %s: %s", student_id, e)

    return [row for row in _MEMORY_SCORES if row.get("student_id") == student_id]


def insert_teacher_feedback(
    student_id: str,
    student_name: str,
    opinion_notes: str,
    support_level: str = "moderate_support",
    teacher_support_rating: float = 50.0,
    subject: str = "General",
    teacher_name: str = "Class Teacher",
) -> Dict[str, Any]:
    """
    Insert an admin/teacher's opinion and support rating for a student into
    the Supabase `teacher_feedback` table.

    Columns inserted:
    - student_id
    - student_name
    - teacher_name
    - subject
    - support_level ('high_support' | 'moderate_support' | 'independent_challenge')
    - teacher_support_rating (0-100)
    - opinion_notes
    - created_at
    """
    row = {
        "student_id": student_id,
        "student_name": student_name,
        "teacher_name": teacher_name or "Class Teacher",
        "subject": subject or "General",
        "support_level": support_level,
        "teacher_support_rating": round(float(teacher_support_rating), 2),
        "opinion_notes": opinion_notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEMORY_TEACHER_FEEDBACK.append(row)

    try:
        client = get_supabase_client()
        if client is not None:
            client.table("teacher_feedback").insert(row).execute()
            logger.info("Logged teacher feedback to Supabase `teacher_feedback` for student_id=%s", student_id)
    except Exception as e:
        logger.warning("[DB Warning] Failed to insert into Supabase `teacher_feedback`: %s", e)

    return row


def get_teacher_feedback(student_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve admin/teacher opinions for a student from the Supabase `teacher_feedback` table,
    ordered newest first.
    """
    try:
        client = get_supabase_client()
        if client is not None:
            response = (
                client.table("teacher_feedback")
                .select("*")
                .eq("student_id", student_id)
                .order("created_at", desc=True)
                .execute()
            )
            if response and getattr(response, "data", None) is not None:
                return list(response.data)
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching teacher_feedback from Supabase for %s: %s", student_id, e)

    matching = [row for row in _MEMORY_TEACHER_FEEDBACK if row.get("student_id") == student_id]
    return list(reversed(matching))


def upsert_student_analytics(student_id: str, analytics_row: Dict[str, Any]) -> bool:
    """
    Upsert a student's 4-factor analysis report into the Supabase `student_analytics` table.

    Columns upserted:
    - student_id
    - student_name
    - overall_score_avg
    - answering_capacity_score
    - overall_enthusiasm_score
    - support_needed_score
    - support_tier
    - capacity_level
    - enthusiasm_level
    - subject_breakdown
    - strengths_and_gaps
    - latest_teacher_opinion
    - adaptive_directive
    - teacher_summary
    - updated_at
    """
    payload = {
        "student_id": student_id,
        "student_name": analytics_row.get("student_name", "Student"),
        "overall_score_avg": analytics_row.get("overall_score_avg", 0.0),
        "answering_capacity_score": analytics_row.get("answering_capacity_score", 0.0),
        "overall_enthusiasm_score": analytics_row.get("overall_enthusiasm_score", 0.0),
        "support_needed_score": analytics_row.get("support_needed_score", 50.0),
        "support_tier": analytics_row.get("support_tier", "guided_support"),
        "capacity_level": analytics_row.get("capacity_level", "developing"),
        "enthusiasm_level": analytics_row.get("enthusiasm_level", "moderate"),
        "subject_breakdown": analytics_row.get("subject_breakdown", {}),
        "strengths_and_gaps": analytics_row.get("strengths_and_gaps", {}),
        "latest_teacher_opinion": analytics_row.get("latest_teacher_opinion", {}),
        "adaptive_directive": analytics_row.get("adaptive_directive", ""),
        "teacher_summary": analytics_row.get("teacher_summary", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _MEMORY_ANALYTICS[student_id] = payload

    try:
        client = get_supabase_client()
        if client is not None:
            client.table("student_analytics").upsert(payload, on_conflict="student_id").execute()
            logger.info("Upserted student_analytics in Supabase for student_id=%s", student_id)
            return True
    except Exception as e:
        logger.warning("[DB Warning] Failed to upsert student_analytics in Supabase for %s: %s", student_id, e)

    return False


def get_student_analytics(student_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest cached 4-factor analysis row for a student from Supabase `student_analytics`.
    Used by POST /chat to inject the student's adaptive Socratic directive and by the Teacher UI.
    """
    try:
        client = get_supabase_client()
        if client is not None:
            response = (
                client.table("student_analytics")
                .select("*")
                .eq("student_id", student_id)
                .limit(1)
                .execute()
            )
            if response and getattr(response, "data", None):
                row = response.data[0]
                _MEMORY_ANALYTICS[student_id] = row
                return row
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching student_analytics from Supabase for %s: %s", student_id, e)

    return _MEMORY_ANALYTICS.get(student_id)


def get_all_tracked_students() -> Dict[str, str]:
    """
    Discover all known students ({student_id: student_name}) across Supabase tables
    (`student_analytics`, `student_scores`, `teacher_feedback`, `chat_logs`)
    so the Teacher Class Dashboard can list and analyze the entire class.
    """
    students: Dict[str, str] = {}

    # Seed from memory first
    for row in _MEMORY_CHAT_LOGS + _MEMORY_SCORES + _MEMORY_TEACHER_FEEDBACK:
        sid = row.get("student_id")
        sname = row.get("student_name")
        if sid and sname:
            students[sid] = sname
    for sid, row in _MEMORY_ANALYTICS.items():
        if sid and row.get("student_name"):
            students[sid] = row["student_name"]

    try:
        client = get_supabase_client()
        if client is not None:
            for table_name in ("student_analytics", "student_scores", "teacher_feedback", "chat_logs"):
                try:
                    resp = (
                        client.table(table_name)
                        .select("student_id, student_name")
                        .limit(200)
                        .execute()
                    )
                    if resp and getattr(resp, "data", None):
                        for item in resp.data:
                            sid = item.get("student_id")
                            sname = item.get("student_name")
                            if sid and sname:
                                students[sid] = sname
                except Exception as table_err:
                    logger.debug("Skipping student discovery on table %s: %s", table_name, table_err)
    except Exception as e:
        logger.warning("[DB Warning] Error discovering students from Supabase: %s", e)

    return students
