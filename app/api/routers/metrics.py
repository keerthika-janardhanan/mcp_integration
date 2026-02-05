"""API router for test metrics endpoints."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.test_metrics_service import get_metrics_service

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/test-metrics")
async def get_test_metrics(
    repo_id: Optional[str] = Query(None, description="Optional repository ID to filter by")
) -> Dict[str, Any]:
    """
    Get comprehensive test metrics aggregated from ALL available Playwright reports.
    
    This endpoint extracts and aggregates test execution metrics from all report folders including:
    - Total tests, passed, failed, skipped, flaky counts (aggregated across all reports)
    - Pass rate percentage (overall)
    - Total duration and average duration
    - Individual test results with details from all runs
    - Report count and per-report breakdown
    - Earliest and latest execution times
    
    Args:
        repo_id: Optional repository ID. If not provided, returns metrics from all reports across all repos.
    
    Returns:
        Dictionary containing comprehensive aggregated test metrics from all available reports
        
    Raises:
        HTTPException: If no report data is found
    """
    print(f"[API] GET /test-metrics called with repo_id={repo_id}")
    try:
        metrics_service = get_metrics_service()
        metrics = metrics_service.get_test_metrics(repo_id)
        print(f"[API] Successfully retrieved aggregated metrics from {metrics.get('totalReports', 0)} reports")
        print(f"[API] Total tests across all reports: {metrics.get('totalTests', 0)}")
        return metrics
    except FileNotFoundError as e:
        print(f"[API] FileNotFoundError: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print(f"[API] Exception: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to retrieve test metrics: {str(e)}")


@router.get("/test-metrics/reports")
async def list_available_reports() -> Dict[str, Any]:
    """
    List all available test report directories.
    
    Returns:
        Dictionary containing available reports organized by repository
    """
    try:
        metrics_service = get_metrics_service()
        reports = []
        
        # Scan all repositories
        if metrics_service.framework_repos_path.exists():
            for repo_dir in metrics_service.framework_repos_path.iterdir():
                if repo_dir.is_dir():
                    report_dir = repo_dir / "report"
                    if report_dir.exists():
                        for run_dir in report_dir.iterdir():
                            if run_dir.is_dir() and run_dir.name.startswith("run-"):
                                reports.append({
                                    'repoId': repo_dir.name,
                                    'runId': run_dir.name,
                                    'path': str(run_dir.relative_to(metrics_service.framework_repos_path))
                                })
        
        # Sort by run ID (timestamp) descending
        reports.sort(key=lambda r: r['runId'], reverse=True)
        
        return {
            'reports': reports,
            'count': len(reports)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@router.get("/test-metrics/summary")
async def get_metrics_summary(
    repo_id: Optional[str] = Query(None, description="Optional repository ID to filter by")
) -> Dict[str, Any]:
    """
    Get a lightweight summary of test metrics.
    
    Returns only high-level statistics without individual test details.
    
    Args:
        repo_id: Optional repository ID
        
    Returns:
        Dictionary containing summary metrics
    """
    try:
        metrics_service = get_metrics_service()
        metrics = metrics_service.get_test_metrics(repo_id)
        
        # Return only summary data (exclude individual tests)
        return {
            'totalTests': metrics['totalTests'],
            'passed': metrics['passed'],
            'failed': metrics['failed'],
            'skipped': metrics['skipped'],
            'flaky': metrics['flaky'],
            'duration': metrics['duration'],
            'passRate': metrics['passRate'],
            'avgDuration': metrics['avgDuration'],
            'startTime': metrics['startTime'],
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics summary: {str(e)}")


@router.get("/reports/{repository_id}/{run_id}/html")
async def serve_interactive_report(repository_id: str, run_id: str):
    """
    Serve the interactive HTML report for a specific test run.
    
    Args:
        repository_id: The repository identifier
        run_id: The test run identifier (timestamp-based folder name)
        
    Returns:
        FileResponse: The HTML report file
        
    Raises:
        HTTPException: If the report file is not found
    """
    report_path = f"framework_repos/{repository_id}/report/{run_id}/index.html"
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Interactive report not found")
    
    return FileResponse(
        report_path, 
        media_type="text/html",
        headers={"Content-Disposition": "inline"}
    )


@router.get("/reports/{repository_id}/{run_id}/assets/{asset_path:path}")
async def serve_report_assets(repository_id: str, run_id: str, asset_path: str):
    """
    Serve assets for the interactive HTML report (CSS, JS, images, etc.).
    
    Args:
        repository_id: The repository identifier
        run_id: The test run identifier
        asset_path: Path to the asset file within the report directory
        
    Returns:
        FileResponse: The requested asset file
        
    Raises:
        HTTPException: If the asset file is not found
    """
    asset_file = f"framework_repos/{repository_id}/report/{run_id}/{asset_path}"
    
    if not os.path.exists(asset_file):
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return FileResponse(asset_file)
