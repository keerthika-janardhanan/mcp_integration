"""Service for extracting test metrics from Playwright report files."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class TestMetricsService:
    """Extract and aggregate test metrics from Playwright reports."""

    def __init__(self, framework_repos_path: str = "framework_repos"):
        """
        Initialize the test metrics service.
        
        Args:
            framework_repos_path: Base path to framework repositories containing reports
        """
        self.framework_repos_path = Path(framework_repos_path).absolute()
        print(f"[TestMetricsService] Initialized with path: {self.framework_repos_path}")
        print(f"[TestMetricsService] Path exists: {self.framework_repos_path.exists()}")

    def get_all_reports(self, repo_id: Optional[str] = None) -> List[Path]:
        """
        Get all report directories.
        
        Args:
            repo_id: Specific repository ID, or None to find all reports across all repos
            
        Returns:
            List of all report directory paths
        """
        if not self.framework_repos_path.exists():
            return []

        all_reports = []
        
        # If no repo_id specified, find all reports across all repos
        if repo_id is None:
            for repo_dir in self.framework_repos_path.iterdir():
                if repo_dir.is_dir():
                    report_dir = repo_dir / "report"
                    if report_dir.exists():
                        for run_dir in report_dir.iterdir():
                            if run_dir.is_dir() and run_dir.name.startswith("run-"):
                                all_reports.append(run_dir)
        else:
            # Find all reports for specific repo
            repo_dir = self.framework_repos_path / repo_id / "report"
            if repo_dir.exists():
                for run_dir in repo_dir.iterdir():
                    if run_dir.is_dir() and run_dir.name.startswith("run-"):
                        all_reports.append(run_dir)
        
        # Sort by directory name (timestamp) - most recent first
        all_reports.sort(key=lambda p: p.name, reverse=True)
        return all_reports

    def get_latest_report(self, repo_id: Optional[str] = None) -> Optional[Path]:
        """
        Get the latest report directory.
        
        Args:
            repo_id: Specific repository ID, or None to find the most recent across all repos
            
        Returns:
            Path to the latest report directory, or None if not found
        """
        all_reports = self.get_all_reports(repo_id)
        return all_reports[0] if all_reports else None

    def parse_report_json(self, report_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Parse the report.json file.
        
        Args:
            report_dir: Path to the report directory
            
        Returns:
            Parsed JSON data or None if file not found
        """
        report_json = report_dir / "report.json"
        if not report_json.exists():
            return None
        
        try:
            with open(report_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error parsing report.json: {e}")
            return None

    def parse_junit_xml(self, report_dir: Path) -> Optional[ET.Element]:
        """
        Parse the junit.xml file.
        
        Args:
            report_dir: Path to the report directory
            
        Returns:
            Parsed XML root element or None if file not found
        """
        junit_xml = report_dir / "junit.xml"
        if not junit_xml.exists():
            return None
        
        try:
            tree = ET.parse(junit_xml)
            return tree.getroot()
        except Exception as e:
            print(f"Error parsing junit.xml: {e}")
            return None

    def extract_test_results(self, report_data: Dict[str, Any], repo_id: str = None, run_id: str = None) -> List[Dict[str, Any]]:
        """
        Extract individual test results from report JSON.
        
        Args:
            report_data: Parsed report.json data
            repo_id: Repository identifier  
            run_id: Test run identifier
            
        Returns:
            List of test result dictionaries
        """
        tests = []
        
        def traverse_suites(suite: Dict[str, Any], file_name: str = ""):
            """Recursively traverse test suites."""
            current_file = suite.get('file', file_name)
            
            # Process specs (test cases)
            for spec in suite.get('specs', []):
                for test in spec.get('tests', []):
                    for result in test.get('results', []):
                        tests.append({
                            'title': spec.get('title', 'Unknown Test'),
                            'file': current_file,
                            'status': result.get('status', 'unknown'),
                            'duration': result.get('duration', 0),
                            'error': result.get('error', {}).get('message') if result.get('error') else None,
                            'startTime': result.get('startTime'),
                            'reportId': repo_id,
                            'runId': run_id,
                        })
            
            # Recursively process nested suites
            for nested_suite in suite.get('suites', []):
                traverse_suites(nested_suite, current_file)
        
        # Start traversal from root suites
        for suite in report_data.get('suites', []):
            traverse_suites(suite)
        
        return tests

    def calculate_aggregated_metrics(self, all_reports_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate comprehensive test metrics from multiple reports.
        
        Args:
            all_reports_data: List of parsed report.json data from all reports
            
        Returns:
            Dictionary containing aggregated metrics from all reports
        """
        if not all_reports_data:
            return {
                'totalTests': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0,
                'flaky': 0,
                'duration': 0,
                'startTime': '',
                'tests': [],
                'passRate': 0,
                'avgDuration': 0,
                'totalReports': 0,
                'reportDetails': []
            }
        
        all_tests = []
        total_duration = 0
        earliest_start = None
        latest_start = None
        report_details = []
        
        # Aggregate data from all reports
        for report_data in all_reports_data:
            stats = report_data.get('stats', {})
            metadata = report_data.get('_metadata', {})
            
            tests = self.extract_test_results(
                report_data, 
                repo_id=metadata.get('repo_id'), 
                run_id=metadata.get('run_id')
            )
            all_tests.extend(tests)
            
            # Track duration
            report_duration = stats.get('duration', 0)
            total_duration += report_duration
            
            # Track start times
            start_time = stats.get('startTime', '')
            if start_time:
                if earliest_start is None or start_time < earliest_start:
                    earliest_start = start_time
                if latest_start is None or start_time > latest_start:
                    latest_start = start_time
            
            # Collect report details
            report_tests = len(tests)
            report_passed = sum(1 for t in tests if t['status'] == 'passed')
            report_failed = sum(1 for t in tests if t['status'] == 'failed')
            report_skipped = sum(1 for t in tests if t['status'] == 'skipped')
            report_flaky = sum(1 for t in tests if t['status'] == 'flaky')
            
            report_details.append({
                'startTime': start_time,
                'duration': report_duration,
                'totalTests': report_tests,
                'passed': report_passed,
                'failed': report_failed,
                'skipped': report_skipped,
                'flaky': report_flaky,
                'passRate': (report_passed / report_tests * 100) if report_tests > 0 else 0
            })
        
        # Calculate aggregated metrics
        total_tests = len(all_tests)
        passed = sum(1 for t in all_tests if t['status'] == 'passed')
        failed = sum(1 for t in all_tests if t['status'] == 'failed')
        skipped = sum(1 for t in all_tests if t['status'] == 'skipped')
        flaky = sum(1 for t in all_tests if t['status'] == 'flaky')
        
        # Calculate pass rate
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate average duration
        durations = [t['duration'] for t in all_tests if t['duration'] > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'totalTests': total_tests,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'flaky': flaky,
            'duration': total_duration,
            'startTime': earliest_start or '',
            'latestStartTime': latest_start or '',
            'tests': all_tests,
            'passRate': pass_rate,
            'avgDuration': avg_duration,
            'totalReports': len(all_reports_data),
            'reportDetails': report_details
        }

    def calculate_metrics(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate comprehensive test metrics for a single report.
        
        Args:
            report_data: Parsed report.json data
            
        Returns:
            Dictionary containing aggregated metrics
        """
        return self.calculate_aggregated_metrics([report_data])

    def get_test_metrics(self, repo_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get complete test metrics aggregated from all available reports.
        
        Args:
            repo_id: Optional repository ID to filter by
            
        Returns:
            Dictionary containing all aggregated test metrics
            
        Raises:
            FileNotFoundError: If no report data is found
        """
        print(f"[TestMetricsService] Getting aggregated metrics for repo_id: {repo_id}")
        
        all_report_dirs = self.get_all_reports(repo_id)
        print(f"[TestMetricsService] Found {len(all_report_dirs)} report directories")
        
        if not all_report_dirs:
            raise FileNotFoundError("No test reports found")
        
        all_reports_data = []
        
        # Parse all report.json files
        for report_dir in all_report_dirs:
            print(f"[TestMetricsService] Parsing report: {report_dir.name}")
            report_data = self.parse_report_json(report_dir)
            if report_data:
                # Extract repo_id and run_id from path
                repo_id_from_path = report_dir.parent.parent.name
                run_id_from_path = report_dir.name
                
                # Add metadata to report data
                report_data['_metadata'] = {
                    'repo_id': repo_id_from_path,
                    'run_id': run_id_from_path
                }
                all_reports_data.append(report_data)
            else:
                print(f"[TestMetricsService] Warning: Could not parse {report_dir}")
        
        if not all_reports_data:
            raise FileNotFoundError("No valid report.json files found")
        
        print(f"[TestMetricsService] Successfully parsed {len(all_reports_data)} reports")
        return self.calculate_aggregated_metrics(all_reports_data)


# Singleton instance
_metrics_service: Optional[TestMetricsService] = None


def get_metrics_service() -> TestMetricsService:
    """Get or create the singleton test metrics service instance."""
    global _metrics_service
    if _metrics_service is None:
        _metrics_service = TestMetricsService()
    return _metrics_service
