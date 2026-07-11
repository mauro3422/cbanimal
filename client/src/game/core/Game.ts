import * as THREE from "three";
import type { Disposable } from "../../core/Disposable";
import { UIManager } from "../../ui/core/UIManager";
import { uiEvents } from "../../ui/core/UIEventBus";
import { localPlayerConfig } from "../config/localPlayerConfig";
import { MovementState } from "../entities/MovementState";
import { MainScene } from "../scenes/MainScene";

const EMOJI_MAP: Record<string, string> = {
  wave: "👋",
  laugh: "😂",
  angry: "😠",
  sleep: "😴",
};

const MOVEMENT_LABELS: Record<string, string> = {
  [MovementState.Idle]: "Idle",
  [MovementState.Walking]: "Walk",
  [MovementState.Sitting]: "Sit",
};

const EMOTE_LABELS: Record<string, string> = {
  wave: "Wave",
  laugh: "Laugh",
  angry: "Angry",
  sleep: "Sleep",
};

export class Game implements Disposable {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene: THREE.Scene;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly mainScene: MainScene;
  private readonly ui: UIManager;
  private readonly clock = new THREE.Clock(false);
  private readonly unsubscribe: Array<() => void> = [];

  private readonly cameraOffset = new THREE.Vector3(8, 8, 8);
  private readonly cameraTargetPosition = new THREE.Vector3();

  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();
  private readonly floorPlane = new THREE.Plane(
    new THREE.Vector3(0, 1, 0),
    0,
  );
  private readonly floorIntersection = new THREE.Vector3();

  private readonly nameplate: HTMLDivElement | null;

  private animationFrameId: number | null = null;
  private running = false;
  private disposed = false;

  constructor(container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
    });

    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();

    this.camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      0.1,
      1000,
    );
    this.camera.position.set(8, 8, 8);
    this.camera.lookAt(0, 0, 0);

    this.ui = new UIManager(localPlayerConfig.displayName);
    this.mainScene = new MainScene(
      this.scene,
      this.camera,
      this.ui,
      localPlayerConfig,
    );

    this.nameplate = document.querySelector<HTMLDivElement>("#nameplate");
    if (this.nameplate) {
      this.nameplate.textContent = localPlayerConfig.displayName;
    }

    this.bindUIEvents();
    window.addEventListener("resize", this.handleResize);
    this.renderer.domElement.addEventListener("click", this.handleClick);
  }

  public start(): void {
    if (this.running || this.disposed) {
      return;
    }

    this.running = true;
    this.clock.start();
    this.animate();
  }

  public dispose(): void {
    if (this.disposed) {
      return;
    }

    this.disposed = true;
    this.running = false;
    this.clock.stop();

    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }

    window.removeEventListener("resize", this.handleResize);
    this.renderer.domElement.removeEventListener("click", this.handleClick);

    for (const unsubscribe of this.unsubscribe) {
      unsubscribe();
    }
    this.unsubscribe.length = 0;

    this.mainScene.dispose();
    this.ui.dispose();
    this.scene.clear();

    this.renderer.renderLists.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  private bindUIEvents(): void {
    this.unsubscribe.push(
      uiEvents.on("chat:send", ({ message }) => {
        this.ui.chatBubble.show(
          message,
          this.mainScene.getPlayerPosition(),
          this.camera,
        );
      }),
      uiEvents.on("emote:selected", ({ emoteId }) => {
        this.mainScene.player.playEmote(emoteId);

        const icon = EMOJI_MAP[emoteId] ?? "✨";
        this.ui.toast.show(`${icon} Emote: ${emoteId}`);
      }),
      uiEvents.on("ui:blocking-changed", ({ blocked }) => {
        this.mainScene.setInputEnabled(!blocked);
      }),
      uiEvents.on("settings:toggle-debug", ({ enabled }) => {
        this.mainScene.toggleDebug(enabled);
      }),
    );
  }

  private animate = (): void => {
    if (!this.running) {
      return;
    }

    this.animationFrameId = requestAnimationFrame(this.animate);

    const deltaTime = Math.min(this.clock.getDelta(), 0.1);
    this.mainScene.update(deltaTime);

    const playerPosition = this.mainScene.getPlayerPosition();

    this.cameraTargetPosition
      .copy(playerPosition)
      .add(this.cameraOffset);

    const cameraDamping = 1 - Math.exp(-7 * deltaTime);
    this.camera.position.lerp(
      this.cameraTargetPosition,
      cameraDamping,
    );
    this.camera.lookAt(playerPosition);

    this.updateHUD();
    this.updateNameplate(playerPosition);
    this.ui.chatBubble.updatePosition(playerPosition, this.camera);

    this.renderer.render(this.scene, this.camera);
  };

  private updateHUD(): void {
    const activeEmote = this.mainScene.player.getActiveEmote();

    if (activeEmote) {
      this.ui.hud.setPlayerState(
        EMOTE_LABELS[activeEmote] ?? activeEmote,
      );
      return;
    }

    const movementState = this.mainScene.player.getMovementState();
    this.ui.hud.setPlayerState(
      MOVEMENT_LABELS[movementState] ?? movementState,
    );
  }

  private handleResize = (): void => {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  };

  private handleClick = (event: MouseEvent): void => {
    if (this.ui.state.isAnyMenuOpen || !this.running) {
      return;
    }

    const bounds = this.renderer.domElement.getBoundingClientRect();

    this.pointer.x = (
      ((event.clientX - bounds.left) / bounds.width) * 2
    ) - 1;
    this.pointer.y = -(
      ((event.clientY - bounds.top) / bounds.height) * 2
    ) + 1;

    this.raycaster.setFromCamera(this.pointer, this.camera);

    const intersection = this.raycaster.ray.intersectPlane(
      this.floorPlane,
      this.floorIntersection,
    );

    if (!intersection) {
      return;
    }

    this.mainScene.player.setMoveTarget(intersection);
  };

  private updateNameplate(playerPosition: THREE.Vector3): void {
    if (!this.nameplate) {
      return;
    }

    const worldPosition = playerPosition.clone();
    worldPosition.y += 2.2;

    const screenPosition = worldPosition.project(this.camera);
    const x = (screenPosition.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-screenPosition.y * 0.5 + 0.5) * window.innerHeight;
    const behindCamera = screenPosition.z > 1;

    this.nameplate.style.display = behindCamera ? "none" : "block";
    this.nameplate.style.transform =
      `translate(-50%, -100%) translate(${x}px, ${y}px)`;
  }
}
