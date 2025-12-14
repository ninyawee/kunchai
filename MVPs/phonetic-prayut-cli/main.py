#!/usr/bin/env python3
"""
Thai Phonetic Input CLI - Prayut & Somchaip Engine

Uses the prayut_and_somchaip cross-language soundex algorithm that can match
romanized English input directly with Thai words.

Reference: "Thai-English cross-language transliterated word retrieval using
soundex technique" (Suwanvisat & Prasitjutrakul, 1998)

Usage:
    uv run main.py                       # Interactive mode
    uv run main.py --build-db            # Build SQLite database
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

from pythainlp.corpus.oscar import word_freqs as oscar_freqs
from pythainlp.soundex import soundex

DB_PATH = Path(__file__).parent / "corpus.db"
MAX_CORPUS_SIZE = 1000000  # 1M words
SOUNDEX_LENGTH = 6  # Longer = more precise matching


def prayut_soundex(text: str, length: int = SOUNDEX_LENGTH) -> str:
    """Generate soundex using prayut_and_somchaip algorithm.

    Works on both Thai text and romanized English, producing matching codes.
    """
    if not text or not text.strip():
        return ""
    try:
        return soundex(text.strip(), engine="prayut_and_somchaip", length=length)
    except Exception:
        return ""


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


# ============== SQLite Database Functions ==============


def init_db() -> sqlite3.Connection:
    """Initialize SQLite database with schema."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY,
            thai TEXT NOT NULL,
            soundex_thai TEXT NOT NULL,
            frequency INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_soundex_thai ON words(soundex_thai)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_frequency ON words(frequency DESC)")
    conn.commit()
    return conn


def is_thai_word(word: str) -> bool:
    """Check if word contains Thai characters."""
    return any("\u0e00" <= c <= "\u0e7f" for c in word)


def build_database() -> None:
    """Build SQLite database from OSCAR word frequencies."""
    print("Loading OSCAR word frequencies...")
    oscar = oscar_freqs()
    print(f"OSCAR entries: {len(oscar):,}")

    print("Filtering Thai words by character range...")
    sorted_words = sorted(
        [(w, f) for w, f in oscar if is_thai_word(w) and 2 <= len(w) <= 15],
        key=lambda x: x[1],
        reverse=True,
    )[:MAX_CORPUS_SIZE]
    print(f"Selected top {len(sorted_words):,} words")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = init_db()
    cursor = conn.cursor()

    print("Building database with prayut_and_somchaip soundex from Thai text...")
    count = 0
    skipped = 0

    for thai_word, freq in sorted_words:
        # Generate soundex directly from Thai text (cross-language feature)
        sx = prayut_soundex(thai_word)
        if sx:
            cursor.execute(
                "INSERT INTO words (thai, soundex_thai, frequency) VALUES (?, ?, ?)",
                (thai_word, sx, freq),
            )
            count += 1
        else:
            skipped += 1

    conn.commit()
    total = cursor.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    print(f"Database built with {total:,} entries (skipped {skipped:,})")
    print(f"Database size: {DB_PATH.stat().st_size / 1024 / 1024:.2f} MB")
    conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Get database connection, building if needed."""
    if not DB_PATH.exists():
        print("Database not found. Building...")
        build_database()
    return sqlite3.connect(DB_PATH)


# ============== Matching Functions ==============


def find_matches(user_input: str, conn: sqlite3.Connection, top_n: int = 5) -> list[dict]:
    """Find Thai words matching the romanized input using prayut_and_somchaip cross-language soundex."""
    input_norm = user_input.lower().strip().replace(" ", "")
    if not input_norm:
        return []

    input_sx = prayut_soundex(input_norm)
    if not input_sx:
        return []

    # Query with prefix matching for flexibility
    input_sx_prefix = input_sx[:3] if len(input_sx) >= 3 else input_sx

    cursor = conn.execute(
        """
        SELECT thai, soundex_thai, frequency
        FROM words
        WHERE soundex_thai = ?
           OR soundex_thai LIKE ?
        ORDER BY frequency DESC
        LIMIT 100
        """,
        (input_sx, input_sx_prefix + "%"),
    )

    results = []
    for thai, sx_thai, freq in cursor.fetchall():
        # Calculate score based on soundex match quality
        if sx_thai == input_sx:
            score = 100.0
            match_type = "exact"
        else:
            # Partial soundex match
            sx_dist = levenshtein_distance(input_sx, sx_thai)
            score = max(0, 80 - (sx_dist * 12))
            match_type = "partial"

        # Frequency boost (log scale, max +10)
        if freq > 0:
            freq_boost = min(10, math.log10(max(1, freq)) / 2)
            score += freq_boost

        if score > 0:
            results.append({
                "thai": thai,
                "soundex_thai": sx_thai,
                "input_soundex": input_sx,
                "frequency": freq,
                "score": score,
                "match_type": match_type,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]


# ============== Display Functions ==============


def display_results(query: str, matches: list[dict]) -> None:
    """Display matching results."""
    if not matches:
        print(f"No matches found for '{query}'")
        return

    input_sx = prayut_soundex(query.lower().strip())
    print(f"\nMatches for '{query}' (input_sx: {input_sx}):")
    for i, m in enumerate(matches, 1):
        freq_str = f", freq:{m['frequency']:,}" if m.get("frequency") else ""
        print(f"  {i}. {m['thai']} (sx:{m['soundex_thai']}) - score: {m['score']:.1f}{freq_str}")


def run_realtime(conn: sqlite3.Connection, verbose: bool = False) -> None:
    """Run real-time mode with IME-style character-by-character input."""
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
            return f"  \033[1m{i}.\033[0m {m['thai']} \033[90m[{m['match_type']}] sx:{m['soundex_thai']} score:{m['score']:.1f} {freq_str}\033[0m"
        else:
            return f"  \033[1m{i}.\033[0m {m['thai']}"

    # Header
    print("\033[1mThai Phonetic CLI - Prayut & Somchaip Engine (IME Mode)\033[0m")
    print("\033[90mSpace=accept  1-5=select  Enter=accept+newline  Backspace=delete  ESC=exit\033[0m")
    if verbose:
        print("\033[93m[VERBOSE MODE]\033[0m")
    print("-" * 65)

    buffer = ""
    output = ""
    last_lines = 0
    matches: list[dict] = []

    while True:
        if last_lines > 0:
            clear_lines(last_lines)

        lines = []

        # Output line (accumulated Thai text)
        if output:
            lines.append(f"\033[32m{output}\033[0m")

        # Input line with cursor and soundex
        if buffer:
            input_sx = prayut_soundex(buffer)
            if verbose:
                input_display = f"\033[36m{buffer}\033[0m \033[90m(sx:{input_sx})\033[0m\033[90m_\033[0m"
            else:
                input_display = f"\033[36m{buffer}\033[0m\033[90m_\033[0m"
        else:
            input_display = "\033[90m_\033[0m"
        lines.append(f"> {input_display}")

        # Suggestions
        if buffer:
            matches = find_matches(buffer, conn, top_n=5)
            if matches:
                lines.append("")
                for i, m in enumerate(matches, 1):
                    if i == 1:
                        # Highlight first option
                        extra = f" [{m['match_type']}] sx:{m['soundex_thai']} score:{m['score']:.1f} freq:{m.get('frequency', 0):,}" if verbose else ""
                        lines.append(f"  \033[7m{i}.\033[0m \033[1m{m['thai']}\033[0m\033[90m{extra}\033[0m")
                    else:
                        lines.append(format_match(i, m, verbose))
            else:
                lines.append("  \033[90m(no matches)\033[0m")
        else:
            matches = []

        for line in lines:
            print(line)
        last_lines = len(lines)

        try:
            ch = getch()
        except (KeyboardInterrupt, EOFError):
            print("\n\033[90mGoodbye!\033[0m")
            break

        if ch in ("\x03", "\x1b"):
            print("\n\033[90mGoodbye!\033[0m")
            break
        elif ch in ("\x7f", "\x08"):
            if buffer:
                buffer = buffer[:-1]
            elif output:
                output = output[:-1]
        elif ch == " ":
            if buffer and matches:
                output += matches[0]["thai"]
                buffer = ""
        elif ch in "12345":
            idx = int(ch) - 1
            if buffer and matches and idx < len(matches):
                output += matches[idx]["thai"]
                buffer = ""
        elif ch in ("\r", "\n"):
            if buffer and matches:
                output += matches[0]["thai"]
            if output:
                clear_lines(last_lines)
                print(f"\033[32m{output}\033[0m")
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

    print("Thai Phonetic CLI - Prayut & Somchaip Engine")
    print("Uses cross-language soundex for Thai-English matching.")
    print("Type romanized text to find Thai words. Type 'quit' to exit.")
    print("Use --realtime [-v|--verbose] for IME-style input mode.")
    print("-" * 50)

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
