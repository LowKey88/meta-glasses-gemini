'use client';

import { useEffect, useState } from 'react';
import { api, RedisKey } from '@/lib/api';
import { Trash2, Copy, Search, RefreshCw } from 'lucide-react';

export default function RedisPage() {
  const [keys, setKeys] = useState<RedisKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchPattern, setSearchPattern] = useState('');
  const [selectedKey, setSelectedKey] = useState<RedisKey | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [keyToDelete, setKeyToDelete] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string>('');

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

  const formatValue = (value: any): string => {
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return value;
      }
    }
    return JSON.stringify(value, null, 2);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Redis Monitor
          </h1>
          <div className="flex gap-2">
            <button
              onClick={() => fetchKeys(searchPattern)}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Filter
            </button>
            <button
              onClick={() => {
                setSearchPattern('');
                fetchKeys();
              }}
              className="px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Reset
            </button>
          </div>
        </div>

        <div className="mb-6">
          <form onSubmit={handleSearch} className="flex gap-4">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder="Search pattern (e.g, user:*, reminder:*)"
                className="w-full px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
                value={searchPattern}
                onChange={(e) => setSearchPattern(e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="px-6 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2"
            >
              Filter
              <Search className="w-4 h-4" />
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Keys List */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Redis Keys ({keys.length})
              </h2>
            </div>
            
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading Redis keys...</div>
            ) : error ? (
              <div className="p-8 text-center text-red-600">Error: {error}</div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[600px] overflow-y-auto">
                {keys.map((key) => (
                  <div
                    key={key.key}
                    className={`px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors ${
                      selectedKey?.key === key.key ? 'bg-gray-50 dark:bg-gray-700' : ''
                    }`}
                    onClick={() => handleViewKey(key.key)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0 pr-4">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {key.key}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setKeyToDelete(key.key);
                            setShowDeleteConfirm(true);
                          }}
                          className="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            copyToClipboard(key.key, true);
                          }}
                          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                          title="Copy"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Key Details */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Key Details
              </h2>
            </div>
            
            {selectedKey ? (
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      Key
                    </h3>
                    <code className="text-sm bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                      {selectedKey.key}
                    </code>
                  </div>
                  <button
                    onClick={() => copyToClipboard(selectedKey.key)}
                    className={`p-2 rounded-lg transition-colors ${
                      copiedKey === selectedKey.key
                        ? 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                    title="Copy key"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex items-center gap-6 mb-6">
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium">
                      {selectedKey.ttl === null ? 'PERMANENT' : `TTL: ${selectedKey.ttl}s`}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {selectedKey.type.toUpperCase()}
                  </div>
                </div>

                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                  <pre className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
{formatValue(selectedKey.value)}
                  </pre>
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
              <div className="p-8 text-center text-gray-500 dark:text-gray-400">
                Select a key from the list to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}