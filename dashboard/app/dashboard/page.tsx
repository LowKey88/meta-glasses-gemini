'use client';

import { useEffect, useState } from 'react';
import { api, SystemStats } from '@/lib/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

export default function DashboardPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  if (loading) return <div>Loading stats...</div>;
  if (error) return <div className="text-red-600">Error: {error}</div>;
  if (!stats) return null;

  // Prepare chart data
  const messageChartData = Object.entries(stats.message_activity).map(([hour, count]) => ({
    hour,
    messages: count,
  }));

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-8">
        System Overview
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-gray-700 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 truncate">
              System Uptime
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.uptime}
            </dd>
            <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Running continuously
            </dd>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 truncate">
              Messages Today
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.recent_messages}
            </dd>
            <dd className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Last 24 hours
            </dd>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 truncate">
              Total Memories
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.total_memories}
            </dd>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 truncate">
              Active Reminders
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.active_reminders}
            </dd>
          </div>
        </div>
      </div>

      {/* AI Model Information */}
      <div className="mt-8 bg-white dark:bg-gray-700 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            AI Model Information
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Vision Model</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">
                {stats.ai_model_vision}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Chat Model</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">
                {stats.ai_model_chat}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">AI Requests Today</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {stats.total_ai_requests_today}
              </dd>
            </div>
          </div>
        </div>
      </div>

      {/* WhatsApp Status */}
      <div className="mt-8 bg-white dark:bg-gray-700 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            WhatsApp API Status
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Status</dt>
              <dd className="mt-1 flex items-center">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
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
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Token Type</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {stats.whatsapp_token_info.token_type || 'Unknown'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">API Version</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">
                {stats.whatsapp_token_info.api_version || 'N/A'}
              </dd>
            </div>
            <div className="sm:col-span-2 lg:col-span-3">
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Message</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {stats.whatsapp_token_info.message}
              </dd>
            </div>
            {stats.whatsapp_token_info.error && (
              <div className="sm:col-span-2 lg:col-span-3">
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Error</dt>
                <dd className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {stats.whatsapp_token_info.error}
                </dd>
              </div>
            )}
            <div className="sm:col-span-2 lg:col-span-3">
              <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Last Checked</dt>
              <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                {new Date(stats.whatsapp_token_info.last_checked).toLocaleString()}
              </dd>
            </div>
          </div>
        </div>
      </div>

      {/* Message Activity Graph */}
      <div className="mt-8 bg-white dark:bg-gray-700 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Message Activity (Last 24 Hours)
          </h2>
          <div className="h-64 -mx-2 sm:mx-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={messageChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="hour" 
                  stroke="#9CA3AF"
                  style={{ fontSize: '12px' }}
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
                <Line 
                  type="monotone" 
                  dataKey="messages" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Weekly Activity Chart */}
      <div className="mt-8">
        <div className="bg-white dark:bg-gray-700 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Weekly Message Activity
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={Object.entries(stats.weekly_activity || {}).map(([day, count]) => ({
                day,
                messages: count
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="day" 
                  stroke="#9CA3AF"
                  style={{ fontSize: '12px' }}
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
                  dataKey="messages" 
                  fill="#10B981"
                  radius={[8, 8, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Today vs Yesterday Comparison */}
      <div className="mt-8">
        <div className="bg-white dark:bg-gray-700 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Today vs Yesterday (Hourly)
            </h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={Object.keys(stats.today_vs_yesterday?.today || {}).map(hour => ({
                hour,
                today: stats.today_vs_yesterday?.today[hour] || 0,
                yesterday: stats.today_vs_yesterday?.yesterday[hour] || 0
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="hour" 
                  stroke="#9CA3AF"
                  style={{ fontSize: '12px' }}
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
                <Legend 
                  wrapperStyle={{ paddingTop: '20px' }}
                  iconType="line"
                />
                <Line 
                  type="monotone" 
                  dataKey="today" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line 
                  type="monotone" 
                  dataKey="yesterday" 
                  stroke="#6B7280" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={{ fill: '#6B7280', r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="bg-white dark:bg-gray-700 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Redis Information
            </h2>
            <dl className="grid grid-cols-1 gap-x-4 gap-y-6">
              <div>
                <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">
                  Total Keys
                </dt>
                <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                  {stats.redis_keys}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Memory Types Distribution
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={Object.entries(stats.memory_by_type).map(([type, count]) => ({
                  type: type.replace('_', ' '),
                  count
                }))}>
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
      </div>
    </div>
  );
}