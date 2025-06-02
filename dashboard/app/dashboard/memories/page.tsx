'use client';

import { useEffect, useState } from 'react';
import { api, Memory } from '@/lib/api';

export default function MemoriesPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<Memory>>({});
  const [showNewForm, setShowNewForm] = useState(false);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, []);

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
    if (!confirm('Are you sure you want to delete this memory?')) return;
    
    try {
      await api.deleteMemory(id);
      await fetchMemories();
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

  if (loading) return <div>Loading memories...</div>;
  if (error) return <div className="text-red-600">Error: {error}</div>;

  return (
    <div>
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            Memory Management
          </h1>
          <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
            A list of all memories in the system including their content, tags, and importance.
          </p>
        </div>
        <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
          <button
            onClick={() => setShowNewForm(true)}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:w-auto"
          >
            Add Memory
          </button>
        </div>
      </div>

      {showNewForm && (
        <div className="mt-8 bg-white dark:bg-gray-700 shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Create New Memory
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <input
              type="text"
              placeholder="User ID"
              className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              value={newForm.user_id}
              onChange={(e) => setNewForm({ ...newForm, user_id: e.target.value })}
            />
            <select
              className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              value={newForm.type}
              onChange={(e) => setNewForm({ ...newForm, type: e.target.value })}
            >
              <option value="general">General</option>
              <option value="personal">Personal</option>
              <option value="preference">Preference</option>
              <option value="relationship">Relationship</option>
            </select>
            <input
              type="text"
              placeholder="Tags (comma separated)"
              className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              value={newForm.tags}
              onChange={(e) => setNewForm({ ...newForm, tags: e.target.value })}
            />
            <input
              type="number"
              placeholder="Importance (1-10)"
              min="1"
              max="10"
              className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              value={newForm.importance}
              onChange={(e) => setNewForm({ ...newForm, importance: parseInt(e.target.value) })}
            />
            <textarea
              placeholder="Content"
              rows={3}
              className="col-span-2 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              value={newForm.content}
              onChange={(e) => setNewForm({ ...newForm, content: e.target.value })}
            />
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleCreate}
              className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Create
            </button>
            <button
              onClick={() => setShowNewForm(false)}
              className="rounded-md bg-gray-300 dark:bg-gray-600 px-3 py-2 text-sm font-medium text-gray-700 dark:text-white hover:bg-gray-400 dark:hover:bg-gray-500"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="mt-8">
        <div className="-mx-4 sm:mx-0">
          <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
              <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-600">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="hidden sm:table-cell px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      User ID
                    </th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Type
                    </th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Content
                    </th>
                    <th className="hidden lg:table-cell px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Tags
                    </th>
                    <th className="hidden md:table-cell px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Importance
                    </th>
                    <th className="hidden sm:table-cell px-3 py-3.5 text-left text-sm font-semibold text-gray-900 dark:text-white">
                      Created
                    </th>
                    <th className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-900">
                  {memories.map((memory) => (
                    <tr key={memory.id}>
                      <td className="hidden sm:table-cell whitespace-nowrap px-3 py-4 text-sm text-gray-900 dark:text-white">
                        {memory.user_id}
                      </td>
                      <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-900 dark:text-white">
                        <span className="inline-flex rounded-full bg-green-100 dark:bg-green-900 px-2 text-xs font-semibold leading-5 text-green-800 dark:text-green-200">
                          {memory.type}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-sm text-gray-900 dark:text-white">
                        {editingId === memory.id ? (
                          <textarea
                            className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                            value={editForm.content}
                            onChange={(e) =>
                              setEditForm({ ...editForm, content: e.target.value })
                            }
                          />
                        ) : (
                          <div className="max-w-xs truncate">{memory.content}</div>
                        )}
                      </td>
                      <td className="hidden lg:table-cell px-3 py-4 text-sm text-gray-900 dark:text-white">
                        {editingId === memory.id ? (
                          <input
                            className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                            value={editForm.tags?.join(', ')}
                            onChange={(e) =>
                              setEditForm({
                                ...editForm,
                                tags: e.target.value.split(',').map((t) => t.trim()),
                              })
                            }
                          />
                        ) : (
                          memory.tags.join(', ')
                        )}
                      </td>
                      <td className="hidden md:table-cell whitespace-nowrap px-3 py-4 text-sm text-gray-900 dark:text-white">
                        {editingId === memory.id ? (
                          <input
                            type="number"
                            min="1"
                            max="10"
                            className="w-16 rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                            value={editForm.importance}
                            onChange={(e) =>
                              setEditForm({ ...editForm, importance: parseInt(e.target.value) })
                            }
                          />
                        ) : (
                          memory.importance
                        )}
                      </td>
                      <td className="hidden sm:table-cell whitespace-nowrap px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {new Date(memory.created_at).toLocaleDateString()}
                      </td>
                      <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                        {editingId === memory.id ? (
                          <>
                            <button
                              onClick={() => handleSave(memory.id)}
                              className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingId(null)}
                              className="ml-3 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => handleEdit(memory)}
                              className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDelete(memory.id)}
                              className="ml-3 text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
        </div>
      </div>
    </div>
  );
}