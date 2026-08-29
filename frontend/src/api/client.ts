export class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = ((import.meta as any).env?.VITE_API_BASE_URL as string) || '/api/v1') {
    this.baseUrl = baseUrl;
  }

  private getHeaders(contentType: string | null = 'application/json'): HeadersInit {
    const headers: Record<string, string> = {};
    if (contentType) {
      headers['Content-Type'] = contentType;
    }
    const token = localStorage.getItem('sat_sa_jwt_token');
    if (token) {
      // Validate that the JWT token has 3 valid segments (header.payload.signature)
      if (token.split('.').length === 3) {
        headers['Authorization'] = `Bearer ${token}`;
      } else {
        // Remove corrupted or malformed tokens from localStorage
        localStorage.removeItem('sat_sa_jwt_token');
        localStorage.removeItem('sat_sa_user');
      }
    }
    return headers;
  }

  private handleAuthError(resp: Response) {
    if (resp.status === 401) {
      localStorage.removeItem('sat_sa_jwt_token');
      localStorage.removeItem('sat_sa_user');
    }
  }

  async get<T>(path: string, params?: Record<string, any>): Promise<T> {
    let url = `${this.baseUrl}${path}`;
    if (params) {
      const query = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          query.append(k, String(v));
        }
      });
      const qs = query.toString();
      if (qs) {
        url += `?${qs}`;
      }
    }

    const resp = await fetch(url, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    if (!resp.ok) {
      this.handleAuthError(resp);
      const errorData = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(errorData.detail || errorData.message || `Request failed with status ${resp.status}`);
    }

    return resp.json();
  }

  async post<T>(path: string, data?: any): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.getHeaders('application/json'),
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });

    if (!resp.ok) {
      this.handleAuthError(resp);
      const errorData = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(errorData.detail || errorData.message || `Request failed with status ${resp.status}`);
    }

    return resp.json();
  }

  async put<T>(path: string, data?: any): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: this.getHeaders('application/json'),
      body: data !== undefined ? JSON.stringify(data) : undefined,
    });

    if (!resp.ok) {
      this.handleAuthError(resp);
      const errorData = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(errorData.detail || errorData.message || `Request failed with status ${resp.status}`);
    }

    return resp.json();
  }

  async delete<T>(path: string): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    if (!resp.ok) {
      this.handleAuthError(resp);
      const errorData = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(errorData.detail || errorData.message || `Request failed with status ${resp.status}`);
    }

    return resp.json();
  }

  async upload<T>(path: string, formData: FormData): Promise<T> {
    const resp = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.getHeaders(null), // multipart boundary handled automatically
      body: formData,
    });

    if (!resp.ok) {
      this.handleAuthError(resp);
      const errorData = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(errorData.detail || errorData.message || `Upload failed with status ${resp.status}`);
    }

    return resp.json();
  }
}

export const apiClient = new ApiClient();
