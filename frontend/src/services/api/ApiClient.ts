/**
 * @fileoverview HTTP客户端封装
 * 提供统一的API请求接口，支持认证、超时和错误处理
 */

/**
 * API错误类
 * 封装HTTP请求失败的错误信息
 */
export class ApiError extends Error {
  /** HTTP状态码 */
  readonly status: number;
  /** 错误详细信息 */
  readonly details: unknown;

  /**
   * 构造函数
   * @param status HTTP状态码
   * @param message 错误消息
   * @param details 额外错误详情（可选）
   */
  constructor(status: number, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

/**
 * API客户端配置选项
 */
interface ApiClientOptions {
  baseUrl: string;              // API基础URL
  timeoutMs?: number;           // 请求超时时间（毫秒）
  getAuthToken?: () => string | null; // 获取认证令牌函数
  defaultHeaders?: HeadersInit; // 默认请求头
}

/**
 * HTTP客户端类
 * 封装Fetch API，提供GET、POST、PUT、DELETE方法
 * 自动处理认证令牌、请求超时和错误响应
 */
export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly getAuthToken?: () => string | null;
  private readonly defaultHeaders: HeadersInit;

  /**
   * 构造函数
   * 初始化客户端配置，自动规范化基础URL
   * @param options 客户端配置选项
   */
  constructor(options: ApiClientOptions) {
    // 移除URL末尾的斜杠，确保一致性
    this.baseUrl = options.baseUrl.replace(/\/+$/, '');
    // 设置超时时间，默认15秒
    this.timeoutMs = options.timeoutMs ?? 15000;
    // 保存认证令牌获取函数
    this.getAuthToken = options.getAuthToken;
    // 设置默认请求头
    this.defaultHeaders = options.defaultHeaders ?? {};
  }

  /**
   * 发起GET请求
   * @param path 请求路径
   * @returns Promise<T> 响应数据
   */
  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'GET' });
  }

  /**
   * 发起POST请求
   * @param path 请求路径
   * @param body 请求体数据
   * @returns Promise<T> 响应数据
   */
  async post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  }

  /**
   * 发起PUT请求
   * @param path 请求路径
   * @param body 请求体数据
   * @returns Promise<T> 响应数据
   */
  async put<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  }

  /**
   * 发起DELETE请求
   * @param path 请求路径
   * @returns Promise<T> 响应数据
   */
  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' });
  }

  /**
   * 核心请求方法
   * 统一处理所有HTTP请求，包含以下功能：
   * - 请求超时控制
   * - 自动添加认证令牌
   * - 响应类型检测（JSON vs 文本）
   * - 错误处理和异常转换
   * @param path 请求路径
   * @param init Fetch请求配置
   * @returns Promise<T> 解析后的响应数据
   */
  private async request<T>(path: string, init: RequestInit): Promise<T> {
    // 创建AbortController用于超时控制
    const controller = new AbortController();
    // 设置超时定时器
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);

    // 构建请求头
    const headers = new Headers({
      'Content-Type': 'application/json', // 默认JSON格式
      ...this.defaultHeaders,            // 合并默认头部
      ...(init.headers || {}),           // 合并请求特定头部
    });

    // 获取并添加认证令牌（如果存在）
    const token = this.getAuthToken?.();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    // 构建完整URL（支持相对路径和绝对路径）
    const url = path.startsWith('http')
      ? path // 绝对路径直接使用
      : `${this.baseUrl}${path.startsWith('/') ? '' : '/'}${path}`; // 相对路径拼接基础URL

    try {
      // 发起Fetch请求
      const response = await fetch(url, {
        ...init,
        headers,
        signal: controller.signal, // 关联超时控制器
      });

      // 检测响应内容类型
      const contentType = response.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');
      // 根据内容类型解析响应体
      const payload = isJson ? await response.json() : await response.text();

      // 检查响应状态，失败则抛出错误
      if (!response.ok) {
        const message = typeof payload === 'string' && payload
          ? payload
          : response.statusText || 'API request failed';
        throw new ApiError(response.status, message, payload);
      }

      return payload as T;
    } catch (error) {
      // 如果是ApiError直接抛出
      if (error instanceof ApiError) {
        throw error;
      }

      // 处理超时错误
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError(
          408,
          `Request timeout after ${this.timeoutMs}ms`
        );
      }

      // 处理网络错误和其他未知错误
      throw new ApiError(
        0,
        error instanceof Error ? error.message : 'Unknown network error',
        error
      );
    } finally {
      // 清理超时定时器
      clearTimeout(timer);
    }
  }
}
