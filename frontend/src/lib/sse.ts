export interface RawSseEvent {
  event: string
  data: string
}

/** Hand-rolled SSE parser over a fetch() ReadableStream. Native EventSource can't send POST
 * bodies, which every agent run endpoint needs, so we read the stream ourselves instead. */
export async function* parseSseStream(body: ReadableStream<Uint8Array>): AsyncGenerator<RawSseEvent> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      // Normalize CRLF to LF -- the server emits "\r\n\r\n" as the event separator, which
      // never matches a literal "\n\n" search otherwise (confirmed by direct browser testing).
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n")

      let sepIndex: number
      while ((sepIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, sepIndex)
        buffer = buffer.slice(sepIndex + 2)
        const parsed = parseEventBlock(rawEvent)
        if (parsed) yield parsed
      }
    }
  } finally {
    reader.releaseLock()
  }
}

function parseEventBlock(block: string): RawSseEvent | null {
  let event = "message"
  const dataLines: string[] = []

  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue // comment/keep-alive ping
    if (line.startsWith("event:")) event = line.slice(6).trim()
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim())
  }

  if (dataLines.length === 0) return null
  return { event, data: dataLines.join("\n") }
}
