# CBAnimal — Next Chat Prompt

Pegá este mensaje en un chat nuevo dentro del Project **Juego**:

```text
Continuemos CBAnimal desde C:\dev\cbanimal.

Primero ejecutá project_context_load y leé AGENTS.md, .bridge/PROJECT_CONTEXT.md y .bridge/PROJECT_STATE.md. Cargá la guía character-concept-blender y verificá Git y el estado real de Blender antes de modificar archivos.

El primer loop del personaje ChatGPT Fox ya llegó a ready_for_blockout. Las cuatro vistas, manifiestos, referencias preparadas, escena Blender y capturas están en assets/concepts/chatgpt-fox/. Abrí assets/concepts/chatgpt-fox/blender/chatgpt_fox_references.blend y comenzá un blockout low-poly en una colección BLOCKOUT separada, preservando REFERENCES.

Trabajá primero la silueta con primitivas simples y Mirror: cabeza, torso, pelvis, brazos, piernas, orejas, hocico, patas y cola. Mantené pose A relajada y compatibilidad con rig humanoide. No avances a detalles, retopología o rig sin mostrar capturas frontal, lateral y tres cuartos del blockout para revisión.

Recordá que las imágenes actuales son proxies de transferencia válidos para blockout, pero deben reemplazarse por alta resolución antes de UV, texturas o modelado detallado. Actualizá PROJECT_STATE.md después del próximo milestone y verificá todo con tools antes de afirmar que quedó hecho.
```

## Contexto breve

- Repositorio: `C:\dev\cbanimal`
- Rama: `master`
- Personaje: zorro antropomórfico turquesa/cian y blanco, estilo low-poly amigable, marcas tecnomágicas.
- Estado del loop: `ready_for_blockout`
- Blender: 5.1.2
- Archivo de trabajo: `assets/concepts/chatgpt-fox/blender/chatgpt_fox_references.blend`
- Objetos de referencia: `REF_FRONT`, `REF_SIDE`, `REF_BACK`, `REF_THREE_QUARTER`
- Siguiente colección: `BLOCKOUT`
- Objetivo posterior: topología limpia → rig compartido → pesos → idle/walk/run/sit/wave/laugh/angry/sleep → GLB para Three.js.
