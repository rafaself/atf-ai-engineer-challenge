import { ChatClientError, type ChatClient, type ChatResponse } from "./chatClient";
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
