"""Few-shot examples for Thai transliteration."""

# Examples from test.csv - English phonetic → Thai
EXAMPLES = [
    ("kon", "คน"),
    ("narak", "น่ารัก"),
    ("kraikinkaikai", "ใครกินไข่ไก่"),
    ("kunmaechop", "คุณแม่ชอบ"),
    ("anakot", "อนาคต"),
    ("kunmae", "คุณแม่"),
    ("lokpaiprasat", "โรคปลายประสาท"),
    ("popainai", "พ่อไปไหน"),
    ("wainee", "วันนี้"),
    ("mainaloei", "ไม่น่าเลย"),
    ("taksin", "ทักษิณ"),
    ("mankoimainaerok", "มันก็ไม่แน่หรอก"),
]


def format_examples_for_prompt(examples: list[tuple[str, str]] | None = None) -> str:
    """Format examples as few-shot prompt text."""
    if examples is None:
        examples = EXAMPLES

    lines = []
    for eng, thai in examples:
        lines.append(f'"{eng}" → {thai}')
    return "\n".join(lines)


def get_system_prompt() -> str:
    """Get the system prompt for Thai transliteration."""
    examples_text = format_examples_for_prompt()
    return f"""You are a Thai transliteration assistant. Given English phonetic input (romanized Thai), output the corresponding Thai word or phrase.

Rules:
1. Output ONLY Thai text, no explanations
2. If the input is incomplete, guess the most likely Thai word
3. Output up to 3 suggestions, one per line, most likely first
4. If unsure, output the most common Thai word matching the pattern

Examples:
{examples_text}

Respond with Thai text only, no other text."""
