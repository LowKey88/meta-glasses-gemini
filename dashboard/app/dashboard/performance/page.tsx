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
  Cell
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

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [timeRange, setTimeRange] = useState('24h');

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/performance?range=${timeRange}`);
      setMetrics(response.data);
      setError('');
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch performance metrics');
      console.error('Error fetching performance metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeRange]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Activity className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
          <div className="text-lg text-gray-600 dark:text-gray-300">Loading performance metrics...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-red-500" />
          <div className="text-xl font-medium text-gray-900 dark:text-white mb-2">Error Loading Metrics</div>
          <div className="text-gray-600 dark:text-gray-300 mb-4">{error}</div>
          <button 
            onClick={fetchMetrics}
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Response Performance</h1>
          <p className="text-gray-600 dark:text-gray-300">Monitor message processing latency and performance metrics</p>
        </div>
        
        <div className="flex items-center gap-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
          <button
            onClick={fetchMetrics}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
          >
            <Activity className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Alerts */}
      {metrics?.alerts && metrics.alerts.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h3 className="font-medium text-red-900 dark:text-red-100">Performance Alerts</h3>
          </div>
          <div className="space-y-2">
            {metrics.alerts.map((alert, index) => (
              <div key={index} className="text-sm text-red-800 dark:text-red-200">
                <strong>{alert.category}:</strong> {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Average Response Time</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics?.responseLatency?.avg?.toFixed(2) || '0.00'}s
              </p>
            </div>
            <Clock className="w-8 h-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">95th Percentile</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics?.responseLatency?.p95?.toFixed(2) || '0.00'}s
              </p>
            </div>
            <TrendingUp className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-gray-300">Error Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {((metrics?.responseLatency?.errorRate || 0) * 100).toFixed(1)}%
              </p>
            </div>
            <Zap className="w-8 h-8 text-red-500" />
          </div>
        </div>
      </div>

      {/* Response Time Trend */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Response Time Trend</h3>
        {metrics?.hourlyData && metrics.hourlyData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
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
        ) : (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            No performance data available for the selected time range
          </div>
        )}
      </div>

      {/* Category Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown Table */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Performance by Category</h3>
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
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Request Distribution</h3>
          {metrics?.categoryBreakdown && metrics.categoryBreakdown.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={metrics.categoryBreakdown}
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
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
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#F9FAFB'
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
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Expected Response Times</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(EXPECTED_LATENCIES).map(([category, { min, max }]) => (
            <div key={category} className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <div className="font-medium text-gray-900 dark:text-white text-sm">{category}</div>
              <div className="text-xs text-gray-600 dark:text-gray-300">{min}s - {max}s</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}