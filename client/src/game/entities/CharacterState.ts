export const CharacterState = {
  Idle: "idle",
  Walking: "walk",
  Sitting: "sit",
  Waving: "wave",
} as const;

export type CharacterState = (typeof CharacterState)[keyof typeof CharacterState];
