# Phonetic CLI Issues & Improvements

## Current Issues

### 1. Missing Proper Nouns
**Problem**: Country names and famous people names not matching well.

| Input | Expected | Got |
|-------|----------|-----|
| `angkrid` | อังกฤษ (England) | อย่างกฤษณ์ |
| `thaksin` | ทักษิณ (Thaksin) | ศักสิ้น |
| `radsia` | รัสเซีย (Russia) | ราชเสีย |

**Solution**: Add proper noun corpus:
- Country names (อังกฤษ, รัสเซีย, ญี่ปุ่น, etc.)
- Famous Thai people names
- City names

### 2. N-gram Ranking Not Implemented
**Problem**: Current matching uses simple soundex + edit distance.
Better results possible with bi-gram/tri-gram analysis.

**Solution**: Implement n-gram similarity scoring:
```python
def ngram_similarity(s1: str, s2: str, n: int = 2) -> float:
    """Calculate Jaccard similarity of n-grams."""
    def get_ngrams(s, n):
        return set(s[i:i+n] for i in range(len(s) - n + 1))

    ngrams1 = get_ngrams(s1, n)
    ngrams2 = get_ngrams(s2, n)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    return intersection / union
```

### 3. Known Mappings to Add

```python
# Countries
("angkrit", "อังกฤษ"),
("angkrid", "อังกฤษ"),
("russia", "รัสเซีย"),
("radsia", "รัสเซีย"),
("japan", "ญี่ปุ่น"),
("yipun", "ญี่ปุ่น"),
("china", "จีน"),
("jeen", "จีน"),
("korea", "เกาหลี"),
("kaoli", "เกาหลี"),
("america", "อเมริกา"),
("india", "อินเดีย"),
("germany", "เยอรมนี"),
("france", "ฝรั่งเศส"),

# Famous people
("thaksin", "ทักษิณ"),
("yinglak", "ยิ่งลักษณ์"),
("prayut", "ประยุทธ์"),
```

## Proposed Improvements

### Priority 1: Add Proper Nouns
- Add countries, cities, famous people to KNOWN_MAPPINGS
- Higher frequency boost for proper nouns

### Priority 2: Bi-gram/Tri-gram Scoring
- Calculate n-gram similarity as additional scoring factor
- Weight: `score += ngram_similarity * 20`

### Priority 3: Prefix Matching
- Boost words that start with same prefix
- `angkr` should strongly prefer `อังกฤษ` over `อย่าง...`

## Test Cases to Fix
```
angkrit → อังกฤษ
angkrid → อังกฤษ
thaksin → ทักษิณ
radsia → รัสเซีย
russia → รัสเซีย
yipun → ญี่ปุ่น
```
