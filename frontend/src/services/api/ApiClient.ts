export class ApiError extends Error {
  readonly status: number;
  readonly details: unknown;

  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

interface ApiClientOptions {
  baseUrl: string;
  timeoutMs?: number;
  getAuthToken?: () => string | null;
  defaultHeaders?: HeadersInit;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly getAuthToken?: () => string | null;
  private readonly defaultHeaders: HeadersInit;

  constructor(options: ApiClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    this.timeoutMs = options.timeoutMs ?? 15000;
    this.getAuthToken = options.getAuthToken;
    this.defaultHeaders = options.defaultHeaders ?? {};
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'GET' });
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: 'POST', body: JSON.stringify(body) });
  }

  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, { method: 'PUT', body: JSON.stringify(body) });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' });
  }

  private async request<T>(path: string, init: RequestInit): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    const headers = new Headers({
      'Content-Type': 'application/json',
      ...this.defaultHeaders,
      ...(init.headers || {}),
    });

    const token = this.getAuthToken?.();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const url = path.startsWith('http') ? path : `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`;

    try {
      const response = await fetch(url, {
        ...init,
        headers,
        signal: controller.signal,
      });

      const contentType = response.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');
      const payload = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const message = typeof payload === 'string' && payload ? payload : response.statusText || 'API request failed';
        throw new ApiError(response.status, message, payload);
      }

      return payload as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError(408, `Request timeout after ${this.timeoutMs}ms`);
      }

      throw new ApiError(0, error instanceof Error ? error.message : 'Unknown network error', error);
    } finally {
      clearTimeout(timer);
    }
  }
}
