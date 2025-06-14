'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, Task, CreateTaskRequest, TaskStats } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { 
  Search, 
  Plus, 
  Edit3, 
  Trash2, 
  Save, 
  X, 
  Calendar,
  Filter,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RefreshCw,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  MoreHorizontal,
  Bot,
  Mic,
  FileText,
  MessageSquare,
  Target,
  BarChart3,
  TrendingUp
} from 'lucide-react';

type TaskSource = 'all' | 'ai_extracted' | 'natural_language' | 'manual' | 'voice_command';
type DueFilter = 'all' | 'today' | 'week' | 'overdue';
type SortBy = 'created' | 'due' | 'title';
type SortOrder = 'asc' | 'desc';

// Source icon and label mapping
const sourceConfig = {
  ai_extracted: { icon: Bot, label: 'AI Extracted', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  natural_language: { icon: Mic, label: 'Voice Recording', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  manual: { icon: FileText, label: 'Manual', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
  voice_command: { icon: MessageSquare, label: 'WhatsApp', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
};

export default function ActionsPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState<TaskSource>('all');
  const [dueFilter, setDueFilter] = useState<DueFilter>('all');
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const [sortBy, setSortBy] = useState<SortBy>('created');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  
  // Create form state
  const [newTask, setNewTask] = useState<CreateTaskRequest>({
    title: '',
    notes: '',
    due_date: ''
  });

  const { toast } = useToast();

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.getTasks(
        includeCompleted,
        dueFilter === 'all' ? undefined : dueFilter,
        sortBy,
        sortOrder
      );
      
      let filteredTasks = response.tasks;
      
      // Apply source filter
      if (sourceFilter !== 'all') {
        filteredTasks = filteredTasks.filter(task => task.source === sourceFilter);
      }
      
      // Apply search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filteredTasks = filteredTasks.filter(task => 
          task.title.toLowerCase().includes(query) ||
          (task.notes && task.notes.toLowerCase().includes(query))
        );
      }
      
      setTasks(filteredTasks);
    } catch (error) {
      console.error('Error loading tasks:', error);
      toast({
        title: 'Error',
        description: 'Failed to load tasks',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [includeCompleted, dueFilter, sortBy, sortOrder, sourceFilter, searchQuery, toast]);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await api.getTaskStats();
      setStats(statsData);
    } catch (error) {
      console.error('Error loading task stats:', error);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    loadStats();
  }, [loadTasks, loadStats]);

  const handleCreateTask = async () => {
    if (!newTask.title.trim()) {
      toast({
        title: 'Error',
        description: 'Task title is required',
        variant: 'destructive',
      });
      return;
    }

    try {
      setCreating(true);
      await api.createTask({
        ...newTask,
        due_date: newTask.due_date || undefined
      });

      toast({
        title: 'Success',
        description: 'Task created successfully',
      });

      setNewTask({ title: '', notes: '', due_date: '' });
      setShowCreateForm(false);
      loadTasks();
      loadStats();
    } catch (error) {
      console.error('Error creating task:', error);
      toast({
        title: 'Error',
        description: 'Failed to create task',
        variant: 'destructive',
      });
    } finally {
      setCreating(false);
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    try {
      await api.completeTask(taskId);
      toast({
        title: 'Success',
        description: 'Task completed',
      });
      loadTasks();
      loadStats();
    } catch (error) {
      console.error('Error completing task:', error);
      toast({
        title: 'Error',
        description: 'Failed to complete task',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    if (!confirm('Are you sure you want to delete this task?')) return;

    try {
      await api.deleteTask(taskId);
      toast({
        title: 'Success',
        description: 'Task deleted',
      });
      loadTasks();
      loadStats();
    } catch (error) {
      console.error('Error deleting task:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete task',
        variant: 'destructive',
      });
    }
  };

  const handleToggleCompleted = async (task: Task) => {
    try {
      await api.updateTask(task.id, { completed: task.status !== 'completed' });
      toast({
        title: 'Success',
        description: task.status === 'completed' ? 'Task marked as incomplete' : 'Task completed',
      });
      loadTasks();
      loadStats();
    } catch (error) {
      console.error('Error updating task:', error);
      toast({
        title: 'Error',
        description: 'Failed to update task',
        variant: 'destructive',
      });
    }
  };

  const getTaskPriorityColor = (task: Task) => {
    if (task.is_overdue) return 'border-l-red-500 dark:border-l-red-400';
    if (task.due_display && task.days_until_due !== undefined && task.days_until_due <= 1) return 'border-l-orange-500 dark:border-l-orange-400';
    if (task.due_display && task.days_until_due !== undefined && task.days_until_due <= 3) return 'border-l-yellow-500 dark:border-l-yellow-400';
    return 'border-l-gray-200 dark:border-l-gray-700';
  };

  const filteredAndSortedTasks = tasks;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="mb-8">
        <div className="sm:flex sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
              <Target className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <span>Actions & Tasks</span>
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              Manage tasks from all sources
            </p>
          </div>
          <div className="mt-4 sm:mt-0 flex items-center gap-3">
            <button
              onClick={() => setShowCreateForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 flex items-center gap-2 transition-colors"
            >
              <Plus className="h-4 w-4" />
              New Task
            </button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <Target className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Total Tasks</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.total_tasks}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Completed</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.completed_tasks}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">{stats.completion_rate}% completion rate</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <Clock className="h-8 w-8 text-orange-600 dark:text-orange-400" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Due Today</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.due_today}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">Overdue</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.overdue_tasks}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Source Distribution */}
      {stats && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-900 dark:text-white">
            <BarChart3 className="h-5 w-5" />
            Task Sources
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(stats.source_distribution).map(([source, count]) => {
              const config = sourceConfig[source as keyof typeof sourceConfig];
              if (!config) return null;
              const Icon = config.icon;
              
              return (
                <div key={source} className="flex items-center gap-2">
                  <div className={`p-2 rounded-lg ${config.color}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{config.label}</p>
                    <p className="text-lg font-bold text-gray-900 dark:text-white">{count}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Enhanced Filters & Search */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="p-6">
          <div className="flex flex-col space-y-4">
            {/* Search Bar - Enhanced */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400 dark:text-gray-500" />
              </div>
              <input
                type="text"
                placeholder="Search tasks by title or notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-11 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-all duration-200"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            {/* Filters Row - Enhanced */}
            <div className="flex flex-wrap gap-3 items-center">
              {/* Source Filter */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Source</label>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value as TaskSource)}
                  className="appearance-none bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-all duration-200 min-w-[140px]"
                >
                  <option value="all">All Sources</option>
                  <option value="ai_extracted">🤖 AI Extracted</option>
                  <option value="natural_language">🎙️ Voice Recording</option>
                  <option value="manual">📝 Manual</option>
                  <option value="voice_command">🗣️ WhatsApp</option>
                </select>
                <ChevronDown className="absolute right-2 top-7 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>

              {/* Due Filter */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Due Date</label>
                <select
                  value={dueFilter}
                  onChange={(e) => setDueFilter(e.target.value as DueFilter)}
                  className="appearance-none bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-all duration-200 min-w-[140px]"
                >
                  <option value="all">All Tasks</option>
                  <option value="today">Due Today</option>
                  <option value="week">Due This Week</option>
                  <option value="overdue">Overdue</option>
                </select>
                <ChevronDown className="absolute right-2 top-7 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>

              {/* Sort Options */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Sort by</label>
                <select
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [newSortBy, newSortOrder] = e.target.value.split('-');
                    setSortBy(newSortBy as SortBy);
                    setSortOrder(newSortOrder as SortOrder);
                  }}
                  className="appearance-none bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent transition-all duration-200 min-w-[140px]"
                >
                  <option value="created-desc">Newest First</option>
                  <option value="created-asc">Oldest First</option>
                  <option value="due-asc">Due Date (Soon)</option>
                  <option value="due-desc">Due Date (Later)</option>
                  <option value="title-asc">Title A-Z</option>
                  <option value="title-desc">Title Z-A</option>
                </select>
                <ArrowUpDown className="absolute right-2 top-7 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>

              {/* Completed Toggle - Enhanced */}
              <div className="flex flex-col">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Options</label>
                <label className="flex items-center gap-3 bg-gray-50 dark:bg-gray-700 rounded-lg px-4 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors">
                  <input
                    type="checkbox"
                    checked={includeCompleted}
                    onChange={(e) => setIncludeCompleted(e.target.checked)}
                    className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300 select-none">Include Completed</span>
                </label>
              </div>

              {/* Refresh Button - Enhanced */}
              <div className="flex flex-col">
                <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">&nbsp;</div>
                <button
                  onClick={loadTasks}
                  className="p-2 rounded-lg bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-500 transition-all duration-200"
                  title="Refresh tasks"
                >
                  <RefreshCw className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Task List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        {loading ? (
          <div className="p-8 text-center">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-gray-400 dark:text-gray-500" />
            <p className="text-gray-600 dark:text-gray-400">Loading tasks...</p>
          </div>
        ) : filteredAndSortedTasks.length === 0 ? (
          <div className="p-8 text-center">
            <Target className="h-12 w-12 mx-auto mb-4 text-gray-400 dark:text-gray-500" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No tasks found</h3>
            <p className="text-gray-600 dark:text-gray-400">
              {searchQuery || sourceFilter !== 'all' || dueFilter !== 'all' 
                ? 'Try adjusting your filters or search query'
                : 'Create your first task to get started'
              }
            </p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredAndSortedTasks.map((task) => {
              const taskSourceConfig = {
                ai_extracted: { icon: Bot, label: 'AI Extracted', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
                natural_language: { icon: Mic, label: 'Voice Recording', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
                manual: { icon: FileText, label: 'Manual', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
                voice_command: { icon: MessageSquare, label: 'WhatsApp', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
              }[task.source];
              
              const SourceIcon = taskSourceConfig?.icon || FileText;
              
              return (
                <div
                  key={task.id}
                  className={`p-4 border-l-4 ${getTaskPriorityColor(task)} hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <button
                        onClick={() => handleToggleCompleted(task)}
                        className={`mt-1 rounded-full p-1 ${
                          task.status === 'completed'
                            ? 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400'
                            : 'bg-gray-100 text-gray-400 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-500 dark:hover:bg-gray-600'
                        }`}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                      </button>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className={`font-medium ${
                            task.status === 'completed' ? 'line-through text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'
                          }`}>
                            {task.title}
                          </h3>
                          
                          {/* Source Badge */}
                          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${taskSourceConfig?.color || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'}`}>
                            <SourceIcon className="h-3 w-3" />
                            {taskSourceConfig?.label}
                          </span>
                          
                          {/* Due Date Badge */}
                          {task.due_display && (
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                              task.is_overdue
                                ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                : task.days_until_due !== undefined && task.days_until_due <= 1
                                ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                                : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                            }`}>
                              <Calendar className="h-3 w-3" />
                              {task.due_display}
                              {task.is_overdue && ' (Overdue)'}
                            </span>
                          )}
                        </div>
                        
                        {task.notes && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{task.notes}</p>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2 ml-4">
                      {task.status !== 'completed' && (
                        <button
                          onClick={() => handleCompleteTask(task.id)}
                          className="text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300 p-1"
                          title="Complete task"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                        </button>
                      )}
                      
                      <button
                        onClick={() => handleDeleteTask(task.id)}
                        className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 p-1"
                        title="Delete task"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Task Modal */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Create New Task</h2>
              <button
                onClick={() => setShowCreateForm(false)}
                className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  placeholder="Enter task title"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Notes
                </label>
                <textarea
                  value={newTask.notes}
                  onChange={(e) => setNewTask({ ...newTask, notes: e.target.value })}
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  rows={3}
                  placeholder="Additional notes (optional)"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Due Date
                </label>
                <input
                  type="date"
                  value={newTask.due_date}
                  onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
                  className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>
            
            <div className="flex gap-2 mt-6">
              <button
                onClick={handleCreateTask}
                disabled={creating}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {creating ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Create Task
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-900 dark:text-white"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}