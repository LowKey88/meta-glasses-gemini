'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { api } from '@/lib/api';
import { 
  Home, 
  Brain, 
  Database, 
  LogOut,
  Glasses,
  Activity,
  Mic,
  Settings
} from 'lucide-react';

const navigation = [
  { name: 'Overview', href: '/dashboard', icon: Home },
  { name: 'Memories', href: '/dashboard/memories', icon: Brain },
  { name: 'Performance', href: '/dashboard/performance', icon: Activity },
  { name: 'Limitless', href: '/dashboard/limitless', icon: Mic },
  { name: 'Redis Monitor', href: '/dashboard/redis', icon: Database },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
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
      <div className={`fixed inset-y-0 left-0 z-30 flex h-full w-64 flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 shadow-lg transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${
        isOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        {/* Header */}
        <div className="flex h-16 items-center justify-center border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-600 to-blue-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/10 rounded-lg">
              <Glasses className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">Meta Glasses</h1>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6">
          <div className="space-y-2">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  onClick={handleLinkClick}
                  className={`
                    group relative flex items-center gap-3 px-3 py-3 text-sm font-medium rounded-xl transition-all duration-200
                    ${
                      isActive
                        ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 shadow-sm'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-white'
                    }
                  `}
                >
                  {/* Active indicator */}
                  {isActive && (
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-600 rounded-r-full" />
                  )}
                  
                  {/* Icon */}
                  <div className={`p-2 rounded-lg transition-colors ${
                    isActive 
                      ? 'bg-blue-100 dark:bg-blue-800/30' 
                      : 'bg-gray-100 dark:bg-gray-800 group-hover:bg-gray-200 dark:group-hover:bg-gray-700'
                  }`}>
                    <Icon className={`w-5 h-5 ${
                      isActive 
                        ? 'text-blue-600 dark:text-blue-400' 
                        : 'text-gray-600 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-300'
                    }`} />
                  </div>
                  
                  {/* Label */}
                  <span className="flex-1">{item.name}</span>
                  
                  {/* Active dot */}
                  {isActive && (
                    <div className="w-2 h-2 bg-blue-600 rounded-full" />
                  )}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Divider */}
        <div className="px-4">
          <div className="h-px bg-gray-200 dark:bg-gray-700" />
        </div>

        {/* Logout */}
        <div className="flex-shrink-0 p-4">
          <button
            onClick={handleLogout}
            className="group flex w-full items-center gap-3 px-3 py-3 text-sm font-medium text-gray-700 dark:text-gray-300 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-700 dark:hover:text-red-300 transition-all duration-200"
          >
            <div className="p-2 bg-gray-100 dark:bg-gray-800 group-hover:bg-red-100 dark:group-hover:bg-red-800/30 rounded-lg transition-colors">
              <LogOut className="w-5 h-5 text-gray-600 dark:text-gray-400 group-hover:text-red-600 dark:group-hover:text-red-400" />
            </div>
            <span className="flex-1 text-left">Logout</span>
          </button>
        </div>
    </div>
    </>
  );
}