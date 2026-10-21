import test from 'node:test';
import assert from 'node:assert/strict';
import { comparisonInsights } from './comparisonInsights.js';

const packageValue = (id, rank, cost, risk, compatibility, status = 'VERIFICATION_REQUIRED') => ({
  package_id: id, rank, total_cost_lkr: cost,
  risk: { mean_rule_risk_score: risk }, compatibility: { score: compatibility },
  feasibility: { final_status: status },
});
test('cost difference and identical evidence use actual values', () => {
  const a = packageValue('USER-A-1', 1, 400000, 80, 85);
  const b = packageValue('USER-A-2', 2, 350000, 80, 85);
  const lines = comparisonInsights([a, b]);
  assert.match(lines[0], /USER-A-2.*LKR 350,000.00.*LKR 50,000.00/);
  assert.match(lines[1], /identical.*80.0\/100/);
  assert.match(lines[2], /identical.*85.0\/100/);
  assert.match(lines.at(-1), /same feasibility status/);
});
test('missing scores stay unknown and output is deterministic', () => {
  const a = packageValue('A', 1, 100, null, null);
  const b = packageValue('B', 2, 120, 60, 90);
  const first = comparisonInsights([a, b]);
  assert.deepEqual(first, comparisonInsights([b, a]));
  assert.match(first[1], /unknown/);
  assert.match(first[2], /unknown or not applicable/);
  assert.deepEqual(comparisonInsights([a]), []);
});
test('higher favorability is described without reliability claims', () => {
  const lines = comparisonInsights([
    packageValue('A', 1, 100, 60, 75),
    packageValue('B', 2, 100, 80, 90, 'PASS_IN_SIMULATION'),
  ]);
  assert.match(lines[1], /80.0\/100 for B/);
  assert.match(lines[2], /90.0\/100 for B/);
  assert.match(lines.at(-1), /statuses differ/);
  assert.doesNotMatch(lines.join(' '), /safest|verified vendor|best overall/i);
});


test('vendor differences and pending counts come from selected records', () => {
  const a = packageValue('A', 1, 100, 60, 85);
  const b = packageValue('B', 2, 120, 60, 85);
  a.service_breakdown = [{ service: 'Photography', vendor_id: 'vendor-1' }];
  b.service_breakdown = [{ service: 'Photography', vendor_id: 'vendor-2' }];
  a.feasibility.pending_checks = [{ code: 'availability' }];
  b.feasibility.pending_checks = [{ code: 'availability' }, { code: 'collaboration' }];
  const lines = comparisonInsights([a, b]);
  assert.equal(lines[3], 'Selected vendors differ for Photography.');
  assert.match(lines[4], /A has 1; B has 2/);
});
