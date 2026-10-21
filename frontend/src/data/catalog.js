import summary from './evaluation_summary.json';
import rules from './compatibility_rules.json';

export { summary, rules };
export const SERVICES = [
  ['Audio Visual', 'Sound, projection and presentation support'],
  ['Catering', 'Food and beverage service'],
  ['Photography', 'Event photography coverage'],
  ['Decoration', 'Event styling and décor'],
  ['Entertainment', 'Performers and event entertainment'],
  ['Equipment Rental', 'Event equipment hire'],
  ['Event Planning', 'Coordination and planning support'],
];
export const EVENT_TYPES = ['Wedding', 'Birthday', 'Corporate'];
export const money = (value) => value == null ? 'Unknown' :
  'LKR ' + Number(value).toLocaleString('en-LK', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });
export const percentage = (value) => value == null ? 'Unknown' :
  (Number(value) * 100).toFixed(1) + '%';
export const score = (value) => value == null ? 'Unknown' : Number(value).toFixed(1) + '/100';
export const dateForInput = (daysAhead = 30) => {
  const next = new Date();
  next.setDate(next.getDate() + daysAhead);
  return [next.getFullYear(), String(next.getMonth() + 1).padStart(2, '0'),
    String(next.getDate()).padStart(2, '0')].join('-');
};

