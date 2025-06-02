'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';

const navigation = [
  { name: 'Overview', href: '/dashboard' },
  { name: 'Memories', href: '/dashboard/memories' },
  { name: 'Redis Monitor', href: '/dashboard/redis' },
];

interface SidebarProps {
  isOpen: boolean;
  onClose?: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  const handleLogout = () => {
    api.clearToken();
    window.location.href = '/login';
  };

  const handleLinkClick = () => {
    // Close sidebar on mobile after clicking a link
    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-20 bg-black bg-opacity-50 md:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-30 flex h-full w-64 flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
      <div className="flex h-16 items-center justify-center border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Meta Glasses</h1>
      </div>
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              onClick={handleLinkClick}
              className={`
                group flex items-center px-2 py-2 text-sm font-medium rounded-md
                ${
                  isActive
                    ? 'bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-white'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
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
          className="group flex w-full items-center px-2 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white"
        >
          Logout
        </button>
      </div>
    </div>
    </>
  );
}