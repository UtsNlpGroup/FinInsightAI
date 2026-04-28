/**
 * chatApi – raw HTTP/SSE communication layer.
 *
 * Responsibilities:
 *  - Serialise ChatRequest payloads and POST to /api/v1/agent/stream.
 *  - Parse the Server-Sent Events wire format (`data: <json>\n\n`).
 *  - Yield typed StreamChunk objects via an async generator.
 *
 * This module has zero React dependencies; it can be tested independently.
 */

const STREAM_ENDPOINT = '/api/v1/agent/stream';

// ── Wire types (mirror backend schemas/agent.py) ─────────────────────────────

export type StreamEventType = 'token' | 'tool_start' | 'tool_end' | 'done' | 'error';

export interface StreamChunk {
  event: StreamEventType;
  data: string | Record<string, unknown>;
  conversation_id: string;
}

export interface ApiMessage {
  role: 'user' | 'assistant' | 'tool' | 'system';
  content: string;
  tool_call_id?: string;
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Stream a chat turn from the backend agent.
 *
 * @param message       The user's latest message.
 * @param history       Prior turns to send as conversation context.
 * @param conversationId Stable ID grouping turns into a thread.
 * @param signal        Optional AbortSignal to cancel mid-stream.
 *
 * Yields one StreamChunk per SSE message until the `done` or `error` event.
 */
export async function* streamChat(
  message: string,
  history: ApiMessage[],
  conversationId: string,
  signal?: AbortSignal,
  model?: string,
): AsyncGenerator<StreamChunk> {
  const body: Record<string, unknown> = {
    message,
    history,
    conversation_id: conversationId,
  };
  if (model) body.model = model;

  const response = await fetch(STREAM_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(`API error ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('Response body is empty — SSE stream unavailable.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // SSE messages are separated by \n\n; buffer handles partial TCP chunks
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop() ?? '';

    for (const block of blocks) {
      const line = block.trim();
      if (!line.startsWith('data: ')) continue;

      const raw = line.slice(6);
      try {
        yield JSON.parse(raw) as StreamChunk;
      } catch {
        // Silently skip malformed SSE frames
      }
    }
  }
}
