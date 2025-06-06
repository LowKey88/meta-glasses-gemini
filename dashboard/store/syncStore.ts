import { create } from 'zustand';
import { api } from '@/lib/api';

interface SyncStore {
  syncStatus: 'idle' | 'syncing';
  lastSync: string | null;
  lastSyncMode: 'auto' | 'manual' | null;
  setSyncStatus: (status: 'idle' | 'syncing') => void;
  setLastSync: (time: string, mode: 'auto' | 'manual') => void;
  triggerAutoSync: () => Promise<void>;
}

export const useSyncStore = create<SyncStore>((set, get) => ({
  syncStatus: 'idle',
  lastSync: null,
  lastSyncMode: null,
  setSyncStatus: (status) => set({ syncStatus: status }),
  setLastSync: (time, mode) => set({ lastSync: time, lastSyncMode: mode }),
  triggerAutoSync: async () => {
    set({ syncStatus: 'syncing' });
    try {
      await api.syncLimitless();
      const now = new Date().toISOString();
      set({ 
        syncStatus: 'idle', 
        lastSync: now, 
        lastSyncMode: 'auto' 
      });
    } catch (error) {
      set({ syncStatus: 'idle' });
      throw error;
    }
  }
}));

// Auto-sync polling
if (typeof window !== 'undefined') {
  setInterval(() => {
    const store = useSyncStore.getState();
    store.triggerAutoSync().catch(console.error);
  }, 15 * 60 * 1000); // 15 minutes
}