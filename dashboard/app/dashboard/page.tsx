'use client';

import { useEffect, useState } from 'react';
import { api, SystemStats } from '@/lib/api';
import { MessageActivityChart, WeeklyActivityChart, ComparisonChart } from '@/components/charts';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

type ChartView = 'message-activity' | 'weekly-activity' | 'comparison';

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeChart, setActiveChart] = useState<ChartView>('message-activity');

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getSystemStats();
        setStats(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  if (loading) return <div className="flex items-center justify-center h-screen">Loading stats...</div>;
  if (error) return <div className="flex items-center justify-center h-screen text-red-600">Error: {error}</div>;
  if (!stats) return null;

  // Prepare chart data
  const messageChartData = Object.entries(stats.message_activity).map(([hour, count]) => ({
    hour,
    messages: count,
  }));

  const weeklyData = Object.entries(stats.weekly_activity || {}).map(([day, count]) => ({
    day,
    messages: count
  }));

  const comparisonData = Object.keys(stats.today_vs_yesterday?.today || {}).map(hour => ({
    hour,
    today: stats.today_vs_yesterday?.today[hour] || 0,
    yesterday: stats.today_vs_yesterday?.yesterday[hour] || 0
  }));

  const memoryTypeData = Object.entries(stats.memory_by_type).map(([type, count]) => ({
    type: type.replace('_', ' '),
    count
  }));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">
          System Overview
        </h1>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              System Uptime
            </dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.uptime}
            </dd>
            <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Running continuously
            </dd>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Messages Today
            </dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.recent_messages}
            </dd>
            <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Last 24 hours
            </dd>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Total Memories
            </dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.total_memories}
            </dd>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Active Reminders
            </dt>
            <dd className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.active_reminders}
            </dd>
          </div>
        </div>

        {/* Main Chart Section with Toggle */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 sm:mb-0">
              Activity Charts
            </h2>
            <div className="flex space-x-2">
              <button
                onClick={() => setActiveChart('message-activity')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeChart === 'message-activity'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                24h Activity
              </button>
              <button
                onClick={() => setActiveChart('weekly-activity')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeChart === 'weekly-activity'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Weekly
              </button>
              <button
                onClick={() => setActiveChart('comparison')}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeChart === 'comparison'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                Comparison
              </button>
            </div>
          </div>
          
          <div className="h-[250px]">
            {activeChart === 'message-activity' && (
              <MessageActivityChart data={messageChartData} />
            )}
            {activeChart === 'weekly-activity' && (
              <WeeklyActivityChart data={weeklyData} />
            )}
            {activeChart === 'comparison' && (
              <ComparisonChart data={comparisonData} />
            )}
          </div>
        </div>

        {/* Secondary Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* AI Model Information */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              AI Model Information
            </h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Vision Model</span>
                <span className="text-sm font-mono text-gray-900 dark:text-white">
                  {stats.ai_model_vision}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">Chat Model</span>
                <span className="text-sm font-mono text-gray-900 dark:text-white">
                  {stats.ai_model_chat}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500 dark:text-gray-400">AI Requests Today</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                  {stats.total_ai_requests_today}
                </span>
              </div>
            </div>
          </div>

          {/* Memory Types Distribution */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Memory Types Distribution
            </h2>
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={memoryTypeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="type" 
                    stroke="#9CA3AF"
                    style={{ fontSize: '12px' }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    style={{ fontSize: '12px' }}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '6px'
                    }}
                    labelStyle={{ color: '#E5E7EB' }}
                  />
                  <Bar 
                    dataKey="count" 
                    fill="#10B981"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* WhatsApp Status */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            WhatsApp API Status
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</dt>
              <dd className="mt-1 flex items-center">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                  stats.whatsapp_status === 'active' 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' 
                    : stats.whatsapp_status === 'expired'
                    ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                }`}>
                  <span className={`mr-1.5 h-2 w-2 rounded-full ${
                    stats.whatsapp_status === 'active' 
                      ? 'bg-green-400' 
                      : stats.whatsapp_status === 'expired'
                      ? 'bg-red-400'
                      : 'bg-yellow-400'
                  }`} />
                  {stats.whatsapp_status.toUpperCase()}
                </span>
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Token Type</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {stats.whatsapp_token_info.token_type || 'Unknown'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">API Version</dt>
              <dd className="mt-1 text-sm font-mono text-gray-900 dark:text-white">
                {stats.whatsapp_token_info.api_version || 'N/A'}
              </dd>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Last Checked</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {new Date(stats.whatsapp_token_info.last_checked).toLocaleString()}
              </dd>
            </div>
            {stats.whatsapp_token_info.message && (
              <div className="sm:col-span-2 lg:col-span-3">
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Message</dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {stats.whatsapp_token_info.message}
                </dd>
              </div>
            )}
            {stats.whatsapp_token_info.error && (
              <div className="sm:col-span-2 lg:col-span-3">
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Error</dt>
                <dd className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {stats.whatsapp_token_info.error}
                </dd>
              </div>
            )}
          </div>
        </div>

        {/* Redis Information */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Redis Information
          </h2>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Total Keys
            </span>
            <span className="text-2xl font-semibold text-gray-900 dark:text-white">
              {stats.redis_keys}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}