'use client';

import { useEffect, useState } from 'react';
import { api, Memory } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { 
  Search, 
  Plus, 
  Edit3, 
  Trash2, 
  Save, 
  X, 
  Brain, 
  Calendar,
  Filter,
  ChevronDown,
  AlertCircle,
  User,
  Hash,
  Grid3X3,
  Network,
  Heart,
  FileText,
  Users,
  Clock,
  Info,
  AlertTriangle,
  StickyNote,
  MoreHorizontal,
  RefreshCw,
  List,
  ArrowUpDown,
  ArrowUp,
  ArrowDown
} from 'lucide-react';
import MemoryGraph from '@/components/MemoryGraph';

type MemoryType = 'all' | 'fact' | 'preference' | 'relationship' | 'routine' | 'important_date' | 'personal_info' | 'allergy' | 'note';

// Memory type icon map (matching backend MEMORY_TYPES)
const memoryTypeIcons = {
  fact: Info,
  preference: Heart,
  relationship: Users,
  routine: Clock,
  important_date: Calendar,
  personal_info: User,
  allergy: AlertTriangle,
  note: StickyNote,
};

// Memory type colors with modern vibrant styling
const memoryTypeColors = {
  fact: 'bg-blue-500 text-white',
  preference: 'bg-green-500 text-white', 
  relationship: 'bg-red-500 text-white',
  routine: 'bg-purple-500 text-white',
  important_date: 'bg-orange-500 text-white',
  personal_info: 'bg-indigo-500 text-white',
  allergy: 'bg-red-600 text-white',
  note: 'bg-gray-500 text-white',
};

// Source type styling with improved dark mode support
const sourceColors = {
  manual: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-600 dark:text-white',
  whatsapp: 'bg-green-100 text-green-800 dark:bg-green-600 dark:text-white',
  limitless: 'bg-purple-100 text-purple-800 dark:bg-purple-500 dark:text-white',
  ai: 'bg-pink-100 text-pink-800 dark:bg-pink-600 dark:text-white',
  auto: 'bg-orange-100 text-orange-800 dark:bg-orange-600 dark:text-white'
};

// Skeleton loader for memory cards
function MemoryCardSkeleton() {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
      <div className="animate-pulse">
        <div className="flex items-start justify-between mb-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded-full w-8"></div>
        </div>
        <div className="space-y-2 mb-4">
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        </div>
        <div className="flex items-center space-x-2">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full w-16"></div>
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded-full w-16"></div>
        </div>
      </div>
    </div>
  );
}

export default function MemoriesPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [filteredMemories, setFilteredMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Memory>>({});
  const [showNewForm, setShowNewForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState<MemoryType>('all');
  const [showFilters, setShowFilters] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'table' | 'graph'>('table');
  const [sortBy, setSortBy] = useState<'created_at' | 'type' | 'content'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [newForm, setNewForm] = useState({
    user_id: '60122873632', // Default user ID matching backend
    type: 'note',
    content: '',
  });
  const { toast } = useToast();

  const fetchMemories = async () => {
    try {
      const data = await api.getMemories();
      setMemories(data);
      setFilteredMemories(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, []);

  // Filter, search, and sort memories
  useEffect(() => {
    let filtered = memories;

    // Type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(m => m.type === filterType);
    }

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(m => 
        m.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
        m.user_id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Sort memories
    filtered.sort((a, b) => {
      let aValue, bValue;
      
      switch (sortBy) {
        case 'created_at':
          aValue = new Date(a.created_at).getTime();
          bValue = new Date(b.created_at).getTime();
          break;
        case 'type':
          aValue = a.type;
          bValue = b.type;
          break;
        case 'content':
          aValue = a.content.toLowerCase();
          bValue = b.content.toLowerCase();
          break;
        default:
          aValue = a.created_at;
          bValue = b.created_at;
      }

      if (sortOrder === 'desc') {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      } else {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      }
    });

    setFilteredMemories(filtered);
  }, [memories, filterType, searchTerm, sortBy, sortOrder]);

  const handleSort = (column: 'created_at' | 'type' | 'content') => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const getSortIcon = (column: 'created_at' | 'type' | 'content') => {
    if (sortBy !== column) return ArrowUpDown;
    return sortOrder === 'asc' ? ArrowUp : ArrowDown;
  };

  const handleEdit = (memory: Memory) => {
    setEditingId(memory.id);
    setEditForm({
      content: memory.content,
      type: memory.type,
    });
  };

  const handleSave = async (id: string) => {
    try {
      // Validate required fields
      if (!editForm.content || editForm.content.trim() === '') {
        toast({
          variant: 'destructive',
          title: 'Validation Error',
          description: 'Content is required and cannot be empty.',
        });
        return;
      }

      // Format data according to backend MemoryUpdate schema
      const updateData = {
        content: editForm.content.trim(),
        memory_type: editForm.type || 'general', // Backend expects 'memory_type', not 'type'
        // Note: tags are not supported in the backend update API
      };
      
      console.log('Updating memory with data:', updateData);
      await api.updateMemory(id, updateData);
      await fetchMemories();
      setEditingId(null);
      
      toast({
        variant: 'success',
        title: 'Success',
        description: 'Memory updated successfully.',
      });
    } catch (err) {
      console.error('Update error:', err);
      
      // Improved error handling
      let errorMessage = 'Failed to update memory';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'object' && err !== null) {
        // Handle case where error is an object
        errorMessage = JSON.stringify(err);
      }
      
      toast({
        variant: 'destructive',
        title: 'Update Failed',
        description: errorMessage,
      });
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteMemory(id);
      await fetchMemories();
      setDeleteConfirmId(null);
      
      toast({
        variant: 'success',
        title: 'Success',
        description: 'Memory deleted successfully.',
      });
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Delete Failed',
        description: err instanceof Error ? err.message : 'Failed to delete memory',
      });
    }
  };

  const handleCreate = async () => {
    try {
      await api.createMemory({
        user_id: newForm.user_id,
        type: newForm.type,
        content: newForm.content,
        tags: [], // Empty array since tags are not used
      });
      await fetchMemories();
      setShowNewForm(false);
      setNewForm({
        user_id: '60122873632',
        type: 'note',
        content: '',
      });
      
      toast({
        variant: 'success',
        title: 'Success',
        description: 'Memory created successfully.',
      });
    } catch (err) {
      toast({
        variant: 'destructive',
        title: 'Create Failed',
        description: err instanceof Error ? err.message : 'Failed to create memory',
      });
    }
  };

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 max-w-md">
          <div className="flex items-center space-x-2 mb-2">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
            <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">Error Loading Memories</h3>
          </div>
          <p className="text-red-600 dark:text-red-300">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-gray-50 to-gray-100 dark:from-gray-900 dark:via-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="sm:flex sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center space-x-2">
                <Brain className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                <span>Memory Management</span>
              </h1>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Manage and organize your AI assistant's knowledge base
              </p>
            </div>
            <div className="mt-4 sm:mt-0 flex items-center gap-3">
              {/* View Toggle */}
              <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                <button
                  onClick={() => setViewMode('table')}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-l-lg transition-all duration-200 ${
                    viewMode === 'table'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <List className="h-4 w-4 mr-2" />
                  Table View
                </button>
                <button
                  onClick={() => setViewMode('grid')}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium transition-all duration-200 ${
                    viewMode === 'grid'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <Grid3X3 className="h-4 w-4 mr-2" />
                  Grid View
                </button>
                <button
                  onClick={() => setViewMode('graph')}
                  className={`inline-flex items-center px-3 py-2 text-sm font-medium rounded-r-lg transition-all duration-200 ${
                    viewMode === 'graph'
                      ? 'bg-purple-600 text-white'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  <Network className="h-4 w-4 mr-2" />
                  Visual View
                </button>
              </div>
              
              <div className="flex items-center gap-3">
                <button
                  onClick={fetchMemories}
                  className="inline-flex items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-all duration-200"
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Refresh
                </button>
                <button
                  onClick={() => setShowNewForm(true)}
                  className="inline-flex items-center justify-center rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create Memory
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="mb-6 space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search memories by content or user..."
                className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center px-4 py-2.5 rounded-lg bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200"
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
              <ChevronDown className={`h-4 w-4 ml-2 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {/* Filter Options */}
          {showFilters && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setFilterType('all')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filterType === 'all'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  All Types
                </button>
                {(['fact', 'preference', 'relationship', 'routine', 'important_date', 'personal_info', 'allergy', 'note'] as const).map((type) => {
                  const Icon = memoryTypeIcons[type];
                  return (
                    <button
                      key={type}
                      onClick={() => setFilterType(type)}
                      className={`inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                        filterType === type
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                      }`}
                    >
                      <Icon className="h-4 w-4 mr-1.5" />
                      {type.replace('_', ' ').split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* New Memory Form */}
        {showNewForm && (
          <div className="mb-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
                <Plus className="h-5 w-5 mr-2 text-purple-600 dark:text-purple-400" />
                Create New Memory
              </h3>
              <button
                onClick={() => setShowNewForm(false)}
                className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  User ID
                </label>
                <input
                  type="text"
                  placeholder="user@example.com"
                  className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                  value={newForm.user_id}
                  onChange={(e) => setNewForm({ ...newForm, user_id: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Type
                </label>
                <select
                  className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                  value={newForm.type}
                  onChange={(e) => setNewForm({ ...newForm, type: e.target.value })}
                >
                  <option value="fact">Fact</option>
                  <option value="preference">Preference</option>
                  <option value="relationship">Relationship</option>
                  <option value="routine">Routine</option>
                  <option value="important_date">Important Date</option>
                  <option value="personal_info">Personal Info</option>
                  <option value="allergy">Allergy</option>
                  <option value="note">Note</option>
                </select>
              </div>
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Content
                </label>
                <textarea
                  placeholder="Enter memory content..."
                  rows={3}
                  className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                  value={newForm.content}
                  onChange={(e) => setNewForm({ ...newForm, content: e.target.value })}
                />
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleCreate}
                className="inline-flex items-center px-4 py-2 rounded-lg bg-purple-600 text-white font-medium hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200"
              >
                <Save className="h-4 w-4 mr-2" />
                Create Memory
              </button>
              <button
                onClick={() => setShowNewForm(false)}
                className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-all duration-200"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Content Views */}
        {viewMode === 'table' ? (
          /* Table View */
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
            {loading ? (
              <div className="p-8 text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-4"></div>
                <p className="text-gray-500 dark:text-gray-400">Loading memories...</p>
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="p-12 text-center">
                <Brain className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  {searchTerm || filterType !== 'all' ? 'No memories found' : 'No memories yet'}
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  {searchTerm || filterType !== 'all' 
                    ? 'Try adjusting your search or filters'
                    : 'Create your first memory to get started'
                  }
                </p>
              </div>
            ) : (
              <>
                {/* Table Header */}
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="grid grid-cols-12 gap-4">
                    <div className="col-span-6">
                      <button
                        onClick={() => handleSort('content')}
                        className="flex items-center space-x-1 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                      >
                        <span>Memory</span>
                        {(() => {
                          const SortIcon = getSortIcon('content');
                          return <SortIcon className="h-4 w-4" />;
                        })()}
                      </button>
                    </div>
                    <div className="col-span-2">
                      <button
                        onClick={() => handleSort('type')}
                        className="flex items-center space-x-1 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                      >
                        <span>Category</span>
                        {(() => {
                          const SortIcon = getSortIcon('type');
                          return <SortIcon className="h-4 w-4" />;
                        })()}
                      </button>
                    </div>
                    <div className="col-span-2">
                      <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Source</span>
                    </div>
                    <div className="col-span-2">
                      <button
                        onClick={() => handleSort('created_at')}
                        className="flex items-center space-x-1 text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                      >
                        <span>Created On</span>
                        {(() => {
                          const SortIcon = getSortIcon('created_at');
                          return <SortIcon className="h-4 w-4" />;
                        })()}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Table Body */}
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredMemories.map((memory) => {
                    const Icon = memoryTypeIcons[memory.type as keyof typeof memoryTypeIcons] || Hash;
                    const isEditing = editingId === memory.id;
                    const isDeleting = deleteConfirmId === memory.id;

                    return (
                      <div key={memory.id} className="group px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                        <div className="grid grid-cols-12 gap-4 items-center">
                          {/* Memory Content */}
                          <div className="col-span-6">
                            {isEditing ? (
                              <textarea
                                className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                                rows={3}
                                value={editForm.content}
                                onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                              />
                            ) : (
                              <div>
                                <p className="text-gray-900 dark:text-white font-medium leading-6 line-clamp-2">
                                  {memory.content}
                                </p>
                                <div className="flex items-center mt-2 space-x-2">
                                  <div className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
                                    <User className="h-3 w-3" />
                                    <span className="truncate max-w-[120px]">{memory.user_id}</span>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Category */}
                          <div className="col-span-2">
                            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${memoryTypeColors[memory.type as keyof typeof memoryTypeColors]}`}>
                              <Icon className="h-3.5 w-3.5 mr-1" />
                              {memory.type.charAt(0).toUpperCase() + memory.type.slice(1)}
                            </span>
                          </div>

                          {/* Source */}
                          <div className="col-span-2">
                            {(() => {
                              const source = memory.extracted_from || memory.metadata?.source || 'manual';
                              return (
                                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                                  sourceColors[source as keyof typeof sourceColors] || sourceColors.manual
                                }`}>
                                  {source.charAt(0).toUpperCase() + source.slice(1)}
                                </span>
                              );
                            })()}
                          </div>

                          {/* Created On */}
                          <div className="col-span-2 flex items-center justify-between">
                            <div className="text-sm text-gray-500 dark:text-gray-400">
                              {new Date(memory.created_at).toLocaleDateString(undefined, { 
                                month: 'short', 
                                day: 'numeric', 
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </div>
                            
                            {/* Actions */}
                            <div className="flex items-center space-x-1">
                              {isEditing ? (
                                <>
                                  <button
                                    onClick={() => handleSave(memory.id)}
                                    className="p-1.5 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/20 transition-colors"
                                  >
                                    <Save className="h-4 w-4 text-green-600 dark:text-green-400" />
                                  </button>
                                  <button
                                    onClick={() => setEditingId(null)}
                                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                  >
                                    <X className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                                  </button>
                                </>
                              ) : isDeleting ? (
                                <div className="flex items-center gap-1">
                                  <button
                                    onClick={() => handleDelete(memory.id)}
                                    className="inline-flex items-center justify-center px-2 py-1 text-xs font-medium rounded bg-red-600 text-white hover:bg-red-700 transition-colors"
                                    title="Confirm delete"
                                  >
                                    ✓
                                  </button>
                                  <button
                                    onClick={() => setDeleteConfirmId(null)}
                                    className="inline-flex items-center justify-center px-2 py-1 text-xs font-medium rounded bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-400 dark:hover:bg-gray-500 transition-colors"
                                    title="Cancel delete"
                                  >
                                    ✕
                                  </button>
                                </div>
                              ) : (
                                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={() => handleEdit(memory)}
                                    className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                                  >
                                    <Edit3 className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                                  </button>
                                  <button
                                    onClick={() => setDeleteConfirmId(memory.id)}
                                    className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors"
                                  >
                                    <Trash2 className="h-4 w-4 text-red-500 dark:text-red-400" />
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        ) : viewMode === 'grid' ? (
          <>
            {/* Memories Grid */}
            {loading ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {[...Array(6)].map((_, i) => (
                  <MemoryCardSkeleton key={i} />
                ))}
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
                <Brain className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  {searchTerm || filterType !== 'all' ? 'No memories found' : 'No memories yet'}
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  {searchTerm || filterType !== 'all' 
                    ? 'Try adjusting your search or filters'
                    : 'Create your first memory to get started'
                  }
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredMemories.map((memory) => {
              const Icon = memoryTypeIcons[memory.type as keyof typeof memoryTypeIcons] || Hash;
              const isEditing = editingId === memory.id;
              const isDeleting = deleteConfirmId === memory.id;

              return (
                <div
                  key={memory.id}
                  className="group bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200"
                >
                  <div className="p-6">
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium ${memoryTypeColors[memory.type as keyof typeof memoryTypeColors]}`}>
                          <Icon className="h-3.5 w-3.5 mr-1" />
                          {memory.type}
                        </span>
                        {(() => {
                          const source = memory.extracted_from || memory.metadata?.source || 'manual';
                          return (
                            <span className={`inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium ${
                              sourceColors[source as keyof typeof sourceColors] || sourceColors.manual
                            }`}>
                              {source.charAt(0).toUpperCase() + source.slice(1)}
                            </span>
                          );
                        })()}
                      </div>
                      <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        {!isEditing && !isDeleting && (
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={() => handleEdit(memory)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                            >
                              <Edit3 className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmId(memory.id)}
                              className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                            >
                              <Trash2 className="h-4 w-4 text-red-500 dark:text-red-400" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="mb-4">
                      {isEditing ? (
                        <textarea
                          className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                          rows={4}
                          value={editForm.content}
                          onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                        />
                      ) : (
                        <p className="text-gray-700 dark:text-gray-300 line-clamp-3">
                          {memory.content}
                        </p>
                      )}
                    </div>


                    {/* Footer */}
                    <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
                      <div className="flex items-center space-x-1">
                        <User className="h-4 w-4" />
                        <span className="truncate max-w-[150px]">{memory.user_id}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{new Date(memory.created_at).toLocaleDateString(undefined, { 
                          month: 'short', 
                          day: 'numeric', 
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}</span>
                      </div>
                    </div>

                    {/* Edit Actions */}
                    {isEditing && (
                      <div className="mt-4 flex gap-2">
                        <button
                          onClick={() => handleSave(memory.id)}
                          className="flex-1 inline-flex items-center justify-center px-3 py-1.5 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-700 transition-colors"
                        >
                          <Save className="h-4 w-4 mr-1" />
                          Save
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="flex-1 px-3 py-1.5 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    )}

                    {/* Delete Confirmation */}
                    {isDeleting && (
                      <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                        <p className="text-sm text-red-700 dark:text-red-300 mb-2">
                          Are you sure you want to delete this memory?
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleDelete(memory.id)}
                            className="flex-1 px-3 py-1.5 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700 transition-colors"
                          >
                            Delete
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="flex-1 px-3 py-1.5 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
          </>
        ) : (
          // Graph View
          <div className="h-[800px] w-full">
            {loading ? (
              <div className="flex items-center justify-center h-full bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                  <p className="text-gray-500 dark:text-gray-400">Loading knowledge graph...</p>
                </div>
              </div>
            ) : filteredMemories.length === 0 ? (
              <div className="flex items-center justify-center h-full bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
                <div className="text-center">
                  <Network className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
                    {searchTerm || filterType !== 'all' ? 'No memories to visualize' : 'No knowledge graph yet'}
                  </h3>
                  <p className="text-gray-500 dark:text-gray-400">
                    {searchTerm || filterType !== 'all' 
                      ? 'Try adjusting your search or filters to see connections'
                      : 'Add some memories to see their relationships in the graph'
                    }
                  </p>
                </div>
              </div>
            ) : (
              <MemoryGraph 
                memories={filteredMemories} 
                onNodeClick={(memory) => {
                  setEditingId(memory.id);
                  setEditForm({
                    content: memory.content,
                    type: memory.type,
                  });
                }}
                width={1200}
                height={800}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}