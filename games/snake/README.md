Arcade Snake

Open index.html in any modern browser (no server required).

Controls
- Keyboard: Arrow keys or WASD to change direction.
- Space: Pause / resume.
- R: Restart.
- On-screen: Directional buttons and Start / Pause / Restart buttons for touch.

Behavior
- The snake starts facing right in the center.
- Eat food to grow and increase score; speed increases gradually and is capped.
- Food spawns only on free cells. If the board fills, you win.
- The best score is saved locally when available; storage errors are handled silently.
- Rapid multiple direction inputs are queued but reversals are prevented.
- Game pauses on tab blur; page scrolling is prevented while interacting with the game area.

Developer API
- game.js exports SnakeGame class. It exposes:
  - reset(): reset the game to ready state
  - setDirection(direction): queue a direction string ('up','down','left','right')
  - step(): perform a single game step
  - animate(dt): advance animation by dt seconds; returns true if state changed
  - fields: snake (array of {x,y} head first), food, score, status, direction

Notes
No external libraries or assets used. Opening index.html directly will run the game.

Tests
Run `node --test game.test.cjs` from this directory to check the game engine.
