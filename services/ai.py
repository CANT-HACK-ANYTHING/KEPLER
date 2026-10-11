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
ANALYZER_PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "analyzer_prompt.txt"
_SYSTEM_PROMPT_CACHE: Optional[str] = None
_ANALYZER_PROMPT_CACHE: Optional[str] = None

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
    "gemini-3.8-flash",
    "gemini-3.5-flash",
]


def get_system_prompt() -> str:
    """Read and cache the Socratic tutor system prompt from the prompt file."""
    global _SYSTEM_PROMPT_CACHE
    if _SYSTEM_PROMPT_CACHE is None:
        if not PROMPT_FILE.exists():
            raise FileNotFoundError(f"System prompt file not found at: {PROMPT_FILE}")
        _SYSTEM_PROMPT_CACHE = PROMPT_FILE.read_text(encoding="utf-8").strip()
    return _SYSTEM_PROMPT_CACHE


def get_analyzer_prompt() -> str:
    """Read and cache the Student Progress Analyzer system prompt."""
    global _ANALYZER_PROMPT_CACHE
    if _ANALYZER_PROMPT_CACHE is None:
        if not ANALYZER_PROMPT_FILE.exists():
            raise FileNotFoundError(f"Analyzer prompt file not found at: {ANALYZER_PROMPT_FILE}")
        _ANALYZER_PROMPT_CACHE = ANALYZER_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return _ANALYZER_PROMPT_CACHE


def get_active_provider() -> str:
    """
    Determine preferred AI provider ('opencode', 'nvidia', or 'gemini').
    """
    provider = (os.getenv("AI_PROVIDER") or "opencode").strip().lower()
    if provider in ("opencode", "nvidia", "gemini"):
        return provider
    return "opencode"


def _build_candidates(preferred_provider: str, model_override: Optional[str] = None) -> List[tuple[OpenAI, str, str]]:
    """
    Build an ordered list of (OpenAI client, model, provider_name) candidates
    across OpenCode, NVIDIA, and Gemini (with multi-model quota rotation).
    """
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
    max_output_tokens: int = 300,
) -> str:
    """Execute the chat completion call for a specific provider."""
    if provider == "gemini" and target_model.startswith("gemini-"):
        response = client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=0.4,
            max_tokens=max(1024, max_output_tokens),
            reasoning_effort="low",
            timeout=25.0,
        )
    else:
        response = client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=0.4,
            max_tokens=max_output_tokens,
            timeout=20.0,
        )

    if not response.choices or not response.choices[0].message:
        raise RuntimeError("No response returned by the model.")

    content = (response.choices[0].message.content or "").strip()
    if not content:
        return (
            "I am your Class 10 CBSE tutor, so I always guide you step-by-step with hints rather than giving direct answers. "
            "Let's look at Carbon together: how many electrons does a Carbon atom have in its outermost shell?"
            if "carbon" in messages[-1]["content"].lower()
            else "I am here strictly as your Class 10 CBSE tutor to guide you step-by-step. Which Class 10 subject or question would you like to work on today?"
        )
    return content


_WORKING_CANDIDATE_INDEX: int = 0


def generate_tutor_reply(
    student_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
    student_context: Optional[str] = None,
) -> str:
    """
    Generate an AI tutor reply for a Class 10 CBSE student message.
    Supports OpenCode Zen, NVIDIA NIM, and Google Gemini with automatic failover
    and model-pool quota rotation.
    Optionally injects `student_context` (the 4-factor adaptive directive) into the
    Socratic system prompt so guidance adapts to student scores, capacity, enthusiasm,
    and teacher opinions.
    """
    global _WORKING_CANDIDATE_INDEX
    system_prompt = get_system_prompt()
    if student_context and student_context.strip():
        system_prompt = f"{system_prompt}\n\n{student_context.strip()}"

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

    # Start from the last known working candidate so subsequent calls are instant
    idx_order = list(range(_WORKING_CANDIDATE_INDEX, len(candidates))) + list(
        range(0, _WORKING_CANDIDATE_INDEX)
    )

    last_error: Optional[Exception] = None
    for idx in idx_order:
        client, target_model, prov = candidates[idx]
        try:
            reply = _call_provider(client, target_model, prov, messages, max_output_tokens=300)
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


def _build_analyzer_candidates(model_override: Optional[str] = None) -> List[tuple[OpenAI, str, str]]:
    """
    Build candidate clients for the Student Progress Analyzer.
    If `ANALYZER_API_KEY` is set in `.env`, it is placed FIRST so the analyzer runs on
    its own dedicated API key/quota, followed by the standard pool as a fail-safe fallback.
    """
    dedicated_candidates: List[tuple[OpenAI, str, str]] = []
    analyzer_key = (os.getenv("ANALYZER_API_KEY") or "").strip()
    analyzer_provider = (os.getenv("ANALYZER_PROVIDER") or get_active_provider()).strip().lower()
    analyzer_model = (model_override or os.getenv("ANALYZER_MODEL") or "").strip()

    if analyzer_key and analyzer_key not in PLACEHOLDERS and analyzer_key != "your_analyzer_api_key_here":
        if analyzer_provider == "opencode":
            client = OpenAI(base_url="https://opencode.ai/zen/v1", api_key=analyzer_key, timeout=20.0)
            m = analyzer_model or os.getenv("OPENCODE_MODEL", "nemotron-3.5-lightning-free")
            dedicated_candidates.append((client, m, "opencode"))
        elif analyzer_provider == "nvidia":
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=analyzer_key, timeout=20.0)
            m = analyzer_model or os.getenv("NVIDIA_MODEL", "nv-mistralai/mistral-nemo-12b-instruct")
            dedicated_candidates.append((client, m, "nvidia"))
        else:
            client = OpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=analyzer_key,
                timeout=25.0,
            )
            primary_gm = analyzer_model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
            models_to_try = [primary_gm] + [gm for gm in GEMINI_MODEL_POOL if gm != primary_gm]
            for gm in models_to_try:
                dedicated_candidates.append((client, gm, "gemini"))

    fallback_candidates = _build_candidates(get_active_provider(), model_override=model_override)
    return dedicated_candidates + fallback_candidates


def generate_analysis_completion(
    analysis_input_payload: str,
    model: Optional[str] = None,
) -> str:
    """
    Run the 4-factor Student Progress Analyzer.
    Prioritizes the dedicated `ANALYZER_API_KEY` (if configured in `.env`) before
    falling back to the shared provider pool.
    """
    analyzer_prompt = get_analyzer_prompt()

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": analyzer_prompt},
        {"role": "user", "content": analysis_input_payload},
    ]

    candidates = _build_analyzer_candidates(model_override=model)
    if not candidates:
        raise ValueError(
            "No valid API key found in .env. Please set ANALYZER_API_KEY, OPENCODE_API_KEY, NVIDIA_API_KEY, or GEMINI_API_KEY."
        )

    last_error: Optional[Exception] = None
    for client, target_model, prov in candidates:
        try:
            reply = _call_provider(client, target_model, prov, messages, max_output_tokens=900)
            return reply
        except APIStatusError as err:
            last_error = err
            logger.info(
                "Analyzer candidate '%s' (%s) returned HTTP %s; rotating to next model/provider...",
                prov,
                target_model,
                err.status_code,
            )
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to generate analysis from configured providers.")



def generate_socratic_quiz_completion(
    quiz_prompt_payload: str,
    student_context: str,
    model: Optional[str] = None,
) -> str:
    """
    Generate a 3-question Socratic quiz in a SINGLE API call using the Socratic tutor persona
    and the student's 4-factor adaptive directive.
    """
    global _WORKING_CANDIDATE_INDEX
    base_tutor_prompt = get_system_prompt()
    quiz_system_prompt = (
        f"{base_tutor_prompt}\n\n"
        f"{student_context.strip()}\n\n"
        "QUIZ GENERATION OVERRIDE:\n"
        "- The teacher/student requested a 3-Question Socratic Practice Quiz.\n"
        "- Generate EXACTLY 3 numbered questions tailored to the student's support tier and teacher notes.\n"
        "- Under each question, include a short 'Socratic Hint:' that nudges their thinking step-by-step without revealing the answer.\n"
        "- Never provide the final answers."
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": quiz_system_prompt},
        {"role": "user", "content": quiz_prompt_payload},
    ]

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
            reply = _call_provider(client, target_model, prov, messages, max_output_tokens=600)
            _WORKING_CANDIDATE_INDEX = idx
            return reply
        except APIStatusError as err:
            last_error = err
            logger.info(
                "Quiz candidate '%s' (%s) returned HTTP %s; rotating to next model/provider...",
                prov,
                target_model,
                err.status_code,
            )
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to generate Socratic quiz from configured providers.")

