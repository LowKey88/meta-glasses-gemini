'use client';

import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'react-hot-toast';
import { useSyncStore } from '@/store/syncStore';

export default function SyncButton() {
  const [loading, setLoading] = useState(false);
  const { setSyncStatus, setLastSync } = useSyncStore();

  const handleSync = async () => {
    setLoading(true);
    setSyncStatus('syncing');
    try {
      await api.syncLimitless();
      const now = new Date().toISOString();
      setLastSync(now, 'manual');
      toast.success('Synced successfully');
    } catch (error) {
      toast.error('Sync failed');
      console.error('Sync error:', error);
    } finally {
      setLoading(false);
      setSyncStatus('idle');
    }
  };

  return (
    <button
      onClick={handleSync}
      disabled={loading}
      className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
    >
      <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
      {loading ? 'Syncing...' : 'Sync Now'}
    </button>
  );
}