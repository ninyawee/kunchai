# Thai Phonetic CLI - Prayut & Somchaip Engine

Thai phonetic input using the `prayut_and_somchaip` cross-language soundex algorithm from PyThaiNLP.

## Algorithm

Uses the soundex algorithm from:
> "Thai-English cross-language transliterated word retrieval using soundex technique"
> Suwanvisat & Prasitjutrakul, 1998

The algorithm generates phonetic codes that can match across Thai and English text.

## Usage

```bash
# Build database (1M words from OSCAR corpus)
uv run main.py --build-db

# Single query
uv run main.py "kon"

# IME-style realtime mode
uv run main.py --realtime

# With verbose debug stats
uv run main.py --realtime --verbose
```

## IME Controls

| Key | Action |
|-----|--------|
| Space | Accept first suggestion |
| 1-5 | Select specific suggestion |
| Enter | Accept and commit line |
| Backspace | Delete character |
| ESC | Exit |

## Comparison with phonetic-cli

| Feature | phonetic-cli | phonetic-prayut-cli |
|---------|--------------|---------------------|
| Soundex | Custom Thai soundex | prayut_and_somchaip |
| DB Source | Romanization → soundex | Thai text → soundex |
| Corpus | 50K (thai_words filtered) | 1M (OSCAR) |
| Known mappings | Yes (user-defined) | No |

## Limitations

The `prayut_and_somchaip` algorithm was designed for matching **English loanwords** with their **Thai transliterations** (e.g., "King" ↔ "คิง"), not for matching **romanized Thai** with **Thai words** (e.g., "narak" ↔ "น่ารัก").

Results may vary depending on the word type.
