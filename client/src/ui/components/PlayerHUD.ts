import type { Disposable } from "../../core/Disposable";
import { uiEvents } from "../core/UIEventBus";

export class PlayerHUD implements Disposable {
  public readonly element: HTMLDivElement;

  private readonly stateElement: HTMLElement;
  private readonly chatButton: HTMLButtonElement;
  private readonly emotesButton: HTMLButtonElement;
  private readonly settingsButton: HTMLButtonElement;

  constructor(playerName: string) {
    this.element = document.createElement("div");
    this.element.className = "player-hud";

    this.element.innerHTML = `
      <section class="player-card">
        <strong class="player-card__name" data-player-name></strong>
        <span class="player-card__state" data-player-state>Idle</span>
      </section>

      <nav class="action-bar">
        <button type="button" data-action="chat" aria-label="Abrir chat">
          Chat
        </button>
        <button type="button" data-action="emotes" aria-label="Abrir emotes">
          Emotes
        </button>
        <button type="button" data-action="settings" aria-label="Abrir ajustes">
          Ajustes
        </button>
      </nav>
    `;

    const nameElement = this.element.querySelector<HTMLElement>(
      "[data-player-name]",
    )!;
    nameElement.textContent = playerName;

    this.stateElement = this.element.querySelector(
      "[data-player-state]",
    )!;
    this.chatButton = this.element.querySelector(
      "[data-action='chat']",
    )!;
    this.emotesButton = this.element.querySelector(
      "[data-action='emotes']",
    )!;
    this.settingsButton = this.element.querySelector(
      "[data-action='settings']",
    )!;

    this.chatButton.addEventListener("click", this.handleChatClick);
    this.emotesButton.addEventListener("click", this.handleEmotesClick);
    this.settingsButton.addEventListener("click", this.handleSettingsClick);
  }

  public setPlayerState(state: string): void {
    this.stateElement.textContent = state;
  }

  public dispose(): void {
    this.chatButton.removeEventListener("click", this.handleChatClick);
    this.emotesButton.removeEventListener("click", this.handleEmotesClick);
    this.settingsButton.removeEventListener("click", this.handleSettingsClick);
    this.element.remove();
  }

  private handleChatClick = (): void => {
    uiEvents.emit("chat:open", {});
  };

  private handleEmotesClick = (): void => {
    uiEvents.emit("emote-menu:open", {});
  };

  private handleSettingsClick = (): void => {
    uiEvents.emit("settings:open", {});
  };
}
