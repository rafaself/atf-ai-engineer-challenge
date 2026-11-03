import { useEffect, useRef, useState, type FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import { ChatClientError, type ChatClient } from "../services/chatClient";
import { ChatScrollFollower } from "./chatScroll";
import { Icon } from "./Icon";

type Message = {
  id: number;
  role: "assistant" | "user";
  text: string;
  status?: "streaming" | "complete" | "partial";
};

type ChatWidgetProps = {
  client: ChatClient;
};

const quickReplies = [
  { label: "Ver violões", prompt: "Quais violões vocês têm?" },
  { label: "Consultar preços", prompt: "Quais são os preços?" },
  { label: "Formas de pagamento", prompt: "Quais formas de pagamento?" },
];

function describeFailure(error: unknown) {
  if (error instanceof ChatClientError) {
    return error.state === "unknown"
      ? `${error.message} Inicie uma nova conversa antes de continuar.`
      : error.message;
  }

  return "Ocorreu um erro inesperado. Não foi possível confirmar a conversa. Inicie uma nova conversa antes de continuar.";
}

export function ChatWidget({ client }: ChatWidgetProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [requiresNewConversation, setRequiresNewConversation] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isFollowingOutput, setIsFollowingOutput] = useState(true);
  const messageInputRef = useRef<HTMLInputElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const scrollFollowerRef = useRef<ChatScrollFollower | null>(null);
  const pendingStreamTextRef = useRef("");
  const streamFrameRef = useRef<number | null>(null);
  const nextMessageId = useRef(1);
  const sessionIdRef = useRef<string | null>(null);

  function flushStreamText(messageId: number) {
    if (streamFrameRef.current !== null) {
      window.cancelAnimationFrame(streamFrameRef.current);
      streamFrameRef.current = null;
    }

    const text = pendingStreamTextRef.current;
    pendingStreamTextRef.current = "";
    if (!text) {
      return;
    }

    setMessages((current) =>
      current.map((item) =>
        item.id === messageId ? { ...item, text: item.text + text } : item,
      ),
    );
  }

  function queueStreamText(messageId: number, text: string) {
    pendingStreamTextRef.current += text;
    if (streamFrameRef.current !== null) {
      return;
    }

    streamFrameRef.current = window.requestAnimationFrame(() => {
      streamFrameRef.current = null;
      flushStreamText(messageId);
    });
  }

  useEffect(() => {
    if (messages.length > 0 && !isSending) {
      messageInputRef.current?.focus({ preventScroll: true });
    }
  }, [isSending, messages.length]);

  useEffect(() => {
    const thread = threadRef.current;
    if (!thread) {
      return;
    }

    const follower = new ChatScrollFollower(
      thread,
      window,
      () => window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      setIsFollowingOutput,
    );
    scrollFollowerRef.current = follower;
    thread.addEventListener("scroll", follower.handleScroll, { passive: true });

    return () => {
      thread.removeEventListener("scroll", follower.handleScroll);
      follower.dispose();
      scrollFollowerRef.current = null;
      if (streamFrameRef.current !== null) {
        window.cancelAnimationFrame(streamFrameRef.current);
        streamFrameRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    scrollFollowerRef.current?.followNewOutput();
  }, [messages]);

  function appendMessage(
    role: Message["role"],
    text: string,
    status?: Message["status"],
  ) {
    const id = nextMessageId.current;
    nextMessageId.current += 1;
    setMessages((current) => [...current, { id, role, text, status }]);
    return id;
  }

  async function sendMessage(prompt: string) {
    const message = prompt.trim();

    if (!message || isSending || requiresNewConversation) {
      return;
    }

    appendMessage("user", message);
    const assistantMessageId = appendMessage("assistant", "", "streaming");
    setDraft("");
    setRequestError(null);
    setIsSending(true);

    try {
      const response = await client.streamMessage(
        message,
        sessionIdRef.current ?? undefined,
        (text) => queueStreamText(assistantMessageId, text),
      );
      flushStreamText(assistantMessageId);
      sessionIdRef.current = response.session_id;
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantMessageId
            ? { ...item, text: response.answer, status: "complete" }
            : item,
        ),
      );
    } catch (error) {
      flushStreamText(assistantMessageId);
      const failureMessage = describeFailure(error);
      setMessages((current) =>
        current.flatMap((item) => {
          if (item.id !== assistantMessageId) {
            return [item];
          }
          return item.text
            ? [{ ...item, status: "partial" }]
            : [];
        }),
      );
      setRequestError(failureMessage);
      if (!(error instanceof ChatClientError) || error.state === "unknown") {
        sessionIdRef.current = null;
        setRequiresNewConversation(true);
      }
    } finally {
      setIsSending(false);
    }
  }

  function startNewConversation() {
    if (isSending) {
      return;
    }

    setMessages([]);
    sessionIdRef.current = null;
    setRequiresNewConversation(false);
    setRequestError(null);
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

        <div className="chat-thread-shell">
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
              message.text && (
                <div className={`message-row message-row--${message.role}`} key={message.id}>
                  <div className="message-bubble">
                    <ReactMarkdown>{message.text}</ReactMarkdown>
                    {message.status === "partial" && (
                      <span className="message-status">Resposta parcial; não foi concluída.</span>
                    )}
                  </div>
                </div>
              )
            ))}

            {isSending && (
              <div className="message-row message-row--assistant">
                <div aria-label="Lia está respondendo" className="typing-indicator" role="status">
                  <span /><span /><span />
                </div>
              </div>
            )}

            {requestError && (
              <div className="chat-error" role="alert">
                <p>{requestError}</p>
              </div>
            )}
          </div>

          {!isFollowingOutput && (
            <button
              aria-label="Rolar para a mensagem mais recente"
              className="chat-scroll-bottom"
              onClick={() => scrollFollowerRef.current?.jumpToBottom()}
              type="button"
            >
              <Icon name="arrowDown" size={18} />
            </button>
          )}
        </div>

        <form className="chat-composer" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="chat-message">Sua mensagem</label>
          <input
            autoComplete="off"
            disabled={isSending || requiresNewConversation}
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
            disabled={!draft.trim() || isSending || requiresNewConversation}
            type="submit"
          >
            <Icon name="send" size={18} />
          </button>
        </form>
      </div>
    </section>
  );
}
