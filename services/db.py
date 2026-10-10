import logging
import os
from datetime import datetime, timezone
from typing import Optional
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
    try:
        client = get_supabase_client()
        if client is None:
            msg = "[DB Warning] SUPABASE_URL or SUPABASE_SERVICE_KEY is not configured. Skipping chat_logs insert."
            print(msg)
            logger.warning(msg)
            return False

        row = {
            "student_id": student_id,
            "student_name": student_name,
            "question": question,
            "ai_response": ai_response,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        client.table("chat_logs").insert(row).execute()
        logger.info("Logged chat interaction to Supabase for student_id=%s", student_id)
        return True

    except Exception as e:
        error_msg = f"[DB Error] Failed to insert chat log into Supabase: {e}"
        print(error_msg)
        logger.error(error_msg)
        return False
