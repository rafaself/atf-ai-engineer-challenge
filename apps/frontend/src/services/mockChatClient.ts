import type { ChatClient } from "./chatClient";

const quickReplyResponses: Record<string, string> = {
  "quais violoes voces tem?":
    "Nesta simulação, posso apresentar um violão clássico de nylon para iniciantes. Conte o que você procura; esta resposta é pré-escrita.",
  "quais sao os precos?":
    "Esta simulação não consulta preços atuais. Em um atendimento integrado, eu consultaria o catálogo para informar os valores.",
  "quais formas de pagamento?":
    "Este protótipo não consulta regras reais de pagamento. As respostas são simuladas e não confirmam condições comerciais.",
};

const keywordResponses: Array<{ keywords: string[]; response: string }> = [
  {
    keywords: ["preco", "valor", "custa", "quanto"],
    response:
      "Esta demonstração não consulta preços nem disponibilidade. As respostas são simuladas para apresentar a experiência de atendimento.",
  },
  {
    keywords: ["pagamento", "parcel", "pix"],
    response:
      "As condições de pagamento não estão conectadas a uma loja real neste protótipo. Posso mostrar como as respostas simuladas aparecem na conversa.",
  },
  {
    keywords: [
      "violao",
      "guitarra",
      "instrumento",
      "teclas",
      "piano",
      "teclado",
      "violino",
      "bateria",
      "saxofone",
    ],
    response:
      "Posso demonstrar uma conversa sobre instrumentos musicais. Conte qual estilo de som você procura; as respostas são simuladas.",
  },
];

const delay = (milliseconds: number) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

const normalize = (value: string) =>
  value
    .trim()
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");

function findResponse(message: string) {
  const normalized = normalize(message);
  const exactResponse = quickReplyResponses[normalized];

  if (exactResponse) {
    return exactResponse;
  }

  return (
    keywordResponses.find(({ keywords }) =>
      keywords.some((keyword) => normalized.includes(keyword)),
    )?.response ??
    "Esta conversa é uma simulação com respostas pré-escritas. Experimente perguntar sobre violões, preços ou formas de pagamento."
  );
}

export const mockChatClient: ChatClient = {
  async sendMessage(message, options) {
    await delay(420);

    if (/\b(erro|falha)\b/i.test(normalize(message))) {
      if (!options?.retry) {
        throw new Error("Falha simulada para demonstrar a recuperação da conversa.");
      }

      return "Consegui recuperar a mensagem simulada. Você pode continuar a conversa.";
    }

    return findResponse(message);
  },
};
