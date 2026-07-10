import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import * as SkeletonUtils from "three/addons/utils/SkeletonUtils.js";

export interface ModelInstance {
  scene: THREE.Group;
  animations: THREE.AnimationClip[];
}

export class ModelRepository {
  private static readonly loader = new GLTFLoader();

  private static readonly cache = new Map<
    string,
    Promise<GLTF>
  >();

  private static loadSource(url: string): Promise<GLTF> {
    const cachedModel = this.cache.get(url);

    if (cachedModel) {
      return cachedModel;
    }

    const loadingPromise = this.loader.loadAsync(url);

    this.cache.set(url, loadingPromise);

    return loadingPromise.catch((error: unknown) => {
      this.cache.delete(url);

      throw error;
    });
  }

  public static async instantiate(
    url: string,
  ): Promise<ModelInstance> {
    const source = await this.loadSource(url);

    const scene = SkeletonUtils.clone(
      source.scene,
    ) as THREE.Group;

    return {
      scene,
      animations: source.animations,
    };
  }
}
