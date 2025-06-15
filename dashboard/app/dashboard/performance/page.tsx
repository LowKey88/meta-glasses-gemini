'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { 
  Clock, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle,
  Activity,
  Zap
} from 'lucide-react';

interface PerformanceMetrics {
  responseLatency: {
    avg: number;
    p95: number;
    errorRate: number;
  };
  categoryBreakdown: Array<{
    category: string;
    avgLatency: number;
    count: number;
    errorRate: number;
  }>;
  hourlyData: Array<{
    hour: string;
    avgLatency: number;
    requestCount: number;
  }>;
  alerts: Array<{
    category: string;
    message: string;
    severity: 'warning' | 'error';
  }>;
}

const CATEGORY_COLORS = {
  'AI Response': '#3B82F6',
  'Calendar': '#10B981',
  'Task': '#F59E0B',
  'Automation': '#8B5CF6',
  'Search': '#EF4444',
  'Image': '#06B6D4',
  'Notion': '#6366F1',
  'Other': '#6B7280'
};

const EXPECTED_LATENCIES = {
  'AI Response': { min: 3, max: 8 },
  'Calendar': { min: 2, max: 5 },
  'Task': { min: 1, max: 3 },
  'Automation': { min: 1, max: 4 },
  'Search': { min: 4, max: 10 },
  'Image': { min: 5, max: 12 },
  'Notion': { min: 2, max: 6 },
  'Other': { min: 1, max: 3 }
};

interface LimitlessPerformanceData {
  summary: {
    total_records: number;
    records_last_24h: number;
    avg_processing_time: number;
    min_processing_time: number;
    max_processing_time: number;
    current_status: 'optimal' | 'suboptimal' | 'issues_detected' | 'no_data';
    performance_issues: string[];
    timing_breakdown_avg: Record<string, number>;
    bottleneck_analysis: Record<string, {
      avg_time: number;
      percentage: number;
      is_bottleneck: boolean;
    }>;
  };
  recent_records: Array<{
    log_id: string;
    title: string;
    total_time: number;
    timing_breakdown: Record<string, number>;
    results: {
      memories_created: number;
      tasks_created: number;
    };
    processed_at: string;
    has_transcript: boolean;
    transcript_length: number;
  }>;
  hourlyData: Array<{
    hour: string;
    avgLatency: number;
    requestCount: number;
  }>;
  categoryBreakdown: Array<{
    category: string;
    avgLatency: number;
    count: number;
    errorRate: number;
  }>;
  last_updated: string;
}

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [limitlessMetrics, setLimitlessMetrics] = useState<LimitlessPerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [limitlessLoading, setLimitlessLoading] = useState(true);
  const [error, setError] = useState('');
  const [limitlessError, setLimitlessError] = useState('');
  const [timeRange, setTimeRange] = useState('24h');
  const [limitlessTimeRange, setLimitlessTimeRange] = useState('24h');
  const [activeTab, setActiveTab] = useState<'general' | 'limitless'>('limitless');

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const data = await api.getPerformanceMetrics(timeRange);
      setMetrics(data);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to fetch performance metrics');
      console.error('Error fetching performance metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchLimitlessMetrics = async () => {
    try {
      setLimitlessLoading(true);
      const data = await api.getLimitlessPerformanceMetrics(20, limitlessTimeRange);
      setLimitlessMetrics(data);
      setLimitlessError('');
    } catch (err: any) {
      setLimitlessError(err.message || 'Failed to fetch Limitless performance metrics');
      console.error('Error fetching Limitless performance metrics:', err);
    } finally {
      setLimitlessLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(() => {
      fetchMetrics();
    }, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeRange]);

  useEffect(() => {
    fetchLimitlessMetrics();
    const interval = setInterval(() => {
      fetchLimitlessMetrics();
    }, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [limitlessTimeRange]);

  if (loading && limitlessLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <div className="text-lg text-gray-600 dark:text-gray-300">Loading performance metrics...</div>
        </div>
      </div>
    );
  }

  if (error && limitlessError) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <div className="text-xl font-medium text-gray-900 dark:text-white mb-2">Error Loading Metrics</div>
          <div className="text-gray-600 dark:text-gray-300 mb-4">{error || limitlessError}</div>
          <button 
            onClick={() => {
              fetchMetrics();
              fetchLimitlessMetrics();
            }}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const getLatencyStatus = (category: string, avgLatency: number) => {
    const expected = EXPECTED_LATENCIES[category as keyof typeof EXPECTED_LATENCIES];
    if (!expected) return 'unknown';
    
    if (avgLatency <= expected.max) return 'good';
    if (avgLatency <= expected.max * 1.5) return 'warning';
    return 'error';
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'error':
        return <AlertTriangle className="w-5 h-5 text-red-500" />;
      default:
        return <Activity className="w-5 h-5 text-gray-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="sm:flex sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                <Activity className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                <span>Response Performance</span>
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Monitor message processing latency and performance metrics
              </p>
            </div>
            
            <div className="mt-4 sm:mt-0 flex items-center gap-3">
              {activeTab === 'general' && (
                <select
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="1h">Last Hour</option>
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                </select>
              )}
              
              {activeTab === 'limitless' && (
                <select
                  value={limitlessTimeRange}
                  onChange={(e) => setLimitlessTimeRange(e.target.value)}
                  className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                </select>
              )}
              <button
                onClick={() => {
                  fetchMetrics();
                  fetchLimitlessMetrics();
                }}
                className="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200"
              >
                <Activity className="h-4 w-4 mr-2" />
                Refresh
              </button>
            </div>
          </div>
          
          {/* Tabs */}
          <div className="mt-6 border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('limitless')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'limitless'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                🎙️ Limitless Processing
              </button>
              <button
                onClick={() => setActiveTab('general')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'general'
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                📊 Message Processing
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'limitless' ? (
          <LimitlessPerformanceContent 
            metrics={limitlessMetrics} 
            loading={limitlessLoading} 
            error={limitlessError}
            onRefresh={fetchLimitlessMetrics}
          />
        ) : (
          <GeneralPerformanceContent 
            metrics={metrics} 
            loading={loading} 
            error={error}
            onRefresh={fetchMetrics}
            timeRange={timeRange}
            getLatencyStatus={getLatencyStatus}
            getStatusIcon={getStatusIcon}
          />
        )}
      </div>
    </div>
  );
}

// Separate component for Limitless performance content
function LimitlessPerformanceContent({ 
  metrics, 
  loading, 
  error, 
  onRefresh 
}: {
  metrics: LimitlessPerformanceData | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
}) {
  // Helper function to get display names for operations
  const getOperationDisplayName = (operation: string): string => {
    switch(operation) {
      case 'speaker_identification': return 'Speaker Identification';
      case 'natural_language_tasks': return 'Natural Language Tasks (Legacy)';
      case 'gemini_extraction': return 'Combined AI Extraction';
      case 'memory_creation': return 'Memory Creation';
      case 'tasks_creation': return 'Task Creation';
      case 'redis_caching': return 'Redis Caching';
      default: return operation.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  };
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Activity className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <div className="text-lg text-gray-600 dark:text-gray-300">Loading Limitless performance metrics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <div className="text-xl font-medium text-gray-900 dark:text-white mb-2">Error Loading Limitless Metrics</div>
          <div className="text-gray-600 dark:text-gray-300 mb-4">{error}</div>
          <button 
            onClick={onRefresh}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'optimal': return 'text-green-600 dark:text-green-400';
      case 'suboptimal': return 'text-yellow-600 dark:text-yellow-400';
      case 'issues_detected': return 'text-red-600 dark:text-red-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'optimal': return '🟢';
      case 'suboptimal': return '🟡';
      case 'issues_detected': return '🔴';
      default: return '⚪';
    }
  };

  return (
    <>
      {/* Performance Issues Alert */}
      {metrics?.summary.performance_issues && metrics.summary.performance_issues.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-100">Performance Issues Detected</h3>
          </div>
          <div className="space-y-2">
            {metrics.summary.performance_issues.map((issue, index) => (
              <div key={index} className="text-sm text-red-800 dark:text-red-200">
                • {issue}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Avg Processing Time
              </dt>
              <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                {metrics?.summary.avg_processing_time?.toFixed(1) || '0.0'}s
              </dd>
              <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Per recording
              </dd>
            </div>
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <Clock className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
        </div>

        <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Current Status
              </dt>
              <dd className={`mt-2 text-2xl font-semibold ${getStatusColor(metrics?.summary.current_status || 'no_data')}`}>
                {getStatusIcon(metrics?.summary.current_status || 'no_data')} {metrics?.summary.current_status?.replace('_', ' ') || 'No Data'}
              </dd>
              <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Performance status
              </dd>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
          </div>
        </div>

        <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Records Processed
              </dt>
              <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                {metrics?.summary.records_last_24h || 0}
              </dd>
              <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Last 24 hours
              </dd>
            </div>
            <div className="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
              <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
          </div>
        </div>

        <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200">
          <div className="flex items-center justify-between">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                Issues Detected
              </dt>
              <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                {metrics?.summary.performance_issues?.length || 0}
              </dd>
              <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                Active alerts
              </dd>
            </div>
            <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <Zap className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Timing Breakdown Chart */}
      {metrics?.summary.timing_breakdown_avg && Object.keys(metrics.summary.timing_breakdown_avg).length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">⏱️ Processing Time Breakdown</h3>
          <div className="space-y-4">
            {Object.entries(metrics.summary.timing_breakdown_avg)
              .filter(([key]) => !key.endsWith('_count'))
              .sort(([,a], [,b]) => b - a)
              .map(([operation, avgTime]) => {
                const totalTime = Object.values(metrics.summary.timing_breakdown_avg)
                  .filter((_, index, arr) => !Object.keys(metrics.summary.timing_breakdown_avg)[index].endsWith('_count'))
                  .reduce((sum, time) => sum + time, 0);
                const percentage = totalTime > 0 ? (avgTime / totalTime) * 100 : 0;
                const isBottleneck = percentage > 30;
                
                const operationIcons: Record<string, string> = {
                  'speaker_identification': '🎭',
                  'natural_language_tasks': '🧠',  // Legacy - kept for backward compatibility
                  'gemini_extraction': '🤖',      // Now includes task extraction
                  'memory_creation': '💾',
                  'tasks_creation': '✅',
                  'redis_caching': '🗄️'
                };
                
                return (
                  <div key={operation} className="flex items-center">
                    <div className="w-48 flex items-center">
                      <span className="mr-2">{operationIcons[operation] || '⚙️'}</span>
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        {getOperationDisplayName(operation)}
                      </span>
                      {isBottleneck && <span className="ml-2 text-xs bg-red-100 text-red-800 px-2 py-1 rounded">Bottleneck</span>}
                    </div>
                    <div className="flex-1 mx-4">
                      <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                        <div 
                          className={`h-3 rounded-full ${isBottleneck ? 'bg-red-500' : 'bg-blue-500'}`}
                          style={{ width: `${Math.min(percentage, 100)}%` }}
                        />
                      </div>
                    </div>
                    <div className="w-24 text-right">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {avgTime.toFixed(1)}s
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400 block">
                        ({percentage.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Recent Processing Records */}
      {metrics?.recent_records && metrics.recent_records.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">📋 Recent Processing Records</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-gray-200 dark:border-gray-700">
                  <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Recording</th>
                  <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Total Time</th>
                  <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Primary Bottleneck</th>
                  <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Results</th>
                  <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Processed</th>
                </tr>
              </thead>
              <tbody className="space-y-2">
                {metrics.recent_records.slice(0, 10).map((record, index) => {
                  const primaryBottleneck = Object.entries(record.timing_breakdown)
                    .filter(([key]) => !key.endsWith('_count'))
                    .sort(([,a], [,b]) => b - a)[0];
                  
                  return (
                    <tr key={record.log_id} className="border-b border-gray-100 dark:border-gray-700">
                      <td className="py-3 font-medium text-gray-900 dark:text-white max-w-xs">
                        <div className="truncate" title={record.title}>
                          {record.title || 'Untitled Recording'}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400">
                          ID: {record.log_id.slice(0, 8)}...
                        </div>
                      </td>
                      <td className="py-3 text-gray-600 dark:text-gray-300">
                        <span className={`font-medium ${record.total_time > 60 ? 'text-red-600 dark:text-red-400' : record.total_time > 30 ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400'}`}>
                          {record.total_time.toFixed(1)}s
                        </span>
                      </td>
                      <td className="py-3 text-gray-600 dark:text-gray-300">
                        {primaryBottleneck ? (
                          <div>
                            <div className="font-medium">
                              {getOperationDisplayName(primaryBottleneck[0])}
                            </div>
                            <div className="text-xs text-gray-500">
                              {primaryBottleneck[1].toFixed(1)}s
                            </div>
                          </div>
                        ) : (
                          'N/A'
                        )}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-gray-300">
                        <div className="text-xs">
                          📝 {record.results.memories_created} memories
                        </div>
                        <div className="text-xs">
                          ✅ {record.results.tasks_created} tasks
                        </div>
                      </td>
                      <td className="py-3 text-gray-600 dark:text-gray-300 text-xs">
                        {new Date(record.processed_at).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {metrics.recent_records.length === 0 && (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              No processing records available yet
            </div>
          )}
        </div>
      )}

      {/* Processing Time Trend Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">📈 Processing Time Trend</h3>
        {metrics?.hourlyData && metrics.hourlyData.length > 0 ? (
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={metrics.hourlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="hour" 
                  stroke="#6B7280"
                  fontSize={12}
                />
                <YAxis 
                  stroke="#6B7280"
                  fontSize={12}
                  label={{ value: 'Processing Time (seconds)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB'
                  }}
                  formatter={(value: any, name: string) => [
                    `${value}s`, 
                    name === 'avgLatency' ? 'Avg Processing Time' : name
                  ]}
                  labelFormatter={(label: string) => `Time: ${label}`}
                />
                <Line 
                  type="monotone" 
                  dataKey="avgLatency" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            No performance data available for the selected time range
          </div>
        )}
      </div>

      {/* Operation Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Operation Breakdown Table */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">⚙️ Performance by Operation</h3>
          {metrics?.categoryBreakdown && metrics.categoryBreakdown.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-gray-200 dark:border-gray-700">
                    <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Operation</th>
                    <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Avg Time</th>
                    <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Count</th>
                    <th className="pb-3 font-medium text-gray-600 dark:text-gray-300">Status</th>
                  </tr>
                </thead>
                <tbody className="space-y-2">
                  {metrics.categoryBreakdown.map((category, index) => {
                    const isBottleneck = category.avgLatency > 10; // Mark as bottleneck if >10s
                    return (
                      <tr key={index} className="border-b border-gray-100 dark:border-gray-700">
                        <td className="py-3 font-medium text-gray-900 dark:text-white">
                          {category.category}
                        </td>
                        <td className="py-3 text-gray-600 dark:text-gray-300">
                          <span className={`font-medium ${category.avgLatency > 30 ? 'text-red-600 dark:text-red-400' : category.avgLatency > 10 ? 'text-yellow-600 dark:text-yellow-400' : 'text-green-600 dark:text-green-400'}`}>
                            {category.avgLatency.toFixed(1)}s
                          </span>
                        </td>
                        <td className="py-3 text-gray-600 dark:text-gray-300">
                          {category.count}
                        </td>
                        <td className="py-3">
                          {isBottleneck ? (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400">
                              Bottleneck
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400">
                              Good
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              No operation data available
            </div>
          )}
        </div>

        {/* Processing Volume Distribution Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">📊 Processing Volume Distribution</h3>
          {metrics?.categoryBreakdown && metrics.categoryBreakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={metrics.categoryBreakdown}
                  cx="50%"
                  cy="45%"
                  outerRadius={70}
                  dataKey="count"
                  nameKey="category"
                >
                  {metrics.categoryBreakdown.map((entry, index) => {
                    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EF4444', '#06B6D4'];
                    return (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={colors[index % colors.length]} 
                      />
                    );
                  })}
                </Pie>
                <Tooltip 
                  formatter={(value: any, name: string) => [value, name]}
                  labelFormatter={(label: string) => `Operation: ${label}`}
                  contentStyle={{
                    backgroundColor: 'rgb(31 41 55)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'rgb(249 250 251)',
                    fontSize: '14px'
                  }}
                  itemStyle={{
                    color: 'rgb(249 250 251)'
                  }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  wrapperStyle={{
                    paddingTop: '20px',
                    fontSize: '12px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No distribution data available
            </div>
          )}
        </div>
      </div>
    </>
  );
}

// Move the existing performance content to a separate component
function GeneralPerformanceContent({ 
  metrics, 
  loading, 
  error, 
  onRefresh, 
  timeRange,
  getLatencyStatus,
  getStatusIcon
}: {
  metrics: PerformanceMetrics | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
  timeRange: string;
  getLatencyStatus: (category: string, avgLatency: number) => string;
  getStatusIcon: (status: string) => JSX.Element;
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Activity className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <div className="text-lg text-gray-600 dark:text-gray-300">Loading general performance metrics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <div className="text-xl font-medium text-gray-900 dark:text-white mb-2">Error Loading General Metrics</div>
          <div className="text-gray-600 dark:text-gray-300 mb-4">{error}</div>
          <button 
            onClick={onRefresh}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Alerts */}
      {metrics?.alerts && metrics.alerts.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-semibold text-red-900 dark:text-red-100">Performance Alerts</h3>
          </div>
          <div className="space-y-3">
            {metrics.alerts.map((alert, index) => (
              <div key={index} className="text-sm text-red-800 dark:text-red-200">
                <strong>{alert.category}:</strong> {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}

        {/* Overview Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200 hover:border-blue-400 dark:hover:border-blue-600">
            <div className="flex items-center justify-between">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Average Response Time
                </dt>
                <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                  {metrics?.responseLatency?.avg?.toFixed(2) || '0.00'}s
                </dd>
                <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  All operations
                </dd>
              </div>
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
                <Clock className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
            </div>
          </div>

          <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200 hover:border-green-400 dark:hover:border-green-600">
            <div className="flex items-center justify-between">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  95th Percentile
                </dt>
                <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                  {metrics?.responseLatency?.p95?.toFixed(2) || '0.00'}s
                </dd>
                <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Peak performance
                </dd>
              </div>
              <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg group-hover:bg-green-100 dark:group-hover:bg-green-900/30 transition-colors">
                <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
            </div>
          </div>

          <div className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200 hover:border-red-400 dark:hover:border-red-600">
            <div className="flex items-center justify-between">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  Error Rate
                </dt>
                <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
                  {((metrics?.responseLatency?.errorRate || 0) * 100).toFixed(1)}%
                </dd>
                <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Failed requests
                </dd>
              </div>
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg group-hover:bg-red-100 dark:group-hover:bg-red-900/30 transition-colors">
                <Zap className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
            </div>
          </div>
        </div>

        {/* Response Time Trend */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8 hover:shadow-lg transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Response Time Trend</h3>
          {metrics?.hourlyData && metrics.hourlyData.length > 0 ? (
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={metrics.hourlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="hour" 
                    stroke="#6B7280"
                    fontSize={12}
                  />
                  <YAxis 
                    stroke="#6B7280"
                    fontSize={12}
                    label={{ value: 'Latency (seconds)', angle: -90, position: 'insideLeft' }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#F9FAFB'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="avgLatency" 
                    stroke="#3B82F6" 
                    strokeWidth={2}
                    dot={{ fill: '#3B82F6', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No performance data available for the selected time range
            </div>
          )}
        </div>

        {/* Category Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Category Breakdown Table */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow duration-200">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Performance by Category</h3>
          {metrics?.categoryBreakdown && metrics.categoryBreakdown.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b border-gray-200 dark:border-gray-700">
                    <th className="pb-2 font-medium text-gray-600 dark:text-gray-300">Category</th>
                    <th className="pb-2 font-medium text-gray-600 dark:text-gray-300">Avg Latency</th>
                    <th className="pb-2 font-medium text-gray-600 dark:text-gray-300">Count</th>
                    <th className="pb-2 font-medium text-gray-600 dark:text-gray-300">Status</th>
                  </tr>
                </thead>
                <tbody className="space-y-2">
                  {metrics.categoryBreakdown.map((category, index) => {
                    const status = getLatencyStatus(category.category, category.avgLatency);
                    return (
                      <tr key={index} className="border-b border-gray-100 dark:border-gray-700">
                        <td className="py-2 font-medium text-gray-900 dark:text-white">
                          {category.category}
                        </td>
                        <td className="py-2 text-gray-600 dark:text-gray-300">
                          {category.avgLatency.toFixed(2)}s
                        </td>
                        <td className="py-2 text-gray-600 dark:text-gray-300">
                          {category.count}
                        </td>
                        <td className="py-2">
                          {getStatusIcon(status)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              No category data available
            </div>
          )}
        </div>

          {/* Category Distribution Chart */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow duration-200">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Request Distribution</h3>
          {metrics?.categoryBreakdown && metrics.categoryBreakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={metrics.categoryBreakdown}
                  cx="50%"
                  cy="45%"
                  outerRadius={70}
                  dataKey="count"
                  nameKey="category"
                >
                  {metrics.categoryBreakdown.map((entry, index) => (
                    <Cell 
                      key={`cell-${index}`} 
                      fill={CATEGORY_COLORS[entry.category as keyof typeof CATEGORY_COLORS] || '#6B7280'} 
                    />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value: any, name: string) => [value, name]}
                  labelFormatter={(label: string) => `Category: ${label}`}
                  contentStyle={{
                    backgroundColor: 'rgb(31 41 55)',
                    border: 'none',
                    borderRadius: '8px',
                    color: 'rgb(249 250 251)',
                    fontSize: '14px'
                  }}
                  itemStyle={{
                    color: 'rgb(249 250 251)'
                  }}
                />
                <Legend 
                  verticalAlign="bottom" 
                  height={36}
                  wrapperStyle={{
                    paddingTop: '20px',
                    fontSize: '12px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              No distribution data available
            </div>
            )}
          </div>
        </div>

        {/* Expected Latency Reference */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-lg transition-shadow duration-200">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Expected Response Times</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(EXPECTED_LATENCIES).map(([category, { min, max }]) => (
              <div key={category} className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                <div className="font-medium text-gray-900 dark:text-white text-sm">{category}</div>
                <div className="text-xs text-gray-600 dark:text-gray-300 mt-1">{min}s - {max}s</div>
              </div>
            ))}
          </div>
        </div>
      </>
    );
}