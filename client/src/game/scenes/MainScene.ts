import * as THREE from "three";
import type { Disposable } from "../../core/Disposable";
import type { UIManager } from "../../ui/core/UIManager";
import type { LocalPlayerConfig } from "../config/localPlayerConfig";
import { BasicInteractable } from "../entities/BasicInteractable";
import { ChairInteractable } from "../entities/ChairInteractable";
import type { IInteractable } from "../entities/IInteractable";
import { Player } from "../entities/Player";
import { InteractionSystem } from "../systems/InteractionSystem";

const MAP_SIZE = 20;
const MAP_HALF = MAP_SIZE / 2;
const MAP_LIMIT = MAP_HALF - 1;

const OBSTACLE_CFG = [
  {
    position: [4, 0.75, 3] as const,
    size: [1, 1.5, 1] as const,
    color: 0x577590,
  },
  {
    position: [-3, 0.5, -4] as const,
    size: [2, 1, 1] as const,
    color: 0x577590,
  },
  {
    position: [-5, 1, 5] as const,
    size: [1, 2, 2] as const,
    color: 0x577590,
  },
];

function disposeMaterial(
  material: THREE.Material | THREE.Material[],
): void {
  if (Array.isArray(material)) {
    for (const entry of material) {
      entry.dispose();
    }
    return;
  }

  material.dispose();
}

export class MainScene implements Disposable {
  public readonly player: Player;

  private readonly root = new THREE.Group();
  private readonly interactables: IInteractable[] = [];
  private readonly interactionSystem: InteractionSystem;
  private readonly debugHelper: THREE.Box3Helper;

  constructor(
    scene: THREE.Scene,
    camera: THREE.Camera,
    ui: UIManager,
    playerConfig: LocalPlayerConfig,
  ) {
    this.root.name = "MainScene";
    scene.add(this.root);
    scene.background = new THREE.Color(0xbde0fe);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
    this.root.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 2);
    directionalLight.position.set(8, 12, 8);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    directionalLight.shadow.camera.near = 0.5;
    directionalLight.shadow.camera.far = 50;
    directionalLight.shadow.camera.left = -15;
    directionalLight.shadow.camera.right = 15;
    directionalLight.shadow.camera.top = 15;
    directionalLight.shadow.camera.bottom = -15;
    this.root.add(directionalLight);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(MAP_SIZE, MAP_SIZE),
      new THREE.MeshStandardMaterial({
        color: 0x90be6d,
      }),
    );

    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.root.add(floor);

    const colliders: THREE.Box3[] = [];

    for (const cfg of OBSTACLE_CFG) {
      const [px, , pz] = cfg.position;
      const [width, height, depth] = cfg.size;

      const box = new THREE.Mesh(
        new THREE.BoxGeometry(width, height, depth),
        new THREE.MeshStandardMaterial({ color: cfg.color }),
      );

      box.position.set(px, height / 2, pz);
      box.castShadow = true;
      box.receiveShadow = true;
      this.root.add(box);

      colliders.push(new THREE.Box3().setFromObject(box));
    }

    this.buildTree(new THREE.Vector3(-7, 0, 6), colliders);
    this.buildPortal();

    this.player = new Player(
      camera,
      colliders,
      MAP_LIMIT,
      playerConfig.model,
    );
    this.root.add(this.player.object);

    this.debugHelper = new THREE.Box3Helper(
      this.player.getPlayerCollider(),
      0xff0000,
    );
    this.debugHelper.visible = ui.state.isDebugEnabled;
    this.root.add(this.debugHelper);

    this.buildChair(
      new THREE.Vector3(5, 0, -4),
      Math.PI / 4,
    );

    const interactiveBox = new BasicInteractable(
      new THREE.Vector3(3, 0, 2),
      "Interactuaste con la caja",
    );

    this.interactables.push(interactiveBox);
    this.root.add(interactiveBox.object);

    this.interactionSystem = new InteractionSystem(
      this.player,
      this.interactables,
      ui.interactionPrompt,
    );
  }

  public update(deltaTime: number): void {
    this.player.update(deltaTime);
    this.debugHelper.box.copy(this.player.getPlayerCollider());
    this.interactionSystem.update();
  }

  public getPlayerPosition(): THREE.Vector3 {
    return this.player.object.position;
  }

  public setInputEnabled(enabled: boolean): void {
    this.player.setInputEnabled(enabled);
    this.interactionSystem.setEnabled(enabled);
  }

  public toggleDebug(enabled: boolean): void {
    this.debugHelper.visible = enabled;
  }

  public dispose(): void {
    this.interactionSystem.dispose();
    this.player.dispose();

    this.debugHelper.removeFromParent();
    this.debugHelper.geometry.dispose();
    disposeMaterial(this.debugHelper.material);

    this.root.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) {
        return;
      }

      object.geometry.dispose();
      disposeMaterial(object.material);
    });

    this.root.clear();
    this.root.removeFromParent();
    this.interactables.length = 0;
  }

  private buildTree(
    position: THREE.Vector3,
    colliders: THREE.Box3[],
  ): void {
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.3, 0.4, 3, 8),
      new THREE.MeshStandardMaterial({ color: 0x8b5e3c }),
    );

    trunk.position.copy(position);
    trunk.position.y = 1.5;
    trunk.castShadow = true;
    trunk.receiveShadow = true;
    this.root.add(trunk);

    const crown = new THREE.Mesh(
      new THREE.SphereGeometry(1.2, 8, 6),
      new THREE.MeshStandardMaterial({ color: 0x2d6a4f }),
    );

    crown.position.copy(position);
    crown.position.y = 3.2;
    crown.castShadow = true;
    crown.receiveShadow = true;
    this.root.add(crown);

    colliders.push(
      new THREE.Box3().setFromObject(trunk),
      new THREE.Box3().setFromObject(crown),
    );
  }

  private buildPortal(): void {
    const portal = new THREE.Mesh(
      new THREE.RingGeometry(1, 1.3, 32),
      new THREE.MeshStandardMaterial({
        color: 0xffc300,
        side: THREE.DoubleSide,
        emissive: 0xffc300,
        emissiveIntensity: 0.4,
      }),
    );

    portal.rotation.x = -Math.PI / 2;
    portal.position.set(7, 0.01, 7);
    this.root.add(portal);

    const inner = new THREE.Mesh(
      new THREE.CircleGeometry(1, 32),
      new THREE.MeshStandardMaterial({
        color: 0x003049,
        side: THREE.DoubleSide,
      }),
    );

    inner.rotation.x = -Math.PI / 2;
    inner.position.set(7, 0.005, 7);
    this.root.add(inner);
  }

  private buildChair(
    position: THREE.Vector3,
    rotation: number,
  ): void {
    const chair = new ChairInteractable(position, rotation);
    this.interactables.push(chair);
    this.root.add(chair.object);
  }
}
