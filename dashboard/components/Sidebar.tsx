'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';

const navigation = [
  { name: 'Overview', href: '/dashboard' },
  { name: 'Memories', href: '/dashboard/memories' },
  { name: 'Redis Monitor', href: '/dashboard/redis' },
];

export default function Sidebar() {
  const pathname = usePathname();

  const handleLogout = () => {
    api.clearToken();
    window.location.href = '/login';
  };

  return (
    <div className="flex h-full w-64 flex-col bg-gray-900">
      <div className="flex h-16 items-center justify-center">
        <h1 className="text-xl font-semibold text-white">Meta Glasses</h1>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                group flex items-center px-2 py-2 text-sm font-medium rounded-md
                ${
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }
              `}
            >
              {item.name}
            </Link>
          );
        })}
      </nav>
      <div className="flex-shrink-0 p-4">
        <button
          onClick={handleLogout}
          className="group flex w-full items-center px-2 py-2 text-sm font-medium text-gray-300 rounded-md hover:bg-gray-700 hover:text-white"
        >
          Logout
        </button>
      </div>
    </div>
  );
}