type UIEventMap = {
  "chat:open": Record<string, never>;
  "chat:send": {
    message: string;
  };

  "emote-menu:open": Record<string, never>;
  "emote:selected": {
    emoteId: string;
  };

  "settings:open": Record<string, never>;
  "settings:toggle-debug": {
    enabled: boolean;
  };

  "ui:focus-changed": {
    focused: boolean;
  };
  "ui:blocking-changed": {
    blocked: boolean;
  };
};

type EventName = keyof UIEventMap;

type Listener<T extends EventName> = (
  payload: UIEventMap[T],
) => void;

export class UIEventBus {
  private readonly listeners = new Map<
    EventName,
    Set<(payload: unknown) => void>
  >();

  public on<T extends EventName>(
    eventName: T,
    listener: Listener<T>,
  ): () => void {
    const eventListeners =
      this.listeners.get(eventName) ?? new Set();

    eventListeners.add(
      listener as (payload: unknown) => void,
    );

    this.listeners.set(eventName, eventListeners);

    return () => {
      eventListeners.delete(
        listener as (payload: unknown) => void,
      );

      if (eventListeners.size === 0) {
        this.listeners.delete(eventName);
      }
    };
  }

  public emit<T extends EventName>(
    eventName: T,
    payload: UIEventMap[T],
  ): void {
    const eventListeners = this.listeners.get(eventName);

    if (!eventListeners) {
      return;
    }

    for (const listener of eventListeners) {
      listener(payload);
    }
  }
}

export const uiEvents = new UIEventBus();
