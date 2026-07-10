import { UIState } from "../state/UIState";
import { uiEvents } from "./UIEventBus";

import { PlayerHUD } from "../components/PlayerHUD";
import { ChatPanel } from "../components/ChatPanel";
import { EmoteMenu } from "../components/EmoteMenu";
import { InteractionPrompt } from "../components/InteractionPrompt";
import { SettingsMenu } from "../components/SettingsMenu";
import { ToastNotification } from "../components/ToastNotification";
import { ChatBubble } from "../components/ChatBubble";

export class UIManager {
  public readonly root: HTMLDivElement;
  public readonly state: UIState;

  public readonly hud: PlayerHUD;
  public readonly chatPanel: ChatPanel;
  public readonly emoteMenu: EmoteMenu;
  public readonly interactionPrompt: InteractionPrompt;
  public readonly settingsMenu: SettingsMenu;
  public readonly toast: ToastNotification;
  public readonly chatBubble: ChatBubble;

  constructor(playerName: string) {
    this.state = new UIState();

    this.root = document.createElement("div");
    this.root.className = "game-ui";

    this.hud = new PlayerHUD(playerName);
    this.chatPanel = new ChatPanel(this.state, playerName);
    this.emoteMenu = new EmoteMenu(this.state);
    this.interactionPrompt = new InteractionPrompt();
    this.settingsMenu = new SettingsMenu(this.state);
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

  private bindEvents(): void {
    uiEvents.on("chat:open", () => {
      this.chatPanel.toggle();
    });

    uiEvents.on("emote-menu:open", () => {
      this.emoteMenu.toggle();

      if (this.state.isSettingsOpen) {
        this.settingsMenu.close();
      }
    });

    uiEvents.on("settings:open", () => {
      this.settingsMenu.toggle();

      if (this.state.isEmoteMenuOpen) {
        this.emoteMenu.close();
      }
    });

    uiEvents.on("chat:send", ({ message }) => {
      // el ChatPanel ya agrega el mensaje, acá solo logueamos
      console.log(`[Chat] ${message}`);
    });

    uiEvents.on("ui:focus-changed", ({ focused }) => {
      if (!focused) {
        return;
      }

      if (this.state.isEmoteMenuOpen) {
        this.emoteMenu.close();
      }

      if (this.state.isSettingsOpen) {
        this.settingsMenu.close();
      }
    });

    window.addEventListener("keydown", this.handleGlobalKey);
  }

  private handleGlobalKey = (
    event: KeyboardEvent,
  ): void => {
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
