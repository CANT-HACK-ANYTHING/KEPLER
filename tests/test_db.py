import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from main import app
from services.db import log_chat_interaction

client = TestClient(app)


def test_missing_credentials_graceful_skip():
    print("\n--- [Test 1] Missing Credentials Graceful Skip ---")
    with patch("services.db.get_supabase_client", return_value=None):
        result = log_chat_interaction(
            student_id="std_101",
            student_name="Aarav",
            question="What is Ohm's Law?",
            ai_response="Can you tell me how voltage and current relate in a circuit?",
        )
        assert result is False
        print("--> Passed: Gracefully skipped when credentials are not configured.")


def test_exact_column_insert():
    print("\n--- [Test 2] Verify Exact Column Insertion into chat_logs ---")
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_insert = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.insert.return_value = mock_insert

    with patch("services.db.get_supabase_client", return_value=mock_client):
        result = log_chat_interaction(
            student_id="std_102",
            student_name="Diya",
            question="Solve x^2 - 5x + 6 = 0",
            ai_response="What two numbers multiply to 6 and add to -5?",
        )
        assert result is True
        mock_client.table.assert_called_once_with("chat_logs")
        inserted_row = mock_table.insert.call_args[0][0]
        print("Inserted Row Payload:", inserted_row)
        expected_cols = {"student_id", "student_name", "question", "ai_response", "created_at"}
        assert set(inserted_row.keys()) == expected_cols
        assert inserted_row["student_id"] == "std_102"
        assert inserted_row["student_name"] == "Diya"
        assert inserted_row["question"] == "Solve x^2 - 5x + 6 = 0"
        assert inserted_row["ai_response"] == "What two numbers multiply to 6 and add to -5?"
        assert isinstance(inserted_row["created_at"], str) and len(inserted_row["created_at"]) > 10
        print("--> Passed: Exact 5 columns verified!")


def test_db_failure_does_not_break_chat_api():
    print("\n--- [Test 3] DB Exception Must NOT Break POST /chat ---")
    mock_client = MagicMock()
    mock_client.table.side_effect = RuntimeError("Simulated Supabase network outage!")

    with (
        patch("services.db.get_supabase_client", return_value=mock_client),
        patch("main.generate_tutor_reply", return_value="Hint: Think about how plants use sunlight! What pigment absorbs it?"),
    ):
        payload = {
            "student_id": "std_103",
            "student_name": "Rohan",
            "message": "Explain photosynthesis.",
        }
        response = client.post("/chat", json=payload)
        print("HTTP Status:", response.status_code)
        print("API Response:", response.json())
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "Hint:" in response.json()["reply"]
        print("--> Passed: Chat response succeeded even when Supabase threw an error!")


if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 3 - SUPABASE MEMORY & FAIL-SAFE LOGGING TEST SUITE")
    print("=" * 70)
    try:
        test_missing_credentials_graceful_skip()
        test_exact_column_insert()
        test_db_failure_does_not_break_chat_api()
        print("\n" + "=" * 70)
        print("ALL PHASE 3 DATABASE TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[X] Test failed: {e}")
        sys.exit(1)
