'use client';

import { useSyncStore } from '@/store/syncStore';

export default function GlobalProgressBar() {
  const syncStatus = useSyncStore(state => state.syncStatus);

  if (syncStatus !== 'syncing') {
    return null;
  }

  return (
    <div className="fixed top-0 left-0 right-0 h-0.5 bg-blue-500 animate-pulse z-50" />
  );
}