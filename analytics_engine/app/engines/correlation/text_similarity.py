"""Investigation Note Text Similarity Analyzer using TF-IDF and Jaccard."""

from collections import defaultdict
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from shared.logging import logger
from ..execution_gap.interpreter import LogicInterpreter
from .models import CorrelationDraft

# Standard English stop words
STOP_WORDS: Set[str] = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves",
}


def preprocess_text(text: str) -> Tuple[str, List[str]]:
    """
    Cleans and tokenizes text:
    1. Lowercase
    2. Strip punctuation
    3. Filter stop words
    Returns:
        (clean_text: str, tokens: List[str])
    """
    if not text:
        return "", []

    # 1. Lowercase
    text_lower = text.lower()

    # 2. Punctuation removal
    text_clean = re.sub(r"[^\w\s]", " ", text_lower)

    # 3. Tokenize & filter stop words
    raw_tokens = text_clean.split()
    tokens = [t for t in raw_tokens if len(t) > 2 and t not in STOP_WORDS]

    cleaned_str = " ".join(tokens)
    return cleaned_str, tokens


def compute_jaccard_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Computes Jaccard token similarity = |A intersect B| / |A union B|."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)

    if not set_a or not set_b:
        return 0.0

    intersection = set_a.intersection(set_b)
    union = set_a.union(set_b)

    return float(len(intersection)) / float(len(union))


class NoteSimilarityAnalyzer:
    """Detects boilerplate copy-paste investigation notes using TF-IDF and Jaccard similarity."""

    def __init__(
        self,
        tfidf_threshold: float = 0.85,
        jaccard_threshold: float = 0.80,
        min_tokens: int = 10,
    ):
        self.tfidf_threshold = tfidf_threshold
        self.jaccard_threshold = jaccard_threshold
        self.min_tokens = min_tokens

    def find_similar_notes(
        self,
        investigations: List[Any],
        entity_id: uuid.UUID,
    ) -> List[CorrelationDraft]:
        """
        Analyzes investigation notes and generates correlation links for text clones.
        """
        correlations: List[CorrelationDraft] = []
        if len(investigations) < 2:
            return correlations

        # Prepare corpus of eligible notes
        valid_items: List[Dict[str, Any]] = []

        for inv in investigations:
            raw_text = (
                LogicInterpreter.extract_field_value(inv, "investigation_notes")
                or LogicInterpreter.extract_field_value(inv, "conclusion")
                or LogicInterpreter.extract_field_value(inv, "action_taken")
            )
            if not raw_text:
                continue

            cleaned_str, tokens = preprocess_text(str(raw_text))
            if len(tokens) < self.min_tokens:
                continue

            event_id_raw = LogicInterpreter.extract_field_value(inv, "event_id")
            event_uuid = uuid.UUID(str(event_id_raw)) if event_id_raw else uuid.uuid4()
            case_id = LogicInterpreter.extract_field_value(inv, "case_id") or LogicInterpreter.extract_field_value(inv, "raw_ref_id")
            analyst_id = LogicInterpreter.extract_field_value(inv, "analyst_id") or LogicInterpreter.extract_field_value(inv, "user_id")
            asset_id = LogicInterpreter.extract_field_value(inv, "asset_id")

            valid_items.append({
                "event_uuid": event_uuid,
                "case_id": str(case_id or "Case"),
                "analyst_id": str(analyst_id or "Unknown"),
                "asset_id": str(asset_id or ""),
                "cleaned_str": cleaned_str,
                "tokens": tokens,
                "raw_text": str(raw_text),
            })

        n = len(valid_items)
        if n < 2:
            return correlations

        # Compute TF-IDF matrix
        corpus = [item["cleaned_str"] for item in valid_items]
        try:
            vectorizer = TfidfVectorizer(min_df=1, max_df=1.0)
            tfidf_matrix = vectorizer.fit_transform(corpus)
            cosine_sim_matrix = cosine_similarity(tfidf_matrix)
        except Exception as exc:
            logger.error(f"Error computing TF-IDF matrix: {exc}")
            cosine_sim_matrix = np.zeros((n, n))

        # Vectorized candidate filtering: only inspect pairs with non-trivial cosine similarity
        candidate_mask = np.triu(cosine_sim_matrix >= (self.tfidf_threshold * 0.7), k=1)
        candidate_pairs = np.argwhere(candidate_mask)

        seen_pairs = set()

        for i, j in candidate_pairs:
            item_a = valid_items[i]
            item_b = valid_items[j]

            # If same case_id, skip (we want to detect clones across distinct cases)
            if item_a["case_id"] == item_b["case_id"] and item_a["case_id"] != "Case":
                continue

            pair_key = tuple(sorted([str(item_a["event_uuid"]), str(item_b["event_uuid"])]))
            if pair_key in seen_pairs:
                continue

            cosine_score = float(cosine_sim_matrix[i, j])
            jaccard_score = compute_jaccard_similarity(item_a["tokens"], item_b["tokens"])

            is_similar = (cosine_score >= self.tfidf_threshold) or (jaccard_score >= self.jaccard_threshold)

            if is_similar:
                seen_pairs.add(pair_key)
                max_score = max(cosine_score, jaccard_score)
                shared_tokens = list(set(item_a["tokens"]).intersection(set(item_b["tokens"])))[:15]

                corr = CorrelationDraft(
                    entity_id=entity_id,
                    correlation_type="TFIDF_NOTE_SIMILARITY",
                    primary_event_id=item_a["event_uuid"],
                    correlated_event_id=item_b["event_uuid"],
                    asset_id=item_a["asset_id"] or item_b["asset_id"] or None,
                    similarity_score=round(max_score, 4),
                    shared_attributes={
                        "cosine_similarity": round(cosine_score, 4),
                        "jaccard_similarity": round(jaccard_score, 4),
                        "case_id_a": item_a["case_id"],
                        "case_id_b": item_b["case_id"],
                        "analyst_a": item_a["analyst_id"],
                        "analyst_b": item_b["analyst_id"],
                        "shared_tokens": shared_tokens,
                    },
                    rationale=(
                        f"Investigation note boilerplate clone detected between Case {item_a['case_id']} and "
                        f"Case {item_b['case_id']} (TF-IDF Cosine={round(cosine_score, 2)}, Jaccard={round(jaccard_score, 2)}). "
                        f"Indicates copy-paste rubber-stamp triage."
                    ),
                )
                correlations.append(corr)

        return correlations
