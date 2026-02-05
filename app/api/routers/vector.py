from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
import os
from pydantic import BaseModel


router = APIRouter(prefix="/vector", tags=["vector"])


class VectorQueryRequest(BaseModel):
    query: str
    topK: int = 5
    where: Optional[Dict[str, Any]] = None


class VectorRecord(BaseModel):
    id: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = {}


class VectorQueryResponse(BaseModel):
    results: List[VectorRecord]


@router.post("/query", response_model=VectorQueryResponse)
async def query(req: VectorQueryRequest) -> VectorQueryResponse:
    try:
        from ...core.vector_db import VectorDBClient
    except Exception as exc:  # pragma: no cover
        print(f"[Vector Query] Import error: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failure: {exc}") from exc

    client = VectorDBClient(path=os.getenv("VECTOR_DB_PATH", "./vector_store"))  # type: ignore[name-defined]
    # The above uses os from the global scope if available; fallback to default path if not.
    try:
        top_k = max(1, req.topK)
        query_str = (req.query or "").strip()
        where = req.where or None
        # When query string is empty, treat as a listing operation for admin UX.
        if not query_str:
            if where:
                # Use get_where (list semantics) instead of similarity search.
                raw = client.get_where(where=where, limit=top_k)
            else:
                raw = client.list_all(limit=top_k)
        else:
            if where:
                raw = client.query_where(query_str, where=where, top_k=top_k)
            else:
                raw = client.query(query_str, top_k=top_k)
    except Exception as exc:
        print(f"[Vector Query] Query execution error: {exc}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Vector query failed: {exc}") from exc

    records: List[VectorRecord] = []
    for item in raw or []:
        content = item.get("content")
        if content is None:
            continue
        records.append(
            VectorRecord(
                id=item.get("id"),
                content=str(content),
                metadata=item.get("metadata") or {},
            )
        )
    return VectorQueryResponse(results=records)


class FlowListItem(BaseModel):
    flowName: str
    flowSlug: str
    timestamp: Optional[str] = None
    stepCount: int = 0


class FlowListResponse(BaseModel):
    flows: List[FlowListItem]


@router.get("/flows", response_model=FlowListResponse)
async def list_flows() -> FlowListResponse:
    """List all refined recorder flows from the generated_flows directory (disk-based)."""
    import json
    from pathlib import Path
    
    # Load from disk instead of vector DB
    generated_dir = Path(__file__).resolve().parent.parent.parent / "generated_flows"
    
    if not generated_dir.exists():
        return FlowListResponse(flows=[])
    
    flows_map: Dict[str, Dict[str, Any]] = {}
    
    try:
        # Find all .refined.json files
        for json_file in generated_dir.glob("*.refined.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                flow_name = data.get("flow_name") or data.get("flow_id") or json_file.stem
                flow_slug = flow_name.replace(" ", "-").lower()
                steps = data.get("steps") or []
                timestamp = data.get("generated_at") or data.get("timestamp")
                
                flows_map[flow_slug] = {
                    "flowName": flow_name,
                    "flowSlug": flow_slug,
                    "timestamp": timestamp,
                    "stepCount": len(steps)
                }
            except Exception as file_exc:
                # Skip files that fail to parse
                print(f"[Flows] Failed to parse {json_file.name}: {file_exc}")
                continue
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read flows directory: {exc}") from exc

    # Convert to list and sort by timestamp (newest first)
    flows = list(flows_map.values())
    flows.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
    
    return FlowListResponse(flows=[FlowListItem(**f) for f in flows])
