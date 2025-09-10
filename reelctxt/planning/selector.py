from __future__ import annotations
from typing import List, Dict
from .segment import Segment
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def select_images_for_segments(segments: List[Segment], images: List[Dict], corpus_texts: List[str]):
    # Build a tf-idf matrix over corpus + segment narrations using their text
    if not images:
        return
    texts = corpus_texts + [s['narration'] for s in segments]
    vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
    X = vectorizer.fit_transform(texts)
    corpus_X = X[:len(corpus_texts)]
    seg_X = X[len(corpus_texts):]

    # For now treat each image equally (no vision embedding). Future: CLIP embeddings.
    # We just assign images round-robin weighted by segment length.
    img_paths = [im['path'] for im in images]
    for i, seg in enumerate(segments):
        seg_vec = seg_X[i]
        # similarity to corpus texts to find most representative text, then choose image by index
        sims = cosine_similarity(seg_vec, corpus_X).ravel()
        top_idx = int(np.argmax(sims)) if sims.size else 0
        seg.image = img_paths[top_idx % len(img_paths)]
