import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import ts from "typescript";

async function loadTypeScriptModule(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const encoded = Buffer.from(compiled).toString("base64");
  return import(`data:text/javascript;base64,${encoded}`);
}

const { readServerSentEvents } = await loadTypeScriptModule(
  "../src/services/sse.ts",
);
const { ChatScrollFollower } = await loadTypeScriptModule(
  "../src/components/chatScroll.ts",
);

test("SSE parsing preserves UTF-8 and delimiters split across fetch chunks", async () => {
  const encoder = new TextEncoder();
  const bytes = encoder.encode(
    'event: delta\r\ndata: {"text":"ação 🎸"}\r\n\r\nevent: done\ndata: {"answer":"final"}\n\n',
  );
  const accentByte = bytes.indexOf(0xc3) + 1;
  const carriageReturn = bytes.indexOf(0x0d);
  const chunks = [
    bytes.slice(0, carriageReturn + 1),
    bytes.slice(carriageReturn + 1, accentByte),
    bytes.slice(accentByte),
  ];
  const body = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(chunk);
      }
      controller.close();
    },
  });
  const events = [];

  for await (const event of readServerSentEvents(body)) {
    events.push(event);
  }

  assert.deepEqual(events, [
    { event: "delta", data: '{"text":"ação 🎸"}' },
    { event: "done", data: '{"answer":"final"}' },
  ]);
});

test("scroll following throttles output and resumes at the bottom after manual pause", () => {
  let nextFrameId = 1;
  const frames = new Map();
  const cancelledFrames = [];
  const scrolls = [];
  const changes = [];
  let reducedMotion = false;
  const scheduler = {
    requestAnimationFrame(callback) {
      const id = nextFrameId++;
      frames.set(id, callback);
      return id;
    },
    cancelAnimationFrame(id) {
      cancelledFrames.push(id);
      frames.delete(id);
    },
  };
  const container = {
    clientHeight: 300,
    scrollHeight: 1000,
    scrollTop: 700,
    scrollTo(options) {
      scrolls.push(options);
      this.scrollTop = Math.min(options.top, this.scrollHeight - this.clientHeight);
    },
  };
  const follower = new ChatScrollFollower(
    container,
    scheduler,
    () => reducedMotion,
    (following) => changes.push(following),
  );

  follower.followNewOutput();
  follower.followNewOutput();
  assert.equal(frames.size, 1);
  container.scrollHeight = 1100;
  const [frameId, frame] = frames.entries().next().value;
  frames.delete(frameId);
  frame(0);
  assert.deepEqual(scrolls, [{ top: 1100, behavior: "smooth" }]);

  follower.followNewOutput();
  const pendingFrameId = frames.keys().next().value;
  container.scrollTop = 500;
  follower.handleScroll();
  assert.deepEqual(changes, [false]);
  assert.deepEqual(cancelledFrames, [pendingFrameId]);
  follower.followNewOutput();
  assert.equal(frames.size, 0);

  container.scrollTop = container.scrollHeight - container.clientHeight;
  follower.handleScroll();
  assert.deepEqual(changes, [false, true]);

  reducedMotion = true;
  follower.jumpToBottom();
  assert.deepEqual(scrolls.at(-1), { top: 1100, behavior: "instant" });
  follower.dispose();
});
