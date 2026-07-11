import type { Disposable } from "../../core/Disposable";
import { ChatBubble } from "../components/ChatBubble";
import { ChatPanel } from "../components/ChatPanel";
import { EmoteMenu } from "../components/EmoteMenu";
import { InteractionPrompt } from "../components/InteractionPrompt";
import { PlayerHUD } from "../components/PlayerHUD";
import { SettingsMenu } from "../components/SettingsMenu";
import { ToastNotification } from "../components/ToastNotification";
import { UIState } from "../state/UIState";
import { uiEvents } from "./UIEventBus";

export class UIManager implements Disposable {
  public readonly root: HTMLDivElement;
  public readonly state: UIState;

  public readonly hud: PlayerHUD;
  public readonly chatPanel: ChatPanel;
  public readonly emoteMenu: EmoteMenu;
  public readonly interactionPrompt: InteractionPrompt;
  public readonly settingsMenu: SettingsMenu;
  public readonly toast: ToastNotification;
  public readonly chatBubble: ChatBubble;

  private readonly unsubscribe: Array<() => void> = [];

  constructor(playerName: string) {
    this.state = new UIState();

    this.root = document.createElement("div");
    this.root.className = "game-ui";

    this.hud = new PlayerHUD(playerName);
    this.chatPanel = new ChatPanel(this.state, playerName);
    this.emoteMenu = new EmoteMenu(this.state, this.emitFocusState);
    this.interactionPrompt = new InteractionPrompt();
    this.settingsMenu = new SettingsMenu(this.state, this.emitFocusState);
    this.toast = new ToastNotification();
    this.chatBubble = new ChatBubble();

    this.root.append(
      this.hud.element,
      this.chatPanel.element,
      this.emoteMenu.element,
      this.settingsMenu.element,
      this.interactionPrompt.element,
      this.toast.element,
      this.chatBubble.element,
    );

    this.bindEvents();
    document.body.appendChild(this.root);
  }

  public dispose(): void {
    window.removeEventListener("keydown", this.handleGlobalKey);

    for (const unsubscribe of this.unsubscribe) {
      unsubscribe();
    }
    this.unsubscribe.length = 0;

    this.hud.dispose();
    this.chatPanel.dispose();
    this.emoteMenu.dispose();
    this.settingsMenu.dispose();
    this.toast.dispose();
    this.chatBubble.dispose();
    this.root.remove();
  }

  private bindEvents(): void {
    this.unsubscribe.push(
      uiEvents.on("chat:open", () => {
        this.chatPanel.toggle();
      }),
      uiEvents.on("emote-menu:open", () => {
        if (this.state.isSettingsOpen) {
          this.settingsMenu.close();
        }

        this.emoteMenu.toggle();
      }),
      uiEvents.on("settings:open", () => {
        if (this.state.isEmoteMenuOpen) {
          this.emoteMenu.close();
        }

        this.settingsMenu.toggle();
      }),
      uiEvents.on("chat:send", ({ message }) => {
        console.log(`[Chat] ${message}`);
      }),
      uiEvents.on("ui:focus-changed", ({ focused }) => {
        if (focused) {
          if (this.state.isEmoteMenuOpen) {
            this.emoteMenu.close();
          }

          if (this.state.isSettingsOpen) {
            this.settingsMenu.close();
          }
        }

        this.emitFocusState();
      }),
    );

    window.addEventListener("keydown", this.handleGlobalKey);
  }

  private emitFocusState = (): void => {
    uiEvents.emit("ui:blocking-changed", {
      blocked: this.state.isAnyMenuOpen,
    });
  };


  private handleGlobalKey = (event: KeyboardEvent): void => {
    if (this.state.isChatOpen) {
      if (event.code === "Escape") {
        this.chatPanel.close();
      }

      return;
    }

    if (this.state.isAnyMenuOpen) {
      if (event.code === "Escape") {
        this.emoteMenu.close();
        this.settingsMenu.close();
      }

      return;
    }

    if (event.code === "Enter") {
      event.preventDefault();
      this.chatPanel.open();
    }
  };
}
