import type { Disposable } from "../../core/Disposable";
import { uiEvents } from "../core/UIEventBus";
import type { UIState } from "../state/UIState";

export class SettingsMenu implements Disposable {
  public readonly element: HTMLDivElement;

  private readonly debugCheckbox: HTMLInputElement;
  private readonly state: UIState;
  private readonly onVisibilityChange: () => void;

  constructor(state: UIState, onVisibilityChange: () => void) {
    this.state = state;
    this.onVisibilityChange = onVisibilityChange;

    this.element = document.createElement("div");
    this.element.className = "popup-menu";
    this.element.style.display = "none";
    this.element.innerHTML = `
      <label class="settings-label">
        <span>Collider debug</span>
        <input type="checkbox" />
      </label>
      <div class="popup-menu__backdrop" data-menu-backdrop></div>
    `;

    this.debugCheckbox = this.element.querySelector("input")!;
    this.debugCheckbox.addEventListener("change", this.handleDebugChange);
    this.element.addEventListener("click", this.handleClick);
  }

  public open(): void {
    this.element.style.display = "flex";
    this.state.isSettingsOpen = true;
    this.debugCheckbox.checked = this.state.isDebugEnabled;
    this.onVisibilityChange();
  }

  public close(): void {
    this.element.style.display = "none";
    this.state.isSettingsOpen = false;
    this.onVisibilityChange();
  }

  public toggle(): void {
    if (this.state.isSettingsOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  public dispose(): void {
    this.debugCheckbox.removeEventListener("change", this.handleDebugChange);
    this.element.removeEventListener("click", this.handleClick);
    this.element.remove();
  }

  private handleDebugChange = (): void => {
    this.state.isDebugEnabled = this.debugCheckbox.checked;
    uiEvents.emit("settings:toggle-debug", {
      enabled: this.debugCheckbox.checked,
    });
  };

  private handleClick = (event: MouseEvent): void => {
    const target = event.target;

    if (
      target instanceof HTMLElement
      && target.closest("[data-menu-backdrop]")
    ) {
      this.close();
    }
  };
}
