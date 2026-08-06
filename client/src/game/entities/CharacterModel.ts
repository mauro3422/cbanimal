import * as THREE from "three";
import type { Disposable } from "../../core/Disposable";
import { ModelRepository } from "../assets/ModelRepository";
import type { MovementState } from "./MovementState";

const LOOPING_ANIMATIONS = new Set(["idle", "walking"]);
// Calibrated against the exported GLB at scale 0.32, not Blender frame time.
const WALK_REFERENCE_SPEED = 1.385;

export type WalkingSupportFoot = "left" | "right";

export interface CharacterModelConfig {
  url: string;
  scale?: number;
  rotationY?: number;
  yOffset?: number;
}

export class CharacterModel implements Disposable {
  public readonly object = new THREE.Group();

  private readonly placeholderParts: THREE.Mesh[] = [];
  private placeholderDisposed = false;

  private mixer: THREE.AnimationMixer | null = null;
  private modelRoot: THREE.Group | null = null;
  private leftFoot: THREE.Object3D | null = null;
  private rightFoot: THREE.Object3D | null = null;

  private readonly actions = new Map<
    string,
    THREE.AnimationAction
  >();

  private currentAction: THREE.AnimationAction | null = null;
  private currentAnimationName: string | null = null;
  private walkingTimeScale = 1;
  private loaded = false;
  private disposed = false;

  constructor() {
    const body = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.5, 0.8, 8, 16),
      new THREE.MeshStandardMaterial({
        color: 0xf28482,
      }),
    );

    body.position.y = 0.9;
    body.castShadow = true;
    body.receiveShadow = true;

    const nose = new THREE.Mesh(
      new THREE.ConeGeometry(0.15, 0.5, 8),
      new THREE.MeshStandardMaterial({
        color: 0x222222,
      }),
    );

    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, 1, 0.65);
    nose.castShadow = true;

    this.placeholderParts.push(body, nose);
    this.object.add(body, nose);
  }

  public async load(
    config: CharacterModelConfig,
  ): Promise<void> {
    if (this.disposed) {
      return;
    }

    try {
      const modelInstance =
        await ModelRepository.instantiate(config.url);

      if (this.disposed) {
        return;
      }

      const model = modelInstance.scene;

      model.scale.setScalar(config.scale ?? 1);
      model.rotation.y = config.rotationY ?? 0;
      model.position.y = config.yOffset ?? 0;

      model.traverse((child) => {
        if (!(child instanceof THREE.Mesh)) {
          return;
        }

        child.castShadow = true;
        child.receiveShadow = true;
      });

      this.disposePlaceholder();
      this.object.clear();
      this.object.add(model);

      this.modelRoot = model;
      this.leftFoot = model.getObjectByName("MDL_FOOT_L") ?? null;
      this.rightFoot = model.getObjectByName("MDL_FOOT_R") ?? null;
      this.mixer = new THREE.AnimationMixer(model);

      for (const clip of modelInstance.animations) {
        const normalizedName = clip.name.trim().toLowerCase();
        const action = this.mixer.clipAction(clip);

        this.configureAction(normalizedName, action);
        this.actions.set(normalizedName, action);
      }

      this.loaded = true;

      console.log(
        "Animaciones encontradas:",
        modelInstance.animations.map((clip) => clip.name),
      );

      this.play("idle", 0);
    } catch (error: unknown) {
      console.error(
        `No se pudo cargar el modelo ${config.url}`,
        error,
      );
    }
  }

  public update(deltaTime: number): void {
    this.mixer?.update(deltaTime);
  }

  public setWalkingSpeed(unitsPerSecond: number): void {
    this.walkingTimeScale = Math.max(0.1, unitsPerSecond / WALK_REFERENCE_SPEED);
    this.actions.get("walking")?.setEffectiveTimeScale(this.walkingTimeScale);
  }

  public getWalkingSupportFootWorldPosition(
    target: THREE.Vector3,
  ): WalkingSupportFoot | null {
    if (
      this.currentAnimationName !== "walking"
      || !this.currentAction
      || !this.leftFoot
      || !this.rightFoot
    ) {
      return null;
    }

    const duration = this.currentAction.getClip().duration;
    if (duration <= 0) {
      return null;
    }

    const wrappedTime = ((this.currentAction.time % duration) + duration) % duration;
    const normalizedPhase = wrappedTime / duration;
    const supportFoot: WalkingSupportFoot = normalizedPhase < 0.5 ? "left" : "right";
    const footObject = supportFoot === "left" ? this.leftFoot : this.rightFoot;

    this.object.updateWorldMatrix(true, true);
    footObject.getWorldPosition(target);
    return supportFoot;
  }

  public play(
    animationName: string,
    fadeDuration = 0.2,
  ): boolean {
    if (!this.loaded) {
      return false;
    }

    const normalizedName = animationName
      .trim()
      .toLowerCase();

    if (normalizedName === this.currentAnimationName) {
      return true;
    }

    const nextAction = this.actions.get(normalizedName);

    if (!nextAction) {
      if (import.meta.env.DEV) {
        console.warn(`Animación no encontrada: ${normalizedName}`, {
          available: [...this.actions.keys()],
        });
      }

      return false;
    }

    nextAction.reset();
    nextAction.enabled = true;
    nextAction.setEffectiveTimeScale(
      normalizedName === "walking" ? this.walkingTimeScale : 1,
    );
    nextAction.setEffectiveWeight(1);

    if (fadeDuration <= 0 || !this.currentAction) {
      this.currentAction?.stop();
      nextAction.play();
    } else {
      this.currentAction.fadeOut(fadeDuration);
      nextAction.fadeIn(fadeDuration).play();
    }

    this.currentAction = nextAction;
    this.currentAnimationName = normalizedName;

    if (import.meta.env.DEV) {
      console.debug("Animación activa:", normalizedName);
    }

    return true;
  }

  public setMovementState(
    state: MovementState,
    fadeDuration = 0.2,
  ): boolean {
    return this.play(state, fadeDuration);
  }

  public hasAnimation(animationName: string): boolean {
    return this.actions.has(
      animationName.trim().toLowerCase(),
    );
  }

  public get isLoaded(): boolean {
    return this.loaded;
  }

  public dispose(): void {
    this.disposed = true;
    this.mixer?.stopAllAction();

    if (this.mixer && this.modelRoot) {
      this.mixer.uncacheRoot(this.modelRoot);
    }

    this.disposePlaceholder();
    this.actions.clear();
    this.currentAction = null;
    this.currentAnimationName = null;
    this.mixer = null;
    this.modelRoot = null;
    this.loaded = false;
    this.object.clear();
  }

  private configureAction(
    animationName: string,
    action: THREE.AnimationAction,
  ): void {
    if (LOOPING_ANIMATIONS.has(animationName)) {
      action.setLoop(THREE.LoopRepeat, Infinity);
      action.clampWhenFinished = false;
      return;
    }

    action.setLoop(THREE.LoopOnce, 1);
    action.clampWhenFinished = true;
  }

  private disposePlaceholder(): void {
    if (this.placeholderDisposed) {
      return;
    }

    for (const mesh of this.placeholderParts) {
      mesh.geometry.dispose();

      if (Array.isArray(mesh.material)) {
        for (const material of mesh.material) {
          material.dispose();
        }
      } else {
        mesh.material.dispose();
      }
    }

    this.placeholderDisposed = true;
  }
}
