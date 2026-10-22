const test = require('node:test');
const assert = require('node:assert/strict');
const SnakeGame = require('./game.js');

test('moves, eats food, grows and scores', () => {
  const game = new SnakeGame();
  const head = game.snake[0];
  game.food = {x: head.x + 1, y: head.y};
  const length = game.snake.length;
  game.resume();
  game.step();
  assert.equal(game.score, 1);
  assert.equal(game.snake.length, length + 1);
  assert.ok(!game.snake.some(p => p.x === game.food.x && p.y === game.food.y));
});

test('cannot reverse even after rapid direction inputs', () => {
  const game = new SnakeGame();
  game.food = {x: 0, y: 0};
  game.resume();
  game.setDirection('left');
  game.step();
  assert.equal(game.direction, 'right');
  game.setDirection('up');
  game.setDirection('left');
  game.step();
  assert.equal(game.direction, 'up');
  game.step();
  assert.equal(game.direction, 'left');
});

test('moving into the vacating tail cell is legal', () => {
  const game = new SnakeGame();
  game.snake = [{x:1,y:1},{x:1,y:2},{x:0,y:2},{x:0,y:1}];
  game.direction = game.nextDirection = 'left';
  game.food = {x:5,y:5};
  game.resume();
  game.step();
  assert.equal(game.status, 'playing');
  assert.deepEqual(game.snake[0], {x:0,y:1});
});

test('wall and body collisions end the game', () => {
  const wall = new SnakeGame();
  wall.snake = [{x:19,y:5},{x:18,y:5},{x:17,y:5}];
  wall.resume();
  wall.step();
  assert.equal(wall.status, 'over');
  const body = new SnakeGame();
  body.snake = [{x:2,y:2},{x:2,y:3},{x:1,y:3},{x:1,y:2},{x:1,y:1},{x:2,y:1}];
  body.direction = body.nextDirection = 'left';
  body.food = {x:5,y:5};
  body.resume();
  body.step();
  assert.equal(body.status, 'over');
});

test('paused game does not advance and resume preserves score', () => {
  const game = new SnakeGame();
  game.resume();
  game.score = 3;
  game.pause();
  const before = JSON.stringify(game.snake);
  game.step();
  game.animate(10);
  assert.equal(JSON.stringify(game.snake), before);
  assert.equal(game.status, 'paused');
  game.resume();
  assert.equal(game.score, 3);
});

test('restart resets score, speed and pending turns', () => {
  const game = new SnakeGame({speed:4});
  game.food = {x:game.snake[0].x + 1,y:game.snake[0].y};
  game.resume();
  game.step();
  assert.ok(game.speed > 4);
  game.setDirection('up');
  game.reset();
  assert.equal(game.speed, 4);
  assert.equal(game.score, 0);
  assert.equal(game.status, 'ready');
  game.resume();
  game.food = {x:0,y:0};
  game.step();
  assert.equal(game.direction, 'right');
});

test('full board wins without attempting to spawn more food', () => {
  const game = new SnakeGame({cols:3,rows:3,initialLen:1});
  game.snake = [{x:1,y:0},{x:0,y:0},{x:0,y:1},{x:1,y:1},
    {x:2,y:1},{x:2,y:2},{x:1,y:2},{x:0,y:2}];
  game.food = {x:2,y:0};
  game.resume();
  game.step();
  assert.equal(game.status, 'won');
  assert.equal(game.snake.length, 9);
  assert.equal(game.food, null);
});

test('resume cannot resurrect a terminal game', () => {
  const game = new SnakeGame();
  game.status = 'over';
  const before = JSON.stringify(game.snake);
  game.resume();
  game.start();
  game.step();
  assert.equal(game.status, 'over');
  assert.equal(JSON.stringify(game.snake), before);
});
