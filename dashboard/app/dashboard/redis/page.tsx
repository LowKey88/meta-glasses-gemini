'use client';

import { useEffect, useState } from 'react';
import { api, RedisKey } from '@/lib/api';

export default function RedisPage() {
  const [keys, setKeys] = useState<RedisKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchPattern, setSearchPattern] = useState('');
  const [selectedKey, setSelectedKey] = useState<RedisKey | null>(null);

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

  const handleDeleteKey = async (key: string) => {
    if (!confirm(`Are you sure you want to delete the key "${key}"?`)) return;
    
    try {
      await api.deleteRedisKey(key);
      await fetchKeys(searchPattern);
      if (selectedKey?.key === key) {
        setSelectedKey(null);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete key');
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-8">
        Redis Monitor
      </h1>

      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
          <input
            type="text"
            placeholder="Search pattern (e.g., user:*, reminder:*)"
            className="flex-1 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            value={searchPattern}
            onChange={(e) => setSearchPattern(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 sm:flex-none rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchPattern('');
                fetchKeys();
              }}
              className="flex-1 sm:flex-none rounded-md bg-gray-300 dark:bg-gray-600 px-4 py-2 text-sm font-medium text-gray-700 dark:text-white hover:bg-gray-400 dark:hover:bg-gray-500"
            >
              Reset
            </button>
          </div>
        </div>
      </form>

      {loading && <div>Loading Redis keys...</div>}
      {error && <div className="text-red-600">Error: {error}</div>}

      <div className="grid grid-cols-1 gap-4 lg:gap-6 lg:grid-cols-2">
        <div className="bg-white dark:bg-gray-700 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Redis Keys ({keys.length})
            </h3>
            <div className="overflow-hidden">
              <ul className="divide-y divide-gray-200 dark:divide-gray-600 max-h-96 overflow-y-auto">
                {keys.map((key) => (
                  <li
                    key={key.key}
                    className="py-3 px-2 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer"
                    onClick={() => handleViewKey(key.key)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                          {key.key}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Type: {key.type} | TTL: {key.ttl === null ? 'No expiry' : `${key.ttl}s`}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteKey(key.key);
                        }}
                        className="ml-2 text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-700 shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Key Details
            </h3>
            {selectedKey ? (
              <div>
                <dl className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Key</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white break-all">
                      {selectedKey.key}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">Type</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {selectedKey.type}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-300">TTL</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {selectedKey.ttl === null ? 'No expiry' : `${selectedKey.ttl} seconds`}
                    </dd>
                  </div>
                </dl>
                <div className="mt-4">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-300 mb-2">
                    Value
                  </dt>
                  <dd className="mt-1">
                    <pre className="bg-gray-100 dark:bg-gray-800 rounded p-3 text-xs overflow-auto max-h-64">
                      {JSON.stringify(selectedKey.value, null, 2)}
                    </pre>
                  </dd>
                </div>
              </div>
            ) : (
              <p className="text-gray-500 dark:text-gray-400">
                Select a key from the list to view details
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}