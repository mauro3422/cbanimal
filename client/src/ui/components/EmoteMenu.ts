import { uiEvents } from "../core/UIEventBus";
import type { UIState } from "../state/UIState";

const EMOTES = [
  { id: "wave", label: "Saludar", icon: "👋" },
  { id: "laugh", label: "Reír", icon: "😂" },
  { id: "angry", label: "Enojarse", icon: "😠" },
  { id: "sleep", label: "Dormir", icon: "😴" },
];

export class EmoteMenu {
  public readonly element: HTMLDivElement;

  private readonly state: UIState;

  constructor(state: UIState) {
    this.state = state;

    this.element = document.createElement("div");
    this.element.className = "popup-menu";
    this.element.style.display = "none";

    const backdrop = document.createElement("div");
    backdrop.className = "popup-menu__backdrop";
    backdrop.addEventListener("click", () => this.close());

    const list = EMOTES
      .map(
        (emote) => `
          <button
            type="button"
            data-emote-id="${emote.id}"
          >
            ${emote.icon} ${emote.label}
          </button>
        `,
      )
      .join("");

    this.element.innerHTML = list;
    this.element.appendChild(backdrop);

    this.element
      .querySelectorAll("[data-emote-id]")
      .forEach((button) => {
        button.addEventListener("click", () => {
          const emoteId =
            (button as HTMLElement).dataset.emoteId;

          if (emoteId) {
            uiEvents.emit("emote:selected", {
              emoteId,
            });

            this.close();
          }
        });
      });
  }

  public open(): void {
    this.element.style.display = "flex";
    this.state.isEmoteMenuOpen = true;
  }

  public close(): void {
    this.element.style.display = "none";
    this.state.isEmoteMenuOpen = false;
  }

  public toggle(): void {
    if (this.state.isEmoteMenuOpen) {
      this.close();
    } else {
      this.open();
    }
  }
}
