import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import ts from "typescript";

function compile(source, imports = []) {
  let compiled = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  for (const [specifier, replacement] of imports) {
    compiled = compiled.replaceAll(`from "${specifier}"`, `from "${replacement}"`);
  }
  return `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`;
}

const chatClientSource = await readFile(
  new URL("../src/services/chatClient.ts", import.meta.url),
  "utf8",
);
const chatClientUrl = compile(chatClientSource);
const chatClient = await import(chatClientUrl);
const sseSource = await readFile(
  new URL("../src/services/sse.ts", import.meta.url),
  "utf8",
);
const sseUrl = compile(sseSource);
const httpClientSource = await readFile(
  new URL("../src/services/httpChatClient.ts", import.meta.url),
  "utf8",
);
const { httpChatClient } = await import(
  compile(httpClientSource, [
    ["./chatClient", chatClientUrl],
    ["./sse", sseUrl],
  ])
);

const sessionId = "c0c43b62-c3fb-4c72-8c1b-a0dd192d7ca4";

test("history client lists, loads, and deletes conversations", async () => {
  const requests = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    requests.push([String(input), init?.method ?? "GET"]);
    if (init?.method === "DELETE") {
      return new Response(null, { status: 204 });
    }
    return new Response(JSON.stringify(
      String(input) === "/api/conversations"
        ? [{ session_id: sessionId, title: "Primeira pergunta" }]
        : {
            session_id: sessionId,
            messages: [
              { role: "user", content: "Primeira pergunta" },
              { role: "assistant", content: "Resposta" },
            ],
          },
    ), { status: 200, headers: { "Content-Type": "application/json" } });
  };

  try {
    assert.deepEqual(await httpChatClient.listConversations(), [
      { session_id: sessionId, title: "Primeira pergunta" },
    ]);
    assert.deepEqual(await httpChatClient.getConversation(sessionId), {
      session_id: sessionId,
      messages: [
        { role: "user", content: "Primeira pergunta" },
        { role: "assistant", content: "Resposta" },
      ],
    });
    await httpChatClient.deleteConversation(sessionId);
    assert.deepEqual(requests, [
      ["/api/conversations", "GET"],
      [`/api/conversations/${sessionId}`, "GET"],
      [`/api/conversations/${sessionId}`, "DELETE"],
    ]);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("history client rejects incomplete transcripts and reports missing chats", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    session_id: sessionId,
    messages: [{ role: "user", content: "Sem resposta" }],
  }), { status: 200 });
  try {
    await assert.rejects(
      httpChatClient.getConversation(sessionId),
      (error) => error instanceof chatClient.ChatClientError && error.state === "unknown",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  globalThis.fetch = async () => new Response(
    JSON.stringify({ detail: "Conversation session unavailable" }),
    { status: 404 },
  );
  try {
    await assert.rejects(
      httpChatClient.deleteConversation(sessionId),
      (error) => error instanceof chatClient.ChatClientError && error.state === "failed",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
