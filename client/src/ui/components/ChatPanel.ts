import { uiEvents } from "../core/UIEventBus";
import type { UIState } from "../state/UIState";

export class ChatPanel {
  public readonly element: HTMLDivElement;

  private readonly messagesEl: HTMLDivElement;
  private readonly inputEl: HTMLInputElement;

  private readonly state: UIState;
  private readonly author: string;

  constructor(state: UIState, author: string) {
    this.state = state;
    this.author = author;

    this.element = document.createElement("div");
    this.element.className = "chat-panel";
    this.element.style.display = "none";

    this.element.innerHTML = `
      <div class="chat-panel__messages" data-messages></div>
      <input
        type="text"
        class="chat-panel__input"
        placeholder="Escribir mensaje..."
        data-chat-input
      />
    `;

    this.messagesEl = this.element.querySelector(
      "[data-messages]",
    )!;

    this.inputEl = this.element.querySelector(
      "[data-chat-input]",
    )!;

    this.inputEl.addEventListener(
      "keydown",
      this.handleInputKey,
    );

    this.inputEl.addEventListener(
      "focus",
      () => {
        this.state.isChatOpen = true;
        uiEvents.emit("ui:focus-changed", {
          focused: true,
        });
      },
    );

    this.inputEl.addEventListener(
      "blur",
      () => {
        this.state.isChatOpen = false;
        uiEvents.emit("ui:focus-changed", {
          focused: false,
        });
      },
    );
  }

  public open(): void {
    this.element.style.display = "flex";
    this.inputEl.focus();
  }

  public close(): void {
    this.element.style.display = "none";
    this.inputEl.value = "";
    this.inputEl.blur();
  }

  public toggle(): void {
    if (this.element.style.display === "flex") {
      this.close();
    } else {
      this.open();
    }
  }

  public addMessage(author: string, text: string): void {
    const msg = document.createElement("div");
    msg.className = "chat-panel__message";

    msg.innerHTML = `
      <span class="chat-panel__message-author">${author}:</span>
      <span>${text}</span>
    `;

    this.messagesEl.appendChild(msg);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  private handleInputKey = (
    event: KeyboardEvent,
  ): void => {
    if (event.code !== "Enter") {
      return;
    }

    const message = this.inputEl.value.trim();

    if (!message) {
      return;
    }

    this.addMessage(this.author, message);

    uiEvents.emit("chat:send", { message });

    this.inputEl.value = "";
  };
}
