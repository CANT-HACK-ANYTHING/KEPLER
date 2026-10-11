import json
import logging
import re
from typing import Any, Dict, List, Optional

from services.ai import generate_analysis_completion, generate_socratic_quiz_completion
from services.db import (
    get_all_tracked_students,
    get_student_analytics,
    get_student_chat_logs,
    get_student_scores,
    get_teacher_feedback,
    upsert_student_analytics,
)

logger = logging.getLogger("ai_student_analyzer")

CBSE_SUBJECTS = ["Mathematics", "Science", "Social Science", "English", "Hindi"]

SUBJECT_KEYWORDS: Dict[str, List[str]] = {
    "Mathematics": [
        "math", "maths", "quadratic", "equation", "polynomial", "triangle", "trigonometry",
        "sine", "cosine", "tangent", "arithmetic progression", "circle", "probability", "statistics",
        "coordinate", "surface area", "volume", "real number", "hcf", "lcm", "x^2", "solve",
        "factor", "hypotenuse", "pythagoras", "linear", "algebra",
    ],
    "Science": [
        "science", "physics", "chemistry", "biology", "newton", "force", "motion", "inertia",
        "velocity", "acceleration", "gravity", "ohm", "current", "voltage", "resistor",
        "circuit", "light", "lens", "mirror", "refraction", "reflection", "carbon", "atom",
        "electron", "acid", "base", "salt", "ph", "metal", "non-metal", "photosynthesis",
        "respiration", "heart", "nephron", "heredity", "evolution", "magnetic", "chemical",
        "reaction", "periodic", "life process",
    ],
    "Social Science": [
        "history", "geography", "civics", "political science", "economics", "nationalism",
        "gandhi", "europe", "french revolution", "rowlatt", "satyagraha", "resource", "soil",
        "agriculture", "mineral", "manufacturing", "power sharing", "federalism", "democracy",
        "gdp", "reserve bank", "rbi", "globalisation", "sector", "credit",
    ],
    "English": [
        "english", "grammar", "tense", "poem", "poet", "stanza", "metaphor", "simile",
        "lencho", "nelson mandela", "anne frank", "footprints", "first flight", "letter writing",
        "analytical paragraph", "active voice", "passive voice", "reported speech",
    ],
    "Hindi": [
        "hindi", "vyakaran", "samas", "alankar", "padbandh", "muhavare", "kabir", "surdas",
        "premchand", "sparsh", "sanchayan", "kshitij", "kritika", "patra lekhan",
    ],
}


def detect_subject(text: str) -> str:
    """
    Detect the most likely Class 10 CBSE subject from a question, topic, or message.
    Returns one of CBSE_SUBJECTS or 'General'.
    """
    if not text:
        return "General"
    lowered = text.lower()

    # Direct subject name match first
    for subj in CBSE_SUBJECTS:
        if re.search(rf"\b{re.escape(subj.lower())}\b", lowered):
            return subj

    best_subject = "General"
    best_hits = 0
    for subj, keywords in SUBJECT_KEYWORDS.items():
        hits = sum(
            1
            for kw in keywords
            if (kw in lowered if "^" in kw else re.search(rf"\b{re.escape(kw)}\b", lowered) is not None)
        )
        if hits > best_hits:
            best_hits = hits
            best_subject = subj

    return best_subject


def normalize_subject_name(subject: str) -> str:
    """Normalize subject aliases (e.g. 'Maths' -> 'Mathematics', 'Physics' -> 'Science')."""
    if not subject:
        return "General"
    s = subject.strip().lower()
    if s in ("math", "maths", "mathematics"):
        return "Mathematics"
    if s in ("science", "physics", "chemistry", "biology"):
        return "Science"
    if s in ("social science", "sst", "history", "geography", "civics", "economics", "political science"):
        return "Social Science"
    if s in ("english", "eng"):
        return "English"
    if s in ("hindi", "hin"):
        return "Hindi"
    return detect_subject(subject)


def analyze_scores(student_id: str, raw_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Factor 1: Quantitative Academic Score Analysis from Supabase `student_scores`.
    Calculates overall average (0-100), subject averages, score trend, and weak/strong topics.
    """
    subject_totals: Dict[str, List[float]] = {subj: [] for subj in CBSE_SUBJECTS}
    all_percentages: List[float] = []
    weak_topics: List[str] = []
    strong_topics: List[str] = []

    for row in raw_scores:
        score = float(row.get("score", 0.0))
        max_score = float(row.get("max_score", 100.0))
        pct = float(row.get("percentage", (score / max_score * 100.0) if max_score > 0 else 0.0))
        pct = max(0.0, min(100.0, round(pct, 2)))
        all_percentages.append(pct)

        subj = normalize_subject_name(str(row.get("subject", "General")))
        if subj in subject_totals:
            subject_totals[subj].append(pct)

        topic = str(row.get("topic") or "General").strip()
        label = f"{subj}: {topic}" if topic and topic != "General" else subj
        if pct < 60.0 and label not in weak_topics:
            weak_topics.append(label)
        elif pct >= 75.0 and label not in strong_topics:
            strong_topics.append(label)

    overall_avg = round(sum(all_percentages) / len(all_percentages), 2) if all_percentages else 0.0

    subject_averages: Dict[str, Optional[float]] = {}
    for subj, vals in subject_totals.items():
        subject_averages[subj] = round(sum(vals) / len(vals), 2) if vals else None

    # Compute score trend comparing first half vs second half of assessments
    if len(all_percentages) >= 2:
        mid = len(all_percentages) // 2
        first_half = sum(all_percentages[:mid]) / max(1, len(all_percentages[:mid]))
        second_half = sum(all_percentages[mid:]) / max(1, len(all_percentages[mid:]))
        diff = second_half - first_half
        if diff >= 5.0:
            trend = "improving"
        elif diff <= -5.0:
            trend = "declining"
        else:
            trend = "stable"
    elif len(all_percentages) == 1:
        trend = "stable"
    else:
        trend = "no_scores_yet"

    scored_subjects = {k: v for k, v in subject_averages.items() if v is not None}
    strongest_subject = max(scored_subjects, key=scored_subjects.get) if scored_subjects else None
    weakest_subject = min(scored_subjects, key=scored_subjects.get) if scored_subjects else None

    return {
        "student_id": student_id,
        "has_scores": len(all_percentages) > 0,
        "assessments_count": len(all_percentages),
        "overall_score_avg": overall_avg,
        "score_trend": trend,
        "subject_averages": subject_averages,
        "strongest_subject": strongest_subject,
        "weakest_subject": weakest_subject,
        "strong_topics": strong_topics[:5],
        "weak_topics": weak_topics[:5],
    }


def evaluate_answering_capacity(
    chat_logs: List[Dict[str, Any]],
    ai_eval: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Factor 2: Cognitive Answering Capacity Evaluation from Supabase `chat_logs`.
    Measures how effectively the student engages with Socratic hints, reasoning depth,
    and whether they attempt intermediate steps or ask for direct answers.
    """
    if not chat_logs and not ai_eval:
        return {
            "answering_capacity_score": 50.0,
            "capacity_level": "developing",
            "hint_efficiency": "No Socratic chat sessions recorded yet; baseline scaffolding active.",
            "reasoning_depth": "developing",
        }

    # Heuristic baseline from chat_logs
    reasoning_markers = (
        "because", "since", "therefore", "i think", "so ", "equals", "=", "+", "-", "*", "/",
        "formula", "step", "if ", "then", "multiply", "divide", "electrons", "valence",
    )
    shortcut_markers = (
        "just give me the answer", "tell me the answer", "idk", "i don't know", "solve it for me",
        "write the essay", "give full answer",
    )

    reasoning_hits = 0
    shortcut_hits = 0
    substantial_turns = 0

    for row in chat_logs:
        q = str(row.get("question", "")).strip().lower()
        if len(q.split()) >= 5:
            substantial_turns += 1
        if any(m in q for m in reasoning_markers):
            reasoning_hits += 1
        if any(m in q for m in shortcut_markers):
            shortcut_hits += 1

    total = max(1, len(chat_logs))
    heuristic_score = 55.0 + (reasoning_hits / total) * 30.0 + (substantial_turns / total) * 15.0 - (shortcut_hits / total) * 30.0
    heuristic_score = max(15.0, min(98.0, round(heuristic_score, 2)))

    # Blend with AI evaluation if available
    if ai_eval and isinstance(ai_eval.get("answering_capacity_score"), (int, float)):
        ai_score = float(ai_eval["answering_capacity_score"])
        final_score = round(0.65 * ai_score + 0.35 * heuristic_score, 2)
    else:
        final_score = heuristic_score

    final_score = max(0.0, min(100.0, final_score))

    if final_score >= 75.0:
        level = "strong"
        default_depth = "strong_conceptual"
        default_hint = "Connects Socratic hints quickly and demonstrates solid step-by-step reasoning."
    elif final_score >= 45.0:
        level = "developing"
        default_depth = "developing"
        default_hint = "Responds to Socratic prompts but benefits from intermediate step verification."
    else:
        level = "needs_attention"
        default_depth = "surface_guessing"
        default_hint = "Frequently gets stuck on multi-step prompts and needs smaller micro-hints."

    return {
        "answering_capacity_score": final_score,
        "capacity_level": str(ai_eval.get("capacity_level") if ai_eval and ai_eval.get("capacity_level") in ("strong", "developing", "needs_attention") else level),
        "hint_efficiency": str(ai_eval.get("hint_efficiency") if ai_eval and ai_eval.get("hint_efficiency") else default_hint),
        "reasoning_depth": str(ai_eval.get("reasoning_depth") if ai_eval and ai_eval.get("reasoning_depth") in ("strong_conceptual", "developing", "surface_guessing") else default_depth),
    }


def evaluate_subject_enthusiasm(
    chat_logs: List[Dict[str, Any]],
    ai_eval: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Factor 3: Subject Enthusiasm Evaluation from Supabase `chat_logs`.
    Measures curiosity, interaction frequency per subject, and persistence.
    """
    subject_counts: Dict[str, int] = {subj: 0 for subj in CBSE_SUBJECTS}
    curiosity_markers = ("why", "how", "what happens if", "can we", "interesting", "understand", "explain", "example", "?")

    curiosity_hits = 0
    for row in chat_logs:
        q = str(row.get("question", "")).strip()
        subj = detect_subject(q)
        if subj in subject_counts:
            subject_counts[subj] += 1
        if any(m in q.lower() for m in curiosity_markers):
            curiosity_hits += 1

    total_msgs = len(chat_logs)
    subject_enthusiasm: Dict[str, float] = {}
    ai_subj_map = (ai_eval or {}).get("subject_enthusiasm") or {}

    for subj in CBSE_SUBJECTS:
        count = subject_counts[subj]
        if total_msgs == 0:
            base = 50.0
        else:
            share = count / total_msgs
            # Active questions in a subject boost its enthusiasm score
            base = min(95.0, 45.0 + count * 12.0 + share * 25.0) if count > 0 else 40.0

        if isinstance(ai_subj_map, dict) and isinstance(ai_subj_map.get(subj), (int, float)):
            blended = round(0.6 * float(ai_subj_map[subj]) + 0.4 * base, 2)
        else:
            blended = round(base, 2)
        subject_enthusiasm[subj] = max(0.0, min(100.0, blended))

    if total_msgs == 0 and not ai_eval:
        overall_enthusiasm = 50.0
    else:
        curiosity_ratio = curiosity_hits / max(1, total_msgs)
        volume_bonus = min(25.0, total_msgs * 4.0)
        heuristic_overall = min(96.0, 45.0 + curiosity_ratio * 25.0 + volume_bonus)
        if ai_eval and isinstance(ai_eval.get("overall_enthusiasm_score"), (int, float)):
            overall_enthusiasm = round(0.65 * float(ai_eval["overall_enthusiasm_score"]) + 0.35 * heuristic_overall, 2)
        else:
            overall_enthusiasm = round(heuristic_overall, 2)

    overall_enthusiasm = max(0.0, min(100.0, overall_enthusiasm))

    if overall_enthusiasm >= 72.0:
        enth_level = "high_curiosity"
    elif overall_enthusiasm >= 45.0:
        enth_level = "moderate"
    else:
        enth_level = "low_enthusiasm"

    favorite_subject = max(subject_enthusiasm, key=subject_enthusiasm.get) if any(subject_counts.values()) else None

    return {
        "overall_enthusiasm_score": overall_enthusiasm,
        "enthusiasm_level": enth_level,
        "subject_enthusiasm": subject_enthusiasm,
        "subject_question_counts": subject_counts,
        "favorite_subject": favorite_subject,
    }


def evaluate_teacher_opinion(feedback_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Factor 4: Admin / Teacher Opinion & Support Directive from Supabase `teacher_feedback`.
    Extracts the teacher's explicit support level, numeric support rating (0-100),
    and classroom observation notes.
    """
    if not feedback_rows:
        return {
            "has_teacher_feedback": False,
            "teacher_name": None,
            "support_level": "moderate_support",
            "teacher_support_rating": 50.0,
            "subject": "General",
            "opinion_notes": "No specific teacher observations recorded yet; using balanced Socratic guidance.",
            "feedback_count": 0,
        }

    latest = feedback_rows[0]
    raw_level = str(latest.get("support_level", "moderate_support")).strip().lower()
    if raw_level not in ("high_support", "moderate_support", "independent_challenge"):
        raw_level = "moderate_support"

    rating = float(latest.get("teacher_support_rating", 50.0))
    rating = max(0.0, min(100.0, round(rating, 2)))

    return {
        "has_teacher_feedback": True,
        "teacher_name": str(latest.get("teacher_name", "Class Teacher")),
        "support_level": raw_level,
        "teacher_support_rating": rating,
        "subject": normalize_subject_name(str(latest.get("subject", "General"))),
        "opinion_notes": str(latest.get("opinion_notes", "")).strip(),
        "feedback_count": len(feedback_rows),
        "created_at": latest.get("created_at"),
    }


def calculate_support_allocation(
    scores_data: Dict[str, Any],
    capacity_data: Dict[str, Any],
    enthusiasm_data: Dict[str, Any],
    teacher_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Synthesize all 4 factors (Scores, Answering Capacity, Enthusiasm, and Teacher Opinion)
    to determine how much support needs to be provided to the student by the Socratic chatbot.

    Returns:
    - support_needed_score (0-100: higher means more step-by-step scaffolding required)
    - support_tier ('intensive_scaffolding' | 'guided_support' | 'independent_challenge')
    - support_rationale (human-readable explanation for the teacher & student UI)
    """
    score_avg = float(scores_data.get("overall_score_avg", 65.0)) if scores_data.get("has_scores") else 65.0
    capacity_score = float(capacity_data.get("answering_capacity_score", 50.0))
    enthusiasm_score = float(enthusiasm_data.get("overall_enthusiasm_score", 50.0))
    teacher_rating = float(teacher_data.get("teacher_support_rating", 50.0))
    teacher_level = teacher_data.get("support_level", "moderate_support")

    # 4-factor weighted formula:
    # 30% Academic Score gap + 25% Answering Capacity gap + 15% Enthusiasm gap + 30% Teacher Support Rating
    support_needed = (
        0.30 * (100.0 - score_avg)
        + 0.25 * (100.0 - capacity_score)
        + 0.15 * (100.0 - enthusiasm_score)
        + 0.30 * teacher_rating
    )
    support_needed = max(0.0, min(100.0, round(support_needed, 2)))

    # Respect explicit teacher override while reflecting composite score
    if teacher_data.get("has_teacher_feedback") and teacher_level == "high_support":
        support_needed = max(support_needed, 70.0)
        support_tier = "intensive_scaffolding"
    elif teacher_data.get("has_teacher_feedback") and teacher_level == "independent_challenge" and score_avg >= 70.0:
        support_needed = min(support_needed, 32.0)
        support_tier = "independent_challenge"
    else:
        if support_needed >= 62.0:
            support_tier = "intensive_scaffolding"
        elif support_needed >= 36.0:
            support_tier = "guided_support"
        else:
            support_tier = "independent_challenge"

    reasons: List[str] = []
    if scores_data.get("has_scores"):
        reasons.append(f"academic average is {score_avg:.1f}% ({scores_data.get('score_trend', 'stable')})")
    if capacity_data.get("capacity_level") == "needs_attention":
        reasons.append("needs extra Socratic micro-hints to connect concepts")
    elif capacity_data.get("capacity_level") == "strong":
        reasons.append("demonstrates strong conceptual reasoning in chat")
    if teacher_data.get("has_teacher_feedback"):
        reasons.append(
            f"teacher requested '{teacher_level}' ({teacher_rating:.0f}/100 support rating)"
        )

    rationale = (
        f"Assigned '{support_tier}' (Support Needed: {support_needed:.1f}/100) because "
        + (", ".join(reasons) if reasons else "baseline Socratic profile is active")
        + "."
    )

    return {
        "support_needed_score": support_needed,
        "support_tier": support_tier,
        "support_rationale": rationale,
    }


def build_adaptive_tutor_directive(
    student_analysis: Dict[str, Any],
    current_subject: Optional[str] = None,
) -> str:
    """
    Build the dynamic student guidance block injected into `generate_tutor_reply()`
    during `POST /chat`. Adapts the Socratic tutor's hint depth, tone, and pacing
    while preserving strict Socratic rules (never giving direct answers).
    """
    if not student_analysis:
        return ""

    support_tier = student_analysis.get("support_tier", "guided_support")
    support_score = student_analysis.get("support_needed_score", 50.0)
    capacity_level = student_analysis.get("capacity_level", "developing")
    enthusiasm_level = student_analysis.get("enthusiasm_level", "moderate")
    teacher_opinion = student_analysis.get("latest_teacher_opinion") or {}
    teacher_notes = str(teacher_opinion.get("opinion_notes", "")).strip()

    if support_tier == "intensive_scaffolding":
        pacing_instruction = (
            "HIGH SUPPORT MODE (Intensive Scaffolding): Break the concept down into very small, beginner-friendly "
            "micro-steps. Use a warm, reassuring tone and a simple real-life analogy before asking your single guiding question."
        )
    elif support_tier == "independent_challenge":
        pacing_instruction = (
            "CHALLENGE MODE (Independent Socratic Stretch): The student has strong mastery. Give minimal hand-holding "
            "and ask a deeper, Higher-Order Thinking Skills (HOTS) 'why' or 'how' question to stretch their reasoning."
        )
    else:
        pacing_instruction = (
            "GUIDED SUPPORT MODE (Balanced Socratic Pacing): Guide the student with clear intermediate hints and "
            "verify their understanding one step at a time."
        )

    enthusiasm_instruction = ""
    if enthusiasm_level == "low_enthusiasm":
        enthusiasm_instruction = (
            " Enthusiastic Spark: The student has shown low enthusiasm recently—start with an encouraging hook or "
            "curious real-world connection to make the topic exciting."
        )

    teacher_instruction = ""
    if teacher_opinion.get("has_teacher_feedback") and teacher_notes:
        teacher_instruction = f"\n- Teacher's Classroom Directive: \"{teacher_notes}\""

    subject_note = f" (Current Subject: {current_subject})" if current_subject and current_subject != "General" else ""

    return (
        f"ADAPTIVE STUDENT GUIDANCE PROFILE{subject_note}:\n"
        f"- Support Allocation: {support_tier} (Support Needed: {support_score}/100 | Answering Capacity: {capacity_level} | Enthusiasm: {enthusiasm_level})\n"
        f"- Pedagogical Adjustment: {pacing_instruction}{enthusiasm_instruction}"
        f"{teacher_instruction}\n"
        f"- Reminder: Strictly maintain the Socratic method (2-4 short sentences, ask ONLY ONE question, NEVER give the final answer directly)."
    )


def _extract_json_dict(raw_text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON from LLM output even if wrapped in markdown code fences."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def generate_student_report(
    student_id: str,
    student_name: Optional[str] = None,
    use_ai: bool = True,
) -> Dict[str, Any]:
    """
    Master orchestrator:
    1. Pulls `student_scores`, `chat_logs`, and `teacher_feedback` from Supabase.
    2. Runs quantitative + AI qualitative analysis across all 4 factors.
    3. Computes the Socratic Support Needed score, Support Tier, and Adaptive Directive.
    4. Saves the synthesized report to Supabase `student_analytics` and returns it.
    """
    raw_scores = get_student_scores(student_id)
    chat_logs = get_student_chat_logs(student_id, limit=50)
    feedback_rows = get_teacher_feedback(student_id)

    # Infer student_name from available Supabase records if not explicitly passed
    resolved_name = student_name
    if not resolved_name:
        for collection in (feedback_rows, raw_scores, chat_logs):
            if collection and collection[0].get("student_name"):
                resolved_name = str(collection[0]["student_name"])
                break
    resolved_name = resolved_name or f"Student {student_id}"

    scores_data = analyze_scores(student_id, raw_scores)
    teacher_data = evaluate_teacher_opinion(feedback_rows)

    ai_eval: Optional[Dict[str, Any]] = None
    if use_ai and (raw_scores or chat_logs or feedback_rows):
        try:
            prompt_payload = json.dumps(
                {
                    "student_id": student_id,
                    "student_name": resolved_name,
                    "scores_summary": scores_data,
                    "recent_chat_logs": [
                        {
                            "question": row.get("question"),
                            "ai_response": row.get("ai_response"),
                        }
                        for row in chat_logs[:15]
                    ],
                    "teacher_feedback": teacher_data,
                },
                ensure_ascii=False,
            )
            raw_ai_output = generate_analysis_completion(prompt_payload)
            ai_eval = _extract_json_dict(raw_ai_output)
        except Exception as err:
            logger.warning("AI qualitative analysis skipped/fell back to heuristics for %s: %s", student_id, err)

    capacity_data = evaluate_answering_capacity(chat_logs, ai_eval=ai_eval)
    enthusiasm_data = evaluate_subject_enthusiasm(chat_logs, ai_eval=ai_eval)
    support_data = calculate_support_allocation(scores_data, capacity_data, enthusiasm_data, teacher_data)

    # Build per-subject breakdown for frontend radar/bar charts
    subject_breakdown: Dict[str, Dict[str, Any]] = {}
    for subj in CBSE_SUBJECTS:
        subj_score = scores_data["subject_averages"].get(subj)
        subj_enth = enthusiasm_data["subject_enthusiasm"].get(subj, 50.0)
        subj_q_count = enthusiasm_data["subject_question_counts"].get(subj, 0)
        subject_breakdown[subj] = {
            "score_average": subj_score,
            "enthusiasm_score": subj_enth,
            "questions_asked": subj_q_count,
            "status": (
                "needs_attention"
                if (subj_score is not None and subj_score < 60.0)
                else ("strong" if (subj_score is not None and subj_score >= 75.0) else "developing")
            ),
        }

    mastered_topics = (
        (ai_eval.get("mastered_topics") if ai_eval and isinstance(ai_eval.get("mastered_topics"), list) else None)
        or scores_data["strong_topics"]
        or ([f"{scores_data['strongest_subject']} foundations"] if scores_data.get("strongest_subject") else [])
    )
    gaps = (
        (ai_eval.get("misconceptions_and_gaps") if ai_eval and isinstance(ai_eval.get("misconceptions_and_gaps"), list) else None)
        or scores_data["weak_topics"]
        or ([f"{scores_data['weakest_subject']} practice"] if scores_data.get("weakest_subject") else [])
    )

    student_tips = (
        ai_eval.get("student_guidance_tips")
        if ai_eval and isinstance(ai_eval.get("student_guidance_tips"), list) and ai_eval.get("student_guidance_tips")
        else [
            "Try explaining your intermediate step in your own words when answering the Socratic tutor's question.",
            f"Spend 15 minutes reviewing {gaps[0] if gaps else 'your recent class notes'} and ask the tutor for a step-by-step practice problem.",
        ]
    )

    default_teacher_summary = (
        f"{resolved_name} has an academic score average of {scores_data['overall_score_avg']:.1f}% ({scores_data['score_trend']}), "
        f"an answering capacity of {capacity_data['answering_capacity_score']:.1f}/100 ({capacity_data['capacity_level']}), "
        f"and an enthusiasm rating of {enthusiasm_data['overall_enthusiasm_score']:.1f}/100 ({enthusiasm_data['enthusiasm_level']}). "
        f"{support_data['support_rationale']}"
    )
    teacher_summary = (
        str(ai_eval.get("teacher_summary")).strip()
        if ai_eval and ai_eval.get("teacher_summary")
        else default_teacher_summary
    )

    recommended_interventions = (
        ai_eval.get("recommended_interventions")
        if ai_eval and isinstance(ai_eval.get("recommended_interventions"), list) and ai_eval.get("recommended_interventions")
        else [
            f"Socratic chatbot is set to '{support_data['support_tier']}' mode ({support_data['support_needed_score']:.0f}/100 support intensity).",
            (
                f"Focus classroom check-ins on {gaps[0]}."
                if gaps
                else "Encourage the student to attempt multi-step CBSE application problems in chat."
            ),
        ]
    )

    strengths_and_gaps = {
        "mastered_topics": mastered_topics,
        "misconceptions_and_gaps": gaps,
        "hint_efficiency": capacity_data["hint_efficiency"],
        "reasoning_depth": capacity_data["reasoning_depth"],
        "score_trend": scores_data["score_trend"],
        "student_guidance_tips": student_tips,
        "recommended_interventions": recommended_interventions,
        "support_rationale": support_data["support_rationale"],
    }

    preliminary_report = {
        "student_id": student_id,
        "student_name": resolved_name,
        "overall_score_avg": scores_data["overall_score_avg"],
        "answering_capacity_score": capacity_data["answering_capacity_score"],
        "overall_enthusiasm_score": enthusiasm_data["overall_enthusiasm_score"],
        "support_needed_score": support_data["support_needed_score"],
        "support_tier": support_data["support_tier"],
        "capacity_level": capacity_data["capacity_level"],
        "enthusiasm_level": enthusiasm_data["enthusiasm_level"],
        "subject_breakdown": subject_breakdown,
        "strengths_and_gaps": strengths_and_gaps,
        "latest_teacher_opinion": teacher_data,
        "teacher_summary": teacher_summary,
    }

    adaptive_directive = build_adaptive_tutor_directive(preliminary_report)
    preliminary_report["adaptive_directive"] = adaptive_directive

    upsert_student_analytics(student_id, preliminary_report)
    return preliminary_report


def get_or_create_student_directive(student_id: str, student_name: str, current_message: str) -> Dict[str, Any]:
    """
    Fast helper for `POST /chat`:
    Fetches the cached analytics row from Supabase `student_analytics` (or computes a quick
    heuristic profile if none exists yet) and returns the tailored Socratic directive
    plus metadata for the frontend response.
    """
    subject = detect_subject(current_message)
    cached = get_student_analytics(student_id)
    if cached is None:
        cached = generate_student_report(student_id=student_id, student_name=student_name, use_ai=False)

    directive = build_adaptive_tutor_directive(cached, current_subject=subject)
    return {
        "detected_subject": subject,
        "support_tier": cached.get("support_tier", "guided_support"),
        "support_needed_score": float(cached.get("support_needed_score", 50.0)),
        "adaptive_directive": directive,
    }


def generate_admin_class_overview() -> Dict[str, Any]:
    """
    Aggregate performance across all students in Supabase for the Teacher/Admin Class Dashboard.
    """
    students_map = get_all_tracked_students()
    student_summaries: List[Dict[str, Any]] = []
    students_needing_attention: List[Dict[str, Any]] = []

    for sid, sname in students_map.items():
        cached = get_student_analytics(sid)
        if cached is None:
            cached = generate_student_report(student_id=sid, student_name=sname, use_ai=False)

        card = {
            "student_id": sid,
            "student_name": cached.get("student_name", sname),
            "overall_score_avg": float(cached.get("overall_score_avg", 0.0)),
            "answering_capacity_score": float(cached.get("answering_capacity_score", 50.0)),
            "overall_enthusiasm_score": float(cached.get("overall_enthusiasm_score", 50.0)),
            "support_needed_score": float(cached.get("support_needed_score", 50.0)),
            "support_tier": cached.get("support_tier", "guided_support"),
            "capacity_level": cached.get("capacity_level", "developing"),
            "enthusiasm_level": cached.get("enthusiasm_level", "moderate"),
            "teacher_summary": cached.get("teacher_summary", ""),
        }
        student_summaries.append(card)

        if (
            card["support_tier"] == "intensive_scaffolding"
            or card["support_needed_score"] >= 62.0
            or card["capacity_level"] == "needs_attention"
        ):
            students_needing_attention.append(card)

    total = len(student_summaries)
    if total > 0:
        class_score_avg = round(sum(s["overall_score_avg"] for s in student_summaries) / total, 2)
        class_capacity_avg = round(sum(s["answering_capacity_score"] for s in student_summaries) / total, 2)
        class_enthusiasm_avg = round(sum(s["overall_enthusiasm_score"] for s in student_summaries) / total, 2)
        class_support_avg = round(sum(s["support_needed_score"] for s in student_summaries) / total, 2)
    else:
        class_score_avg = 0.0
        class_capacity_avg = 0.0
        class_enthusiasm_avg = 0.0
        class_support_avg = 0.0

    # Sort students needing attention by highest support_needed_score first
    students_needing_attention.sort(key=lambda x: x["support_needed_score"], reverse=True)

    return {
        "total_students": total,
        "class_averages": {
            "overall_score_avg": class_score_avg,
            "answering_capacity_score": class_capacity_avg,
            "overall_enthusiasm_score": class_enthusiasm_avg,
            "support_needed_score": class_support_avg,
        },
        "students_needing_attention": students_needing_attention,
        "all_students": student_summaries,
    }


def generate_student_socratic_quiz(
    student_id: str,
    student_name: Optional[str] = None,
    subject: Optional[str] = None,
    num_questions: int = 3,
) -> Dict[str, Any]:
    """
    Generate a 3-question Socratic quiz tailored to the student's 4-factor profile
    using ONLY 1 API call (reusing the cached heuristic/Supabase profile).
    """
    profile = get_student_analytics(student_id)
    if profile is None:
        profile = generate_student_report(student_id=student_id, student_name=student_name, use_ai=False)

    resolved_name = profile.get("student_name") or student_name or f"Student {student_id}"
    support_tier = profile.get("support_tier", "guided_support")
    support_score = profile.get("support_needed_score", 50.0)
    strengths_gaps = profile.get("strengths_and_gaps") or {}
    weak_topics = strengths_gaps.get("misconceptions_and_gaps") or []
    strong_topics = strengths_gaps.get("mastered_topics") or []
    teacher_op = profile.get("latest_teacher_opinion") or {}

    target_subject = (
        normalize_subject_name(subject)
        if subject
        else (teacher_op.get("subject") if teacher_op.get("subject") and teacher_op.get("subject") != "General" else "Mathematics")
    )
    directive = build_adaptive_tutor_directive(profile, current_subject=target_subject)

    quiz_prompt = (
        f"Create a {num_questions}-question Class 10 CBSE Socratic Quiz for {resolved_name} in {target_subject}.\n"
        f"- Student Support Mode: {support_tier} (Support Needed: {support_score}/100)\n"
        f"- Weak/Focus Topics: {', '.join(weak_topics) if weak_topics else target_subject}\n"
        f"- Mastered Topics: {', '.join(strong_topics) if strong_topics else 'General foundations'}\n"
        f"- Teacher Note: {teacher_op.get('opinion_notes', 'None')}\n\n"
        f"Format strictly as Q1, Q2, Q3. Under each question, provide a 'Socratic Hint:' that guides {resolved_name} "
        f"on the very first step to think about without giving away the answer."
    )

    quiz_text = generate_socratic_quiz_completion(
        quiz_prompt_payload=quiz_prompt,
        student_context=directive,
    )

    return {
        "student_id": student_id,
        "student_name": resolved_name,
        "subject": target_subject,
        "support_tier": support_tier,
        "support_needed_score": support_score,
        "num_questions": num_questions,
        "quiz": quiz_text,
    }

