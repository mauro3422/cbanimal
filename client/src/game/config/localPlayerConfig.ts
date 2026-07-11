import type { CharacterModelConfig } from "../entities/CharacterModel";

export interface LocalPlayerConfig {
  displayName: string;
  creatureId: string;
  model: CharacterModelConfig | null;
}

const configuredModelUrl = import.meta.env.VITE_PLAYER_MODEL_URL?.trim();

export const localPlayerConfig = {
  displayName: "Mauro",
  creatureId: "axolotl",
  model: configuredModelUrl
    ? {
        url: configuredModelUrl,
        scale: 1,
        rotationY: 0,
        yOffset: 0,
      }
    : null,
} satisfies LocalPlayerConfig;
