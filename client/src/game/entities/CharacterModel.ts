import * as THREE from "three";
import { ModelRepository } from "../assets/ModelRepository";
import { CharacterState } from "./CharacterState";

export interface CharacterModelConfig {
  url: string;
  scale?: number;
  rotationY?: number;
  yOffset?: number;
}

export class CharacterModel {
  public readonly object = new THREE.Group();

  private readonly placeholder: THREE.Mesh;

  private mixer: THREE.AnimationMixer | null = null;

  private readonly actions = new Map<
    string,
    THREE.AnimationAction
  >();

  private currentAction: THREE.AnimationAction | null = null;
  private currentAnimationName: string | null = null;

  private loaded = false;

  constructor() {
    this.placeholder = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.5, 0.8, 8, 16),
      new THREE.MeshStandardMaterial({
        color: 0xf28482,
      }),
    );

    this.placeholder.position.y = 0.9;
    this.placeholder.castShadow = true;
    this.placeholder.receiveShadow = true;

    this.object.add(this.placeholder);

    const nose = new THREE.Mesh(
      new THREE.ConeGeometry(0.15, 0.5, 8),
      new THREE.MeshStandardMaterial({
        color: 0x222222,
      }),
    );

    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, 1, 0.65);
    nose.castShadow = true;

    this.object.add(nose);
  }

  public async load(
    config: CharacterModelConfig,
  ): Promise<void> {
    try {
      const modelInstance =
        await ModelRepository.instantiate(config.url);

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

      this.object.clear();
      this.object.add(model);

      this.mixer = new THREE.AnimationMixer(model);

      for (const clip of modelInstance.animations) {
        const normalizedName = clip.name
          .trim()
          .toLowerCase();

        const action = this.mixer.clipAction(clip);

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

  public play(
    animationName: string,
    fadeDuration = 0.2,
  ): void {
    if (!this.loaded) {
      return;
    }

    const normalizedName = animationName
      .trim()
      .toLowerCase();

    if (normalizedName === this.currentAnimationName) {
      return;
    }

    const nextAction = this.actions.get(normalizedName);

    if (!nextAction) {
      return;
    }

    nextAction.reset();
    nextAction.enabled = true;
    nextAction.setEffectiveTimeScale(1);
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
  }

  public setState(
    state: CharacterState,
    fadeDuration = 0.2,
  ): void {
    this.play(state, fadeDuration);
  }

  public hasAnimation(animationName: string): boolean {
    return this.actions.has(
      animationName.trim().toLowerCase(),
    );
  }
}
