export type ServerSentEvent = {
  event: string;
  data: string;
};

export async function* readServerSentEvents(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<ServerSentEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  const pending: ServerSentEvent[] = [];
  let buffer = "";
  let eventName = "";
  let dataLines: string[] = [];
  let firstLine = true;
  let ended = false;

  function processLine(line: string) {
    if (firstLine) {
      line = line.replace(/^\uFEFF/, "");
      firstLine = false;
    }

    if (line === "") {
      if (dataLines.length > 0) {
        pending.push({ event: eventName || "message", data: dataLines.join("\n") });
      }
      eventName = "";
      dataLines = [];
      return;
    }

    if (line.startsWith(":")) {
      return;
    }

    const separator = line.indexOf(":");
    const field = separator < 0 ? line : line.slice(0, separator);
    let value = separator < 0 ? "" : line.slice(separator + 1);
    if (value.startsWith(" ")) {
      value = value.slice(1);
    }

    if (field === "event") {
      eventName = value;
    } else if (field === "data") {
      dataLines.push(value);
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });

      while (buffer.length > 0) {
        const lineFeed = buffer.indexOf("\n");
        const carriageReturn = buffer.indexOf("\r");
        let lineEnd = -1;

        if (lineFeed >= 0 && carriageReturn >= 0) {
          lineEnd = Math.min(lineFeed, carriageReturn);
        } else {
          lineEnd = Math.max(lineFeed, carriageReturn);
        }

        if (lineEnd < 0 || (!done && buffer[lineEnd] === "\r" && lineEnd === buffer.length - 1)) {
          break;
        }

        const line = buffer.slice(0, lineEnd);
        const isCarriageReturn = buffer[lineEnd] === "\r";
        const hasLineFeed = isCarriageReturn && buffer[lineEnd + 1] === "\n";
        buffer = buffer.slice(lineEnd + (hasLineFeed ? 2 : 1));
        processLine(line);

        while (pending.length > 0) {
          yield pending.shift()!;
        }
      }

      if (done) {
        if (buffer.length > 0) {
          processLine(buffer);
          buffer = "";
        }
        processLine("");
        while (pending.length > 0) {
          yield pending.shift()!;
        }
        ended = true;
        return;
      }
    }
  } finally {
    if (!ended) {
      try {
        await reader.cancel();
      } catch {
        // The transport may already have cancelled the response body.
      }
    }
    reader.releaseLock();
  }
}
