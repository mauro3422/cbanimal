import type { CharacterModelConfig } from "../entities/CharacterModel";

export interface LocalPlayerConfig {
  displayName: string;
  creatureId: string;
  model: CharacterModelConfig | null;
}

const DEFAULT_PLAYER_MODEL_URL = "/models/chatgpt-fox-proxy-v2.glb";
const configuredModelUrl = import.meta.env.VITE_PLAYER_MODEL_URL?.trim();
const playerModelUrl = configuredModelUrl || DEFAULT_PLAYER_MODEL_URL;

export const localPlayerConfig = {
  displayName: "Mauro",
  creatureId: "chatgpt-fox",
  model: {
    url: playerModelUrl,
    scale: configuredModelUrl ? 1 : 0.32,
    rotationY: 0,
    yOffset: 0,
  },
} satisfies LocalPlayerConfig;
