import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def resolve_parallel_reference_ids(
    reference_id_str: str,
    worker_index: int,
    total_workers: int
) -> str:
    """
    Split comma-separated reference IDs and assign one per worker.
    
    Args:
        reference_id_str: Comma-separated reference IDs (e.g., "10005,10003")
        worker_index: Current worker index (0-based)
        total_workers: Total number of parallel workers
    
    Returns:
        Single reference ID for this worker
    """
    if not reference_id_str or ',' not in reference_id_str:
        return reference_id_str
    
    ids = [id.strip() for id in reference_id_str.split(',') if id.strip()]
    
    if not ids:
        return reference_id_str
    
    # Assign ID based on worker index (round-robin if more workers than IDs)
    assigned_id = ids[worker_index % len(ids)]
    
    logger.info(
        f"[ParallelDataResolver] Worker {worker_index}/{total_workers} "
        f"assigned reference ID: {assigned_id} from [{', '.join(ids)}]"
    )
    
    return assigned_id


def create_parallel_config(reference_ids: List[str], output_path: Optional[Path] = None) -> Dict:
    """
    Create a parallel execution config mapping worker indices to reference IDs.
    
    Args:
        reference_ids: List of reference IDs to distribute
        output_path: Optional path to save config JSON
    
    Returns:
        Config dict with worker mappings
    """
    config = {
        "parallel_workers": len(reference_ids),
        "worker_mappings": {str(i): ref_id for i, ref_id in enumerate(reference_ids)}
    }
    
    if output_path:
        output_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
        logger.info(f"[ParallelDataResolver] Saved config to {output_path}")
    
    return config
