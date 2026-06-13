from pydantic import BaseModel
from typing import List, Optional

class MatchRequest(BaseModel):
    text: str

class MatchResponse(BaseModel):
    category: dict
    score: float
    entities: Optional[List[dict]] = []

class TaxUpdate(BaseModel):
    category: str
    example: str

class FeedbackItem(BaseModel):
    text: str
    correct_category: str

class FeedbackRequest(BaseModel):
    feedback: List[FeedbackItem]
