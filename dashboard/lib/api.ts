const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    return origin.replace(':3000', ':8080');
  }
  return 'http://localhost:8080';
};

export interface LoginResponse {
  token: string;
  user: string;
}

export interface Memory {
  id: string;
  user_id: string;
  type: string;
  content: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  extracted_from?: string;
  metadata?: {
    source?: string;
    log_id?: string;
    people_mentioned?: Array<{
      name: string;
      context?: string;
      is_speaker?: boolean;
    }>;
  };
}

export interface CreateMemoryRequest {
  user_id: string;
  type: string;
  content: string;
  tags: string[];
}

export interface Task {
  id: string;
  title: string;
  notes?: string;
  status: 'needsAction' | 'completed';
  due?: string;
  due_formatted?: string;
  due_display?: string;
  is_overdue?: boolean;
  source: 'ai_extracted' | 'natural_language' | 'manual' | 'voice_command';
  source_icon: string;
  days_until_due?: number;
}

export interface CreateTaskRequest {
  title: string;
  notes?: string;
  due_date?: string; // YYYY-MM-DD format
}

export interface UpdateTaskRequest {
  title?: string;
  notes?: string;
  due_date?: string;
  completed?: boolean;
}

export interface TaskStats {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  overdue_tasks: number;
  due_today: number;
  due_this_week: number;
  completion_rate: number;
  recent_completions: number;
  source_distribution: Record<string, number>;
}

export interface TaskList {
  id: string;
  title: string;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  sort_by?: 'created_at' | 'type' | 'content';
  sort_order?: 'asc' | 'desc';
  memory_type?: string;
  search?: string;
}

export interface PaginatedMemoriesResponse {
  memories: Memory[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  sort_by: string;
  sort_order: string;
}

export interface RedisKey {
  key: string;
  type: string;
  ttl: number | null;
  value?: any;
}

export interface SystemStats {
  uptime: string;
  total_memories: number;
  memory_by_type: Record<string, number>;
  redis_keys: number;
  active_reminders: number;
  recent_messages: number;
  ai_model_vision: string;
  ai_model_chat: string;
  total_ai_requests_today: number;
  message_activity: Record<string, number>;
  weekly_activity: Record<string, number>;
  today_vs_yesterday: {
    today: Record<string, number>;
    yesterday: Record<string, number>;
  };
  whatsapp_status: string;
  whatsapp_token_info: {
    status: string;
    is_valid: boolean;
    message: string;
    token_type?: string;
    api_version?: string;
    last_checked: string;
    error?: string;
  };
  ai_status: {
    status: string;
    is_available: boolean;
    message: string;
    response_time_ms?: number;
    rate_limit?: {
      requests_per_minute?: string | null;
      remaining_requests?: string | null;
      reset_time?: string | null;
    };
    available_models?: number;
    api_key_present?: boolean;
    last_checked: string;
    error?: string;
  };
  ai_usage_stats: {
    requests_today: number;
    errors_last_hour: number;
    models_configured: {
      vision_model?: string;
      chat_model?: string;
    };
  };
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${getApiUrl()}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  async login(password: string): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/api/dashboard/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
    this.setToken(response.token);
    return response;
  }

  async getMemories(): Promise<Memory[]> {
    const response = await this.request<{memories: Memory[], total: number}>('/api/dashboard/memories');
    return response.memories;
  }

  async getMemoriesPaginated(params: PaginationParams = {}): Promise<PaginatedMemoriesResponse> {
    const searchParams = new URLSearchParams();
    
    if (params.page) searchParams.append('page', params.page.toString());
    if (params.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params.sort_order) searchParams.append('sort_order', params.sort_order);
    if (params.memory_type) searchParams.append('memory_type', params.memory_type);
    if (params.search) searchParams.append('search', params.search);
    
    const url = `/api/dashboard/memories${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
    return this.request<PaginatedMemoriesResponse>(url);
  }

  async getMemory(id: string): Promise<Memory> {
    return this.request<Memory>(`/api/dashboard/memories/${id}`);
  }

  async createMemory(memory: CreateMemoryRequest): Promise<Memory> {
    return this.request<Memory>('/api/dashboard/memories', {
      method: 'POST',
      body: JSON.stringify(memory),
    });
  }

  async updateMemory(id: string, memory: Partial<Memory>): Promise<Memory> {
    return this.request<Memory>(`/api/dashboard/memories/${id}`, {
      method: 'PUT',
      body: JSON.stringify(memory),
    });
  }

  async deleteMemory(id: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/dashboard/memories/${id}`, {
      method: 'DELETE',
    });
  }

  async getRedisKeys(pattern?: string): Promise<RedisKey[]> {
    const params = pattern ? `?pattern=${encodeURIComponent(pattern)}` : '';
    const response = await this.request<{keys: RedisKey[], total: number}>(`/api/dashboard/redis/keys${params}`);
    return response.keys;
  }

  async getRedisKey(key: string): Promise<RedisKey> {
    return this.request<RedisKey>(`/api/dashboard/redis/key/${encodeURIComponent(key)}`);
  }

  async deleteRedisKey(key: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/dashboard/redis/key/${encodeURIComponent(key)}`, {
      method: 'DELETE',
    });
  }

  async getSystemStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/api/dashboard/stats');
  }

  async getRedisInfo(): Promise<{
    status: string;
    uptime: string;
    memory_used: string;
    memory_total: string;
    total_keys: number;
    connected_clients: number;
    redis_version: string;
    uptime_seconds: number;
  }> {
    return this.request('/api/dashboard/redis/info');
  }

  async getRedisStats(): Promise<{
    total_commands: number;
    ops_per_sec: number;
    recent_commands: Array<{
      command: string;
      key: string;
      time: string;
    }>;
    avg_latency: string;
  }> {
    return this.request('/api/dashboard/redis/stats');
  }

  async getPerformanceMetrics(range: string = '24h'): Promise<{
    responseLatency: {
      avg: number;
      p95: number;
      errorRate: number;
    };
    categoryBreakdown: Array<{
      category: string;
      avgLatency: number;
      count: number;
      errorRate: number;
    }>;
    hourlyData: Array<{
      hour: string;
      avgLatency: number;
      requestCount: number;
    }>;
    alerts: Array<{
      category: string;
      message: string;
      severity: 'warning' | 'error';
    }>;
  }> {
    return this.request(`/api/dashboard/performance?range=${range}`);
  }

  // Limitless endpoints
  async getLimitlessStats(): Promise<{
    total_lifelogs: number;
    synced_today: number;
    last_sync: string | null;
    sync_status: 'idle' | 'syncing' | 'error';
    memories_created: number;
    tasks_created: number;
    pending_sync: number;
  }> {
    return this.request('/api/dashboard/limitless/stats');
  }

  async getLimitlessLifelogs(date?: string): Promise<any[]> {
    const params = date ? `?date=${encodeURIComponent(date)}` : '';
    return this.request(`/api/dashboard/limitless/lifelogs${params}`);
  }

  async searchLimitlessLifelogs(query: string): Promise<any[]> {
    return this.request(`/api/dashboard/limitless/search?q=${encodeURIComponent(query)}`);
  }

  async syncLimitless(): Promise<{ task_id: string; message: string }> {
    return this.request('/api/dashboard/limitless/sync', {
      method: 'POST'
    });
  }

  async getSyncStatus(taskId: string): Promise<{
    status: 'running' | 'completed' | 'failed';
    progress?: number;
    message?: string;
    result?: string;
    error?: string;
  }> {
    return this.request(`/api/dashboard/limitless/sync/status/${taskId}`);
  }

  async getLimitlessPerformanceMetrics(limit: number = 10, range: string = '24h'): Promise<{
    summary: {
      total_records: number;
      records_last_24h: number;
      avg_processing_time: number;
      min_processing_time: number;
      max_processing_time: number;
      current_status: 'optimal' | 'suboptimal' | 'issues_detected' | 'no_data';
      performance_issues: string[];
      timing_breakdown_avg: Record<string, number>;
      bottleneck_analysis: Record<string, {
        avg_time: number;
        percentage: number;
        is_bottleneck: boolean;
      }>;
    };
    recent_records: Array<{
      log_id: string;
      title: string;
      total_time: number;
      timing_breakdown: Record<string, number>;
      results: {
        memories_created: number;
        tasks_created: number;
      };
      processed_at: string;
      has_transcript: boolean;
      transcript_length: number;
    }>;
    hourlyData: Array<{
      hour: string;
      avgLatency: number;
      requestCount: number;
    }>;
    categoryBreakdown: Array<{
      category: string;
      avgLatency: number;
      count: number;
      errorRate: number;
    }>;
    last_updated: string;
  }> {
    return this.request(`/api/dashboard/limitless/performance-metrics?limit=${limit}&range=${range}`);
  }

  // Settings endpoints
  async getSettingsSchema(): Promise<{
    schema: Record<string, any>;
    categories: Record<string, string>;
  }> {
    return this.request('/api/dashboard/settings/schema');
  }

  async getSettings(): Promise<{
    settings: Record<string, {
      value: string;
      source: string;
      has_value: boolean;
      category: string;
      description: string;
      is_sensitive: boolean;
      requires_restart: boolean;
      options?: string[];
    }>;
  }> {
    return this.request('/api/dashboard/settings/');
  }

  async getSetting(key: string): Promise<{
    key: string;
    value: string;
    source: string;
    has_value: boolean;
    category: string;
    description: string;
    is_sensitive: boolean;
    requires_restart: boolean;
    options?: string[];
  }> {
    return this.request(`/api/dashboard/settings/${key}`);
  }

  async updateSetting(key: string, value: string): Promise<{
    success: boolean;
    message: string;
    requires_restart: boolean;
  }> {
    return this.request(`/api/dashboard/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    });
  }

  async deleteSetting(key: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.request(`/api/dashboard/settings/${key}`, {
      method: 'DELETE',
    });
  }

  async testSettingConnection(key: string, value: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.request(`/api/dashboard/settings/test/${key}`, {
      method: 'POST',
      body: JSON.stringify({ key, value }),
    });
  }

  // Task endpoints
  async getTasks(
    includeCompleted: boolean = false,
    dueFilter?: 'today' | 'week' | 'overdue',
    sortBy: string = 'created',
    sortOrder: string = 'desc'
  ): Promise<{
    tasks: Task[];
    total: number;
    filters: {
      include_completed: boolean;
      due_filter?: string;
      sort_by: string;
      sort_order: string;
    };
  }> {
    const params = new URLSearchParams({
      include_completed: includeCompleted.toString(),
      sort_by: sortBy,
      sort_order: sortOrder,
    });
    
    if (dueFilter) {
      params.append('due_filter', dueFilter);
    }
    
    return this.request(`/api/dashboard/tasks/?${params.toString()}`);
  }

  async createTask(task: CreateTaskRequest): Promise<{
    success: boolean;
    message: string;
    task: Task;
  }> {
    return this.request('/api/dashboard/tasks/', {
      method: 'POST',
      body: JSON.stringify(task),
    });
  }

  async updateTask(taskId: string, update: UpdateTaskRequest): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.request(`/api/dashboard/tasks/${taskId}`, {
      method: 'PUT',
      body: JSON.stringify(update),
    });
  }

  async deleteTask(taskId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.request(`/api/dashboard/tasks/${taskId}`, {
      method: 'DELETE',
    });
  }

  async completeTask(taskId: string): Promise<{
    success: boolean;
    message: string;
  }> {
    return this.request(`/api/dashboard/tasks/${taskId}/complete`, {
      method: 'POST',
    });
  }

  async getUpcomingTasks(days: number = 7): Promise<{
    upcoming_tasks: Task[];
    total: number;
    days_ahead: number;
  }> {
    return this.request(`/api/dashboard/tasks/upcoming?days=${days}`);
  }

  async getTaskStats(): Promise<TaskStats> {
    return this.request('/api/dashboard/tasks/stats');
  }

  async getTaskLists(): Promise<{
    task_lists: TaskList[];
    total: number;
  }> {
    return this.request('/api/dashboard/tasks/lists');
  }
}

export const api = new ApiClient();