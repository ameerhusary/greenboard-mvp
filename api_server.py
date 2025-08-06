# api_server.py
from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional
from search_engine import ContributionSearchEngine 
from fastapi.middleware.cors import CORSMiddleware
import threading

app = FastAPI(title="Political Contribution Search API")
search_engine = ContributionSearchEngine(db_path="contributions.db")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Pydantic request models ----
class SearchRequest(BaseModel):
    first_name: str
    last_name: str
    city: Optional[str] = None
    limit: int = 10

class BulkSearchRequest(BaseModel):
    names: List[str]  # e.g. ["John Smith", "Jane Doe"]
    city: Optional[str] = None
    limit: int = 10

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/bulk_search")
def bulk_search(req: BulkSearchRequest):
    names_string = ", ".join(req.names)
    results, summary = search_engine.bulk_search(names_string, req.city, req.limit)
    # Replace NaN with None for JSON serialization
    results = results.where(pd.notnull(results), None)
    return {
        "summary": summary,
        "results": results.to_dict(orient="records")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)