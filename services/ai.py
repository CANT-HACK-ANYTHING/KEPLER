import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

# Load environment variables
load_dotenv()

logger = logging.getLogger("ai_tutor_service")

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "tutor_prompt.txt"
_BASE_PROMPT_CACHE: Optional[str] = None

PLACEHOLDERS = {
    "",
    "PASTE_YOUR_KEY_HERE",
    "PASTE_YOUR_NVIDIA_KEY_HERE",
    "PASTE_YOUR_OPENCODE_KEY_HERE",
    "your_gemini_api_key_here",
    "your_nvidia_api_key_here",
    "your_opencode_api_key_here",
}

GEMINI_MODEL_POOL = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemma-4-26b-a4b-it",
    "gemini-3.5-flash",
]

# Mode-specific guidelines matching the frontend 3 function modes
MODE_INSTRUCTIONS: Dict[str, str] = {
    "socratic": """
### ACTIVE MODE: SOCRATIC METHOD
- NEVER provide direct answers, complete solutions, or write full answers for the student.
- Break down concepts into small, digestible steps.
- Guide the student by giving an intuitive hint and asking exactly ONE thoughtful question at a time.
- Keep reply concise: exactly 2 to 4 short sentences in simple language.
- Prompt the student to think critically and discover the solution on their own.
""",
    "detailed_explanation": """
### ACTIVE MODE: DETAILED EXPLANATION
- Provide deep conceptual clarity and comprehensive understanding for the student.
- Structure your response cleanly:
  1. **Core Concept & Intuition**: Real-world analogy or easy visual explanation to build an intuition.
  2. **Step-by-Step Breakdown**: Clear, structured explanation of 'why' and 'how' with bullet points.
  3. **Key NCERT Terms & Formulas**: State important definitions, scientific laws, or mathematical relations.
  4. **Key Takeaway**: A 1-sentence memorable summary.
- Use simple, engaging, age-appropriate language suitable for a Class 10 student.
""",
    "exam_ready": """
### ACTIVE MODE: EXAM READY (CBSE BOARD FORMAT)
- Tailor the entire response specifically to score 100% marks under CBSE Class 10 Board Exam marking schemes.
- Structure the answer exactly as examiners expect on board exam answer sheets:
  1. **Exact NCERT Definition / Core Law**: Precise definition with crucial technical keywords in bold.
  2. **Point-wise Breakdown**: Numbered or bulleted points (CBSE awards marks per distinct point).
  3. **Formula / Balanced Equation / SI Units**: State applicable mathematical formulas (with SI units) or balanced chemical reactions.
  4. **Examiner's Tip / Common Pitfall**: One critical mistake or trap where students typically lose 0.5 to 1 mark in board exams.
- Ensure the answer is structured so the student can directly memorize or reproduce it in their board exams.
""",
}


def get_base_prompt() -> str:
    """Read and cache the base system prompt from the prompt file."""
    global _BASE_PROMPT_CACHE
    if _BASE_PROMPT_CACHE is None:
        if not PROMPT_FILE.exists():
            raise FileNotFoundError(f"System prompt file not found at: {PROMPT_FILE}")
        _BASE_PROMPT_CACHE = PROMPT_FILE.read_text(encoding="utf-8").strip()
    return _BASE_PROMPT_CACHE


def build_system_prompt_for_mode(mode: str, student_context: Optional[str] = None) -> str:
    """
    Compose the system prompt combining base CBSE rules, active function mode,
    and optional student adaptive learning context.
    """
    normalized_mode = (mode or "socratic").lower().strip().replace(" ", "_").replace("-", "_")
    if normalized_mode not in MODE_INSTRUCTIONS:
        normalized_mode = "socratic"

    base_prompt = get_base_prompt()
    mode_text = MODE_INSTRUCTIONS[normalized_mode]

    prompt = f"{base_prompt}\n\n{mode_text}"
    if student_context and student_context.strip():
        prompt += f"\n\n### STUDENT ADAPTIVE PROFILE & GUIDANCE DIRECTIVE:\n{student_context.strip()}"

    return prompt


def get_active_provider() -> str:
    """Determine preferred AI provider ('opencode', 'nvidia', or 'gemini')."""
    provider = (os.getenv("AI_PROVIDER") or "opencode").strip().lower()
    if provider in ("opencode", "nvidia", "gemini"):
        return provider
    return "opencode"


def _build_candidates(preferred_provider: str, model_override: Optional[str] = None) -> List[tuple[OpenAI, str, str]]:
    """Build an ordered list of (OpenAI client, model, provider_name) candidates."""
    candidates: List[tuple[OpenAI, str, str]] = []
    provider_order = [preferred_provider] + [
        p for p in ("opencode", "nvidia", "gemini") if p != preferred_provider
    ]

    for prov in provider_order:
        if prov == "opencode":
            key = (os.getenv("OPENCODE_API_KEY") or "").strip()
            if key not in PLACEHOLDERS:
                client = OpenAI(base_url="https://opencode.ai/zen/v1", api_key=key, timeout=20.0)
                m = (model_override if prov == preferred_provider else None) or os.getenv(
                    "OPENCODE_MODEL", "nemotron-3.5-lightning-free"
                )
                candidates.append((client, m, "opencode"))

        elif prov == "nvidia":
            key = (os.getenv("NVIDIA_API_KEY") or "").strip()
            if key not in PLACEHOLDERS:
                client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key, timeout=20.0)
                m = (model_override if prov == preferred_provider else None) or os.getenv(
                    "NVIDIA_MODEL", "nv-mistralai/mistral-nemo-12b-instruct"
                )
                candidates.append((client, m, "nvidia"))

        elif prov == "gemini":
            key = (os.getenv("GEMINI_API_KEY") or "").strip()
            if key not in PLACEHOLDERS:
                client = OpenAI(
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    api_key=key,
                    timeout=25.0,
                )
                primary_gemini = (model_override if prov == preferred_provider else None) or os.getenv(
                    "GEMINI_MODEL", "gemini-3.5-flash-lite"
                )
                models_to_try = [primary_gemini] + [
                    gm for gm in GEMINI_MODEL_POOL if gm != primary_gemini
                ]
                for gm in models_to_try:
                    candidates.append((client, gm, "gemini"))

    return candidates


def _call_provider(
    client: OpenAI,
    target_model: str,
    provider: str,
    messages: List[Dict[str, str]],
    is_longer_mode: bool = False,
) -> str:
    """Execute the chat completion call for a specific provider."""
    max_tokens = 1200 if is_longer_mode else 350

    if provider == "gemini" and target_model.startswith("gemini-"):
        response = client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens if is_longer_mode else 1024,
            reasoning_effort="low",
            timeout=25.0,
        )
    else:
        response = client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens,
            timeout=20.0,
        )

    if not response.choices or not response.choices[0].message:
        raise RuntimeError("No response returned by the model.")

    content = (response.choices[0].message.content or "").strip()
    if not content:
        return (
            "I am here strictly as your Class 10 CBSE tutor to guide you step-by-step. "
            "Which Class 10 subject or question would you like to work on today?"
        )
    return content


_WORKING_CANDIDATE_INDEX: int = 0


def generate_tutor_reply(
    student_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    mode: str = "socratic",
    student_context: Optional[str] = None,
) -> str:
    """
    Generate an AI tutor reply for a Class 10 CBSE student message.

    Function Modes supported:
      1. 'socratic' — Socratic Method (hints + 1 guiding question, 2-4 sentences, no direct answers)
      2. 'detailed_explanation' — Detailed Explanation (deep conceptual clarity, analogies, step-by-step breakdown)
      3. 'exam_ready' — Exam Ready (CBSE Board exam answers: keywords bolded, point-wise, formulas/reactions, examiner traps)
    """
    global _WORKING_CANDIDATE_INDEX

    normalized_mode = (mode or "socratic").lower().strip().replace(" ", "_").replace("-", "_")
    system_prompt = build_system_prompt_for_mode(normalized_mode, student_context=student_context)
    is_longer_mode = normalized_mode in ("detailed_explanation", "exam_ready")

    # Build conversation payload starting with the system prompt
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    if history:
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": str(content)})

    messages.append({"role": "user", "content": student_message})

    candidates = _build_candidates(get_active_provider(), model_override=model)
    if not candidates:
        raise ValueError(
            "No valid API key found in .env. Please set OPENCODE_API_KEY, NVIDIA_API_KEY, or GEMINI_API_KEY."
        )

    idx_order = list(range(_WORKING_CANDIDATE_INDEX, len(candidates))) + list(
        range(0, _WORKING_CANDIDATE_INDEX)
    )

    last_error: Optional[Exception] = None
    for idx in idx_order:
        client, target_model, prov = candidates[idx]
        try:
            reply = _call_provider(
                client,
                target_model,
                prov,
                messages,
                is_longer_mode=is_longer_mode,
            )
            _WORKING_CANDIDATE_INDEX = idx
            return reply
        except APIStatusError as err:
            last_error = err
            logger.info(
                "Candidate '%s' (%s) returned HTTP %s; rotating to next available model/provider...",
                prov,
                target_model,
                err.status_code,
            )
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to generate reply from configured providers.")


def generate_analysis_completion(prompt_payload: str) -> str:
    """Generate completion for student 4-factor analytics and reports."""
    global _WORKING_CANDIDATE_INDEX
    messages = [
        {
            "role": "system",
            "content": "You are an expert CBSE educational psychologist and student progress analytics evaluator.",
        },
        {"role": "user", "content": prompt_payload},
    ]

    candidates = _build_candidates(get_active_provider())
    if not candidates:
        raise ValueError("No valid API key found in .env.")

    idx_order = list(range(_WORKING_CANDIDATE_INDEX, len(candidates))) + list(range(0, _WORKING_CANDIDATE_INDEX))
    for idx in idx_order:
        client, target_model, prov = candidates[idx]
        try:
            return _call_provider(client, target_model, prov, messages, is_longer_mode=True)
        except Exception:
            continue

    return "{}"


def generate_socratic_quiz_completion(quiz_prompt_payload: str, student_context: str = "") -> str:
    """Generate a personalized Class 10 Socratic quiz based on student's learning profile."""
    global _WORKING_CANDIDATE_INDEX
    messages = [
        {
            "role": "system",
            "content": (
                "You are an encouraging Class 10 CBSE tutor crafting personalized diagnostic Socratic quizzes. "
                f"Student Profile:\n{student_context}"
            ),
        },
        {"role": "user", "content": quiz_prompt_payload},
    ]

    candidates = _build_candidates(get_active_provider())
    if not candidates:
        raise ValueError("No valid API key found in .env.")

    idx_order = list(range(_WORKING_CANDIDATE_INDEX, len(candidates))) + list(range(0, _WORKING_CANDIDATE_INDEX))
    for idx in idx_order:
        client, target_model, prov = candidates[idx]
        try:
            return _call_provider(client, target_model, prov, messages, is_longer_mode=True)
        except Exception:
            continue

    return "Personalized quiz currently unavailable. Please try again in a moment."
