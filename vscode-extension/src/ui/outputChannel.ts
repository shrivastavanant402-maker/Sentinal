import * as vscode from 'vscode';
import { MissionResult } from '../client/mission';

let aegisMeshOutputChannel: vscode.OutputChannel | undefined;

/**
 * Returns or creates the singleton "AegisMesh" Output Channel.
 */
export function getOutputChannel(): vscode.OutputChannel {
  if (!aegisMeshOutputChannel) {
    aegisMeshOutputChannel = vscode.window.createOutputChannel('AegisMesh');
  }
  return aegisMeshOutputChannel;
}

/**
 * Disposes the output channel on extension deactivation.
 */
export function disposeOutputChannel(): void {
  if (aegisMeshOutputChannel) {
    aegisMeshOutputChannel.dispose();
    aegisMeshOutputChannel = undefined;
  }
}

/**
 * Formats a MissionResult according to the AegisMesh Output Channel specification.
 */
export function formatMissionOutput(result: MissionResult): string {
  const lines: string[] = [];

  lines.push('AegisMesh Mission');
  lines.push('=================');
  lines.push('');
  lines.push(`Mission: ${result.mission_id}`);
  lines.push(`Session: ${result.session_id}`);
  lines.push('');
  lines.push('Goal:');
  lines.push(result.goal);
  lines.push('');
  lines.push('Execution Trace');
  lines.push('---------------');
  lines.push('');

  if (result.execution_trace && result.execution_trace.length > 0) {
    result.execution_trace.forEach((step, idx) => {
      const stepNum = step.step ?? idx + 1;
      const agent = step.agent_id || 'Unknown Agent';
      const action = step.action || 'Unknown Action';
      const decision = step.decision || step.status || 'UNKNOWN';
      const reason = step.reason || (step.error ? step.error : 'N/A');
      const risk = step.risk || (step.details?.risk_level ?? (decision === 'ALLOW' ? 'low' : 'critical'));

      lines.push(`[${stepNum}] ${agent}`);
      lines.push(`    Action: ${action}`);
      lines.push(`    Decision: ${decision}`);
      lines.push(`    Reason: ${reason}`);
      lines.push(`    Risk: ${risk}`);

      if (step.event_id) {
        lines.push(`    Event ID: ${step.event_id}`);
      }
      if (step.error) {
        lines.push(`    Error: ${step.error}`);
      }
      if (step.details && Object.keys(step.details).length > 0) {
        lines.push(`    Details: ${JSON.stringify(step.details)}`);
      }
      lines.push('');
    });
  } else {
    lines.push('No execution trace recorded.');
    lines.push('');
  }

  lines.push(`Mission Status: ${result.status}`);
  lines.push('');

  if (result.status !== 'COMPLETED') {
    if (result.error) {
      lines.push(`Error: ${result.error}`);
    }
    if (result.error_details && Object.keys(result.error_details).length > 0) {
      lines.push(`Error Details: ${JSON.stringify(result.error_details, null, 2)}`);
    }
    lines.push('');
  }

  lines.push('Event IDs:');
  if (result.event_ids && result.event_ids.length > 0) {
    for (const eid of result.event_ids) {
      lines.push(eid);
    }
  } else {
    lines.push('None');
  }

  return lines.join('\n');
}

/**
 * Writes mission result text to the AegisMesh Output Channel and brings it into focus.
 */
export function displayMissionResult(result: MissionResult): void {
  const channel = getOutputChannel();
  const text = formatMissionOutput(result);
  channel.appendLine(text);
  channel.show(true);
}
