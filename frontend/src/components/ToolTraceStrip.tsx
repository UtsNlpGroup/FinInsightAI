/**
 * Shows MCP tool invocations after an agent-backed request completes.
 * Styling matches the chat ToolBanner "done" / error states.
 */

import type { ToolCallTraceItem } from '../lib/toolCalls';

export type { ToolCallTraceItem } from '../lib/toolCalls';

export function ToolTraceStrip({
  traces,
  className = '',
}: {
  traces: ToolCallTraceItem[];
  className?: string;
}) {
  if (!traces.length) return null;
  return (
    <div className={`flex flex-wrap justify-center gap-2 ${className}`}>
      {traces.map((t, i) => {
        const ok = !t.error;
        return (
          <span
            key={`${t.toolName}-${i}`}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border"
            style={{
              background: ok ? '#F0FDF4' : '#FEF2F2',
              color: ok ? '#15803D' : '#B91C1C',
              borderColor: ok ? '#86EFAC' : '#FECACA',
            }}
          >
            <span>⚙</span>
            {ok ? `${t.toolName} complete` : `${t.toolName} failed`}
          </span>
        );
      })}
    </div>
  );
}
