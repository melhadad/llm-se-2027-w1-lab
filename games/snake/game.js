/* Arcade Snake - pure engine + DOM glue guarded for Node
   Exposes SnakeGame class with reset(), setDirection(dir), step(), animate(dt) and fields.
*/
(function(){
  // Utility
  function randInt(n){ return Math.floor(Math.random()*n); }

  class SnakeGame {
    constructor(opts={}){
      this.cols = opts.cols || 20;
      this.rows = opts.rows || 20;
      this.initialLen = opts.initialLen || 3;
      this.maxSpeed = opts.maxSpeed || 12; // steps per second
      this.speed = opts.speed || 4; // initial steps per second
      // remember the configured initial speed so reset restores it
      this._initialSpeed = this.speed;
      this.speedInc = opts.speedInc || 0.25; // per food
      this.reset();
      // storage
      this.best = 0; try{ const b = localStorage.getItem('snake_best'); if (b) this.best = Number(b)||0; }catch(e){}
      this._acc = 0; // accumulator seconds
      this._turnQueue = [];
    }

    reset(){
      // center start, facing right
      const midX = Math.floor(this.cols/2);
      const midY = Math.floor(this.rows/2);
      this.snake = [];
      for(let i=0;i<this.initialLen;i++) this.snake.push({x:midX - i, y:midY});
      this.direction = 'right';
      this.nextDirection = 'right';
      this.status = 'ready';
      this.score = 0;
      // restore configured initial speed
      this.speed = Math.max(1, this._initialSpeed || 4);
      this.food = null;
      this._acc = 0;
      this._turnQueue = [];
      this.placeFood();
    }

    placeFood(){
      // spawn in free cell
      const free = [];
      const occupied = new Set(this.snake.map(p=>p.x+','+p.y));
      for(let x=0;x<this.cols;x++) for(let y=0;y<this.rows;y++) if(!occupied.has(x+','+y)) free.push({x,y});
      if (free.length===0){ this.food = null; this.status='won'; this._saveBest(); return; }
      this.food = free[randInt(free.length)];
    }

    _saveBest(){
      try{ if (this.score > (this.best||0)){ this.best = this.score; localStorage.setItem('snake_best', String(this.best)); }}catch(e){ /* ignore storage errors */ }
    }

    setDirection(dir){
      if (!['up','down','left','right'].includes(dir)) return;
      // prevent immediate reversal
      const opposites = {up:'down',down:'up',left:'right',right:'left'};
      const lastDir = this._turnQueue.length? this._turnQueue[this._turnQueue.length-1] : this.nextDirection || this.direction;
      if (opposites[lastDir] === dir) return; // ignore reversal
      // queue turn; limit to prevent many queued in one tick
      if (this._turnQueue.length < 3) this._turnQueue.push(dir);
    }

    start(){
      // only start from ready state; do not resurrect terminal games
      if (this.status === 'ready'){
        this.status='playing'; this._acc=0;
      }
    }
    resume(){
      // only resume from paused or ready; do not resurrect terminal games
      if (this.status === 'paused' || this.status === 'ready'){
        this.status='playing';
      }
    }
    pause(){ if (this.status==='playing'){ this.status='paused'; } }
    togglePause(){ if (this.status==='playing') this.pause(); else if (this.status==='paused' || this.status==='ready') this.resume(); }

    step(){
      // don't advance if terminal or paused
      if (this.status === 'over' || this.status === 'won' || this.status === 'paused') return false;
      if (this.status === 'ready') this.status = 'playing';
      // apply queued turn at most one per step
      if (this._turnQueue.length) this.nextDirection = this._turnQueue.shift();
      const dir = this.nextDirection || this.direction;
      this.direction = dir;
      const head = Object.assign({}, this.snake[0]);
      if (dir==='up') head.y -=1;
      if (dir==='down') head.y +=1;
      if (dir==='left') head.x -=1;
      if (dir==='right') head.x +=1;

      // determine if this step will grow (eat food) BEFORE collision checks
      const willGrow = !!(this.food && head.x===this.food.x && head.y===this.food.y);

      // wall collision
      if (head.x < 0 || head.x >= this.cols || head.y < 0 || head.y >= this.rows){ this.status='over'; this._saveBest(); return true; }
      // self collision - allow moving into the current tail cell if it will vacate (i.e., not growing)
      for(let i=0;i<this.snake.length;i++){ const p=this.snake[i];
        // skip tail cell if it will be removed this step
        if (!willGrow && i === this.snake.length - 1) continue;
        if (p.x===head.x && p.y===head.y){ this.status='over'; this._saveBest(); return true; }
      }
      // move
      this.snake.unshift(head);
      let grew = false;
      if (willGrow){ grew=true; this.score += 1; this.speed = Math.min(this.maxSpeed, this.speed + this.speedInc); this.placeFood(); this._saveBest(); }
      if (!grew) this.snake.pop();
      return true;
    }

    // one controlled animation: returns true when drawn/changed
    animate(dt){
      // only animate while playing
      if (this.status !== 'playing') return false;
      // cap elapsed time to avoid huge jumps
      const maxDt = 0.25; // seconds
      const useDt = Math.min(dt, maxDt);
      this._acc += useDt * this.speed;
      let updated = false;
      while(this._acc >= 1){
        // if a terminal state was reached, stop further stepping
        if (this.status === 'over' || this.status === 'won' || this.status === 'paused') break;
        this._acc -= 1;
        updated = this.step() || updated;
      }
      return updated;
    }
  }

  // expose in both browser and Node
  if (typeof module !== 'undefined' && module.exports) module.exports = SnakeGame;
  if (typeof window !== 'undefined') window.SnakeGame = SnakeGame;
})();