"""Unit tests for Thai Phonetic Input CLI."""

import pytest
from main import (
    thai_soundex,
    levenshtein_distance,
    find_matches,
    build_corpus,
    KNOWN_MAPPINGS,
)


class TestThaiSoundex:
    """Tests for the Thai-aware soundex function."""

    def test_basic_soundex(self):
        """Test basic soundex generation."""
        assert thai_soundex("narak") != ""
        assert thai_soundex("kon") != ""

    def test_similar_consonants_group(self):
        """Similar consonants should produce same code."""
        # k and c are same group (velar)
        assert thai_soundex("kat")[0] == thai_soundex("cat")[0]
        # g and k are same group
        assert thai_soundex("gai")[0] == thai_soundex("kai")[0]

    def test_liquid_sounds_group(self):
        """l and r should be in same group (liquids)."""
        sx_l = thai_soundex("la")
        sx_r = thai_soundex("ra")
        assert sx_l[0] == sx_r[0]  # Both should map to '5'

    def test_nasal_sounds_group(self):
        """n and m should be in same group (nasals)."""
        sx_n = thai_soundex("na")
        sx_m = thai_soundex("ma")
        assert sx_n[0] == sx_m[0]  # Both should map to '4'

    def test_vowel_normalization(self):
        """Vowel variants should normalize."""
        # ai and ay should both become 'I'
        assert "I" in thai_soundex("mai")
        assert "I" in thai_soundex("may")
        # ee should become 'I'
        assert "I" in thai_soundex("dee")

    def test_empty_string(self):
        """Empty string should return empty soundex."""
        assert thai_soundex("") == ""
        assert thai_soundex("   ") == ""

    def test_length_limit(self):
        """Soundex should respect length limit."""
        sx = thai_soundex("abcdefghijklmnop", length=4)
        assert len(sx) <= 4


class TestLevenshteinDistance:
    """Tests for edit distance calculation."""

    def test_identical_strings(self):
        assert levenshtein_distance("narak", "narak") == 0
        assert levenshtein_distance("", "") == 0

    def test_single_substitution(self):
        assert levenshtein_distance("narak", "narok") == 1

    def test_single_deletion(self):
        assert levenshtein_distance("narak", "arak") == 1

    def test_single_insertion(self):
        assert levenshtein_distance("narak", "naraks") == 1

    def test_empty_string(self):
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "") == 3

    def test_completely_different(self):
        assert levenshtein_distance("abc", "xyz") == 3


class TestFindMatches:
    """Tests for the main matching function."""

    @pytest.fixture
    def sample_corpus(self):
        """Small corpus for testing."""
        return [
            {"thai": "น่ารัก", "romanized": "narak", "soundex": thai_soundex("narak")},
            {"thai": "คน", "romanized": "kon", "soundex": thai_soundex("kon")},
            {"thai": "นาค", "romanized": "nak", "soundex": thai_soundex("nak")},
            {"thai": "รัก", "romanized": "rak", "soundex": thai_soundex("rak")},
        ]

    def test_exact_match(self, sample_corpus):
        """Exact romanization should return highest score."""
        matches = find_matches("narak", sample_corpus)
        assert len(matches) > 0
        assert matches[0]["thai"] == "น่ารัก"
        assert matches[0]["score"] == 100
        assert matches[0]["match_type"] == "exact"

    def test_partial_match(self, sample_corpus):
        """Similar input should still find matches."""
        matches = find_matches("narok", sample_corpus)
        # Should find narak with high score due to soundex similarity
        thai_results = [m["thai"] for m in matches]
        assert "น่ารัก" in thai_results

    def test_empty_input(self, sample_corpus):
        """Empty input returns no matches."""
        matches = find_matches("", sample_corpus)
        assert len(matches) == 0
        matches = find_matches("   ", sample_corpus)
        assert len(matches) == 0


class TestKnownMappings:
    """Test that known mappings work correctly."""

    @pytest.fixture(scope="class")
    def corpus(self):
        """Build corpus once for all tests in this class."""
        return build_corpus(size=100)

    @pytest.mark.parametrize(
        "romanized,expected_thai",
        [
            ("kon", "คน"),
            ("narak", "น่ารัก"),
            ("sawatdee", "สวัสดี"),
            ("rak", "รัก"),
            ("mai", "ไม่"),
            ("chai", "ใช่"),
            ("dee", "ดี"),
        ],
    )
    def test_known_mapping(self, corpus, romanized, expected_thai):
        """Test that known mappings are found correctly."""
        matches = find_matches(romanized, corpus)
        assert len(matches) > 0, f"No matches found for '{romanized}'"
        # Expected word should be in results
        thai_results = [m["thai"] for m in matches]
        assert expected_thai in thai_results, (
            f"Expected '{expected_thai}' for input '{romanized}', got {thai_results}"
        )


class TestCorpusBuilding:
    """Tests for corpus generation."""

    def test_corpus_has_known_mappings(self):
        """Corpus should include known mappings."""
        corpus = build_corpus(size=50)
        corpus_thai = {entry["thai"] for entry in corpus}

        # Check that some known words are in corpus
        known_thai = {thai for _, thai in KNOWN_MAPPINGS}
        overlap = corpus_thai & known_thai
        assert len(overlap) > 0, "Corpus should include known mappings"

    def test_corpus_structure(self):
        """Each entry should have required fields."""
        corpus = build_corpus(size=10)
        for entry in corpus:
            assert "thai" in entry
            assert "romanized" in entry
            assert "soundex" in entry
            assert entry["romanized"]  # Not empty
            assert entry["soundex"]  # Not empty

    def test_corpus_size(self):
        """Corpus should have requested size (or close to it)."""
        corpus = build_corpus(size=100)
        assert len(corpus) >= 90  # Allow some tolerance
