import { ChatClientError, type ChatClient, type ChatResponse } from "./chatClient";

const demoCustomerId = 1;

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
  async sendMessage(message, sessionId) {
    const requestBody = {
      message,
      customer_id: demoCustomerId,
      ...(sessionId ? { session_id: sessionId } : {}),
    };

    let response: Response;

    try {
      response = await fetch("/api/chat", {
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
      throw new ChatClientError(errorMessageForStatus(response.status), "failed");
    }

    let result: unknown;

    try {
      result = await response.json();
    } catch {
      throw new ChatClientError(
        "A resposta do atendimento estava inválida. Não foi possível confirmar a conversa.",
        "unknown",
      );
    }

    if (!isChatResponse(result)) {
      throw new ChatClientError(
        "A resposta do atendimento estava inválida. Não foi possível confirmar a conversa.",
        "unknown",
      );
    }

    return result;
  },
};
