'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { 
  Settings as SettingsIcon, 
  Shield, 
  Database, 
  MessageSquare, 
  Briefcase, 
  Home, 
  Globe, 
  Cloud,
  Key,
  Eye,
  EyeOff,
  TestTube,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  RefreshCw,
  Loader2,
  XCircle,
  Bot
} from 'lucide-react';

interface Setting {
  value: string;
  source: string;
  has_value: boolean;
  category: string;
  description: string;
  is_sensitive: boolean;
  requires_restart: boolean;
  options?: string[];
}

interface SettingsSchema {
  schema: Record<string, any>;
  categories: Record<string, string>;
}

interface TestResult {
  success: boolean;
  message: string;
}

// Category metadata with icons and descriptions
const categoryMetadata = {
  system: {
    name: 'System Configuration',
    description: 'Core system settings and configuration',
    icon: SettingsIcon,
    badgeClass: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    gradient: 'from-blue-500 to-blue-600'
  },
  ai_services: {
    name: 'AI Services',
    description: 'AI model configuration and API keys',
    icon: Bot,
    badgeClass: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    gradient: 'from-purple-500 to-purple-600'
  },
  communication: {
    name: 'Communication',
    description: 'WhatsApp and messaging configuration',
    icon: MessageSquare,
    badgeClass: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    gradient: 'from-green-500 to-green-600'
  },
  productivity: {
    name: 'Productivity Tools',
    description: 'Notion and task management integrations',
    icon: Briefcase,
    badgeClass: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
    gradient: 'from-orange-500 to-orange-600'
  },
  home_automation: {
    name: 'Home Automation',
    description: 'Home Assistant and smart home settings',
    icon: Home,
    badgeClass: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-300',
    gradient: 'from-indigo-500 to-indigo-600'
  },
  external_services: {
    name: 'External Services',
    description: 'Search engines and web scraping APIs',
    icon: Globe,
    badgeClass: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
    gradient: 'from-cyan-500 to-cyan-600'
  },
  storage: {
    name: 'Cloud Storage',
    description: 'Google Cloud Storage and file management',
    icon: Cloud,
    badgeClass: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
    gradient: 'from-pink-500 to-pink-600'
  }
};

// Skeleton component for loading state
function SettingCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded-full w-8"></div>
        </div>
        <div className="space-y-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    </div>
  );
}

function CategorySkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
      <div className="animate-pulse">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded"></div>
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-40"></div>
            </div>
            <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, Setting>>({});
  const [schema, setSchema] = useState<SettingsSchema | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['system']));
  const [editingSettings, setEditingSettings] = useState<Set<string>>(new Set());
  const [settingValues, setSettingValues] = useState<Record<string, string>>({});
  const [testingConnection, setTestingConnection] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    loadSettings();
    loadSchema();
  }, []);

  const loadSettings = async () => {
    try {
      const response = await api.getSettings();
      setSettings(response.settings);
      
      // Initialize editing values
      const values: Record<string, string> = {};
      Object.entries(response.settings).forEach(([key, setting]) => {
        values[key] = setting.is_sensitive && setting.value ? '' : setting.value;
      });
      setSettingValues(values);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load settings',
        variant: 'destructive',
      });
    }
  };

  const loadSchema = async () => {
    try {
      const response = await api.getSettingsSchema();
      setSchema(response);
      setLoading(false);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to load settings schema',
        variant: 'destructive',
      });
      setLoading(false);
    }
  };

  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  const startEditing = (key: string) => {
    const newEditing = new Set(editingSettings);
    newEditing.add(key);
    setEditingSettings(newEditing);
    if (settings[key]?.is_sensitive) {
      setSettingValues({ ...settingValues, [key]: '' });
    }
  };

  const cancelEditing = (key: string) => {
    const newEditing = new Set(editingSettings);
    newEditing.delete(key);
    setEditingSettings(newEditing);
    
    // Reset value
    const originalValue = settings[key]?.is_sensitive && settings[key]?.value ? '' : settings[key]?.value || '';
    setSettingValues({ ...settingValues, [key]: originalValue });
  };

  const saveSetting = async (key: string) => {
    try {
      const value = settingValues[key];
      if (!value && settings[key]?.is_sensitive) {
        toast({
          title: 'Error',
          description: 'Value is required for sensitive settings',
          variant: 'destructive',
        });
        return;
      }

      await api.updateSetting(key, value);
      
      const newEditing = new Set(editingSettings);
      newEditing.delete(key);
      setEditingSettings(newEditing);
      
      // Reload settings to get updated values
      await loadSettings();
      
      toast({
        title: 'Success',
        description: settings[key]?.requires_restart 
          ? 'Setting saved. Restart required to take effect.'
          : 'Setting saved successfully',
        variant: settings[key]?.requires_restart ? 'default' : 'default',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save setting',
        variant: 'destructive',
      });
    }
  };

  const testConnection = async (key: string) => {
    try {
      setTestingConnection(key);
      const value = settingValues[key] || settings[key]?.value;
      
      if (!value) {
        toast({
          title: 'Error',
          description: 'No value to test',
          variant: 'destructive',
        });
        return;
      }

      const result: TestResult = await api.testSettingConnection(key, value);
      
      toast({
        title: result.success ? 'Connection Test Successful' : 'Connection Test Failed',
        description: result.message,
        variant: result.success ? 'default' : 'destructive',
      });
    } catch (error: any) {
      toast({
        title: 'Test Failed',
        description: error.response?.data?.detail || 'Failed to test connection',
        variant: 'destructive',
      });
    } finally {
      setTestingConnection(null);
    }
  };

  const revertSetting = async (key: string) => {
    try {
      await api.deleteSetting(key);
      await loadSettings();
      
      toast({
        title: 'Setting Reverted',
        description: 'Setting has been reverted to environment variable',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to revert setting',
        variant: 'destructive',
      });
    }
  };

  const getSettingsByCategory = (category: string): [string, Setting][] => {
    return Object.entries(settings).filter(([_, setting]) => (setting as Setting).category === category) as [string, Setting][];
  };

  const hasTestableConnection = (key: string) => {
    return ['gemini_api_key', 'whatsapp_auth_token', 'notion_integration_secret', 'home_assistant_token'].includes(key);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64 mb-2"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-96"></div>
          </div>
          <div className="space-y-6">
            <CategorySkeleton />
            <CategorySkeleton />
            <CategorySkeleton />
            <CategorySkeleton />
          </div>
        </div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 max-w-md">
          <div className="flex items-center space-x-2 mb-2">
            <XCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">Failed to Load Settings</h3>
          </div>
          <p className="text-red-600 dark:text-red-300">Unable to load settings schema. Please try refreshing the page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center space-x-3 mb-4">
            <div className="p-3 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg">
              <SettingsIcon className="h-8 w-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Settings Management
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Configure your application settings and API integrations
              </p>
            </div>
          </div>
        </div>

        {/* Important Notice */}
        <div className="mb-8 bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 border border-yellow-200 dark:border-yellow-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              </div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">
                Configuration Priority
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 leading-relaxed">
                Settings configured here take precedence over environment variables. Changes to sensitive settings may require a system restart to take effect.
              </p>
            </div>
          </div>
        </div>

        {/* Settings Categories */}
        <div className="space-y-6">
          {Object.entries(schema.categories).map(([categoryKey, categoryName]) => {
            const categorySettings = getSettingsByCategory(categoryKey);
            if (categorySettings.length === 0) return null;

            const isExpanded = expandedCategories.has(categoryKey);
            const metadata = categoryMetadata[categoryKey as keyof typeof categoryMetadata];
            const IconComponent = metadata?.icon || SettingsIcon;

            return (
              <div key={categoryKey} className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(categoryKey)}
                  className="w-full px-6 py-5 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-xl transition-all duration-200 flex items-center justify-between"
                >
                  <div className="flex items-center space-x-4">
                    <div className={`p-3 bg-gradient-to-br ${metadata?.gradient || 'from-gray-500 to-gray-600'} rounded-xl shadow-md group-hover:shadow-lg transition-all duration-200`}>
                      <IconComponent className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-gray-700 dark:group-hover:text-gray-200 transition-colors">
                        {metadata?.name || categoryName}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                        {metadata?.description || 'Configuration settings'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <span className={`inline-flex items-center px-3 py-1 rounded-lg text-xs font-medium ${metadata?.badgeClass || 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'}`}>
                      {categorySettings.length} setting{categorySettings.length !== 1 ? 's' : ''}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="h-5 w-5 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
                    )}
                  </div>
                </button>

                {/* Settings Content */}
                {isExpanded && (
                  <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-700/20 rounded-b-xl">
                    <div className="p-6 space-y-6">
                      {categorySettings.map(([key, setting]) => (
                        <div key={key} className="group/setting bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all duration-200">
                          {/* Setting Header */}
                          <div className="flex items-start justify-between mb-4">
                            <div className="flex-1">
                              <div className="flex items-center space-x-3 mb-2">
                                <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg">
                                  <Key className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                                </div>
                                <div>
                                  <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                  </h4>
                                  <p className="text-sm text-gray-500 dark:text-gray-400">
                                    {setting.description}
                                  </p>
                                </div>
                              </div>
                              
                              {/* Badges */}
                              <div className="flex items-center space-x-2">
                                {setting.is_sensitive && (
                                  <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                                    <Shield className="h-3 w-3 mr-1" />
                                    Sensitive
                                  </span>
                                )}
                                {setting.requires_restart && (
                                  <span className="inline-flex items-center px-3 py-1 rounded-lg text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300">
                                    <RefreshCw className="h-3 w-3 mr-1" />
                                    Restart Required
                                  </span>
                                )}
                                <span className={`inline-flex items-center px-3 py-1 rounded-lg text-xs font-medium ${
                                  setting.source === 'redis' 
                                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' 
                                    : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                                }`}>
                                  <Database className="h-3 w-3 mr-1" />
                                  {setting.source === 'redis' ? 'Override Active' : 'Environment'}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Setting Value and Controls */}
                          <div className="space-y-4">
                            {editingSettings.has(key) ? (
                              /* Edit Mode */
                              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 space-y-4">
                                <div>
                                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                                    New Value
                                  </label>
                                  {setting.options ? (
                                    <select
                                      value={settingValues[key] || ''}
                                      onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSettingValues({ ...settingValues, [key]: e.target.value })}
                                      className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 text-gray-900 dark:text-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500 transition-all duration-200"
                                    >
                                      <option value="">Select an option...</option>
                                      {(setting.options as string[]).map((option: string) => (
                                        <option key={option} value={option}>{option}</option>
                                      ))}
                                    </select>
                                  ) : (
                                    <div className="relative">
                                      <input
                                        type={setting.is_sensitive ? 'password' : 'text'}
                                        value={settingValues[key] || ''}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSettingValues({ ...settingValues, [key]: e.target.value })}
                                        placeholder={setting.is_sensitive ? 'Enter new value...' : 'Enter value...'}
                                        className="block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-3 pr-10 text-gray-900 dark:text-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500 transition-all duration-200"
                                      />
                                      {setting.is_sensitive && (
                                        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                                          <Key className="h-4 w-4 text-gray-400" />
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                                
                                {/* Action Buttons */}
                                <div className="flex items-center space-x-3">
                                  <button
                                    onClick={() => saveSetting(key)}
                                    className="inline-flex items-center px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-all duration-200"
                                  >
                                    <Check className="h-4 w-4 mr-2" />
                                    Save Changes
                                  </button>
                                  <button
                                    onClick={() => cancelEditing(key)}
                                    className="inline-flex items-center px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-all duration-200"
                                  >
                                    <X className="h-4 w-4 mr-2" />
                                    Cancel
                                  </button>
                                  {hasTestableConnection(key) && (
                                    <button
                                      onClick={() => testConnection(key)}
                                      disabled={testingConnection === key}
                                      className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                                    >
                                      {testingConnection === key ? (
                                        <>
                                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                          Testing...
                                        </>
                                      ) : (
                                        <>
                                          <TestTube className="h-4 w-4 mr-2" />
                                          Test Connection
                                        </>
                                      )}
                                    </button>
                                  )}
                                </div>
                              </div>
                            ) : (
                              /* Display Mode */
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-4">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Current Value:</span>
                                      {setting.is_sensitive ? (
                                        <EyeOff className="h-4 w-4 text-gray-400" />
                                      ) : (
                                        <Eye className="h-4 w-4 text-gray-400" />
                                      )}
                                    </div>
                                    <div className="mt-1 font-mono text-sm text-gray-900 dark:text-white break-all">
                                      {setting.has_value ? (setting.value || '(empty)') : '(not configured)'}
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Action Buttons */}
                                <div className="ml-4 flex items-center space-x-2">
                                  <button
                                    onClick={() => startEditing(key)}
                                    className="inline-flex items-center px-4 py-2 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200 group/edit"
                                  >
                                    <SettingsIcon className="h-4 w-4 mr-2 group-hover/edit:rotate-90 transition-transform duration-200" />
                                    Configure
                                  </button>
                                  
                                  {setting.source === 'redis' && (
                                    <button
                                      onClick={() => revertSetting(key)}
                                      className="inline-flex items-center px-4 py-2 rounded-lg bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 text-sm font-medium hover:bg-orange-200 dark:hover:bg-orange-900/50 transition-all duration-200"
                                    >
                                      <RefreshCw className="h-4 w-4 mr-2" />
                                      Revert
                                    </button>
                                  )}
                                  
                                  {hasTestableConnection(key) && setting.has_value && (
                                    <button
                                      onClick={() => testConnection(key)}
                                      disabled={testingConnection === key}
                                      className="inline-flex items-center px-4 py-2 rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 text-sm font-medium hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                                    >
                                      {testingConnection === key ? (
                                        <>
                                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                          Testing...
                                        </>
                                      ) : (
                                        <>
                                          <TestTube className="h-4 w-4 mr-2" />
                                          Test
                                        </>
                                      )}
                                    </button>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}