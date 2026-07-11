import type { Disposable } from "../../core/Disposable";
import { uiEvents } from "../core/UIEventBus";
import type { UIState } from "../state/UIState";

const EMOTES = [
  { id: "wave", label: "Saludar", icon: "👋" },
  { id: "laugh", label: "Reír", icon: "😂" },
  { id: "angry", label: "Enojarse", icon: "😠" },
  { id: "sleep", label: "Dormir", icon: "😴" },
];

export class EmoteMenu implements Disposable {
  public readonly element: HTMLDivElement;

  private readonly state: UIState;
  private readonly onVisibilityChange: () => void;

  constructor(state: UIState, onVisibilityChange: () => void) {
    this.state = state;
    this.onVisibilityChange = onVisibilityChange;

    this.element = document.createElement("div");
    this.element.className = "popup-menu";
    this.element.style.display = "none";

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

    this.element.innerHTML = `
      ${list}
      <div class="popup-menu__backdrop" data-menu-backdrop></div>
    `;

    this.element.addEventListener("click", this.handleClick);
  }

  public open(): void {
    this.element.style.display = "flex";
    this.state.isEmoteMenuOpen = true;
    this.onVisibilityChange();
  }

  public close(): void {
    this.element.style.display = "none";
    this.state.isEmoteMenuOpen = false;
    this.onVisibilityChange();
  }

  public toggle(): void {
    if (this.state.isEmoteMenuOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  public dispose(): void {
    this.element.removeEventListener("click", this.handleClick);
    this.element.remove();
  }

  private handleClick = (event: MouseEvent): void => {
    const target = event.target;

    if (!(target instanceof HTMLElement)) {
      return;
    }

    if (target.closest("[data-menu-backdrop]")) {
      this.close();
      return;
    }

    const button = target.closest<HTMLButtonElement>(
      "[data-emote-id]",
    );
    const emoteId = button?.dataset.emoteId;

    if (!emoteId) {
      return;
    }

    uiEvents.emit("emote:selected", { emoteId });
    this.close();
  };
}
