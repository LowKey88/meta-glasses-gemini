'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { Mic, Clock, Search, Users, Calendar, RefreshCw, CheckCircle, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface LimitlessStats {
  total_lifelogs: number;
  synced_today: number;
  last_sync: string | null;
  sync_status: 'idle' | 'syncing' | 'error';
  memories_created: number;
  tasks_created: number;
  pending_sync: number;
}

interface Lifelog {
  id: string;
  title: string;
  summary: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  has_transcript: boolean;
  processed: boolean;
  extracted_data?: {
    facts: string[];
    tasks: Array<{ description: string; due_date?: string }>;
    people: Array<{ name: string; context: string }>;
  };
}

export default function LimitlessPage() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [stats, setStats] = useState<LimitlessStats>({
    total_lifelogs: 0,
    synced_today: 0,
    last_sync: null,
    sync_status: 'idle',
    memories_created: 0,
    tasks_created: 0,
    pending_sync: 0
  });
  const [lifelogs, setLifelogs] = useState<Lifelog[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Load stats and lifelogs
  const loadData = async () => {
    try {
      setLoading(true);
      const [statsRes, lifelogsRes] = await Promise.all([
        api.getLimitlessStats(),
        api.getLimitlessLifelogs()
      ]);
      
      setStats(statsRes);
      setLifelogs(lifelogsRes);
    } catch (error) {
      console.error('Error loading Limitless data:', error);
      toast({
        title: 'Error',
        description: 'Failed to load Limitless data',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  // Manual sync
  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await api.syncLimitless();
      toast({
        title: 'Success',
        description: 'Limitless sync initiated'
      });
      
      // Reload data after sync
      setTimeout(loadData, 3000);
    } catch (error) {
      console.error('Error syncing:', error);
      toast({
        title: 'Error',
        description: 'Failed to sync Limitless',
        variant: 'destructive'
      });
    } finally {
      setSyncing(false);
    }
  };

  // Search lifelogs
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      loadData();
      return;
    }

    try {
      const results = await api.searchLimitlessLifelogs(searchQuery);
      setLifelogs(results);
    } catch (error) {
      console.error('Error searching:', error);
      toast({
        title: 'Error',
        description: 'Failed to search Lifelogs',
        variant: 'destructive'
      });
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Format time
  const formatTime = (isoString: string | null) => {
    if (!isoString) {
      return 'Date not available';
    }
    try {
      return new Date(isoString).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid date';
    }
  };

  // Format duration
  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 text-gray-900 dark:text-gray-100">Limitless Integration</h1>
        <p className="text-gray-600 dark:text-gray-400">
          Sync and manage your Limitless Pendant recordings
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Recordings</p>
              <p className="text-2xl font-bold mt-1 text-gray-900 dark:text-gray-100">{stats.total_lifelogs}</p>
            </div>
            <Mic className="text-blue-500 w-8 h-8" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Synced Today</p>
              <p className="text-2xl font-bold mt-1 text-gray-900 dark:text-gray-100">{stats.synced_today}</p>
            </div>
            <Calendar className="text-green-500 w-8 h-8" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Memories Created</p>
              <p className="text-2xl font-bold mt-1 text-gray-900 dark:text-gray-100">{stats.memories_created}</p>
            </div>
            <CheckCircle className="text-purple-500 w-8 h-8" />
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Tasks Created</p>
              <p className="text-2xl font-bold mt-1 text-gray-900 dark:text-gray-100">{stats.tasks_created}</p>
            </div>
            <Clock className="text-orange-500 w-8 h-8" />
          </div>
        </div>
      </div>

      {/* Sync Status Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Last Sync: {stats.last_sync ? formatTime(stats.last_sync) : 'Never'}
              </p>
              {stats.pending_sync > 0 && (
                <p className="text-sm text-orange-500 mt-1">
                  {stats.pending_sync} recordings pending sync
                </p>
              )}
            </div>
            {stats.sync_status === 'syncing' && (
              <div className="flex items-center gap-2 text-blue-500">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span className="text-sm">Syncing...</span>
              </div>
            )}
            {stats.sync_status === 'error' && (
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm">Sync error</span>
              </div>
            )}
          </div>
          <button
            onClick={handleSync}
            disabled={syncing || stats.sync_status === 'syncing'}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
            Sync Now
          </button>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-8">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="Search recordings..."
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Search
          </button>
        </div>
      </div>

      {/* Lifelogs List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-gray-400" />
            <p className="text-gray-500 dark:text-gray-400 mt-2">Loading recordings...</p>
          </div>
        ) : lifelogs.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
            <Mic className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No recordings found</p>
          </div>
        ) : (
          lifelogs.map((log) => (
            <div
              key={log.id}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold mb-1 text-gray-900 dark:text-gray-100">{log.title}</h3>
                  <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <span>{formatTime(log.start_time)}</span>
                    <span>•</span>
                    <span>{formatDuration(log.duration_minutes)}</span>
                    {log.processed && (
                      <>
                        <span>•</span>
                        <span className="flex items-center gap-1 text-green-500">
                          <CheckCircle className="w-4 h-4" />
                          Processed
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {log.summary && (
                <p className="text-gray-700 dark:text-gray-300 mb-4">{log.summary}</p>
              )}

              {log.extracted_data && (
                <div className="space-y-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                  {log.extracted_data.facts.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                        Key Facts ({log.extracted_data.facts.length})
                      </p>
                      <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                        {log.extracted_data.facts.slice(0, 3).map((fact, i) => (
                          <li key={i}>• {fact}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {log.extracted_data.tasks.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                        Tasks ({log.extracted_data.tasks.length})
                      </p>
                      <ul className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                        {log.extracted_data.tasks.slice(0, 3).map((task, i) => (
                          <li key={i}>
                            ✓ {task.description}
                            {task.due_date && (
                              <span className="text-gray-500 dark:text-gray-400 ml-2">
                                (Due: {new Date(task.due_date).toLocaleDateString()})
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {log.extracted_data.people.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                        People Mentioned
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {log.extracted_data.people.map((person, i) => (
                          <div
                            key={i}
                            className="flex items-center gap-1 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm"
                          >
                            <Users className="w-3 h-3" />
                            {person.name}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}