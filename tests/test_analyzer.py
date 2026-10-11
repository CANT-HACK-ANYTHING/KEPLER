import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from main import app
from services.analyzer import detect_subject

client = TestClient(app)


def test_subject_detection():
    print("\n--- [Test 1] Subject Detection ---")
    assert detect_subject("How do I solve quadratic equation x^2 - 5x + 6 = 0?") == "Mathematics"
    assert detect_subject("Explain Ohm's law and electric circuit resistance.") == "Science"
    assert detect_subject("What was the role of Mahatma Gandhi in Nationalism in India?") == "Social Science"
    print("--> Passed: Subject detection accurately maps CBSE Class 10 topics.")


def test_scores_and_teacher_opinion_drive_support_level():
    print("\n--- [Test 2] 4-Factor Analysis: Scores + Chat + Teacher Opinion -> Support Tier ---")
    student_id = "std_analyzer_201"
    student_name = "Riya"

    # 1. Teacher records a low Mathematics quiz score (8/20 = 40%)
    score_resp = client.post(
        "/scores",
        json={
            "student_id": student_id,
            "student_name": student_name,
            "subject": "Mathematics",
            "topic": "Quadratic Equations",
            "score": 8,
            "max_score": 20,
            "assessment_type": "quiz",
        },
    )
    assert score_resp.status_code == 200
    score_data = score_resp.json()
    assert score_data["overall_score_avg"] == 40.0
    print("Recorded Score Avg:", score_data["overall_score_avg"])

    # 2. Teacher submits an Admin Opinion requesting high support
    feedback_resp = client.post(
        "/admin/feedback",
        json={
            "student_id": student_id,
            "student_name": student_name,
            "teacher_name": "Mrs. Sharma",
            "subject": "Mathematics",
            "support_level": "high_support",
            "teacher_support_rating": 85.0,
            "opinion_notes": "Riya gets overwhelmed by algebra symbols; break factoring into tiny steps with number examples.",
        },
    )
    assert feedback_resp.status_code == 200
    fb_data = feedback_resp.json()
    print("Updated Support Tier:", fb_data["updated_support_tier"])
    print("Updated Support Needed Score:", fb_data["updated_support_needed_score"])
    assert fb_data["updated_support_tier"] == "intensive_scaffolding"
    assert fb_data["updated_support_needed_score"] >= 70.0
    assert "Riya gets overwhelmed by algebra symbols" in fb_data["adaptive_directive"]
    print("--> Passed: Teacher opinion & low score elevated support tier to 'intensive_scaffolding'!")


def test_adaptive_chat_uses_student_directive():
    print("\n--- [Test 3] POST /chat Injects 4-Factor Adaptive Directive into Socratic Model ---")
    captured_context = {}

    def fake_tutor_reply(student_message, history=None, model=None, student_context=None):
        captured_context["student_context"] = student_context
        return "Let's take a tiny step together! Can you tell me what 2 times 3 equals?"

    with patch("main.generate_tutor_reply", side_effect=fake_tutor_reply):
        chat_resp = client.post(
            "/chat",
            json={
                "student_id": "std_analyzer_201",
                "student_name": "Riya",
                "message": "I don't understand how to factor x^2 + 5x + 6 = 0",
            },
        )
        assert chat_resp.status_code == 200
        body = chat_resp.json()
        print("Chat Response:", body)
        assert body["status"] == "success"
        assert body["detected_subject"] == "Mathematics"
        assert body["support_tier"] == "intensive_scaffolding"
        assert "HIGH SUPPORT MODE" in (captured_context.get("student_context") or "")
        assert "Riya gets overwhelmed by algebra symbols" in (captured_context.get("student_context") or "")
        print("--> Passed: POST /chat injected the 4-factor adaptive directive into the Socratic tutor!")


def test_admin_and_student_dashboard_endpoints():
    print("\n--- [Test 4] Admin Student Report, Class Overview & Student Guidance Endpoints ---")
    # Admin single-student report
    admin_resp = client.get("/admin/analysis/student/std_analyzer_201?refresh_ai=false")
    assert admin_resp.status_code == 200
    report = admin_resp.json()["student_analysis"]
    assert report["student_id"] == "std_analyzer_201"
    assert report["support_tier"] == "intensive_scaffolding"
    assert "Mathematics" in report["subject_breakdown"]

    # Admin class-wide overview
    class_resp = client.get("/admin/analysis/class")
    assert class_resp.status_code == 200
    overview = class_resp.json()["class_overview"]
    assert overview["total_students"] >= 1
    assert any(s["student_id"] == "std_analyzer_201" for s in overview["students_needing_attention"])

    # Student-facing guidance card
    student_resp = client.get("/student/std_analyzer_201/guidance")
    assert student_resp.status_code == 200
    guidance = student_resp.json()
    assert guidance["active_support_mode"] == "intensive_scaffolding"
    assert len(guidance["study_tips"]) >= 1
    print("--> Passed: Admin and Student analytics endpoints returned complete 4-factor payloads!")


if __name__ == "__main__":
    print("=" * 70)
    print("PHASE 4 - 4-FACTOR STUDENT ANALYZER & ADAPTIVE GUIDANCE TEST SUITE")
    print("=" * 70)
    try:
        test_subject_detection()
        test_scores_and_teacher_opinion_drive_support_level()
        test_adaptive_chat_uses_student_directive()
        test_admin_and_student_dashboard_endpoints()
        print("\n" + "=" * 70)
        print("ALL PHASE 4 ANALYZER & ADAPTIVE SOCRATIC TESTS PASSED SUCCESSFULLY!")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n[X] Test failed: {e}")
        sys.exit(1)
