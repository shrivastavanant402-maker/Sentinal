import { getConfig } from '../config';

export type DecisionStatus = 'ALLOW' | 'BLOCK' | 'APPROVAL' | 'QUARANTINE';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface ActionRequest {
  agent_id: string;
  action: string;
  payload?: Record<string, any>;
  mission_id?: string | null;
  session_id?: string | null;
  provenance?: Record<string, any> | null;
  signature?: string | null;
  timestamp?: number | null;
  nonce?: string | null;
}

export interface DecisionResponse {
  decision: DecisionStatus;
  allowed: boolean;
  reason: string;
  risk_level: RiskLevel;
  agent_id: string;
  action: string;
  event_id?: string | null;
  details?: Record<string, any>;
}

export interface EnforcementResult {
  ok: boolean;
  statusCode?: number;
  decision?: DecisionResponse;
  error?: string;
  durationMs: number;
}

/**
 * Client for communicating with the AegisMesh PEP POST /enforce endpoint.
 * Encapsulates network transport, timeout, error resilience, and typing.
 */
export class EnforcementClient {
  /**
   * Submits an ActionRequest to the AegisMesh Policy Enforcement Point (PEP).
   *
   * @param request Action request payload conforming to backend schema
   * @param backendUrl Optional override for the backend URL (defaults to configuration)
   * @param timeoutMs Request timeout in milliseconds (default: 5000)
   */
  async enforce(
    request: ActionRequest,
    backendUrl?: string,
    timeoutMs = 5000
  ): Promise<EnforcementResult> {
    const startTime = Date.now();
    const config = getConfig();
    const baseUrl = (backendUrl || config.backendUrl).trim().replace(/\/+$/, '');
    const targetUrl = `${baseUrl}/enforce`;

    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);

      const response = await fetch(targetUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'User-Agent': 'AegisMesh-VSCode-Adapter/0.1.0',
        },
        body: JSON.stringify({
          agent_id: request.agent_id,
          action: request.action,
          payload: request.payload || {},
          mission_id: request.mission_id ?? null,
          session_id: request.session_id ?? null,
          provenance: request.provenance ?? null,
          signature: request.signature ?? null,
          timestamp: request.timestamp ?? null,
          nonce: request.nonce ?? null,
        }),
        signal: controller.signal,
      });

      clearTimeout(timer);
      const durationMs = Date.now() - startTime;

      if (!response.ok) {
        let errorDetail = `HTTP ${response.status} ${response.statusText}`;
        try {
          const errorBody = await response.json() as any;
          if (errorBody?.detail) {
            errorDetail += ` - ${JSON.stringify(errorBody.detail)}`;
          }
        } catch {
          // Response body was not JSON
        }

        return {
          ok: false,
          statusCode: response.status,
          error: errorDetail,
          durationMs,
        };
      }

      const decision = (await response.json()) as DecisionResponse;

      // Validate required contract fields exist
      if (!decision || typeof decision.decision !== 'string' || typeof decision.allowed !== 'boolean') {
        return {
          ok: false,
          statusCode: response.status,
          error: 'Malformed response from AegisMesh enforcement endpoint',
          durationMs,
        };
      }

      return {
        ok: true,
        statusCode: response.status,
        decision,
        durationMs,
      };
    } catch (err: unknown) {
      const durationMs = Date.now() - startTime;
      let errorMsg = 'Unknown enforcement communication error';

      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMsg = `Enforcement request timed out after ${timeoutMs}ms`;
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
