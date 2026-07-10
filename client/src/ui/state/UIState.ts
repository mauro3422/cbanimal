export class UIState {
  public isChatOpen = false;
  public isEmoteMenuOpen = false;
  public isSettingsOpen = false;
  public isDebugEnabled = false;

  public get isAnyInputFocused(): boolean {
    return this.isChatOpen;
  }

  public get isAnyMenuOpen(): boolean {
    return this.isChatOpen
      || this.isEmoteMenuOpen
      || this.isSettingsOpen;
  }
}
