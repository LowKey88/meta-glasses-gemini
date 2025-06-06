'use client';

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { Mic, Clock, Search, Users, Calendar, RefreshCw, CheckCircle, AlertCircle, ChevronDown, ChevronUp, User, BrainCircuit, CheckSquare, CalendarDays, Filter, X } from 'lucide-react';
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
    tasks: Array<{ 
      description: string; 
      due_date?: string;
      assigned_to?: string;
      assigned_by?: string;
    }>;
    people: Array<{ 
      name: string; 
      context: string;
      is_speaker?: boolean;
      role?: string;
    }>;
    speakers?: Array<{
      name: string;
      context: string;
      role: string;
    }>;
  };
}

interface FilterState {
  hasTasks: boolean;
  hasFacts: boolean;
  multipleSpeakers: boolean;
  personName: string;
  processed: boolean;
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
  const [expandedRecordings, setExpandedRecordings] = useState<Set<string>>(new Set());
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [filters, setFilters] = useState<FilterState>({
    hasTasks: false,
    hasFacts: false,
    multipleSpeakers: false,
    personName: '',
    processed: false
  });
  const [allLifelogs, setAllLifelogs] = useState<Lifelog[]>([]);

  // Load stats and lifelogs
  const loadData = async (date?: string) => {
    try {
      setLoading(true);
      const [statsRes, lifelogsRes] = await Promise.all([
        api.getLimitlessStats(),
        api.getLimitlessLifelogs(date || selectedDate)
      ]);
      
      setStats(statsRes);
      setAllLifelogs(lifelogsRes);
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
      console.log('Manual sync button clicked - calling API...');
      const result = await api.syncLimitless();
      console.log('Sync API result:', result);
      toast({
        title: 'Success',
        description: 'Limitless sync initiated'
      });
      
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

  // Filter recordings based on current filters
  const applyFilters = (recordings: Lifelog[]) => {
    return recordings.filter(log => {
      // Check if has tasks
      if (filters.hasTasks && (!log.extracted_data?.tasks.length)) {
        return false;
      }
      
      // Check if has facts
      if (filters.hasFacts && (!log.extracted_data?.facts.length)) {
        return false;
      }
      
      // Check if has multiple speakers
      if (filters.multipleSpeakers) {
        const speakerCount = log.extracted_data?.people?.filter(p => p.is_speaker).length || 0;
        if (speakerCount <= 1) {
          return false;
        }
      }
      
      // Check if processed
      if (filters.processed && !log.processed) {
        return false;
      }
      
      // Check person name filter
      if (filters.personName.trim()) {
        const hasPersonMention = log.extracted_data?.people?.some(p => 
          p.name.toLowerCase().includes(filters.personName.toLowerCase())
        ) || false;
        if (!hasPersonMention) {
          return false;
        }
      }
      
      return true;
    });
  };

  // Handle date change
  const handleDateChange = (newDate: string) => {
    setSelectedDate(newDate);
    setSearchQuery(''); // Clear search when changing date
    setFilters({
      hasTasks: false,
      hasFacts: false,
      multipleSpeakers: false,
      personName: '',
      processed: false
    }); // Reset filters when changing date
    loadData(newDate);
  };

  // Apply filters when filters or data changes
  useEffect(() => {
    if (searchQuery.trim()) {
      // If there's a search query, don't apply filters (search takes precedence)
      return;
    }
    const filtered = applyFilters(allLifelogs);
    setLifelogs(filtered);
  }, [filters, allLifelogs, searchQuery]);

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

  // Toggle expanded state for a recording
  const toggleExpanded = (recordingId: string) => {
    setExpandedRecordings(prev => {
      const newSet = new Set(prev);
      if (newSet.has(recordingId)) {
        newSet.delete(recordingId);
      } else {
        newSet.add(recordingId);
      }
      return newSet;
    });
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
          <div className="flex items-center gap-3">
            {stats.pending_sync > 0 && (
              <div className="flex items-center gap-2 px-3 py-1 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-medium">{stats.pending_sync} pending</span>
              </div>
            )}
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
      </div>

      {/* Date Navigation */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <CalendarDays className="w-5 h-5 text-gray-500" />
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const prevDate = new Date(selectedDate);
                  prevDate.setDate(prevDate.getDate() - 1);
                  handleDateChange(prevDate.toISOString().split('T')[0]);
                }}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400"
              >
                <ChevronDown className="w-4 h-4 rotate-90" />
              </button>
              
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => handleDateChange(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              
              <button
                onClick={() => {
                  const nextDate = new Date(selectedDate);
                  nextDate.setDate(nextDate.getDate() + 1);
                  const tomorrow = new Date();
                  tomorrow.setDate(tomorrow.getDate() + 1);
                  if (nextDate < tomorrow) {
                    handleDateChange(nextDate.toISOString().split('T')[0]);
                  }
                }}
                disabled={selectedDate >= new Date().toISOString().split('T')[0]}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-600 dark:text-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronUp className="w-4 h-4 rotate-90" />
              </button>
            </div>
            
            {selectedDate !== new Date().toISOString().split('T')[0] && (
              <button
                onClick={() => handleDateChange(new Date().toISOString().split('T')[0])}
                className="text-sm text-blue-500 hover:text-blue-600"
              >
                Today
              </button>
            )}
          </div>
          
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Showing recordings for {new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', { 
              weekday: 'long', 
              year: 'numeric', 
              month: 'long', 
              day: 'numeric' 
            })}
          </div>
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

        {/* Filter Controls */}
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Filters</span>
            {(filters.hasTasks || filters.hasFacts || filters.multipleSpeakers || filters.processed || filters.personName) && (
              <button
                onClick={() => setFilters({
                  hasTasks: false,
                  hasFacts: false,
                  multipleSpeakers: false,
                  personName: '',
                  processed: false
                })}
                className="text-xs text-blue-500 hover:text-blue-600 ml-2"
              >
                Clear All
              </button>
            )}
          </div>
          
          <div className="flex flex-wrap gap-3">
            {/* Has Tasks Filter */}
            <button
              onClick={() => setFilters(prev => ({ ...prev, hasTasks: !prev.hasTasks }))}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors ${
                filters.hasTasks
                  ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <CheckSquare className="w-3 h-3" />
              Has Tasks
              {filters.hasTasks && <X className="w-3 h-3" />}
            </button>

            {/* Has Facts Filter */}
            <button
              onClick={() => setFilters(prev => ({ ...prev, hasFacts: !prev.hasFacts }))}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors ${
                filters.hasFacts
                  ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-700'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <BrainCircuit className="w-3 h-3" />
              Has Facts
              {filters.hasFacts && <X className="w-3 h-3" />}
            </button>

            {/* Multiple Speakers Filter */}
            <button
              onClick={() => setFilters(prev => ({ ...prev, multipleSpeakers: !prev.multipleSpeakers }))}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors ${
                filters.multipleSpeakers
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <Users className="w-3 h-3" />
              Multiple Speakers
              {filters.multipleSpeakers && <X className="w-3 h-3" />}
            </button>

            {/* Processed Filter */}
            <button
              onClick={() => setFilters(prev => ({ ...prev, processed: !prev.processed }))}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm transition-colors ${
                filters.processed
                  ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              <CheckCircle className="w-3 h-3" />
              Processed Only
              {filters.processed && <X className="w-3 h-3" />}
            </button>

            {/* Person Name Filter */}
            <div className="relative">
              <input
                type="text"
                value={filters.personName}
                onChange={(e) => setFilters(prev => ({ ...prev, personName: e.target.value }))}
                placeholder="Filter by person..."
                className="pl-8 pr-8 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-full bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[150px]"
              />
              <User className="absolute left-2.5 top-1/2 transform -translate-y-1/2 text-gray-400 w-3 h-3" />
              {filters.personName && (
                <button
                  onClick={() => setFilters(prev => ({ ...prev, personName: '' }))}
                  className="absolute right-2.5 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
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
          <>
            {lifelogs.map((log) => {
            const isExpanded = expandedRecordings.has(log.id);
            const hasExtractedData = log.extracted_data && (
              log.extracted_data.facts.length > 0 ||
              log.extracted_data.tasks.length > 0 ||
              log.extracted_data.people.length > 0
            );

            return (
              <div
                key={log.id}
                className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow"
              >
                {/* Recording Header */}
                <div 
                  className={`p-6 ${hasExtractedData ? 'cursor-pointer' : ''}`}
                  onClick={() => hasExtractedData && toggleExpanded(log.id)}
                >
                  <div className="flex items-start justify-between">
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
                        {/* Speaker Indicator */}
                        {log.extracted_data && log.extracted_data.people.filter(p => p.is_speaker).length > 1 && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1 text-blue-500">
                              <Users className="w-4 h-4" />
                              {log.extracted_data.people.filter(p => p.is_speaker).length} speakers
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    {hasExtractedData && (
                      <button
                        className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpanded(log.id);
                        }}
                      >
                        {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                      </button>
                    )}
                  </div>

                  {log.summary && (
                    <p className="text-gray-700 dark:text-gray-300 mt-3">{log.summary}</p>
                  )}

                  {/* Speaker Names Preview */}
                  {log.extracted_data && log.extracted_data.people.filter(p => p.is_speaker).length > 0 && !isExpanded && (
                    <div className="flex items-center gap-2 mt-3">
                      <Users className="w-4 h-4 text-gray-500" />
                      <div className="flex flex-wrap gap-2">
                        {log.extracted_data.people
                          .filter(p => p.is_speaker)
                          .slice(0, 3)
                          .map((person, i) => (
                            <span key={i} className="text-sm text-gray-600 dark:text-gray-400">
                              {person.name}{i < Math.min(log.extracted_data!.people.filter(p => p.is_speaker).length - 1, 2) ? ',' : ''}
                            </span>
                          ))}
                        {log.extracted_data.people.filter(p => p.is_speaker).length > 3 && (
                          <span className="text-sm text-gray-500 dark:text-gray-400">
                            +{log.extracted_data.people.filter(p => p.is_speaker).length - 3} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Quick Stats */}
                  {hasExtractedData && !isExpanded && (
                    <div className="flex items-center gap-4 mt-4">
                      {log.extracted_data!.facts.length > 0 && (
                        <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                          <BrainCircuit className="w-4 h-4" />
                          <span>{log.extracted_data!.facts.length} facts</span>
                        </div>
                      )}
                      {log.extracted_data!.tasks.length > 0 && (
                        <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                          <CheckSquare className="w-4 h-4" />
                          <span>{log.extracted_data!.tasks.length} tasks</span>
                        </div>
                      )}
                      {log.extracted_data!.people.length > 0 && (
                        <div className="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
                          <Users className="w-4 h-4" />
                          <span>{log.extracted_data!.people.length} people</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Expanded Content */}
                {isExpanded && log.extracted_data && (
                  <div className="border-t border-gray-200 dark:border-gray-700 p-6 bg-gray-50 dark:bg-gray-900/50">
                    <div className="space-y-6">
                      {/* Facts Section */}
                      {log.extracted_data.facts.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <BrainCircuit className="w-5 h-5 text-purple-500" />
                            <h4 className="font-medium text-gray-900 dark:text-gray-100">
                              Key Facts ({log.extracted_data.facts.length})
                            </h4>
                          </div>
                          <ul className="space-y-2">
                            {log.extracted_data.facts.map((fact, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-purple-500 mt-0.5">•</span>
                                <span className="text-gray-700 dark:text-gray-300">{fact}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Tasks Section */}
                      {log.extracted_data.tasks.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <CheckSquare className="w-5 h-5 text-blue-500" />
                            <h4 className="font-medium text-gray-900 dark:text-gray-100">
                              Tasks & Action Items ({log.extracted_data.tasks.length})
                            </h4>
                          </div>
                          <div className="space-y-3">
                            {log.extracted_data.tasks.map((task, i) => (
                              <div key={i} className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                                <div className="flex items-start gap-3">
                                  <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                                  <div className="flex-1">
                                    <p className="text-gray-900 dark:text-gray-100">{task.description}</p>
                                    <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-600 dark:text-gray-400">
                                      {task.assigned_to && (
                                        <span className="flex items-center gap-1">
                                          <User className="w-3 h-3" />
                                          Assigned to: {task.assigned_to}
                                        </span>
                                      )}
                                      {task.assigned_by && task.assigned_by !== task.assigned_to && (
                                        <span>By: {task.assigned_by}</span>
                                      )}
                                      {task.due_date && (
                                        <span className="flex items-center gap-1">
                                          <Calendar className="w-3 h-3" />
                                          Due: {new Date(task.due_date).toLocaleDateString()}
                                        </span>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* People Section */}
                      {log.extracted_data.people.length > 0 && (
                        <div>
                          <div className="flex items-center gap-2 mb-3">
                            <Users className="w-5 h-5 text-green-500" />
                            <h4 className="font-medium text-gray-900 dark:text-gray-100">
                              People & Speakers ({log.extracted_data.people.length})
                            </h4>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {log.extracted_data.people.map((person, i) => (
                              <div 
                                key={i} 
                                className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
                              >
                                <div className="flex items-start gap-3">
                                  <div className={`p-2 rounded-full ${
                                    person.is_speaker 
                                      ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' 
                                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                                  }`}>
                                    <User className="w-4 h-4" />
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      <p className="font-medium text-gray-900 dark:text-gray-100">{person.name}</p>
                                      {person.is_speaker && (
                                        <span className="text-xs px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">
                                          Speaker
                                        </span>
                                      )}
                                    </div>
                                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{person.context}</p>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
          </>
        )}
      </div>
    </div>
  );
}