export interface HealthResponse {
  status: string;
  service?: string;
  environment?: string;
  timestamp?: string;
  supabase?: {
    connected: boolean;
    error?: string;
  };
}

export interface HealthCheckResult {
  ok: boolean;
  statusCode?: number;
  data?: HealthResponse;
  error?: string;
  durationMs: number;
}

/**
 * Lightweight client for querying the AegisMesh backend GET /health endpoint.
 * Designed to be resilient, fail-soft, and non-blocking.
 */
export class HealthClient {
  /**
   * Queries the /health endpoint of the configured AegisMesh backend.
   *
   * @param backendUrl Base URL of the backend (e.g. "http://127.0.0.1:8000")
   * @param timeoutMs Timeout in milliseconds (default: 5000)
   */
  async check(backendUrl: string, timeoutMs = 5000): Promise<HealthCheckResult> {
    const startTime = Date.now();
    const cleanUrl = backendUrl.trim().replace(/\/+$/, '');
    const targetUrl = `${cleanUrl}/health`;

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      const response = await fetch(targetUrl, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'User-Agent': 'AegisMesh-VSCode-Adapter/0.1.0',
        },
        signal: controller.signal,
      });

      clearTimeout(timer);
      const durationMs = Date.now() - startTime;

      if (!response.ok) {
        return {
          ok: false,
          statusCode: response.status,
          error: `HTTP ${response.status} ${response.statusText}`,
          durationMs,
        };
      }

      const data = (await response.json()) as HealthResponse;
      const isHealthy = data.status === 'healthy' || data.status === 'ok';

      return {
        ok: isHealthy,
        statusCode: response.status,
        data,
        error: isHealthy ? undefined : `Backend reported non-healthy status: ${data.status}`,
        durationMs,
      };
    } catch (err: unknown) {
      const durationMs = Date.now() - startTime;
      let errorMsg = 'Unknown connection error';

      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMsg = `Connection timed out after ${timeoutMs}ms`;
        } else {
          errorMsg = err.message;
        }
      }

      return {
        ok: false,
        error: errorMsg,
        durationMs,
      };
    }
  }
}
