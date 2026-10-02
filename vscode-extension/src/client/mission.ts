import { getConfig } from '../config';

export interface MissionRunRequest {
  goal: string;
  mission_id?: string | null;
  session_id?: string | null;
}

export interface ExecutionTraceStep {
  step: number;
  agent_id: string;
  action: string;
  status: string;
  decision?: string;
  reason?: string;
  risk?: string;
  event_id?: string;
  output?: Record<string, any>;
  error?: string;
  details?: Record<string, any>;
}

export interface MissionResult {
  mission_id: string;
  session_id: string;
  goal: string;
  status: string;
  planner_result?: Record<string, any> | null;
  researcher_result?: Record<string, any> | null;
  executor_result?: Record<string, any> | null;
  execution_trace: ExecutionTraceStep[];
  event_ids: string[];
  error?: string | null;
  error_details?: Record<string, any> | null;
}

export interface MissionClientResult {
  ok: boolean;
  statusCode?: number;
  data?: MissionResult;
  error?: string;
  durationMs: number;
}

/**
 * Client for communicating with the AegisMesh POST /missions/run endpoint.
 */
export class MissionClient {
  /**
   * Runs a multi-agent mission on the AegisMesh backend.
   *
   * @param request Mission payload containing goal and optional mission_id/session_id
   * @param backendUrl Optional backend URL override
   * @param timeoutMs Request timeout in milliseconds (default: 60000)
   */
  async runMission(
    request: MissionRunRequest,
    backendUrl?: string,
    timeoutMs = 60000
  ): Promise<MissionClientResult> {
    const startTime = Date.now();
    const config = getConfig();
    const baseUrl = (backendUrl || config.backendUrl).trim().replace(/\/+$/, '');
    const targetUrl = `${baseUrl}/missions/run`;

    let timer: NodeJS.Timeout | null = null;
    try {
      const controller = new AbortController();
      timer = setTimeout(() => controller.abort(), timeoutMs);

      const response = await fetch(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'AegisMesh-VSCode-Adapter/0.1.0',
        },
        body: JSON.stringify({
          goal: request.goal,
          mission_id: request.mission_id ?? null,
          session_id: request.session_id ?? null,
        }),
        signal: controller.signal,
      });

      const durationMs = Date.now() - startTime;

      if (!response.ok) {
        let errorDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errorBody = (await response.json()) as any;
          if (errorBody?.detail) {
            errorDetail += ` - ${JSON.stringify(errorBody.detail)}`;
          }
        } catch {
          // Non-JSON response
        }

        return {
          ok: false,
          statusCode: response.status,
          error: errorDetail,
          durationMs,
        };
      }

      const data = (await response.json()) as MissionResult;
      return {
        ok: true,
        statusCode: response.status,
        data,
        durationMs,
      };
    } catch (err: any) {
      const durationMs = Date.now() - startTime;
      let errorMsg = 'Failed to execute mission request';

      if (err.name === 'AbortError') {
        errorMsg = `Mission request timed out after ${timeoutMs}ms`;
      } else if (err.code === 'ECONNREFUSED' || err.message?.includes('ECONNREFUSED')) {
        errorMsg = `Connection refused at ${targetUrl}. Is AegisMesh backend running?`;
      } else if (err instanceof Error) {
        errorMsg = err.message;
      }

      return {
        ok: false,
        error: errorMsg,
        durationMs,
      };
    } finally {
      if (timer) {
        clearTimeout(timer);
      }
    }
  }
}
