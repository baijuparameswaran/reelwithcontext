from reelctxt.planning.segment import Segment, validate_segments, normalize_segments
import pytest


def test_segment_roundtrip_and_validation():
    raw = [
        {"idx": 0, "title": "Intro", "narration": "Hello world"},
        {"idx": 1, "title": "Point", "narration": "A short point."},
    ]
    segs = normalize_segments(raw)
    validate_segments(segs)
    assert segs[0].title == "Intro"
    assert segs[1].idx == 1


def test_segment_validation_failure_long_narration():
    long_text = "word " * 61
    segs = [Segment(idx=0, title="TooLong", narration=long_text)]
    with pytest.raises(ValueError):
        validate_segments(segs)
