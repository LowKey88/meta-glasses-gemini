'use client';

import { useEffect, useState } from 'react';
import { api, Memory } from '@/lib/api';
import { 
  Search, 
  Plus, 
  Edit3, 
  Trash2, 
  Save, 
  X, 
  Brain, 
  Tag, 
  Calendar,
  Filter,
  ChevronDown,
  AlertCircle,
  User,
  Star,
  Hash
} from 'lucide-react';

type MemoryType = 'all' | 'general' | 'personal' | 'preference' | 'relationship';

// Memory type icon map
const memoryTypeIcons = {
  general: Hash,
  personal: User,
  preference: Star,
  relationship: Brain,
};

// Memory type colors
const memoryTypeColors = {
  general: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
  personal: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
  preference: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
  relationship: 'bg-pink-100 text-pink-800 dark:bg-pink-900/20 dark:text-pink-400',
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
  const [newForm, setNewForm] = useState({
    user_id: '',
    type: 'general',
    content: '',
    tags: '',
    importance: 5,
  });

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

  // Filter and search memories
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
        m.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase())) ||
        m.user_id.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredMemories(filtered);
  }, [memories, filterType, searchTerm]);

  const handleEdit = (memory: Memory) => {
    setEditingId(memory.id);
    setEditForm({
      content: memory.content,
      tags: memory.tags,
      importance: memory.importance,
    });
  };

  const handleSave = async (id: string) => {
    try {
      await api.updateMemory(id, editForm);
      await fetchMemories();
      setEditingId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update memory');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteMemory(id);
      await fetchMemories();
      setDeleteConfirmId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete memory');
    }
  };

  const handleCreate = async () => {
    try {
      await api.createMemory({
        ...newForm,
        tags: newForm.tags.split(',').map((t) => t.trim()).filter(Boolean),
      });
      await fetchMemories();
      setShowNewForm(false);
      setNewForm({
        user_id: '',
        type: 'general',
        content: '',
        tags: '',
        importance: 5,
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create memory');
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
            <div className="mt-4 sm:mt-0">
              <button
                onClick={() => setShowNewForm(true)}
                className="inline-flex items-center justify-center rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white shadow-md hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all duration-200"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Memory
              </button>
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
                placeholder="Search memories by content, tags, or user..."
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
                {(['general', 'personal', 'preference', 'relationship'] as const).map((type) => {
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
                      {type.charAt(0).toUpperCase() + type.slice(1)}
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
                  <option value="general">General</option>
                  <option value="personal">Personal</option>
                  <option value="preference">Preference</option>
                  <option value="relationship">Relationship</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Tags
                </label>
                <input
                  type="text"
                  placeholder="work, meeting, important (comma separated)"
                  className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                  value={newForm.tags}
                  onChange={(e) => setNewForm({ ...newForm, tags: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Importance (1-10)
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                  value={newForm.importance}
                  onChange={(e) => setNewForm({ ...newForm, importance: parseInt(e.target.value) })}
                />
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
                        <span className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                          <Star className="h-3.5 w-3.5 mr-1" />
                          {memory.importance}/10
                        </span>
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

                    {/* Tags */}
                    <div className="mb-4">
                      {isEditing ? (
                        <input
                          className="w-full rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600 px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500 transition-all duration-200"
                          placeholder="Tags (comma separated)"
                          value={editForm.tags?.join(', ')}
                          onChange={(e) =>
                            setEditForm({
                              ...editForm,
                              tags: e.target.value.split(',').map((t) => t.trim()),
                            })
                          }
                        />
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {memory.tags.map((tag, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                            >
                              <Tag className="h-3 w-3 mr-1" />
                              {tag}
                            </span>
                          ))}
                        </div>
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
                        <span>{new Date(memory.created_at).toLocaleDateString()}</span>
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
      </div>
    </div>
  );
}