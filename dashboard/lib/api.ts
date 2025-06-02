const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    const origin = window.location.origin;
    return origin.replace(':3000', ':8111');
  }
  return 'http://localhost:8111';
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
  importance: number;
  created_at: string;
  updated_at: string;
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

  async getMemory(id: string): Promise<Memory> {
    return this.request<Memory>(`/api/dashboard/memories/${id}`);
  }

  async createMemory(memory: Omit<Memory, 'id' | 'created_at' | 'updated_at'>): Promise<Memory> {
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
    return this.request<RedisKey>(`/api/dashboard/redis/keys/${encodeURIComponent(key)}`);
  }

  async deleteRedisKey(key: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/dashboard/redis/keys/${encodeURIComponent(key)}`, {
      method: 'DELETE',
    });
  }

  async getSystemStats(): Promise<SystemStats> {
    return this.request<SystemStats>('/api/dashboard/stats');
  }
}

export const api = new ApiClient();