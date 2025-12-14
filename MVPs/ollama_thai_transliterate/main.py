#!/usr/bin/env python3
"""CLI for Thai transliteration using AI models."""

import argparse
import sys

from transliterator import ThaiTransliterator


def main():
    parser = argparse.ArgumentParser(
        description="Thai transliteration from English phonetic input"
    )
    parser.add_argument(
        "--url",
        default="http://vedas:8000/v1",
        help="vLLM/OpenAI API base URL (default: http://vedas:8000/v1)",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B",
        help="Model to use (default: Qwen/Qwen3-0.6B)",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="English phonetic input (if not provided, enters REPL mode)",
    )
    args = parser.parse_args()

    trans = ThaiTransliterator(base_url=args.url, model=args.model)

    if args.input:
        # Single query mode
        suggestions, elapsed = trans.transliterate(args.input)
        print(f"Thai: {' | '.join(suggestions)}")
        print(f"({elapsed:.3f}s)")
    else:
        # REPL mode
        print(f"Thai Transliterator (using {args.model})")
        print("Type English phonetic text, get Thai suggestions.")
        print("Type 'quit' or Ctrl+C to exit.\n")

        while True:
            try:
                user_input = input("en> ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    break

                suggestions, elapsed = trans.transliterate(user_input)
                if suggestions:
                    print(f"th> {suggestions[0]}")
                    if len(suggestions) > 1:
                        print(f"    alt: {' | '.join(suggestions[1:])}")
                else:
                    print("th> (no suggestion)")
                print(f"    ({elapsed:.3f}s)\n")

            except KeyboardInterrupt:
                print("\nBye!")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
