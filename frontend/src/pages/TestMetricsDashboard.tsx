import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { ArrowLeft, Activity, CheckCircle2, XCircle, Clock, AlertTriangle, TrendingUp, TrendingDown, BarChart3, PieChart, Zap, FileText, Layers, RotateCcw, ExternalLink } from 'lucide-react';
import { getTestMetrics, type TestMetrics, type TestResult } from '../api/metrics';
import { ReportModal } from '../components/ReportModal';
import { API_BASE_URL } from '../api/client';

interface TestMetricsDashboardProps {
  onBack: () => void;
}

export function TestMetricsDashboard({ onBack }: TestMetricsDashboardProps) {
  const [metrics, setMetrics] = useState<TestMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'passed' | 'failed' | 'skipped'>('all');
  const [showReportModal, setShowReportModal] = useState(false);
  const [selectedReportUrl, setSelectedReportUrl] = useState('');
  const [selectedReportInfo, setSelectedReportInfo] = useState<{repoId: string, runId: string} | null>(null);

  useEffect(() => {
    loadMetrics();
  }, []);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Call backend API to get metrics
      const data = await getTestMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  };

  const filteredTests = metrics?.tests.filter(test => {
    if (selectedFilter === 'all') return true;
    return test.status === selectedFilter;
  }) || [];

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed': return 'text-green-400';
      case 'failed': return 'text-red-400';
      case 'skipped': return 'text-yellow-400';
      case 'flaky': return 'text-orange-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusBgColor = (status: string) => {
    switch (status) {
      case 'passed': return 'bg-green-500/20 border-green-500/50';
      case 'failed': return 'bg-red-500/20 border-red-500/50';
      case 'skipped': return 'bg-yellow-500/20 border-yellow-500/50';
      case 'flaky': return 'bg-orange-500/20 border-orange-500/50';
      default: return 'bg-gray-500/20 border-gray-500/50';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed': return <CheckCircle2 className="w-5 h-5" />;
      case 'failed': return <XCircle className="w-5 h-5" />;
      case 'skipped': return <AlertTriangle className="w-5 h-5" />;
      case 'flaky': return <Activity className="w-5 h-5" />;
      default: return null;
    }
  };

  const openInteractiveReport = (repoId: string, runId: string) => {
    const reportUrl = `${API_BASE_URL}/api/reports/${repoId}/${runId}/html`;
    console.log('🔗 Opening interactive report:', reportUrl);
    setSelectedReportUrl(reportUrl);
    setSelectedReportInfo({ repoId, runId });
    setShowReportModal(true);
  };

  const closeReportModal = () => {
    setShowReportModal(false);
    setSelectedReportUrl('');
    setSelectedReportInfo(null);
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-gray-900 via-blue-900/20 to-purple-900/20 text-white relative overflow-hidden">
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-blue-400/30 rounded-full"
            initial={{
              x: Math.random() * window.innerWidth,
              y: Math.random() * window.innerHeight,
            }}
            animate={{
              y: [null, Math.random() * window.innerHeight],
              x: [null, Math.random() * window.innerWidth],
            }}
            transition={{
              duration: Math.random() * 20 + 10,
              repeat: Infinity,
              ease: 'linear',
            }}
          />
        ))}
      </div>

      <div className="w-full max-w-none px-8 py-8 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative mb-12 max-w-7xl mx-auto"
        >
          {/* Refresh Button - Top Right */}
          <motion.button
            whileHover={{ scale: 1.05, rotate: 180 }}
            whileTap={{ scale: 0.95 }}
            onClick={loadMetrics}
            className="absolute top-0 right-0 p-3 rounded-xl bg-gradient-to-r from-blue-500/20 to-cyan-500/20 hover:from-blue-500/30 hover:to-cyan-500/30 border border-blue-500/50 hover:border-cyan-500/50 transition-all duration-300 shadow-lg shadow-blue-500/20 backdrop-blur-sm"
            title="Refresh metrics"
          >
            <RotateCcw className="w-5 h-5 text-blue-400" />
          </motion.button>

          {/* Centered Content */}
          <div className="text-center">
            <h1 className="text-3xl lg:text-4xl font-bold bg-gradient-to-r from-blue-400 via-cyan-400 to-teal-400 bg-clip-text text-transparent mb-3">
              Test Metrics Dashboard
            </h1>
            <p className="text-gray-400 text-base lg:text-lg">Real-time insights from Playwright test execution</p>
          </div>
        </motion.div>

        {loading && (
          <div className="flex items-center justify-center h-96">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full"
            />
          </div>
        )}

        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-red-500/20 border border-red-500/50 rounded-xl p-6 mb-8"
          >
            <div className="flex items-center gap-3">
              <XCircle className="w-6 h-6 text-red-400" />
              <div>
                <h3 className="font-semibold text-red-400">Error Loading Metrics</h3>
                <p className="text-sm text-red-300 mt-1">{error}</p>
              </div>
            </div>
          </motion.div>
        )}

        {!loading && !error && metrics && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 lg:gap-6 mb-12 max-w-7xl mx-auto">
              <MetricCard
                icon={<BarChart3 className="w-8 h-8" />}
                title="Total Tests"
                value={metrics.totalTests}
                subtitle={`${metrics.totalReports || 1} Report${(metrics.totalReports || 1) > 1 ? 's' : ''}`}
                color="blue"
                delay={0.1}
              />
              <MetricCard
                icon={<CheckCircle2 className="w-8 h-8" />}
                title="Passed"
                value={metrics.passed}
                subtitle={`${metrics.passRate.toFixed(1)}% Success`}
                color="green"
                delay={0.2}
              />
              <MetricCard
                icon={<XCircle className="w-8 h-8" />}
                title="Failed"
                value={metrics.failed}
                subtitle={metrics.failed > 0 ? 'Needs Attention' : 'All Good'}
                color="red"
                delay={0.3}
              />
              <MetricCard
                icon={<AlertTriangle className="w-8 h-8" />}
                title="Skipped"
                value={metrics.skipped}
                subtitle={metrics.skipped > 0 ? 'Not Executed' : 'None Skipped'}
                color="purple"
                delay={0.4}
              />
              <MetricCard
                icon={<Clock className="w-8 h-8" />}
                title="Avg Duration"
                value={formatDuration(metrics.avgDuration)}
                subtitle={`Total: ${formatDuration(metrics.duration)}`}
                color="blue"
                delay={0.5}
              />
            </div>

            {/* Pass Rate Visualization */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-8 mb-8 max-w-7xl mx-auto"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold flex items-center gap-3">
                  <PieChart className="w-6 h-6 text-cyan-400" />
                  Test Distribution
                </h2>
              </div>
              
              <div className="grid md:grid-cols-2 gap-8">
                {/* Progress Bar */}
                <div>
                  <div className="space-y-4">
                    <ProgressBar label="Passed" value={metrics.passed} total={metrics.totalTests} color="green" />
                    <ProgressBar label="Failed" value={metrics.failed} total={metrics.totalTests} color="red" />
                    <ProgressBar label="Skipped" value={metrics.skipped} total={metrics.totalTests} color="yellow" />
                    {metrics.flaky > 0 && (
                      <ProgressBar label="Flaky" value={metrics.flaky} total={metrics.totalTests} color="orange" />
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center justify-center">
                  <div className="relative">
                    <svg className="w-48 h-48 transform -rotate-90">
                      <circle
                        cx="96"
                        cy="96"
                        r="80"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        className="text-gray-700"
                      />
                      <circle
                        cx="96"
                        cy="96"
                        r="80"
                        stroke="currentColor"
                        strokeWidth="12"
                        fill="none"
                        strokeDasharray={`${(metrics.passRate / 100) * 502.4} 502.4`}
                        className="text-green-400"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-4xl font-bold text-green-400">{metrics.passRate.toFixed(1)}%</div>
                        <div className="text-sm text-gray-400 mt-1">Pass Rate</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Filter Tabs */}
            <div className="flex gap-3 mb-6">
              {(['all', 'passed', 'failed', 'skipped'] as const).map((filter) => (
                <motion.button
                  key={filter}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => setSelectedFilter(filter)}
                  className={`px-6 py-2 rounded-lg font-medium transition-all ${
                    selectedFilter === filter
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/30'
                      : 'bg-white/5 hover:bg-white/10 text-gray-400'
                  }`}
                >
                  {filter.charAt(0).toUpperCase() + filter.slice(1)}
                </motion.button>
              ))}
            </div>

            {/* Test Results Table */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
              className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden"
            >
              <div className="p-6 border-b border-white/10">
                <h2 className="text-2xl font-bold flex items-center gap-3">
                  <Layers className="w-6 h-6 text-purple-400" />
                  Test Results ({filteredTests.length})
                </h2>
              </div>

              <div className="overflow-x-auto">
                <div className="max-h-96 overflow-y-auto">
                  {filteredTests.length === 0 ? (
                    <div className="p-12 text-center text-gray-400">
                      <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                      <p>No tests found for selected filter</p>
                    </div>
                  ) : (
                    <table className="w-full">
                      <thead className="bg-white/5 sticky top-0">
                        <tr>
                          <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Status</th>
                          <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Test Name</th>
                          <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">File</th>
                          <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Duration</th>
                          <th className="px-6 py-4 text-left text-sm font-semibold text-gray-300">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {filteredTests.map((test, idx) => (
                          <motion.tr
                            key={idx}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.05 }}
                            className="hover:bg-white/5 transition-colors cursor-pointer"
                          >
                            <td className="px-6 py-4">
                              <div className={`flex items-center gap-2 ${getStatusColor(test.status)}`}>
                                {getStatusIcon(test.status)}
                                <span className="font-medium capitalize">{test.status}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="font-medium text-white">{test.title}</div>
                              {test.error && (
                                <div className="text-xs text-red-400 mt-1 truncate max-w-md" title={test.error}>
                                  {test.error}
                                </div>
                              )}
                            </td>
                            <td className="px-6 py-4 text-gray-400 text-sm font-mono">{test.file}</td>
                            <td className="px-6 py-4">
                              <div className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm ${
                                test.duration > 60000 ? 'bg-red-500/20 text-red-400' :
                                test.duration > 30000 ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-green-500/20 text-green-400'
                              }`}>
                                <Clock className="w-4 h-4" />
                                {formatDuration(test.duration)}
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              {test.reportId && test.runId ? (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openInteractiveReport(test.reportId, test.runId);
                                  }}
                                  className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-400 bg-blue-500/20 border border-blue-500/50 rounded-lg hover:bg-blue-500/30 hover:border-blue-400 transition-colors"
                                >
                                  <ExternalLink className="w-4 h-4" />
                                  View Details
                                </button>
                              ) : (
                                <span className="text-gray-500 text-sm">No report available</span>
                              )}
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </motion.div>

            {/* Quick Insights */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
              className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8"
            >
              <InsightCard
                icon={<Zap className="w-6 h-6" />}
                title="Fastest Test"
                value={formatDuration(Math.min(...metrics.tests.map(t => t.duration)))}
                trend="up"
                color="green"
              />
              <InsightCard
                icon={<Clock className="w-6 h-6" />}
                title="Slowest Test"
                value={formatDuration(Math.max(...metrics.tests.map(t => t.duration)))}
                trend="down"
                color="red"
              />
              <InsightCard
                icon={<Activity className="w-6 h-6" />}
                title="Success Rate"
                value={`${metrics.passRate.toFixed(1)}%`}
                trend={metrics.passRate >= 80 ? 'up' : 'down'}
                color={metrics.passRate >= 80 ? 'green' : metrics.passRate >= 60 ? 'blue' : 'red'}
              />
              <InsightCard
                icon={<Layers className="w-6 h-6" />}
                title="Total Reports"
                value={metrics.totalReports || 1}
                trend="up"
                color="purple"
              />
            </motion.div>
          </>
        )}
      </div>

      {/* Report Modal */}
      {showReportModal && (
        <ReportModal
          url={selectedReportUrl}
          onClose={closeReportModal}
          repoId={selectedReportInfo?.repoId}
          runId={selectedReportInfo?.runId}
        />
      )}
    </div>
  );
}

// Helper Components

interface MetricCardProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  color: 'blue' | 'green' | 'red' | 'purple';
  delay: number;
}

function MetricCard({ icon, title, value, subtitle, color, delay }: MetricCardProps) {
  const colorClasses = {
    blue: 'from-blue-500/20 to-cyan-500/20 border-blue-500/50 text-blue-400',
    green: 'from-green-500/20 to-emerald-500/20 border-green-500/50 text-green-400',
    red: 'from-red-500/20 to-rose-500/20 border-red-500/50 text-red-400',
    purple: 'from-purple-500/20 to-pink-500/20 border-purple-500/50 text-purple-400',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay }}
      whileHover={{ scale: 1.05, y: -5 }}
      className={`bg-gradient-to-br ${colorClasses[color]} backdrop-blur-xl border rounded-2xl p-6 shadow-xl`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={colorClasses[color]}>{icon}</div>
      </div>
      <div className="text-4xl font-bold mb-2">{value}</div>
      <div className="text-sm text-gray-300 font-medium">{title}</div>
      {subtitle && <div className="text-xs text-gray-400 mt-1">{subtitle}</div>}
    </motion.div>
  );
}

interface ProgressBarProps {
  label: string;
  value: number;
  total: number;
  color: 'green' | 'red' | 'yellow' | 'orange';
}

function ProgressBar({ label, value, total, color }: ProgressBarProps) {
  const percentage = (value / total) * 100;
  const colorClasses = {
    green: 'bg-green-500',
    red: 'bg-red-500',
    yellow: 'bg-yellow-500',
    orange: 'bg-orange-500',
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className="text-sm text-gray-400">{value} ({percentage.toFixed(1)}%)</span>
      </div>
      <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
          className={`h-full ${colorClasses[color]} rounded-full`}
        />
      </div>
    </div>
  );
}

interface InsightCardProps {
  icon: React.ReactNode;
  title: string;
  value: string;
  trend: 'up' | 'down';
  color: 'green' | 'red' | 'blue';
}

function InsightCard({ icon, title, value, trend, color }: InsightCardProps) {
  const colorClasses = {
    green: 'text-green-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
  };

  return (
    <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        <div className={colorClasses[color]}>{icon}</div>
        {trend === 'up' ? (
          <TrendingUp className="w-5 h-5 text-green-400" />
        ) : (
          <TrendingDown className="w-5 h-5 text-red-400" />
        )}
      </div>
      <div className="text-2xl font-bold mb-1">{value}</div>
      <div className="text-sm text-gray-400">{title}</div>
    </div>
  );
}
