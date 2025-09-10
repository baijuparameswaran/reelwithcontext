from __future__ import annotations
from typing import Optional, Any, Dict, List, Union
from pydantic import BaseModel, field_validator, ValidationError


class Segment(BaseModel):
    idx: int
    title: str
    narration: str
    hint: str = ""
    image: Optional[str] = None
    start: float = 0.0
    duration: float = 0.0
    meta: Dict[str, Any] = {}

    @field_validator('narration')
    @classmethod
    def narration_not_empty(cls, v: str):
        if not v or not v.strip():
            raise ValueError('Narration must be non-empty')
        return v

    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str):
        if not v.strip():
            return 'Untitled'
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    def __getitem__(self, item: str):  # backward compatibility
        return getattr(self, item)


def normalize_segments(raw_segments: List[Union[dict, Segment]]) -> List[Segment]:
    out: List[Segment] = []
    for s in raw_segments:
        if isinstance(s, Segment):
            out.append(s)
        else:
            try:
                out.append(Segment(**s))
            except ValidationError as e:
                raise ValueError(f"Invalid segment data: {e}") from e
    return out


def validate_segments(segments: List[Segment], require_images: bool = False) -> None:
    if not segments:
        raise ValueError("No segments produced")
    idxs = [s.idx for s in segments]
    if idxs != list(range(len(segments))):
        raise ValueError(f"Segment indices not sequential: {idxs}")
    for s in segments:
        if len(s.narration.split()) > 60:
            raise ValueError(f"Narration too long (>60 words) in segment {s.idx}")
        if require_images and not s.image:
            raise ValueError(f"Missing image in segment {s.idx} while images required")
