import * as THREE from "three";
import { MainScene } from "../scenes/MainScene";
import { UIManager } from "../../ui/core/UIManager";
import { uiEvents } from "../../ui/core/UIEventBus";
import { CharacterState } from "../entities/CharacterState";

const EMOJI_MAP: Record<string, string> = {
  wave: "👋",
  laugh: "😂",
  angry: "😠",
  sleep: "😴",
};

export class Game {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene: THREE.Scene;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly mainScene: MainScene;
  private readonly ui: UIManager;
  private readonly clock = new THREE.Clock();

  private readonly cameraOffset = new THREE.Vector3(8, 8, 8);
  private readonly cameraTargetPosition = new THREE.Vector3();

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

    this.ui = new UIManager("Mauro");

    this.mainScene = new MainScene(this.scene, this.camera, this.ui);

    this.bindUIEvents();

    window.addEventListener("resize", this.handleResize);

    this.renderer.domElement.addEventListener("click", this.handleClick);
  }

  private bindUIEvents(): void {
    uiEvents.on("chat:send", ({ message }) => {
      this.ui.chatBubble.show(
        message,
        this.mainScene.getPlayerPosition(),
        this.camera,
      );
    });

    uiEvents.on("emote:selected", ({ emoteId }) => {
      this.mainScene.player.playEmote(emoteId);

      const icon = EMOJI_MAP[emoteId] ?? "✨";
      this.ui.toast.show(`${icon} Emote: ${emoteId}`);
    });

    uiEvents.on("ui:focus-changed", ({ focused }) => {
      this.mainScene.player.setInputEnabled(!focused);
    });

    uiEvents.on("settings:toggle-debug", ({ enabled }) => {
      this.mainScene.toggleDebug(enabled);
    });
  }

  public start(): void {
    this.animate();
  }

  private animate = (): void => {
    requestAnimationFrame(this.animate);

    const deltaTime = this.clock.getDelta();

    this.mainScene.update(deltaTime);

    const playerPosition = this.mainScene.getPlayerPosition();

    this.cameraTargetPosition
      .copy(playerPosition)
      .add(this.cameraOffset);

    this.camera.position.lerp(
      this.cameraTargetPosition,
      0.08,
    );

    this.camera.lookAt(playerPosition);

    this.updateHUD();
    this.updateNameplate(playerPosition);
    this.updateBubblePosition(playerPosition);

    this.renderer.render(this.scene, this.camera);
  };

  private updateHUD(): void {
    const state = this.mainScene.player.getState();
    const labels: Record<string, string> = {
      [CharacterState.Idle]: "Idle",
      [CharacterState.Walking]: "Walk",
      [CharacterState.Sitting]: "Sit",
      [CharacterState.Waving]: "Wave",
    };

    this.ui.hud.setPlayerState(labels[state] ?? state);
  }

  private handleResize = (): void => {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(window.innerWidth, window.innerHeight);
  };

  private handleClick = (event: MouseEvent): void => {
    if (this.ui.state.isAnyMenuOpen) {
      return;
    }

    const mouse = new THREE.Vector2();

    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, this.camera);

    const floorPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    const intersection = new THREE.Vector3();

    raycaster.ray.intersectPlane(floorPlane, intersection);

    if (intersection) {
      this.mainScene.player.setMoveTarget(intersection);
    }
  };

  private updateNameplate(playerPosition: THREE.Vector3): void {
    const nameplate = document.querySelector<HTMLDivElement>("#nameplate");

    if (!nameplate) {
      return;
    }

    const worldPosition = playerPosition.clone();
    worldPosition.y += 2.2;

    const screenPosition = worldPosition.project(this.camera);

    const x = (screenPosition.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-screenPosition.y * 0.5 + 0.5) * window.innerHeight;

    const behindCamera = screenPosition.z > 1;

    nameplate.style.display = behindCamera ? "none" : "block";
    nameplate.style.transform = `translate(-50%, -100%) translate(${x}px, ${y}px)`;
  }

  private updateBubblePosition(playerPosition: THREE.Vector3): void {
    this.ui.chatBubble.updatePosition(playerPosition, this.camera);
  }
}
