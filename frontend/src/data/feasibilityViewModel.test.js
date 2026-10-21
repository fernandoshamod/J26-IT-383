import test from 'node:test';
import assert from 'node:assert/strict';
import { buildFeasibilityView } from './feasibilityViewModel.js';

const check = (code, status) => ({ code, status, message: code + ' raw message', evidence_origin: 'test' });
test('groups only recorded checks and preserves each original object', () => {
  const passed = [check('service_coverage', 'PASS_IN_SIMULATION'), check('budget', 'PASS_IN_SIMULATION')];
  const pending = [
    check('availability:vendor-1:Photography', 'VERIFICATION_REQUIRED'),
    check('scheduling:vendor-1:Photography', 'VERIFICATION_REQUIRED'),
    check('vendor_collaboration:vendor-1:vendor-2', 'VERIFICATION_REQUIRED'),
    check('venue_suitability', 'VERIFICATION_REQUIRED'),
  ];
  const value = { passed_checks: passed, pending_checks: pending, failed_checks: [] };
  const result = buildFeasibilityView(value, [
    { vendor_id: 'vendor-1', service: 'Photography' },
    { vendor_id: 'vendor-2', service: 'Decoration' },
  ]);
  assert.deepEqual(result.counts, { passed: 2, pending: 4, failed: 0 });
  assert.equal(result.total, 6);
  assert.equal(result.pendingGroups.reduce((sum, group) => sum + group.items.length, 0), 4);
  assert.equal(result.passedGroups.reduce((sum, group) => sum + group.items.length, 0), 2);
  assert.deepEqual(result.pendingGroups.find((group) => group.key === 'collaboration').services,
    ['Photography', 'Decoration']);
  assert.equal(result.pendingGroups[0].items[0], pending[0]);
});
test('failed checks remain failed and missing lists stay unknown', () => {
  const failure = check('capacity:vendor-1:Photography', 'FAIL');
  const view = buildFeasibilityView({ passed_checks: [], pending_checks: [], failed_checks: [failure] });
  assert.deepEqual(view.counts, { passed: 0, pending: 0, failed: 1 });
  assert.equal(view.total, 1);
  assert.equal(view.failed[0], failure);
  assert.equal(view.pendingGroups.length, 0);
  const missing = buildFeasibilityView({ final_status: 'VERIFICATION_REQUIRED' });
  assert.deepEqual(missing.counts, { passed: null, pending: null, failed: null });
  assert.equal(missing.total, null);
});
test('unknown pending codes remain in an other group without invented outcomes', () => {
  const item = check('new_unclassified_code', 'VERIFICATION_REQUIRED');
  const result = buildFeasibilityView({ passed_checks: [], pending_checks: [item], failed_checks: [] });
  assert.equal(result.pendingGroups[0].title, 'Other recorded checks');
  assert.equal(result.pendingGroups[0].items[0], item);
});

