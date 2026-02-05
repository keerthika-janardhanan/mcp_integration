"""API endpoints for test data mapping management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json
from pathlib import Path

router = APIRouter(prefix="/data-mapping", tags=["data-mapping"])

# In-memory storage for demo (replace with database in production)
_mappings: Dict[str, List[Dict[str, Any]]] = {}

class DataMappingItem(BaseModel):
    excel_column: str
    action_type: str
    occurrences: int
    methods: List[str]

class DataMappingRequest(BaseModel):
    flow_name: str
    mappings: List[DataMappingItem]

@router.get("/{flow_name}")
async def get_mappings(flow_name: str):
    """Get current data mappings for a flow."""
    return {"flow_name": flow_name, "mappings": _mappings.get(flow_name, [])}

@router.post("/{flow_name}")
async def save_mappings(flow_name: str, request: DataMappingRequest):
    """Save data mappings for a flow."""
    _mappings[flow_name] = [item.dict() for item in request.mappings]
    return {"status": "saved", "count": len(request.mappings)}

@router.delete("/{flow_name}/{excel_column}")
async def delete_mapping(flow_name: str, excel_column: str):
    """Delete a specific mapping."""
    if flow_name not in _mappings:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    original_count = len(_mappings[flow_name])
    _mappings[flow_name] = [
        item for item in _mappings[flow_name] 
        if item["excel_column"] != excel_column
    ]
    
    if len(_mappings[flow_name]) == original_count:
        raise HTTPException(status_code=404, detail="Mapping not found")
    
    return {"status": "deleted", "excel_column": excel_column}