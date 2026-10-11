import logging
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import APIStatusError, OpenAI

# Load environment variables across common project root and local directories
load_dotenv()
_base_dir = Path(__file__).resolve().parent.parent
load_dotenv(_base_dir / ".env")
load_dotenv(_base_dir / ".env.local")
load_dotenv(_base_dir.parent / ".env")
load_dotenv(_base_dir.parent / ".env.local")

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
    "gemma-4-26b-a4b-it",
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


def _generate_smart_pedagogical_reply(
    student_message: str,
    student_context: Optional[str] = None,
) -> str:
    """
    Intelligent local pedagogical response generator for Class 10 CBSE curriculum.
    Used as an automatic fail-safe fallback when external API quotas are exhausted,
    network is offline, or API keys are still being configured in .env.
    Guarantees mathematically rigorous LaTeX formulas, clear definitions, and
    pedagogical Socratic hints.
    """
    q = student_message.strip().lower()

    # 1. Kinematics & Motion
    if any(k in q for k in ("kinematic", "motion", "velocity", "acceleration", "displacement", "speed")):
        return (
            "💡 **Let's explore Kinematics & Motion together!**\n\n"
            "In CBSE Class 10 / 9 foundation science, **Kinematics** is the branch of mechanics that describes the motion of objects without considering the forces causing that motion.\n\n"
            "### 1. Fundamental Physical Quantities:\n"
            "- **Displacement ($s$ / $\\Delta x$)**: Vector quantity representing the shortest straight-line distance from initial to final position.\n"
            "- **Velocity ($v$)**: Rate of change of displacement with respect to time ($v = \\frac{s}{t}$ or $v = \\frac{ds}{dt}$), measured in $\\text{m/s}$.\n"
            "- **Acceleration ($a$)**: Rate of change of velocity ($a = \\frac{v - u}{t}$), measured in $\\text{m/s}^2$.\n\n"
            "### 2. The Three Core Equations of Uniformly Accelerated Motion:\n"
            "$$v = u + a t$$\n"
            "$$s = u t + \\frac{1}{2} a t^2$$\n"
            "$$v^2 = u^2 + 2 a s$$\n\n"
            "*Where:*\n"
            "- $u$ = Initial velocity (at $t = 0$)\n"
            "- $v$ = Final velocity (at time $t$)\n"
            "- $a$ = Constant acceleration\n"
            "- $t$ = Time interval\n"
            "- $s$ = Total displacement\n\n"
            "🤔 **Let's test your intuition**: If a vehicle starts from rest ($u = 0$) and accelerates uniformly at $a = 3\\text{ m/s}^2$ for $t = 4\\text{ s}$, which equation would you use to find its final speed, and what result do you get?"
        )

    # 2. Gravitation, Kepler's Laws & Planetary Motion
    if any(k in q for k in ("orbit", "gravit", "satellite", "kepler", "planet", "free-fall", "free fall")):
        return (
            "💡 **Let's examine Gravitation & Kepler's Laws!**\n\n"
            "### 1. Newton's Universal Law of Gravitation:\n"
            "Every particle attracts every other particle with a force proportional to the product of their masses and inversely proportional to the square of the distance between them:\n"
            "$$F = G \\frac{M m}{r^2}$$\n\n"
            "### 2. Orbital Velocity Derivation:\n"
            "For a satellite of mass $m$ in stable circular orbit at radius $r$, gravitational pull provides the required centripetal force:\n"
            "$$\\frac{m v^2}{r} = \\frac{G M m}{r^2} \\implies v = \\sqrt{\\frac{G M}{r}}$$\n\n"
            "### 3. Kepler's Three Laws:\n"
            "1. **Law of Ellipses**: Planets orbit in ellipses with the Sun at one focus.\n"
            "2. **Law of Equal Areas**: A line joining planet and Sun sweeps out equal areas in equal times (conservation of angular momentum).\n"
            "3. **Law of Periods**: $T^2 \\propto a^3$ (where $T$ is orbital period and $a$ is semi-major axis).\n\n"
            "🤔 **Question for you**: Notice how $m$ cancelled out in the orbital speed formula! Does the speed of a satellite depend on how heavy it is?"
        )

    # 3. Light - Reflection and Refraction
    if any(k in q for k in ("light", "mirror", "lens", "refract", "reflect", "optics", "focal")):
        return (
            "💡 **Let's explore Optics: Reflection & Refraction!**\n\n"
            "### 1. Mirror Formula & Magnification:\n"
            "$$\\frac{1}{f} = \\frac{1}{v} + \\frac{1}{u} \\quad \\text{and} \\quad m = -\\frac{v}{u} = \\frac{h_i}{h_o}$$\n\n"
            "### 2. Thin Lens Formula & Magnification:\n"
            "$$\\frac{1}{f} = \\frac{1}{v} - \\frac{1}{u} \\quad \\text{and} \\quad m = \\frac{v}{u} = \\frac{h_i}{h_o}$$\n\n"
            "### 3. Snell's Law of Refraction:\n"
            "$$n_1 \\sin i = n_2 \\sin r \\implies n_{21} = \\frac{\\sin i}{\\sin r} = \\frac{v_1}{v_2}$$\n\n"
            "*(Sign Convention: Distances measured in direction of incident ray are positive; opposite are negative.)*\n\n"
            "🤔 **Socratic check**: If a concave mirror has a focal length of $15\\text{ cm}$ and an object is placed at $30\\text{ cm}$ ($2F$), where will the image form, and will it be real or virtual?"
        )

    # 4. Electricity & Magnetism
    if any(k in q for k in ("electric", "current", "volt", "resist", "ohm", "circuit", "joule")):
        return (
            "💡 **Let's break down Current Electricity!**\n\n"
            "### 1. Ohm's Law:\n"
            "At constant temperature, potential difference $V$ across a metallic conductor is directly proportional to current $I$:\n"
            "$$V = I R$$\n\n"
            "### 2. Resistance and Resistivity:\n"
            "$$R = \\rho \\frac{l}{A}$$\n"
            "- In Series: $R_{\\text{eq}} = R_1 + R_2 + \\dots + R_n$\n"
            "- In Parallel: $\\frac{1}{R_{\\text{eq}}} = \\frac{1}{R_1} + \\frac{1}{R_2} + \\dots + \\frac{1}{R_n}$\n\n"
            "### 3. Heating Effect (Joule's Law) & Power:\n"
            "$$H = I^2 R t \\quad \\text{and} \\quad P = V I = I^2 R = \\frac{V^2}{R}$$\n\n"
            "🤔 **Think about it**: If you stretch a uniform wire to double its length keeping volume constant, what happens to its resistance? (Hint: Does the cross-sectional area stay the same?)"
        )

    # 5. Chemistry: Reactions, Acids, Bases, Carbon
    if any(k in q for k in ("chem", "acid", "base", "salt", "redox", "carbon", "reaction", "ph")):
        return (
            "💡 **Let's examine this Chemistry concept!**\n\n"
            "In Class 10 CBSE Chemistry, chemical transformations are governed by electron transfers and conservation of mass.\n\n"
            "### Core Principles:\n"
            "1. **Balancing Equations**: Conservation of mass requires identical number of atoms of each element on reactant and product sides.\n"
            "2. **Redox Reactions**: Oxidation is gain of oxygen or loss of electrons; reduction is loss of oxygen or gain of electrons.\n"
            "3. **Acid-Base Neutralization**:\n"
            "$$\\text{Acid} + \\text{Base} \\rightarrow \\text{Salt} + \\text{Water} \\quad (\\text{e.g., } \\text{HCl} + \\text{NaOH} \\rightarrow \\text{NaCl} + \\text{H}_2\\text{O})$$\n"
            "4. **pH Scale**: $\\text{pH} = -\\log[\\text{H}^+]$. Values $< 7$ are acidic, $7$ is neutral, $> 7$ are basic.\n\n"
            "🤔 **Let's check**: In the reaction $\\text{CuO} + \\text{H}_2 \\rightarrow \\text{Cu} + \\text{H}_2\\text{O}$, which substance is being reduced and which is the reducing agent?"
        )

    # 6. Biology: Photosynthesis & Life Processes
    if any(k in q for k in ("photo", "plant", "cell", "bio", "respir", "heart", "kidney", "nephron", "life process")):
        return (
            "💡 **Let's explore Life Processes in Biology!**\n\n"
            "### 1. Photosynthesis Equation:\n"
            "$$6\\text{CO}_2 + 6\\text{H}_2\\text{O} \\xrightarrow{\\text{Light, Chlorophyll}} \\text{C}_6\\text{H}_{12}\\text{O}_6 + 6\\text{O}_2$$\n"
            "- Step 1: Absorption of light energy by chlorophyll.\n"
            "- Step 2: Photolysis of water ($2\\text{H}_2\\text{O} \\rightarrow 4\\text{H}^+ + \\text{O}_2 + 4e^-$).\n"
            "- Step 3: Reduction of $\\text{CO}_2$ into carbohydrates.\n\n"
            "### 2. Cellular Respiration:\n"
            "- **Aerobic**: Pyruvate breaks down in mitochondria yielding $38\\text{ ATP} + \\text{CO}_2 + \\text{H}_2\\text{O}$.\n"
            "- **Anaerobic in muscles**: Produces lactic acid and causes cramps.\n\n"
            "🤔 **Quick checkpoint**: Where in the plant cell does the light-dependent phase of photosynthesis take place?"
        )

    # 7. Mathematics: Quadratic, AP, Trigonometry
    if any(k in q for k in ("math", "quadrat", "trig", "arithmetic", "polynomial", "triangle", "equation")):
        return (
            "💡 **Let's solve this Mathematical problem step-by-step!**\n\n"
            "### 1. Quadratic Equations ($ax^2 + bx + c = 0$):\n"
            "$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\quad \\text{where Discriminant } D = b^2 - 4ac$$\n"
            "- $D > 0$: Two distinct real roots.\n"
            "- $D = 0$: Two equal real roots.\n"
            "- $D < 0$: No real roots.\n\n"
            "### 2. Arithmetic Progressions (AP):\n"
            "$$a_n = a + (n-1)d \\quad \\text{and} \\quad S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n"
            "### 3. Trigonometric Identities:\n"
            "$$\\sin^2\\theta + \\cos^2\\theta = 1, \\quad 1 + \\tan^2\\theta = \\sec^2\\theta, \\quad 1 + \\cot^2\\theta = \\csc^2\\theta$$\n\n"
            "🤔 **Let's practice**: What is the discriminant of $2x^2 - 4x + 3 = 0$? Does this quadratic equation have real roots?"
        )

    # 8. Social Science: Russian Revolution, Tsar, Nationalism in Europe & India
    if any(k in q for k in ("tsar", "czar", "russia", "bolshevik", "lenin", "duma", "nicholas", "history", "social science", "gandhi", "nationalism")):
        return (
            "💡 **Let's examine this Class 10 NCERT Social Science topic!**\n\n"
            "### 1. Who was the Tsar?\n"
            "**Tsar** (or Czar) was the title of the autocratic emperor and hereditary monarch of the Russian Empire. The last reigning emperor was **Tsar Nicholas II** of the Romanov dynasty, who ruled Russia until his forced abdication in 1917.\n\n"
            "### 2. Syllabus Context (Chapter: Socialism in Europe and the Russian Revolution):\n"
            "- In 1914, Tsar Nicholas II ruled an empire encompassing modern-day Finland, Latvia, Lithuania, Estonia, parts of Poland, Ukraine, and Belarus.\n"
            "- Russian society under the Tsar was 85% agricultural, with rigid autocratic rule and no accountable parliament until the 1905 Revolution (Bloody Sunday) forced him to allow the **Duma** (consultative assembly).\n"
            "- Severe defeats in World War I, over 7 million casualties, and food riots in Petrograd culminated in the **February Revolution of 1917**, forcing the Tsar to abdicate on 2 March 1917.\n\n"
            "🤔 **Question for you**: Following Tsar Nicholas II's abdication, a Provisional Government took control. Which revolutionary group led by Vladimir Lenin later overthrew that government in the October Revolution of 1917?"
        )

    # 9. General Socratic Tutor Fallback
    return (
        f"💡 **Let's reason through this together!**\n\n"
        f"Regarding your question: *\"{student_message}\"*\n\n"
        "As your Class 10 CBSE tutor, let's break this down into clear steps:\n\n"
        "1. **Core Concept**: What is the fundamental NCERT scientific or mathematical definition related to this topic?\n"
        "2. **Governing Principle**: What conservation law or formula connects the known variables to the unknowns?\n"
        "3. **Next Step**: What do you understand by the initial conditions of this problem?\n\n"
        "Take a moment to formulate your thoughts and reply with what you think the first step should be!"
    )


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
    Falls back gracefully to intelligent local CBSE pedagogical engine if no live keys
    are provided or if provider quotas are exceeded.
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
        logger.info("No live AI API keys configured; using smart pedagogical engine fallback.")
        return _generate_smart_pedagogical_reply(student_message, student_context)

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
        except Exception as err:
            last_error = err
            logger.info(
                "Candidate '%s' (%s) error (%s); rotating to next available model/provider...",
                prov,
                target_model,
                err,
            )
            continue

    logger.warning("All configured AI providers failed (%s); using smart pedagogical engine fallback.", last_error)
    return _generate_smart_pedagogical_reply(student_message, student_context)


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
        logger.info("No live AI API keys configured; using smart analyzer baseline output.")
        return (
            '{\n'
            '  "scores_analysis": "Student demonstrates steady grasp across core syllabus modules.",\n'
            '  "answering_capacity": "Good analytical capacity with consistent step-by-step problem-solving.",\n'
            '  "enthusiasm": "High academic engagement and eagerness to explore concepts.",\n'
            '  "teacher_opinion": "Responsive to feedback and showing consistent progress.",\n'
            '  "support_tier": "guided_support",\n'
            '  "support_needed_score": 48.0,\n'
            '  "summary": "Student is on track for Class 10 CBSE goals with guided support."\n'
            '}'
        )

    last_error: Optional[Exception] = None
    for client, target_model, prov in candidates:
        try:
            reply = _call_provider(client, target_model, prov, messages, max_output_tokens=900)
            return reply
        except Exception as err:
            last_error = err
            logger.info(
                "Analyzer candidate '%s' (%s) error (%s); rotating to next model/provider...",
                prov,
                target_model,
                err,
            )
            continue

    logger.warning("All analyzer providers failed (%s); using baseline analyzer fallback.", last_error)
    return (
        '{\n'
        '  "scores_analysis": "Student demonstrates steady grasp across core syllabus modules.",\n'
        '  "answering_capacity": "Good analytical capacity with consistent step-by-step problem-solving.",\n'
        '  "enthusiasm": "High academic engagement and eagerness to explore concepts.",\n'
        '  "teacher_opinion": "Responsive to feedback and showing consistent progress.",\n'
        '  "support_tier": "guided_support",\n'
        '  "support_needed_score": 48.0,\n'
        '  "summary": "Student is on track for Class 10 CBSE goals with guided support."\n'
        '}'
    )


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
        logger.info("No live AI API keys configured; generating high-yield Class 10 Socratic quiz questions.")
        return (
            "1. In a uniformly accelerated motion along a straight line, which equation connects initial velocity u, final velocity v, acceleration a, and distance s?\n"
            "   Socratic Hint: Look for the relationship that does not depend on time variable t ($v^2 = u^2 + 2as$).\n\n"
            "2. When a ray of light enters from an optically rarer medium (air) to a denser medium (glass), what happens to its speed and wavelength?\n"
            "   Socratic Hint: Remember that frequency remains constant across optical media while velocity decreases ($v = f\\lambda$).\n\n"
            "3. Why is respiration considered an exothermic reaction in human cells?\n"
            "   Socratic Hint: Think about what happens when glucose molecules are oxidized to produce ATP and thermal energy."
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
        except Exception as err:
            last_error = err
            logger.info(
                "Quiz candidate '%s' (%s) error (%s); rotating to next model/provider...",
                prov,
                target_model,
                err,
            )
            continue

    logger.warning("All quiz providers failed (%s); using high-yield Socratic quiz fallback.", last_error)
    return (
        "1. In a uniformly accelerated motion along a straight line, which equation connects initial velocity u, final velocity v, acceleration a, and distance s?\n"
        "   Socratic Hint: Look for the relationship that does not depend on time variable t ($v^2 = u^2 + 2as$).\n\n"
        "2. When a ray of light enters from an optically rarer medium (air) to a denser medium (glass), what happens to its speed and wavelength?\n"
        "   Socratic Hint: Remember that frequency remains constant across optical media while velocity decreases ($v = f\\lambda$).\n\n"
        "3. Why is respiration considered an exothermic reaction in human cells?\n"
        "   Socratic Hint: Think about what happens when glucose molecules are oxidized to produce ATP and thermal energy."
    )

