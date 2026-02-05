import { apiClient } from './client';

export interface TestResult {
  title: string;
  file: string;
  status: 'passed' | 'failed' | 'skipped' | 'flaky';
  duration: number;
  error?: string;
  startTime?: string;
  reportId?: string;
  runId?: string;
}

export interface TestMetrics {
  totalTests: number;
  passed: number;
  failed: number;
  skipped: number;
  flaky: number;
  duration: number;
  startTime: string;
  tests: TestResult[];
  passRate: number;
  avgDuration: number;
  totalReports: number;
}

export interface AvailableReport {
  repoId: string;
  runId: string;
  path: string;
}

export interface ReportsListResponse {
  reports: AvailableReport[];
  count: number;
}

/**
 * Get comprehensive test metrics from the latest Playwright report
 */
export async function getTestMetrics(repoId?: string): Promise<TestMetrics> {
  const params = repoId ? { repo_id: repoId } : {};
  const response = await apiClient.get<TestMetrics>('/api/test-metrics', { params });
  return response.data;
}

/**
 * List all available test report directories
 */
export async function listAvailableReports(): Promise<ReportsListResponse> {
  const response = await apiClient.get<ReportsListResponse>('/api/test-metrics/reports');
  return response.data;
}

/**
 * Get lightweight summary of test metrics
 */
export async function getMetricsSummary(repoId?: string): Promise<Omit<TestMetrics, 'tests'>> {
  const params = repoId ? { repo_id: repoId } : {};
  const response = await apiClient.get<Omit<TestMetrics, 'tests'>>('/api/test-metrics/summary', { params });
  return response.data;
}
