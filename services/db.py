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


def _resolve_student_name(client: Optional[Client], student_id: str) -> Optional[str]:
    """Look up student_name from `students` table or memory if given a numeric/string student_id."""
    for row in _MEMORY_CHAT_LOGS + _MEMORY_SCORES + _MEMORY_TEACHER_FEEDBACK:
        if str(row.get("student_id")) == str(student_id) and row.get("student_name"):
            return str(row["student_name"])
    if student_id in _MEMORY_ANALYTICS and _MEMORY_ANALYTICS[student_id].get("student_name"):
        return str(_MEMORY_ANALYTICS[student_id]["student_name"])

    if client is not None:
        try:
            res = client.table("students").select("id, name").eq("id", str(student_id)).limit(1).execute()
            if res and getattr(res, "data", None):
                return str(res.data[0].get("name"))
        except Exception:
            pass
    return None


def log_chat_interaction(
    student_id: str,
    student_name: str,
    question: str,
    ai_response: str,
) -> bool:
    """
    Insert a chat interaction record into the Supabase `chat_logs` table.
    Guaranteed never to raise an exception so chat replies are never broken by DB issues.
    Supports both the 5-column schema (`student_id`, `student_name`, `question`, `ai_response`, `created_at`)
    and the existing KEPLER schema (`student_name`, `question`, `response`, `timestamp`).
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    row = {
        "student_id": student_id,
        "student_name": student_name,
        "question": question,
        "ai_response": ai_response,
        "created_at": now_iso,
    }
    _MEMORY_CHAT_LOGS.append(row)

    try:
        client = get_supabase_client()
        if client is None:
            msg = "[DB Warning] SUPABASE_URL or SUPABASE_SERVICE_KEY is not configured. Skipping chat_logs insert."
            print(msg)
            logger.warning(msg)
            return False

        try:
            client.table("chat_logs").insert(row).execute()
        except Exception:
            # Fallback to KEPLER live schema: (student_name, question, response, timestamp)
            legacy_row = {
                "student_name": student_name,
                "question": question,
                "response": ai_response,
                "timestamp": now_iso,
            }
            client.table("chat_logs").insert(legacy_row).execute()

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
    Automatically normalizes columns (`response` -> `ai_response`, `timestamp` -> `created_at`)
    and matches by either `student_id` or `student_name`.
    """
    try:
        client = get_supabase_client()
        if client is not None:
            resolved_name = _resolve_student_name(client, student_id) or student_id
            resp = client.table("chat_logs").select("*").limit(200).execute()
            rows = (resp.data or []) if resp else []

            matched: List[Dict[str, Any]] = []
            for r in rows:
                r_sid = str(r.get("student_id") or "").strip()
                r_sname = str(r.get("student_name") or "").strip()
                if (
                    (r_sid and r_sid.lower() == str(student_id).strip().lower())
                    or (r_sname and r_sname.lower() == str(student_id).strip().lower())
                    or (r_sname and r_sname.lower() == str(resolved_name).strip().lower())
                ):
                    matched.append(
                        {
                            "id": r.get("id"),
                            "student_id": r_sid or student_id,
                            "student_name": r_sname or resolved_name,
                            "question": r.get("question") or "",
                            "ai_response": r.get("ai_response") or r.get("response") or "",
                            "created_at": r.get("created_at") or r.get("timestamp") or "",
                        }
                    )

            matched.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
            if matched:
                return matched[:limit]
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching chat_logs from Supabase for %s: %s", student_id, e)

    matching = [
        row
        for row in _MEMORY_CHAT_LOGS
        if str(row.get("student_id")).lower() == str(student_id).lower()
        or str(row.get("student_name")).lower() == str(student_id).lower()
    ]
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
    Retrieve all academic test/quiz scores for a student from Supabase.
    Checks:
    1. `student_scores` table
    2. `test_attempts` table (if present)
    3. `students` table baseline `score` and `weakness` (if present)
    """
    results: List[Dict[str, Any]] = []
    try:
        client = get_supabase_client()
        if client is not None:
            resolved_name = _resolve_student_name(client, student_id) or student_id

            # 1. Check student_scores table
            response = (
                client.table("student_scores")
                .select("*")
                .order("created_at", desc=False)
                .execute()
            )
            if response and getattr(response, "data", None):
                for r in response.data:
                    if (
                        str(r.get("student_id", "")).lower() == str(student_id).lower()
                        or str(r.get("student_name", "")).lower() == str(resolved_name).lower()
                    ):
                        results.append(r)

            # 2. Check test_attempts table if student_scores was empty
            if not results:
                try:
                    att_resp = client.table("test_attempts").select("*").eq("student_id", str(student_id)).execute()
                    if att_resp and getattr(att_resp, "data", None):
                        for att in att_resp.data:
                            sc = float(att.get("score") or 0.0)
                            tot = float(att.get("total_marks") or 100.0)
                            results.append(
                                {
                                    "student_id": str(student_id),
                                    "student_name": resolved_name,
                                    "subject": "General",
                                    "topic": str(att.get("test_id") or "Mock Test"),
                                    "score": sc,
                                    "max_score": tot,
                                    "percentage": round((sc / tot) * 100.0, 2) if tot > 0 else 0.0,
                                    "assessment_type": "mock_exam",
                                    "created_at": att.get("submitted_at") or "",
                                }
                            )
                except Exception:
                    pass

            # 3. Check `students` table baseline `score` if still empty
            if not results:
                try:
                    stu_resp = client.table("students").select("*").execute()
                    if stu_resp and getattr(stu_resp, "data", None):
                        for stu in stu_resp.data:
                            if (
                                str(stu.get("id", "")).lower() == str(student_id).lower()
                                or str(stu.get("name", "")).lower() == str(resolved_name).lower()
                            ):
                                if stu.get("score") is not None:
                                    sc = float(stu["score"])
                                    results.append(
                                        {
                                            "student_id": str(stu.get("id") or student_id),
                                            "student_name": str(stu.get("name") or resolved_name),
                                            "subject": "General",
                                            "topic": str(stu.get("target_exam") or "Overall Record"),
                                            "score": sc,
                                            "max_score": 100.0,
                                            "percentage": sc,
                                            "assessment_type": "overall",
                                            "created_at": stu.get("updated_at") or stu.get("created_at") or "",
                                        }
                                    )
                except Exception:
                    pass

            if results:
                return results
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching student_scores from Supabase for %s: %s", student_id, e)

    return [
        row
        for row in _MEMORY_SCORES
        if str(row.get("student_id")).lower() == str(student_id).lower()
        or str(row.get("student_name")).lower() == str(student_id).lower()
    ]


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
            resolved_name = _resolve_student_name(client, student_id) or student_id
            response = (
                client.table("teacher_feedback")
                .select("*")
                .order("created_at", desc=True)
                .execute()
            )
            if response and getattr(response, "data", None) is not None:
                matched = [
                    r
                    for r in response.data
                    if str(r.get("student_id", "")).lower() == str(student_id).lower()
                    or str(r.get("student_name", "")).lower() == str(resolved_name).lower()
                ]
                if matched:
                    return matched
    except Exception as e:
        logger.warning("[DB Warning] Failed fetching teacher_feedback from Supabase for %s: %s", student_id, e)

    matching = [
        row
        for row in _MEMORY_TEACHER_FEEDBACK
        if str(row.get("student_id")).lower() == str(student_id).lower()
        or str(row.get("student_name")).lower() == str(student_id).lower()
    ]
    return list(reversed(matching))


def upsert_student_analytics(student_id: str, analytics_row: Dict[str, Any]) -> bool:
    """
    Upsert a student's 4-factor analysis report into the Supabase `student_analytics` table.
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
    Discover all unique students ({student_id: student_name}) across Supabase tables
    (`students`, `student_analytics`, `student_scores`, `teacher_feedback`, `chat_logs`).
    """
    students: Dict[str, str] = {}
    name_to_id: Dict[str, str] = {}

    # Seed from memory first
    for row in _MEMORY_CHAT_LOGS + _MEMORY_SCORES + _MEMORY_TEACHER_FEEDBACK:
        sid = row.get("student_id")
        sname = row.get("student_name")
        if sid and sname:
            students[str(sid)] = str(sname)
            name_to_id[str(sname).strip().lower()] = str(sid)
    for sid, row in _MEMORY_ANALYTICS.items():
        if sid and row.get("student_name"):
            students[str(sid)] = str(row["student_name"])
            name_to_id[str(row["student_name"]).strip().lower()] = str(sid)

    try:
        client = get_supabase_client()
        if client is not None:
            # 1. Read canonical `students` table first so we map student names to their IDs
            try:
                stu_resp = client.table("students").select("*").limit(500).execute()
                if stu_resp and getattr(stu_resp, "data", None):
                    for item in stu_resp.data:
                        sid = item.get("id") or item.get("student_id")
                        sname = item.get("name") or item.get("student_name")
                        if sid is not None and sname:
                            students[str(sid)] = str(sname)
                            name_to_id[str(sname).strip().lower()] = str(sid)
            except Exception:
                pass

            # 2. Read analytics, scores, feedback, and chat_logs
            for table_name in ("student_analytics", "student_scores", "teacher_feedback", "chat_logs"):
                try:
                    resp = client.table(table_name).select("*").limit(500).execute()
                    if resp and getattr(resp, "data", None):
                        for item in resp.data:
                            sname = item.get("student_name") or item.get("name")
                            sid = item.get("student_id")
                            if not sid and sname:
                                # In `chat_logs`, only `student_name` exists; map to canonical ID or use name Slug
                                sid = name_to_id.get(str(sname).strip().lower()) or str(sname).strip()
                            if sid is not None and sname:
                                if str(sname).strip().lower() not in name_to_id:
                                    students[str(sid)] = str(sname)
                                    name_to_id[str(sname).strip().lower()] = str(sid)
                except Exception as table_err:
                    logger.debug("Skipping student discovery on table %s: %s", table_name, table_err)
    except Exception as e:
        logger.warning("[DB Warning] Error discovering students from Supabase: %s", e)

    return students
