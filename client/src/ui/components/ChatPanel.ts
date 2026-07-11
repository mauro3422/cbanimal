import type { Disposable } from "../../core/Disposable";
import { uiEvents } from "../core/UIEventBus";
import type { UIState } from "../state/UIState";

export class ChatPanel implements Disposable {
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
        maxlength="300"
        data-chat-input
      />
    `;

    this.messagesEl = this.element.querySelector(
      "[data-messages]",
    )!;

    this.inputEl = this.element.querySelector(
      "[data-chat-input]",
    )!;

    this.inputEl.addEventListener("keydown", this.handleInputKey);
    this.inputEl.addEventListener("focus", this.handleFocus);
    this.inputEl.addEventListener("blur", this.handleBlur);
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
    const messageElement = document.createElement("div");
    messageElement.className = "chat-panel__message";

    const authorElement = document.createElement("span");
    authorElement.className = "chat-panel__message-author";
    authorElement.textContent = `${author}:`;

    const textElement = document.createElement("span");
    textElement.textContent = text;

    messageElement.append(authorElement, textElement);
    this.messagesEl.appendChild(messageElement);
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  public dispose(): void {
    this.inputEl.removeEventListener("keydown", this.handleInputKey);
    this.inputEl.removeEventListener("focus", this.handleFocus);
    this.inputEl.removeEventListener("blur", this.handleBlur);
    this.element.remove();
  }

  private handleFocus = (): void => {
    this.state.isChatOpen = true;
    uiEvents.emit("ui:focus-changed", { focused: true });
  };

  private handleBlur = (): void => {
    this.state.isChatOpen = false;
    uiEvents.emit("ui:focus-changed", { focused: false });
  };

  private handleInputKey = (event: KeyboardEvent): void => {
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
