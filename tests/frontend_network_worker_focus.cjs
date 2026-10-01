const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

function loadWorkerHarness() {
  const src = fs.readFileSync('/app/frontend/src/game/network.worker.js', 'utf8');
  const posts = [];
  const intervals = new Map();
  let timerId = 1;
  let now = 0;
  const sockets = [];

  class FakeWebSocket {
    constructor(url) {
      this.url = url;
      this.readyState = 1;
      this.bufferedAmount = 0;
      this.sent = [];
      this.closed = false;
      sockets.push(this);
    }
    send(payload) {
      this.sent.push(payload);
    }
    close() {
      this.closed = true;
      this.readyState = 3;
      if (this.onclose) this.onclose();
    }
  }

  function setIntervalFake(fn, ms) {
    const id = timerId++;
    intervals.set(id, { id, fn, ms, next: now + ms, active: true });
    return id;
  }

  function clearIntervalFake(id) {
    const item = intervals.get(id);
    if (item) item.active = false;
    intervals.delete(id);
  }

  function advance(ms) {
    const target = now + ms;
    while (true) {
      let next = null;
      for (const item of intervals.values()) {
        if (!item.active) continue;
        if (!next || item.next < next.next) next = item;
      }
      if (!next || next.next > target) break;
      now = next.next;
      next.fn();
      if (next.active) next.next += next.ms;
    }
    now = target;
  }

  const sandbox = {
    performance: {
      timeOrigin: 1_000_000,
      now: () => now,
    },
    setInterval: setIntervalFake,
    clearInterval: clearIntervalFake,
    WebSocket: FakeWebSocket,
    self: {
      postMessage: msg => posts.push(msg),
      onmessage: null,
    },
    console,
  };

  vm.runInNewContext(src, sandbox, { filename: 'network.worker.js' });
  return {
    posts,
    sockets,
    advance,
    sendToWorker: data => sandbox.self.onmessage({ data }),
    sendFromServer: message => sockets[0].onmessage({ data: JSON.stringify(message) }),
    openSocket: () => sockets[0].onopen(),
  };
}

function loadSnapshotTrack() {
  let code = fs.readFileSync('/app/frontend/src/game/snapshotTrack.js', 'utf8');
  code = code.replace('export class SnapshotTrack', 'class SnapshotTrack');
  code += '\nmodule.exports = { SnapshotTrack };\n';
  const ctx = { module: { exports: {} }, exports: {} };
  vm.runInNewContext(code, ctx, { filename: 'snapshotTrack.js' });
  return ctx.module.exports.SnapshotTrack;
}

function loadMovementController() {
  let code = fs.readFileSync('/app/frontend/src/game/movement.js', 'utf8');
  code = code.replace("import * as CANNON from 'cannon-es';", "const CANNON = require('/app/frontend/node_modules/cannon-es');");
  code = code.replace('export class MovementController', 'class MovementController');
  code += '\nmodule.exports = { MovementController };\n';
  let now = 0;
  const ctx = {
    require,
    module: { exports: {} },
    exports: {},
    performance: { now: () => now },
  };
  vm.runInNewContext(code, ctx, { filename: 'movement.js' });
  return {
    MovementController: ctx.module.exports.MovementController,
    setNow: value => {
      now = value;
    },
  };
}

try {
  console.log('Worker tests: start');
  const h = loadWorkerHarness();
  h.sendToWorker({ type: 'connect', url: 'wss://example/ws' });
  h.openSocket();

  assert(h.posts.some(m => m.type === 'open'), 'open message missing');
  const firstPing = JSON.parse(h.sockets[0].sent[0]);
  assert(firstPing.type === 'ping', 'immediate ping not sent');

  h.sendFromServer({ type: 'state', seq: 1, events: [{ id: 'e1' }] });
  const firstState = h.posts.find(m => m.type === 'state');
  assert(firstState && firstState.seq === 1, 'state not published immediately');

  h.sendFromServer({ type: 'state', seq: 2, events: [{ id: 'e2' }] });
  h.sendFromServer({ type: 'state', seq: 3, events: Array.from({ length: 300 }, (_, i) => ({ n: i })) });
  assert(h.posts.filter(m => m.type === 'state').length === 1, 'more than one in-flight state published');

  h.sendToWorker({ type: 'state-consumed' });
  const published = h.posts.filter(m => m.type === 'state');
  const latest = published[published.length - 1];
  assert(latest.seq === 3, 'latest snapshot not kept');
  assert(latest.events.length <= 256, 'events cap exceeded');

  h.advance(300);
  const pingPayload = JSON.parse(h.sockets[0].sent.find(s => JSON.parse(s).type === 'ping'));
  h.sendFromServer({ type: 'pong', time: pingPayload.time });
  const pingMsg = h.posts.find(m => m.type === 'ping');
  assert(pingMsg && pingMsg.value >= 295 && pingMsg.value <= 320, 'RTT not using monotonic timing');

  const sentBeforeEdge = h.sockets[0].sent.length;
  h.sendToWorker({ type: 'input', x: 1, z: 0, angle: 0, fire: false, sprint: false, reload: false });
  assert(h.sockets[0].sent.length > sentBeforeEdge, 'edge input not sent immediately');

  h.sendToWorker({ type: 'input', x: 0, z: 0, angle: 0, fire: true, sprint: false, reload: false });
  const firePayload = JSON.parse(h.sockets[0].sent[h.sockets[0].sent.length - 1]);
  assert(firePayload.fire_pressed === true, 'fire edge did not mark fire_pressed');

  h.sockets[0].bufferedAmount = 9000;
  const beforeBlocked = h.sockets[0].sent.length;
  h.sendToWorker({ type: 'input', x: 0, z: 1, angle: 0, fire: false, sprint: false, reload: true });
  assert(h.sockets[0].sent.length === beforeBlocked, 'buffer guard failed when bufferedAmount > 8KB');
  h.sockets[0].bufferedAmount = 0;

  h.advance(450);
  const stalePayload = JSON.parse(h.sockets[0].sent[h.sockets[0].sent.length - 1]);
  assert(stalePayload.x === 0 && stalePayload.z === 0 && stalePayload.fire === false, 'stale-input stop after 400ms failed');

  console.log('Worker tests: PASS');

  console.log('SnapshotTrack tests: start');
  const SnapshotTrack = loadSnapshotTrack();
  const track = new SnapshotTrack();
  track.push({ x: 0, z: 0, angle: 0 }, 1000);
  track.push({ x: 4, z: 0, angle: Math.PI - 0.1 }, 1100);
  track.push({ x: 8, z: 0, angle: -Math.PI + 0.1 }, 1200);
  const mid = track.sample(1150);
  assert(mid.x > 4 && mid.x < 8, 'interpolation failed');
  assert(Math.abs(mid.angle) > 3.0, 'shortest angle interpolation failed');

  const extrap = track.sample(1400);
  assert(extrap.x <= 11.3, 'extrapolation was not clamped at 80ms');

  for (let i = 0; i < 10; i++) track.push({ x: 20 + i, z: i, angle: 0 }, 1300 + i * 10);
  assert(track.samples.length <= 6, 'sample history exceeded six');

  track.push({ x: 200, z: 200, angle: 0 }, 1500);
  assert(track.samples.length === 1, 'teleport reset not applied');
  track.push({ x: 201, z: 200, angle: 0 }, 1499);
  assert(track.samples.length === 1, 'non-monotonic sample was incorrectly accepted');
  console.log('SnapshotTrack tests: PASS');

  console.log('MovementController tests: start');
  const { MovementController, setNow } = loadMovementController();
  const mc = new MovementController();
  mc.load([]);
  const me = {
    id: 'p1',
    x: 0,
    z: 0,
    hp: 100,
    stamina: 100,
    statuses: {},
    vx: 0,
    vz: 0,
    input_seq: 0,
  };

  setNow(100);
  mc.noteInput({ x: 1, z: 0, sprint: false, seq: 10 }, 100);
  mc.reset(20, 20);
  mc.id = me.id;
  mc.update(0.05, { x: 0, z: 0, sprint: false }, me, 0.01, 300);
  assert(Math.hypot(mc.body.position.x - me.x, mc.body.position.z - me.z) > 5, 'ack grace not respected');

  setNow(900);
  mc.update(0.05, { x: 0, z: 0, sprint: false }, me, 0.01, 300);
  assert(Math.hypot(mc.body.position.x - me.x, mc.body.position.z - me.z) < 1, 'old unacked stop grace did not expire');

  const deadOut = mc.update(0.05, { x: 1, z: 0, sprint: true }, { ...me, hp: 0 }, 0.01, 0);
  assert(deadOut.speed < 0.2, 'dead player should not keep local movement speed');

  const wall = new MovementController();
  wall.load([{ id: 'chunk1', barriers: [{ x: 2, z: 0, w: 1, d: 6 }] }]);
  wall.reset(0, 0);
  const wallMe = { ...me, id: 'wall', x: 0, z: 0, hp: 100, input_seq: 0 };
  wall.id = 'wall';
  for (let i = 0; i < 40; i++) {
    wall.update(0.05, { x: 1, z: 0, sprint: false }, wallMe, 0.01, 0);
  }
  assert(wall.body.position.x < 2.2, 'collision barrier not respected');
  console.log('MovementController tests: PASS');

  process.exit(0);
} catch (err) {
  console.error('Frontend focused tests FAILED:', err.message);
  process.exit(1);
}
