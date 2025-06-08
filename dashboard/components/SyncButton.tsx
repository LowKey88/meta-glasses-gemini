'use client';

import { useState, useEffect, useRef } from 'react';
import { RefreshCw } from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'react-hot-toast';
import { useSyncStore } from '@/store/syncStore';

export default function SyncButton() {
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const { setSyncStatus, setLastSync } = useSyncStore();
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const pollSyncStatus = async (taskId: string) => {
    try {
      const status = await api.getSyncStatus(taskId);
      
      if (status.status === 'completed') {
        // Sync completed successfully
        clearInterval(pollIntervalRef.current!);
        setLoading(false);
        setSyncStatus('idle');
        setTaskId(null);
        const now = new Date().toISOString();
        setLastSync(now, 'manual');
        toast.success('Synced successfully');
        
        // Refresh the page data
        window.location.reload();
      } else if (status.status === 'failed') {
        // Sync failed
        clearInterval(pollIntervalRef.current!);
        setLoading(false);
        setSyncStatus('idle');
        setTaskId(null);
        toast.error(status.error || 'Sync failed');
      }
      // If still running, continue polling
    } catch (error) {
      // Task might not exist yet, continue polling
      console.debug('Polling sync status...', error);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    setSyncStatus('syncing');
    try {
      // Start sync in background
      const response = await api.syncLimitless();
      setTaskId(response.task_id);
      toast.success('Sync started in background');
      
      // Start polling for status
      pollIntervalRef.current = setInterval(() => {
        pollSyncStatus(response.task_id);
      }, 1000); // Poll every second
      
    } catch (error) {
      setLoading(false);
      setSyncStatus('idle');
      toast.error('Failed to start sync');
      console.error('Sync error:', error);
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