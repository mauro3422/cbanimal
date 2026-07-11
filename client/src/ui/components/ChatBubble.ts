import * as THREE from "three";
import type { Disposable } from "../../core/Disposable";

export class ChatBubble implements Disposable {
  public readonly element: HTMLDivElement;

  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.element = document.createElement("div");
    this.element.className = "chat-bubble";
    this.element.style.display = "none";
  }

  public show(
    text: string,
    worldPosition: THREE.Vector3,
    camera: THREE.Camera,
  ): void {
    this.clearTimer();

    this.element.textContent = text;
    this.element.style.display = "block";
    this.element.classList.remove("chat-bubble--fading");

    this.updatePosition(worldPosition, camera);

    this.timer = setTimeout(() => {
      this.element.classList.add("chat-bubble--fading");

      this.timer = setTimeout(() => {
        this.element.style.display = "none";
        this.timer = null;
      }, 400);
    }, 4000);
  }

  public updatePosition(
    worldPosition: THREE.Vector3,
    camera: THREE.Camera,
  ): void {
    if (this.element.style.display === "none") {
      return;
    }

    const pos = worldPosition.clone();
    pos.y += 2.2;

    const screen = pos.project(camera);
    const x = (screen.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-screen.y * 0.5 + 0.5) * window.innerHeight;

    this.element.style.transform = `translate(-50%, -100%) translate(${x}px, ${y}px)`;
    this.element.style.opacity = screen.z > 1 ? "0" : "1";
  }

  public dispose(): void {
    this.clearTimer();
    this.element.remove();
  }

  private clearTimer(): void {
    if (!this.timer) {
      return;
    }

    clearTimeout(this.timer);
    this.timer = null;
  }
}
