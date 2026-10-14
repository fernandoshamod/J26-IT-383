// Tests for the phone page's offline queue (NFR-07). Run: node tests/js/test_checkin_queue.mjs
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const html = readFileSync(new URL('../../api/static/checkin.html', import.meta.url), 'utf8');
const code = html.split('// QUEUE-START')[1].split('// QUEUE-END')[0];
const { readQueue, enqueue, flushQueue } = new Function(code + '; return { readQueue, enqueue, flushQueue };')();

const memory = () => { const m = {}; return { getItem: k => m[k] ?? null, setItem: (k, v) => { m[k] = String(v); } }; };
const item = (id, type = 'started') => ({ client_id: id, activity_id: 'photos', type, at_minutes: 900, queued_offline: false });

// 1. Offline: nothing is sent, nothing is lost.
{ const s = memory(); enqueue(s, item('a')); enqueue(s, item('b', 'completed'));
  let calls = 0;
  const r = await flushQueue(s, async () => { calls++; return 'ok'; }, () => true);
  assert.equal(calls, 0); assert.equal(r.remaining, 2); }

// 2. Network failure mid-way: the failed item and everything after it stay,
//    in order, marked as delivered-late; items already sent are gone.
{ const s = memory(); enqueue(s, item('a')); enqueue(s, item('b', 'completed'));
  let n = 0;
  const r = await flushQueue(s, async () => { if (n++ === 1) throw new Error('no signal'); return 'ok'; }, () => false);
  assert.equal(r.sent, 1); assert.equal(r.remaining, 1);
  const q = readQueue(s); assert.equal(q[0].client_id, 'b'); assert.equal(q[0].queued_offline, true); }

// 3. Signal back: everything goes, in tap order.
{ const s = memory(); enqueue(s, item('a')); enqueue(s, item('b', 'completed'));
  const order = [];
  const r = await flushQueue(s, async x => { order.push(x.client_id); return 'ok'; }, () => false);
  assert.deepEqual(order, ['a', 'b']); assert.equal(r.remaining, 0); }

// 4. Server rejects an invalid check-in (409): dropped and reported, not retried forever.
{ const s = memory(); enqueue(s, item('a')); enqueue(s, item('b', 'completed'));
  const r = await flushQueue(s, async x => x.client_id === 'a' ? { reason: 'already started' } : 'ok', () => false);
  assert.equal(r.sent, 1); assert.equal(r.rejected.length, 1); assert.equal(r.rejected[0].reason, 'already started');
  assert.equal(r.remaining, 0); }

// 5. Corrupt storage never crashes the page.
{ const s = memory(); s.setItem('c3_checkin_queue', '{not json'); assert.deepEqual(readQueue(s), []); }

console.log('checkin queue: 5 tests passed');
