const pendingDefinitions = [
  { key: 'availability', title: 'Vendor availability', prefix: 'availability:' },
  { key: 'capacity', title: 'Vendor capacity', prefix: 'capacity:' },
  { key: 'scheduling', title: 'Travel, setup and scheduling', prefix: 'scheduling:' },
  { key: 'collaboration', title: 'Vendor collaboration', prefix: 'vendor_collaboration:' },
  { key: 'venue', title: 'Venue suitability', prefix: 'venue_suitability' },
];
const passedDefinitions = [
  { key: 'coverage', title: 'Required service coverage', prefix: 'service_coverage' },
  { key: 'vendors', title: 'Distinct vendor selection', prefix: 'unique_vendors' },
  { key: 'duration', title: 'Event duration', prefix: 'event_duration' },
  { key: 'type', title: 'Event type support', prefix: 'event_type:' },
  { key: 'location', title: 'Simulated location match', prefix: 'location:' },
  { key: 'pricing', title: 'Estimated option pricing', prefix: 'cost:' },
  { key: 'capacity', title: 'Simulated capacity fit', prefix: 'capacity:' },
  { key: 'budget', title: 'Estimated budget fit', prefix: 'budget' },
];
const arrayOrNull = (value) => Array.isArray(value) ? value : null;
const matches = (code, prefix) => prefix.endsWith(':')
  ? code.startsWith(prefix) : code === prefix;
const unique = (items) => [...new Set(items.filter(Boolean))];
function labelsFor(checks, options) {
  const vendorService = new Map(options.map((option) => [
    String(option.vendor_id), option.service,
  ]));
  return unique(checks.flatMap((check) => {
    const parts = String(check.code || '').split(':');
    if (parts[0] === 'vendor_collaboration') {
      return [vendorService.get(parts[1]), vendorService.get(parts[2])];
    }
    if (parts.length >= 3 && parts[2]) return [parts.slice(2).join(':')];
    return [];
  }));
}
function group(checks, definitions, options) {
  const assigned = new Set();
  const groups = definitions.map((definition) => {
    const items = checks.filter((check) => matches(String(check.code || ''), definition.prefix));
    items.forEach((item) => assigned.add(item));
    return { key: definition.key, title: definition.title, items, services: labelsFor(items, options) };
  }).filter((entry) => entry.items.length);
  const other = checks.filter((check) => !assigned.has(check));
  if (other.length) groups.push({
    key: 'other', title: 'Other recorded checks', items: other,
    services: labelsFor(other, options),
  });
  return groups;
}
export function buildFeasibilityView(value, serviceBreakdown = []) {
  const passed = arrayOrNull(value?.passed_checks);
  const pending = arrayOrNull(value?.pending_checks);
  const failed = arrayOrNull(value?.failed_checks);
  const options = Array.isArray(serviceBreakdown) ? serviceBreakdown : [];
  return {
    counts: {
      passed: passed?.length ?? null,
      pending: pending?.length ?? null,
      failed: failed?.length ?? null,
    },
    total: passed && pending && failed ? passed.length + pending.length + failed.length : null,
    pendingGroups: pending ? group(pending, pendingDefinitions, options) : [],
    passedGroups: passed ? group(passed, passedDefinitions, options) : [],
    passed, pending, failed,
  };
}

