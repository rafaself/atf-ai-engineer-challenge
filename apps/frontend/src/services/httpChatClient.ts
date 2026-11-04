import {
  ChatClientError,
  type ChatClient,
  type ChatResponse,
  type ConversationSummary,
  type ConversationTranscript,
} from "./chatClient";
import { readServerSentEvents } from "./sse";

function isChatResponse(value: unknown): value is ChatResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const response = value as Record<string, unknown>;

  return (
    typeof response.answer === "string" &&
    response.answer.trim().length > 0 &&
    typeof response.session_id === "string" &&
    response.session_id.length > 0
  );
}

function errorMessageForStatus(status: number) {
  switch (status) {
    case 422:
      return "Não foi possível validar sua mensagem. Revise o texto antes de enviar outra.";
    case 404:
      return "Esta conversa não está disponível. Inicie uma nova conversa.";
    case 409:
      return "Já existe uma solicitação em andamento nesta conversa. Aguarde antes de enviar outra.";
    case 503:
      return "O atendimento está indisponível no momento. Tente mais tarde.";
    case 504:
      return "O atendimento demorou demais e esta mensagem não foi concluída.";
    default:
      return "O atendimento não conseguiu concluir esta mensagem.";
  }
}

function isConversationSummary(value: unknown): value is ConversationSummary {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const item = value as Record<string, unknown>;
  return typeof item.session_id === "string" && item.session_id.length > 0 &&
    typeof item.title === "string" && item.title.trim().length > 0;
}

function isConversationTranscript(value: unknown): value is ConversationTranscript {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const transcript = value as Record<string, unknown>;
  return typeof transcript.session_id === "string" && transcript.session_id.length > 0 &&
    Array.isArray(transcript.messages) && transcript.messages.length > 0 &&
    transcript.messages.every((message, index) => {
      if (typeof message !== "object" || message === null) {
        return false;
      }
      const item = message as Record<string, unknown>;
      return item.role === (index % 2 === 0 ? "user" : "assistant") &&
        typeof item.content === "string" && item.content.trim().length > 0;
    }) && transcript.messages.length % 2 === 0;
}

async function readHistoryResponse(response: Response): Promise<unknown> {
  if (!response.ok) {
    throw new ChatClientError(
      response.status === 404
        ? "Esta conversa não está mais disponível. Atualize o histórico."
        : "Não foi possível carregar o histórico de conversas. Tente novamente.",
      "failed",
    );
  }

  try {
    return await response.json();
  } catch {
    throw new ChatClientError(
      "A resposta do histórico estava inválida. Tente novamente.",
      "unknown",
    );
  }
}

export const httpChatClient: ChatClient = {
  async streamMessage(message, sessionId, onDelta) {
    const requestBody = {
      message,
      ...(sessionId ? { session_id: sessionId } : {}),
    };

    let response: Response;

    try {
      response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
    } catch {
      throw new ChatClientError(
        "A conexão foi interrompida. Não foi possível confirmar se a mensagem foi processada; ela pode ter sido registrada.",
        "unknown",
      );
    }

    if (!response.ok) {
      throw new ChatClientError(
        errorMessageForStatus(response.status),
        response.status === 404 ? "unknown" : "failed",
      );
    }

    if (!response.headers.get("content-type")?.includes("text/event-stream") || !response.body) {
      throw new ChatClientError(
        "A resposta do atendimento estava inválida. Não foi possível confirmar a conversa.",
        "unknown",
      );
    }

    try {
      for await (const event of readServerSentEvents(response.body)) {
        let payload: unknown;
        try {
          payload = JSON.parse(event.data);
        } catch {
          throw new ChatClientError(
            "A resposta do atendimento estava inválida. Não foi possível confirmar a conversa.",
            "unknown",
          );
        }

        if (event.event === "delta") {
          if (
            typeof payload === "object" && payload !== null &&
            typeof (payload as Record<string, unknown>).text === "string"
          ) {
            const text = (payload as Record<string, string>).text;
            if (text.length > 0) {
              onDelta(text);
            }
            continue;
          }

          throw new ChatClientError(
            "A resposta do atendimento estava inválida. Não foi possível confirmar a conversa.",
            "unknown",
          );
        }

        if (event.event === "done") {
          if (isChatResponse(payload)) {
            return payload;
          }
          throw new ChatClientError(
            "A resposta do atendimento estava inválida. Não foi possível confirmar a conversa.",
            "unknown",
          );
        }

        if (event.event === "error") {
          const message =
            typeof payload === "object" && payload !== null &&
            typeof (payload as Record<string, unknown>).message === "string"
              ? (payload as Record<string, string>).message
              : "";
          throw new ChatClientError(
            messageForStreamFailure(message),
            message === "Conversation session unavailable" ? "unknown" : "failed",
          );
        }
      }
    } catch (error) {
      if (error instanceof ChatClientError) {
        throw error;
      }
      throw new ChatClientError(
        "A conexão foi interrompida. Não foi possível confirmar se a mensagem foi processada; ela pode ter sido registrada.",
        "unknown",
      );
    }

    throw new ChatClientError(
      "A conexão foi interrompida. Não foi possível confirmar se a mensagem foi processada; ela pode ter sido registrada.",
      "unknown",
    );
  },

  async listConversations() {
    let response: Response;
    try {
      response = await fetch("/api/conversations");
    } catch {
      throw new ChatClientError(
        "Não foi possível conectar para carregar o histórico.",
        "unknown",
      );
    }
    const value = await readHistoryResponse(response);
    if (!Array.isArray(value) || !value.every(isConversationSummary)) {
      throw new ChatClientError(
        "A resposta do histórico estava inválida. Tente novamente.",
        "unknown",
      );
    }
    return value;
  },

  async getConversation(sessionId) {
    let response: Response;
    try {
      response = await fetch(`/api/conversations/${encodeURIComponent(sessionId)}`);
    } catch {
      throw new ChatClientError(
        "Não foi possível conectar para abrir esta conversa.",
        "unknown",
      );
    }
    const value = await readHistoryResponse(response);
    if (!isConversationTranscript(value)) {
      throw new ChatClientError(
        "A resposta da conversa estava inválida. Tente novamente.",
        "unknown",
      );
    }
    return value;
  },

  async deleteConversation(sessionId) {
    let response: Response;
    try {
      response = await fetch(`/api/conversations/${encodeURIComponent(sessionId)}`, {
        method: "DELETE",
      });
    } catch {
      throw new ChatClientError(
        "Não foi possível conectar para excluir esta conversa.",
        "unknown",
      );
    }
    if (!response.ok) {
      throw new ChatClientError(
        response.status === 404
          ? "Esta conversa não está mais disponível. Atualize o histórico."
          : "Não foi possível excluir esta conversa. Tente novamente.",
        "failed",
      );
    }
  },
};

function messageForStreamFailure(message: string) {
  switch (message) {
    case "Unknown demo customer":
      return "Não foi possível validar o cliente de demonstração.";
    case "Conversation session unavailable":
      return "Esta conversa não está disponível. Inicie uma nova conversa.";
    case "Conversation turn conflicts":
      return "Já existe uma solicitação em andamento nesta conversa. Aguarde antes de enviar outra.";
    case "Agent service unavailable":
      return "O atendimento está indisponível no momento. Tente mais tarde.";
    case "Conversation timed out":
      return "O atendimento demorou demais e esta mensagem não foi concluída.";
    default:
      return "O atendimento não conseguiu concluir esta mensagem.";
  }
}
