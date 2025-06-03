'use client';

import { useEffect, useState } from 'react';
import { api, RedisKey } from '@/lib/api';
import { 
  Trash2, 
  Copy, 
  Search, 
  RefreshCw, 
  ChevronDown, 
  ChevronRight, 
  Database,
  Key,
  Clock,
  Type,
  Filter,
  RotateCcw,
  AlertCircle,
  Inbox
} from 'lucide-react';

export default function RedisPage() {
  const [keys, setKeys] = useState<RedisKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchPattern, setSearchPattern] = useState('');
  const [selectedKey, setSelectedKey] = useState<RedisKey | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string>('');
  const [isJsonCollapsed, setIsJsonCollapsed] = useState(true);

  const fetchKeys = async (pattern?: string) => {
    setLoading(true);
    try {
      const data = await api.getRedisKeys(pattern);
      setKeys(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Redis keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchKeys(searchPattern);
  };

  const handleViewKey = async (key: string) => {
    try {
      const data = await api.getRedisKey(key);
      setSelectedKey(data);
      setIsJsonCollapsed(true); // Reset collapse state for new key
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to load key details');
    }
  };

  const handleDeleteKey = async () => {
    try {
      await api.deleteRedisKey(keyToDelete);
      await fetchKeys(searchPattern);
      if (selectedKey?.key === keyToDelete) {
        setSelectedKey(null);
      }
      setShowDeleteConfirm(false);
      setKeyToDelete('');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete key');
    }
  };

  const copyToClipboard = (text: string, isKey: boolean = false) => {
    navigator.clipboard.writeText(text);
    if (isKey) {
      setCopiedKey(text);
      setTimeout(() => setCopiedKey(''), 2000);
    }
  };

  const formatValue = (value: any): { formatted: string; isJson: boolean } => {
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        return {
          formatted: JSON.stringify(parsed, null, 2),
          isJson: true
        };
      } catch {
        return {
          formatted: value,
          isJson: false
        };
      }
    }
    return {
      formatted: JSON.stringify(value, null, 2),
      isJson: true
    };
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header Section */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500 rounded-lg">
              <Database className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Redis Monitor
            </h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => fetchKeys(searchPattern)}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 hover:shadow-md transition-all duration-200 flex items-center gap-2 text-gray-700 dark:text-gray-200"
            >
              <Filter className="w-4 h-4" />
              Filter
            </button>
            <button
              onClick={() => {
                setSearchPattern('');
                fetchKeys();
              }}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 hover:shadow-md transition-all duration-200 flex items-center gap-2 text-gray-700 dark:text-gray-200"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
          </div>
        </div>

        {/* Search Section */}
        <div className="mb-8">
          <form onSubmit={handleSearch} className="flex gap-4">
            <div className="flex-1 relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search pattern (e.g, user:*, reminder:*)"
                className="w-full pl-11 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-all duration-200"
                value={searchPattern}
                onChange={(e) => setSearchPattern(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="px-6 py-3 bg-blue-600 text-white border border-blue-600 rounded-xl hover:bg-blue-700 hover:shadow-md transition-all duration-200 flex items-center gap-2"
            >
              <Search className="w-4 h-4" />
              Search
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Keys List */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all duration-200">
            <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-t-xl">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                  <Key className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Redis Keys
                </h2>
                <span className="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-full text-sm font-semibold">
                  {keys.length}
                </span>
              </div>
            </div>
            
            {loading ? (
              <div className="p-8 text-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  <p className="text-gray-500 dark:text-gray-400">Loading Redis keys...</p>
                </div>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 bg-red-100 dark:bg-red-900/20 rounded-full">
                    <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400" />
                  </div>
                  <p className="text-red-600 dark:text-red-400 font-medium">Error loading keys</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{error}</p>
                </div>
              </div>
            ) : keys.length === 0 ? (
              <div className="p-8 text-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-full">
                    <Inbox className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-gray-500 dark:text-gray-400 font-medium">No Redis keys found</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500">
                    {searchPattern ? 'Try adjusting your search pattern' : 'Your Redis database appears to be empty'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
                {keys.map((key) => (
                  <div
                    key={key.key}
                    className={`px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-all duration-200 ${
                      selectedKey?.key === key.key 
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-r-2 border-blue-500' 
                        : ''
                    }`}
                    onClick={() => handleViewKey(key.key)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className="p-1.5 bg-gray-100 dark:bg-gray-700 rounded">
                          <Key className="w-3 h-3 text-gray-700 dark:text-gray-300" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                            {key.key}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100">
                              <Type className="w-3 h-3" />
                              {key.type}
                            </span>
                            {key.ttl !== null && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-orange-100 dark:bg-orange-900/20 text-orange-900 dark:text-orange-200">
                                <Clock className="w-3 h-3" />
                                {key.ttl}s
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 ml-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            copyToClipboard(key.key, true);
                          }}
                          className={`p-2 rounded-lg transition-all duration-200 ${
                            copiedKey === key.key
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                              : 'text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600'
                          }`}
                          title="Copy key"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setKeyToDelete(key.key);
                            setShowDeleteConfirm(true);
                          }}
                          className="p-2 text-gray-600 hover:text-red-600 dark:text-gray-300 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200"
                          title="Delete key"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Key Details */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all duration-200">
            <div className="px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-t-xl">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                  <AlertCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                </div>
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Key Details
                </h2>
              </div>
            </div>
            
            {selectedKey ? (
              <div className="p-6">
                {/* Key Name Section */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Key className="w-4 h-4 text-gray-700 dark:text-gray-300" />
                      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                        Key Name
                      </h3>
                    </div>
                    <button
                      onClick={() => copyToClipboard(selectedKey.key)}
                      className={`p-2 rounded-lg transition-all duration-200 ${
                        copiedKey === selectedKey.key
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
                      title="Copy key"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                  </div>
                  
                  {/* Scrollable key container for long keys */}
                  <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3 overflow-x-auto max-w-full border border-gray-200 dark:border-gray-600">
                    <code className="text-sm font-mono font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">
                      {selectedKey.key}
                    </code>
                  </div>
                </div>

                {/* Metadata Section */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600">
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-orange-600 dark:text-orange-400" />
                      <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">TTL</span>
                    </div>
                    <span className={`text-sm font-mono font-medium ${
                      selectedKey.ttl === null 
                        ? 'text-green-700 dark:text-green-400' 
                        : 'text-orange-700 dark:text-orange-400'
                    }`}>
                      {selectedKey.ttl === null ? 'PERMANENT' : `${selectedKey.ttl}s`}
                    </span>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 border border-gray-200 dark:border-gray-600">
                    <div className="flex items-center gap-2 mb-2">
                      <Type className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">Type</span>
                    </div>
                    <span className="text-sm font-mono font-medium text-blue-700 dark:text-blue-400">
                      {selectedKey.type.toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Value Section */}
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                    Value
                  </h3>
                  
                  {(() => {
                    const { formatted, isJson } = formatValue(selectedKey.value);
                    const isLongContent = formatted.length > 500;
                    
                    return (
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
                        {/* JSON Toggle Header (only for JSON content) */}
                        {isJson && isLongContent && (
                          <div className="border-b border-gray-200 dark:border-gray-700 px-4 py-3">
                            <button
                              onClick={() => setIsJsonCollapsed(!isJsonCollapsed)}
                              className="flex items-center gap-2 text-sm font-medium text-gray-800 dark:text-gray-200 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                            >
                              {isJsonCollapsed ? (
                                <ChevronRight className="w-4 h-4" />
                              ) : (
                                <ChevronDown className="w-4 h-4" />
                              )}
                              {isJsonCollapsed ? 'Expand JSON' : 'Collapse JSON'}
                              <span className="text-xs text-gray-600 dark:text-gray-400">
                                ({formatted.length} characters)
                              </span>
                            </button>
                          </div>
                        )}
                        
                        {/* Value Content */}
                        <div className="p-4">
                          <pre className={`font-mono text-sm font-medium text-gray-900 dark:text-gray-100 whitespace-pre-wrap break-words overflow-y-auto ${
                            isJson && isLongContent && isJsonCollapsed 
                              ? 'max-h-32' 
                              : 'max-h-80'
                          }`}>
                            {isJson && isLongContent && isJsonCollapsed 
                              ? formatted.substring(0, 200) + '...' 
                              : formatted
                            }
                          </pre>
                          
                          {/* Copy Value Button */}
                          <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                            <button
                              onClick={() => copyToClipboard(formatted)}
                              className="text-xs font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors flex items-center gap-1"
                            >
                              <Copy className="w-3 h-3" />
                              Copy Value
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>

                {showDeleteConfirm && (
                  <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                    <h4 className="text-sm font-medium text-red-800 dark:text-red-300 mb-3">
                      Delete key?
                    </h4>
                    <div className="flex gap-3">
                      <button
                        onClick={() => {
                          setShowDeleteConfirm(false);
                          setKeyToDelete('');
                        }}
                        className="flex-1 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleDeleteKey}
                        className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                      >
                        Confirm
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-8 text-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-full">
                    <Key className="w-6 h-6 text-gray-400" />
                  </div>
                  <p className="text-gray-500 dark:text-gray-400 font-medium">No key selected</p>
                  <p className="text-sm text-gray-400 dark:text-gray-500">
                    Select a key from the list to view its details and value
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}