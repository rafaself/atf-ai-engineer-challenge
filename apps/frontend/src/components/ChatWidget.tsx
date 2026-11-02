import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatClient } from "../services/chatClient";
import { Icon } from "./Icon";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
};

type ChatWidgetProps = {
  client: ChatClient;
};

const quickReplies = [
  { label: "Ver violões", prompt: "Quais violões vocês têm?" },
  { label: "Consultar preços", prompt: "Quais são os preços?" },
  { label: "Formas de pagamento", prompt: "Quais formas de pagamento?" },
];

export function ChatWidget({ client }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [failedPrompt, setFailedPrompt] = useState<string | null>(null);
  const messageInputRef = useRef<HTMLInputElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const nextMessageId = useRef(1);

  useEffect(() => {
    if (messages.length > 0 && !isSending) {
      messageInputRef.current?.focus({ preventScroll: true });
    }
  }, [isSending, messages.length]);

  useEffect(() => {
    const thread = threadRef.current;

    if (thread) {
      thread.scrollTop = thread.scrollHeight;
    }
  }, [messages, isSending, failedPrompt]);

  function appendMessage(role: Message["role"], text: string) {
    const id = nextMessageId.current;
    nextMessageId.current += 1;
    setMessages((current) => [...current, { id, role, text }]);
  }

  async function requestResponse(prompt: string, retry = false) {
    setFailedPrompt(null);
    setIsSending(true);

    try {
      const answer = await client.sendMessage(prompt, { retry });
      appendMessage("assistant", answer);
    } catch {
      setFailedPrompt(prompt);
    } finally {
      setIsSending(false);
    }
  }

  async function sendMessage(prompt: string) {
    const message = prompt.trim();

    if (!message || isSending) {
      return;
    }

    appendMessage("user", message);
    setDraft("");
    await requestResponse(message);
  }

  function startNewConversation() {
    if (isSending) {
      return;
    }

    setMessages([]);
    setFailedPrompt(null);
    setDraft("");
    messageInputRef.current?.focus({ preventScroll: true });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
  }

  return (
    <section
      aria-labelledby="chat-title"
      className="chat-panel"
    >
      <div className="chat-panel__surface">
        <header className="chat-header">
          <div className="assistant-avatar">
            <Icon name="sparkles" size={20} />
          </div>
          <div className="chat-header__identity">
            <h2 id="chat-title">Lia</h2>
            <p>Assistente virtual</p>
          </div>
          <div className="chat-header__actions">
            <button
              aria-label="Iniciar nova conversa"
              className="icon-button"
              disabled={isSending || messages.length === 0}
              onClick={startNewConversation}
              title="Nova conversa"
              type="button"
            >
              <Icon name="plus" size={20} />
            </button>
          </div>
        </header>

        <div
          aria-label="Conversa atual"
          aria-live="polite"
          className="chat-thread"
          ref={threadRef}
          role="log"
        >
          {messages.length === 0 && (
            <div className="chat-welcome">
              <h3>Vamos encontrar<br />o seu próximo som?</h3>
              <p>Escolha uma sugestão ou escreva sua pergunta.</p>
              <div aria-label="Perguntas recomendadas" className="quick-replies quick-replies--center">
                {quickReplies.map(({ label, prompt }) => (
                  <button
                    className="quick-reply"
                    disabled={isSending}
                    key={label}
                    onClick={() => void sendMessage(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div className={`message-row message-row--${message.role}`} key={message.id}>
              <p className="message-bubble">{message.text}</p>
            </div>
          ))}

          {isSending && (
            <div className="message-row message-row--assistant">
              <div aria-label="Lia está digitando" className="typing-indicator" role="status">
                <span /><span /><span />
              </div>
            </div>
          )}

          {failedPrompt && (
            <div className="chat-error" role="alert">
              <p>Não consegui responder agora. Esta é uma falha simulada.</p>
              <button
                disabled={isSending}
                onClick={() => void requestResponse(failedPrompt, true)}
                type="button"
              >
                Tentar novamente
              </button>
            </div>
          )}
        </div>

        <form className="chat-composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-message">Sua mensagem</label>
          <input
            autoComplete="off"
            disabled={isSending}
            id="chat-message"
            maxLength={300}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Escreva sua pergunta..."
            ref={messageInputRef}
            value={draft}
          />
          <button
            aria-label="Enviar mensagem"
            className="send-button"
            disabled={!draft.trim() || isSending}
            type="submit"
          >
            <Icon name="send" size={18} />
          </button>
        </form>
      </div>
    </section>
  );
}
