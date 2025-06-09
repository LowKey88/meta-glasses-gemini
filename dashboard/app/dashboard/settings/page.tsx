'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface Setting {
  key: string;
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
    setEditingSettings(new Set([...editingSettings, key]));
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

  const getSettingsByCategory = (category: string) => {
    return Object.entries(settings).filter(([_, setting]) => setting.category === category);
  };

  const hasTestableConnection = (key: string) => {
    return ['gemini_api_key', 'whatsapp_auth_token', 'notion_integration_secret', 'home_assistant_token'].includes(key);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="text-center text-red-600">
        Failed to load settings schema
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Manage your application configuration and API keys
        </p>
      </div>

      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Important
            </h3>
            <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
              Settings stored here take precedence over environment variables. Some changes may require a restart.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(schema.categories).map(([categoryKey, categoryName]) => {
          const categorySettings = getSettingsByCategory(categoryKey);
          if (categorySettings.length === 0) return null;

          const isExpanded = expandedCategories.has(categoryKey);

          return (
            <div key={categoryKey} className="bg-white dark:bg-gray-800 shadow rounded-lg">
              <button
                onClick={() => toggleCategory(categoryKey)}
                className="w-full px-6 py-4 text-left font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between"
              >
                <span>{categoryName}</span>
                <svg
                  className={`h-5 w-5 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isExpanded && (
                <div className="border-t border-gray-200 dark:border-gray-700">
                  {categorySettings.map(([key, setting]) => (
                    <div key={key} className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 last:border-b-0">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                              {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </h3>
                            {setting.is_sensitive && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                                Sensitive
                              </span>
                            )}
                            {setting.requires_restart && (
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
                                Restart Required
                              </span>
                            )}
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                              setting.source === 'redis' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                            }`}>
                              {setting.source}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                            {setting.description}
                          </p>

                          <div className="mt-3">
                            {editingSettings.has(key) ? (
                              <div className="space-y-2">
                                {setting.options ? (
                                  <select
                                    value={settingValues[key] || ''}
                                    onChange={(e) => setSettingValues({ ...settingValues, [key]: e.target.value })}
                                    className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-indigo-500 focus:ring-indigo-500"
                                  >
                                    <option value="">Select an option...</option>
                                    {setting.options.map(option => (
                                      <option key={option} value={option}>{option}</option>
                                    ))}
                                  </select>
                                ) : (
                                  <input
                                    type={setting.is_sensitive ? 'password' : 'text'}
                                    value={settingValues[key] || ''}
                                    onChange={(e) => setSettingValues({ ...settingValues, [key]: e.target.value })}
                                    placeholder={setting.is_sensitive ? 'Enter new value...' : 'Enter value...'}
                                    className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white focus:border-indigo-500 focus:ring-indigo-500"
                                  />
                                )}
                                <div className="flex space-x-2">
                                  <button
                                    onClick={() => saveSetting(key)}
                                    className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                  >
                                    Save
                                  </button>
                                  <button
                                    onClick={() => cancelEditing(key)}
                                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                  >
                                    Cancel
                                  </button>
                                  {hasTestableConnection(key) && (
                                    <button
                                      onClick={() => testConnection(key)}
                                      disabled={testingConnection === key}
                                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                                    >
                                      {testingConnection === key ? 'Testing...' : 'Test'}
                                    </button>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <div className="flex items-center justify-between">
                                <span className="text-sm text-gray-900 dark:text-white font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                                  {setting.has_value ? (setting.value || '(empty)') : '(not set)'}
                                </span>
                                <div className="flex space-x-2">
                                  <button
                                    onClick={() => startEditing(key)}
                                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                                  >
                                    Edit
                                  </button>
                                  {setting.source === 'redis' && (
                                    <button
                                      onClick={() => revertSetting(key)}
                                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-xs font-medium rounded text-red-700 dark:text-red-400 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                                    >
                                      Revert
                                    </button>
                                  )}
                                  {hasTestableConnection(key) && setting.has_value && (
                                    <button
                                      onClick={() => testConnection(key)}
                                      disabled={testingConnection === key}
                                      className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-xs font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
                                    >
                                      {testingConnection === key ? 'Testing...' : 'Test'}
                                    </button>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}