from pydantic import BaseModel
from typing import List

class Source(BaseModel):
    file_name: str
    page: str = "N/A"

class QueryRequest(BaseModel):
    question: str
    pdf_collection_id: str
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]