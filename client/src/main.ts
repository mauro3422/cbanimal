import "./styles/main.css";
import "./ui/styles/tokens.css";
import "./ui/styles/base.css";
import "./ui/styles/hud.css";
import "./ui/styles/chat.css";
import "./ui/styles/menus.css";
import { Game } from "./game/core/Game";

const container = document.querySelector<HTMLDivElement>("#app");

if (!container) {
  throw new Error("No se encontró el contenedor #app");
}

const game = new Game(container);
game.start();

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    game.dispose();
  });
}
