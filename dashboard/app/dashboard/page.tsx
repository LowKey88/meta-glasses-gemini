'use client';

import { useEffect, useState } from 'react';
import { api, SystemStats } from '@/lib/api';

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

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-8">
        System Overview
      </h1>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white dark:bg-gray-700 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 truncate">
              Uptime
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
              {Math.floor(stats.uptime / 3600)}h {Math.floor((stats.uptime % 3600) / 60)}m
            </dd>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 overflow-hidden shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 truncate">
              Memory Usage
            </dt>
            <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
              {stats.memory_usage.toFixed(1)}%
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

      <div className="mt-8 bg-white dark:bg-gray-700 shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Redis Information
          </h2>
          <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
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
    </div>
  );
}