'use client';

import { UserCheck, Bot } from 'lucide-react';

interface LastSyncBadgeProps {
  mode: 'manual' | 'auto' | null;
  time: string | null;
}

export default function LastSyncBadge({ mode, time }: LastSyncBadgeProps) {
  if (!time || !mode) {
    return null;
  }

  const formattedTime = new Date(time).toLocaleString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  const Icon = mode === 'manual' ? UserCheck : Bot;
  const label = mode === 'manual' ? 'Manual' : 'Auto';

  return (
    <div className="flex items-center bg-gray-100 dark:bg-slate-700/60 px-2 py-0.5 rounded-md text-xs text-gray-600 dark:text-gray-300">
      <Icon className="h-3 w-3 mr-1" />
      <span>Last sync {formattedTime} · {label}</span>
    </div>
  );
}