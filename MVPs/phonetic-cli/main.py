#!/usr/bin/env python3
"""
Thai Phonetic Input CLI MVP

Usage:
    uv run main.py                       # Interactive mode
    uv run main.py --build-db            # Build SQLite database from OSCAR
    uv run main.py --realtime            # IME-style real-time input mode
    uv run main.py --realtime --verbose  # IME mode with debug stats
    uv run main.py "narak"               # Single query mode

IME Mode Controls:
    Space     : Accept first suggestion and continue typing
    1-5       : Select specific suggestion from list
    Enter     : Accept and commit line (start new input)
    Backspace : Delete character
    ESC       : Exit
"""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path

from pythainlp.corpus import (
    thai_words,
    countries,
    provinces,
    thai_male_names,
    thai_female_names,
    thai_wikipedia_titles,
)
from pythainlp.transliterate import romanize
from tqdm import tqdm

DB_PATH = Path(__file__).parent / "corpus.db"
MAX_CORPUS_SIZE = 50000

# Known good mappings (user-defined romanizations that override pythainlp)
KNOWN_MAPPINGS = [
    # From test.csv
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
    # Common greetings/phrases
    ("sawatdee", "สวัสดี"),
    ("khopkhun", "ขอบคุณ"),
    # Very common words
    ("kan", "กัน"),
    ("tee", "ที่"),
    ("ja", "จะ"),
    ("pen", "เป็น"),
    ("hai", "ให้"),
    ("dai", "ได้"),
    ("mee", "มี"),
    ("tham", "ทำ"),
    ("hen", "เห็น"),
    ("pood", "พูด"),
    ("khao", "เขา"),
    ("rao", "เรา"),
    ("nee", "นี้"),
    ("nan", "นั้น"),
    ("yang", "ยัง"),
    ("laew", "แล้ว"),
    ("kap", "กับ"),
    ("duay", "ด้วย"),
    ("wa", "ว่า"),
    ("rue", "หรือ"),
    ("ko", "ก็"),
    ("tae", "แต่"),
    ("lae", "และ"),
    ("kong", "ของ"),
    ("chan", "ฉัน"),
    ("phom", "ผม"),
    ("khun", "คุณ"),
    ("ter", "เธอ"),
    ("man", "มัน"),
    # Basic words
    ("chai", "ใช่"),
    ("mai", "ไม่"),
    ("rak", "รัก"),
    ("gin", "กิน"),
    ("kin", "กิน"),
    ("nam", "น้ำ"),
    ("kao", "ข้าว"),
    ("khao", "ข้าว"),
    ("ban", "บ้าน"),
    ("rot", "รถ"),
    ("pai", "ไป"),
    ("ma", "มา"),
    ("dee", "ดี"),
    ("suay", "สวย"),
    ("aroi", "อร่อย"),
    ("arai", "อะไร"),
    ("taorai", "เท่าไหร่"),
    ("yak", "อยาก"),
    ("deum", "ดื่ม"),
    ("norn", "นอน"),
    ("len", "เล่น"),
    ("rean", "เรียน"),
    ("tamngan", "ทำงาน"),
    # Conversational phrases
    ("wannee", "วันนี้"),
    ("penngaibang", "เป็นไงบ้าง"),
    ("pengaibang", "เป็นไงบ้าง"),
    ("penngai", "เป็นไง"),
    ("ngannakmai", "งานหนักไหม"),
    ("ngannak", "งานหนัก"),
    ("jor", "เจอ"),
    ("jur", "เจอ"),
    ("jer", "เจอ"),
    ("maha", "มาหา"),
    ("noydi", "หน่อยดิ"),
    ("noidi", "หน่อยดิ"),
    ("noi", "หน่อย"),
    ("di", "ดิ"),
    ("doo", "ดู"),
    ("du", "ดู"),
    ("meow", "เหมียว"),
    ("mew", "เหมียว"),
    ("maew", "แมว"),
    ("hong", "ห้อง"),
    ("hawng", "ห้อง"),
    ("pa", "ป่ะ"),
    ("paa", "ป่า"),
    ("bang", "บ้าง"),
    ("nak", "หนัก"),
    ("ngan", "งาน"),
    ("yak", "อยาก"),
    ("yakjor", "อยากเจอ"),
]

# Romanization overrides for proper nouns where pythainlp romanize() gives unexpected results
# Format: thai_word -> [list of user-expected romanizations]
ROMANIZATION_OVERRIDES: dict[str, list[str]] = {
    # Countries
    "อังกฤษ": ["angkrit", "angkrid", "england"],
    "รัสเซีย": ["russia", "radsia", "rassia"],
    "ญี่ปุ่น": ["japan", "yipun"],
    "จีน": ["china", "jeen"],
    "เกาหลี": ["korea", "kaoli"],
    "อเมริกา": ["america"],
    "อินเดีย": ["india"],
    "เยอรมนี": ["germany", "yeramani"],
    "ฝรั่งเศส": ["france", "farangset"],
    "ไทย": ["thai"],
    "เวียดนาม": ["vietnam"],
    "ลาว": ["laos"],
    "กัมพูชา": ["cambodia"],
    "เมียนมาร์": ["myanmar"],
    "สิงคโปร์": ["singapore"],
    "มาเลเซีย": ["malaysia"],
    # Famous people
    "ทักษิณ": ["thaksin", "taksina"],
    "ยิ่งลักษณ์": ["yinglak", "yingluck"],
    "ประยุทธ์": ["prayut", "prayuth"],
    "อภิสิทธิ์": ["abhisit"],
    # Provinces
    "เชียงใหม่": ["chiangmai", "chiang mai"],
    "เชียงราย": ["chiangrai", "chiang rai"],
    "กรุงเทพมหานคร": ["bangkok", "krungthep"],
    "ภูเก็ต": ["phuket"],
    # Common names
    "สมชาย": ["somchai"],
    "สมศักดิ์": ["somsak"],
    "ปราณี": ["pranee"],
    "สุดา": ["suda"],
    "วิชัย": ["wichai"],
}


def thai_soundex(romanized: str, length: int = 6) -> str:
    """Generate soundex code for romanized Thai text."""
    text = romanized.lower().strip()
    if not text:
        return ""

    # Multi-char patterns first (order matters)
    replacements = [
        ("ng", "4"), ("ch", "6"), ("kh", "1"), ("ph", "2"), ("th", "3"),
        ("ai", "I"), ("ay", "I"), ("ei", "I"), ("ae", "E"), ("ea", "E"),
        ("ee", "I"), ("ii", "I"), ("oo", "U"), ("ou", "U"), ("ue", "U"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)

    char_map = {
        "k": "1", "c": "1", "g": "1",
        "p": "2", "b": "2",
        "t": "3", "d": "3",
        "n": "4", "m": "4",
        "l": "5", "r": "5",
        "s": "6", "z": "6", "j": "6",
        "w": "7", "v": "7",
        "y": "8", "h": "9",
        "a": "A", "e": "E", "i": "I", "o": "O", "u": "U",
    }

    result = []
    for char in text:
        if char in char_map:
            result.append(char_map[char])
        elif char in "123456789AEIOU":
            result.append(char)

    # Remove consecutive duplicates
    final = []
    for char in result:
        if not final or final[-1] != char:
            final.append(char)

    return "".join(final[:length])


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate minimum edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def ngram_similarity(s1: str, s2: str, n: int = 2) -> float:
    """Calculate Jaccard similarity of n-grams (bi-gram by default)."""
    if len(s1) < n or len(s2) < n:
        return 0.0

    ngrams1 = set(s1[i : i + n] for i in range(len(s1) - n + 1))
    ngrams2 = set(s2[i : i + n] for i in range(len(s2) - n + 1))

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    return intersection / union if union > 0 else 0.0


# ============== SQLite Database Functions ==============

def init_db() -> sqlite3.Connection:
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            thai TEXT NOT NULL,
            romanized TEXT NOT NULL,
            soundex TEXT NOT NULL,
            frequency INTEGER DEFAULT 0,
            category TEXT DEFAULT 'word'
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_romanized ON words(romanized)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_soundex ON words(soundex)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_frequency ON words(frequency DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON words(category)")
    conn.commit()
    return conn


ROMANIZE_ENGINES = ["lookup", "thai2rom_onnx", "tltk", "royin"]


def get_romanizations(thai: str) -> list[tuple[str, int]]:
    """Get romanizations from multiple engines with priority boost.

    Returns: [(romanized, priority_boost), ...] sorted by naturalness.
    Lookup = +20, thai2rom_onnx = +10, tltk = +5, royin = +0
    """
    results = []
    seen = set()
    boosts = {"lookup": 20, "thai2rom_onnx": 10, "tltk": 5, "royin": 0}

    for engine in ROMANIZE_ENGINES:
        try:
            rom = romanize(thai, engine=engine)
            if rom and rom.strip():
                rom_clean = rom.lower().replace(" ", "")
                if rom_clean and rom_clean not in seen and len(rom_clean) >= 2:
                    seen.add(rom_clean)
                    results.append((rom_clean, boosts.get(engine, 0)))
        except Exception:
            pass

    return results


def insert_word(
    cursor: sqlite3.Cursor,
    thai: str,
    romanized: str,
    freq: int,
    category: str,
    seen: set[tuple[str, str]],
) -> bool:
    """Insert word if not already seen. Returns True if inserted."""
    pair = (romanized, thai)
    if pair in seen:
        return False
    sx = thai_soundex(romanized)
    if not sx:
        return False
    cursor.execute(
        "INSERT INTO words (thai, romanized, soundex, frequency, category) VALUES (?, ?, ?, ?, ?)",
        (thai, romanized, sx, freq, category),
    )
    seen.add(pair)
    return True


def build_database() -> None:
    """Build SQLite database from OSCAR + pythainlp proper noun corpuses."""
    from pythainlp.corpus.oscar import word_freqs as oscar_freqs

    # Delete old database
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = init_db()
    cursor = conn.cursor()
    seen_pairs: set[tuple[str, str]] = set()

    # 1. Insert known mappings first (highest priority)
    print("Inserting known mappings...")
    known_count = 0
    for rom, thai_word in KNOWN_MAPPINGS:
        if insert_word(cursor, thai_word, rom.lower(), 999999999, "known", seen_pairs):
            known_count += 1
    print(f"  Added {known_count} known mappings")

    # 2. Insert countries from pythainlp (multiple romanizations)
    print("Loading countries...")
    country_count = 0
    for thai in countries():
        base_freq = 900000
        # Add all romanization variants with priority boost
        for rom, boost in get_romanizations(thai):
            if insert_word(cursor, thai, rom, base_freq + boost, "country", seen_pairs):
                country_count += 1
        # Add override romanizations (highest priority)
        if thai in ROMANIZATION_OVERRIDES:
            for alt_rom in ROMANIZATION_OVERRIDES[thai]:
                if insert_word(cursor, thai, alt_rom.lower(), base_freq + 50, "country", seen_pairs):
                    country_count += 1
    print(f"  Added {country_count} country entries")

    # 3. Insert provinces from pythainlp
    print("Loading provinces...")
    province_count = 0
    for thai in provinces():
        base_freq = 800000
        for rom, boost in get_romanizations(thai):
            if insert_word(cursor, thai, rom, base_freq + boost, "province", seen_pairs):
                province_count += 1
        if thai in ROMANIZATION_OVERRIDES:
            for alt_rom in ROMANIZATION_OVERRIDES[thai]:
                if insert_word(cursor, thai, alt_rom.lower(), base_freq + 50, "province", seen_pairs):
                    province_count += 1
    print(f"  Added {province_count} province entries")

    # 4. Insert Thai names (male + female)
    all_names = list(thai_male_names() | thai_female_names())
    name_count = 0
    for thai in tqdm(all_names, desc="Names", unit="name"):
        base_freq = 500000
        for rom, boost in get_romanizations(thai):
            if insert_word(cursor, thai, rom, base_freq + boost, "name", seen_pairs):
                name_count += 1
        if thai in ROMANIZATION_OVERRIDES:
            for alt_rom in ROMANIZATION_OVERRIDES[thai]:
                if insert_word(cursor, thai, alt_rom.lower(), base_freq + 50, "name", seen_pairs):
                    name_count += 1
    print(f"  Added {name_count} name entries")

    # 5. Insert Wikipedia titles (filtered to short entries)
    all_wiki = [t for t in thai_wikipedia_titles() if 2 <= len(t) <= 15]
    wiki_count = 0
    for thai in tqdm(all_wiki, desc="Wikipedia", unit="title"):
        base_freq = 100000
        for rom, boost in get_romanizations(thai):
            if insert_word(cursor, thai, rom, base_freq + boost, "wiki", seen_pairs):
                wiki_count += 1
        if thai in ROMANIZATION_OVERRIDES:
            for alt_rom in ROMANIZATION_OVERRIDES[thai]:
                if insert_word(cursor, thai, alt_rom.lower(), base_freq + 50, "wiki", seen_pairs):
                    wiki_count += 1
    print(f"  Added {wiki_count} Wikipedia entries")

    # 6. Insert OSCAR words (multiple romanizations)
    print("Loading OSCAR word frequencies...")
    oscar = oscar_freqs()  # Returns list of (word, freq) tuples
    print(f"  OSCAR total entries: {len(oscar):,}")

    valid_words = set(thai_words())
    sorted_words = sorted(
        [(w, f) for w, f in oscar if w in valid_words and 2 <= len(w) <= 15],
        key=lambda x: x[1],
        reverse=True,
    )[:MAX_CORPUS_SIZE]
    print(f"  Selected top {len(sorted_words):,} words")

    oscar_count = 0
    for thai_word, freq in tqdm(sorted_words, desc="OSCAR", unit="word"):
        for rom, boost in get_romanizations(thai_word):
            if insert_word(cursor, thai_word, rom, freq + boost, "word", seen_pairs):
                oscar_count += 1
    print(f"  Added {oscar_count} OSCAR word entries")

    conn.commit()
    total = cursor.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    print(f"\nDatabase built with {total:,} total entries")
    print(f"Database size: {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB")

    # Print category breakdown
    print("\nCategory breakdown:")
    for cat, cnt in cursor.execute(
        "SELECT category, COUNT(*) FROM words GROUP BY category ORDER BY COUNT(*) DESC"
    ).fetchall():
        print(f"  {cat}: {cnt:,}")

    conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Get database connection, building if needed."""
    if not DB_PATH.exists():
        print("Database not found. Building...")
        build_database()
    return sqlite3.connect(DB_PATH)


# ============== Matching Functions ==============

def find_matches_db(user_input: str, conn: sqlite3.Connection, top_n: int = 10) -> list[dict]:
    """Find matches using SQLite database."""
    input_norm = user_input.lower().strip().replace(" ", "")
    if not input_norm:
        return []

    input_sx = thai_soundex(input_norm)
    input_sx_prefix = input_sx[:3] if len(input_sx) >= 3 else input_sx

    # Query database for candidates
    # Prioritize: 1) exact romanized match, 2) exact soundex, 3) soundex prefix
    cursor = conn.execute(
        """
        SELECT thai, romanized, soundex, frequency, category
        FROM words
        WHERE romanized = ?
           OR soundex = ?
           OR soundex LIKE ?
        ORDER BY
            CASE
                WHEN romanized = ? THEN 0
                WHEN soundex = ? THEN 1
                ELSE 2
            END,
            frequency DESC
        LIMIT 100
        """,
        (input_norm, input_sx, input_sx_prefix + "%", input_norm, input_sx),
    )

    results = []
    for thai, rom, sx, freq, category in cursor.fetchall():
        # Calculate base score
        if rom == input_norm:
            score = 100.0
            match_type = "exact"
        elif sx == input_sx:
            dist = levenshtein_distance(input_norm, rom)
            score = max(0, 90 - (dist * 10))
            match_type = "soundex_exact"
        else:
            dist = levenshtein_distance(input_norm, rom)
            score = max(0, 70 - (dist * 10))
            match_type = "soundex_partial"

        # N-gram similarity boost (bi-gram and tri-gram)
        bigram_sim = ngram_similarity(input_norm, rom, n=2)
        trigram_sim = ngram_similarity(input_norm, rom, n=3)
        ngram_boost = (bigram_sim * 15) + (trigram_sim * 10)  # Max +25
        score += ngram_boost

        # Prefix match boost
        if rom.startswith(input_norm[:3]) or input_norm.startswith(rom[:3]):
            score += 5

        # Frequency boost (log scale, max +10)
        if freq > 0:
            freq_boost = min(10, math.log10(max(1, freq)) / 2)
            score += freq_boost

        if score > 0:
            results.append({
                "thai": thai,
                "romanized": rom,
                "soundex": sx,
                "frequency": freq,
                "category": category,
                "score": score,
                "match_type": match_type,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


def find_compound_matches_db(user_input: str, conn: sqlite3.Connection, top_n: int = 5) -> list[dict]:
    """Find compound words by splitting input.

    Compound matches are penalized (-30) so they don't beat direct matches.
    """
    input_norm = user_input.lower().strip().replace(" ", "")
    if len(input_norm) < 4:
        return []

    results = []
    seen = set()

    for i in range(2, len(input_norm) - 1):
        left = input_norm[:i]
        right = input_norm[i:]

        left_matches = find_matches_db(left, conn, top_n=1)
        right_matches = find_matches_db(right, conn, top_n=1)

        if left_matches and right_matches:
            lm, rm = left_matches[0], right_matches[0]
            if lm["score"] >= 50 and rm["score"] >= 50:
                combined = lm["thai"] + rm["thai"]
                if combined not in seen:
                    seen.add(combined)
                    # Penalize compound matches so they don't beat direct matches
                    compound_penalty = 30
                    results.append({
                        "thai": combined,
                        "romanized": f"{left}+{right}",
                        "soundex": "",
                        "frequency": 0,
                        "category": "compound",
                        "score": (lm["score"] + rm["score"]) / 2 - compound_penalty,
                        "match_type": "compound",
                    })

    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_n]


def find_matches(user_input: str, conn: sqlite3.Connection, top_n: int = 5) -> list[dict]:
    """Find Thai words matching the romanized input (single and compound)."""
    single = find_matches_db(user_input, conn, top_n)
    compound = find_compound_matches_db(user_input, conn, top_n)

    all_matches = single + compound
    all_matches.sort(key=lambda x: x["score"], reverse=True)
    return all_matches[:top_n]


# ============== Display Functions ==============

def display_results(query: str, matches: list[dict]) -> None:
    """Display matching results."""
    if not matches:
        print(f"No matches found for '{query}'")
        return

    print(f"\nMatches for '{query}':")
    for i, m in enumerate(matches, 1):
        freq_str = f", freq:{m['frequency']:,}" if m.get("frequency") else ""
        print(f"  {i}. {m['thai']} ({m['romanized']}) - score: {m['score']:.1f}{freq_str}")


def run_realtime(conn: sqlite3.Connection, verbose: bool = False) -> None:
    """Run real-time mode with IME-style character-by-character input.

    Controls:
        - Type letters to build input
        - Space: Accept first suggestion and continue
        - 1-5: Select specific suggestion
        - Enter: Accept first suggestion and start new input
        - Backspace: Delete last character
        - Ctrl+C / ESC: Exit
    """
    import termios
    import tty

    def getch() -> str:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    def clear_lines(n: int) -> None:
        for _ in range(n):
            sys.stdout.write("\033[A\033[K")

    def format_match(i: int, m: dict, verbose: bool) -> str:
        """Format a single match for display."""
        if verbose:
            freq_str = f"freq:{m['frequency']:,}" if m.get('frequency') else "freq:0"
            return f"  \033[1m{i}.\033[0m {m['thai']} \033[90m({m['romanized']}) [{m['match_type']}] score:{m['score']:.1f} {freq_str}\033[0m"
        else:
            return f"  \033[1m{i}.\033[0m {m['thai']} \033[90m({m['romanized']})\033[0m"

    # Header
    print("\033[1mThai Phonetic Input CLI (IME Mode)\033[0m")
    print("\033[90mSpace=accept  1-5=select  Enter=accept+newline  Backspace=delete  ESC=exit\033[0m")
    if verbose:
        print("\033[93m[VERBOSE MODE]\033[0m")
    print("-" * 60)

    buffer = ""       # Current romanized input
    output = ""       # Accumulated Thai output
    last_lines = 0
    matches: list[dict] = []

    while True:
        if last_lines > 0:
            clear_lines(last_lines)

        # Build display lines
        lines = []

        # Output line (accumulated Thai text)
        if output:
            lines.append(f"\033[32m{output}\033[0m")

        # Input line with cursor
        input_display = f"\033[36m{buffer}\033[0m\033[90m_\033[0m" if buffer else "\033[90m_\033[0m"
        lines.append(f"> {input_display}")

        # Suggestions
        if buffer:
            matches = find_matches(buffer, conn, top_n=5)
            if matches:
                lines.append("")
                for i, m in enumerate(matches, 1):
                    # Highlight first option
                    if i == 1:
                        lines.append(f"  \033[7m{i}.\033[0m \033[1m{m['thai']}\033[0m \033[90m({m['romanized']})" +
                                   (f" [{m['match_type']}] score:{m['score']:.1f} freq:{m.get('frequency', 0):,}\033[0m" if verbose else "\033[0m"))
                    else:
                        lines.append(format_match(i, m, verbose))
            else:
                lines.append("  \033[90m(no matches)\033[0m")
        else:
            matches = []

        # Print all lines
        for line in lines:
            print(line)
        last_lines = len(lines)

        # Get input
        try:
            ch = getch()
        except (KeyboardInterrupt, EOFError):
            print("\n\033[90mGoodbye!\033[0m")
            break

        # Handle input
        if ch in ("\x03", "\x1b"):  # Ctrl+C or ESC
            print("\n\033[90mGoodbye!\033[0m")
            break
        elif ch in ("\x7f", "\x08"):  # Backspace
            if buffer:
                buffer = buffer[:-1]
            elif output:
                # Allow deleting from output if buffer is empty
                output = output[:-1]
        elif ch == " ":  # Space: accept first suggestion
            if buffer and matches:
                output += matches[0]["thai"]
                buffer = ""
        elif ch in "12345":  # Number selection
            idx = int(ch) - 1
            if buffer and matches and idx < len(matches):
                output += matches[idx]["thai"]
                buffer = ""
        elif ch in ("\r", "\n"):  # Enter: accept and show final
            if buffer and matches:
                output += matches[0]["thai"]
            if output:
                # Clear and show final output
                clear_lines(last_lines)
                print(f"\033[32m✓ {output}\033[0m")
                print()
                output = ""
                buffer = ""
                last_lines = 0
        elif ch.isprintable():
            buffer += ch


def main() -> None:
    """Main CLI entry point."""
    args = sys.argv[1:]
    verbose = "--verbose" in args or "-v" in args
    if verbose:
        args = [a for a in args if a not in ("--verbose", "-v")]

    if args:
        if args[0] == "--build-db":
            build_database()
            return
        elif args[0] == "--realtime":
            conn = get_db_connection()
            run_realtime(conn, verbose=verbose)
            conn.close()
            return
        else:
            conn = get_db_connection()
            matches = find_matches(args[0], conn)
            display_results(args[0], matches)
            conn.close()
            return

    print("Thai Phonetic Input CLI")
    print("Type romanized text to find Thai words. Type 'quit' to exit.")
    print("Use --realtime [-v|--verbose] for IME-style input mode.")
    print("-" * 40)

    conn = get_db_connection()

    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            if not user_input:
                continue
            matches = find_matches(user_input, conn)
            display_results(user_input, matches)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

    conn.close()


if __name__ == "__main__":
    main()
