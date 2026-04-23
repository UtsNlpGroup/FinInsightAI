/** Normalized MCP tool trace from analysis/agent API responses. */

export interface ToolCallTraceItem {
  toolName: string;
  error?: string | null;
}

export function normalizeToolCalls(raw: unknown): ToolCallTraceItem[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((t: unknown) => {
    const o = t as Record<string, unknown>;
    const name = String(o.tool_name ?? o.toolName ?? 'tool');
    const err = o.error;
    const error = err != null && String(err).trim() !== '' ? String(err) : null;
    return { toolName: name, error };
  });
}
