import { uiEvents } from "../core/UIEventBus";

export class PlayerHUD {
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
        <strong class="player-card__name">
          ${playerName}
        </strong>

        <span
          class="player-card__state"
          data-player-state
        >
          Idle
        </span>
      </section>

      <nav class="action-bar">
        <button
          type="button"
          data-action="chat"
          aria-label="Abrir chat"
        >
          Chat
        </button>

        <button
          type="button"
          data-action="emotes"
          aria-label="Abrir emotes"
        >
          Emotes
        </button>

        <button
          type="button"
          data-action="settings"
          aria-label="Abrir ajustes"
        >
          Ajustes
        </button>
      </nav>
    `;

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

    this.chatButton.addEventListener(
      "click",
      () => {
        uiEvents.emit("chat:open", {});
      },
    );

    this.emotesButton.addEventListener(
      "click",
      () => {
        uiEvents.emit("emote-menu:open", {});
      },
    );

    this.settingsButton.addEventListener(
      "click",
      () => {
        uiEvents.emit("settings:open", {});
      },
    );
  }

  public setPlayerState(state: string): void {
    if (this.stateElement) {
      this.stateElement.textContent = state;
    }
  }
}
