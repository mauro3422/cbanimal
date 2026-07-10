import * as THREE from "three";

export class ChatBubble {
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
    if (this.timer) {
      clearTimeout(this.timer);
    }

    this.element.textContent = text;
    this.element.style.display = "block";
    this.element.classList.remove("chat-bubble--fading");

    this.updatePosition(worldPosition, camera);

    this.timer = setTimeout(() => {
      this.element.classList.add("chat-bubble--fading");

      this.timer = setTimeout(() => {
        this.element.style.display = "none";
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

    if (screen.z > 1) {
      this.element.style.opacity = "0";
    } else {
      this.element.style.opacity = "1";
    }
  }
}
