const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export interface LoginResponse {
  access_token: string;
  token_type: string;
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
  ttl: number;
  value?: any;
}

export interface SystemStats {
  uptime: number;
  memory_usage: number;
  redis_keys: number;
  total_memories: number;
  active_reminders: number;
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
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.clearToken();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/api/dashboard/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    this.setToken(response.access_token);
    return response;
  }

  async getMemories(): Promise<Memory[]> {
    return this.request<Memory[]>('/api/dashboard/memories');
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
    return this.request<RedisKey[]>(`/api/dashboard/redis/keys${params}`);
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