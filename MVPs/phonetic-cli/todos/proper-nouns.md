# Task: Integrate pythainlp Proper Noun Corpuses

## Status: In Progress

## Objective
Replace manual `KNOWN_MAPPINGS` for proper nouns with pythainlp's built-in corpus modules.

## Available Corpus Modules

| Module | Size | Priority | Description |
|--------|------|----------|-------------|
| `countries()` | 247 | High (900K) | Country names |
| `provinces()` | 77 | High (800K) | Thai provinces |
| `thai_male_names()` | 7,124 | Medium (500K) | Male given names |
| `thai_female_names()` | 5,098 | Medium (500K) | Female given names |
| `thai_family_names()` | 9,836 | Low (300K) | Thai surnames |
| `thai_wikipedia_titles()` | 290,055 | Low (100K) | Wikipedia titles |

## Implementation Steps

- [ ] Add new imports from pythainlp.corpus
- [ ] Create `ROMANIZATION_OVERRIDES` dict for pythainlp mistakes
- [ ] Add `category` column to database schema
- [ ] Update `build_database()` to load proper nouns
- [ ] Test with country/name queries
- [ ] Rebuild corpus.db

## Romanization Overrides Needed

pythainlp's `romanize()` sometimes produces non-intuitive romanizations. Override these:

```python
ROMANIZATION_OVERRIDES = {
    "อังกฤษ": ["angkrit", "angkrid", "england"],
    "รัสเซีย": ["russia", "radsia"],
    "ทักษิณ": ["thaksin", "taksina"],
    "ญี่ปุ่น": ["japan", "yipun"],
    "เยอรมนี": ["germany", "yeramani"],
    "ฝรั่งเศส": ["france", "farangset"],
}
```

## Expected Results

| Query | Expected | Source |
|-------|----------|--------|
| `angkrit` | อังกฤษ | countries() + override |
| `chiangmai` | เชียงใหม่ | provinces() |
| `somchai` | สมชาย | thai_male_names() |
| `thaksin` | ทักษิณ | wikipedia + override |

## Notes

- All pythainlp corpus functions return Thai text only (frozenset)
- Romanization must be generated using `romanize(thai, engine="royin")`
- Current manual KNOWN_MAPPINGS: 112 entries
- After integration: ~87,000 entries total
