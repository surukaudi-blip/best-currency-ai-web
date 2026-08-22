'use strict';

/**
 * Currency Strength MVP — Unit Tests for MTF Composite
 */

const { computeMTFComposite } = require('../src/mtf-composite');
const { computeStrength } = require('../src/currency-strength-engine');

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✅ ${message}`);
    passed++;
  } else {
    console.log(`  ❌ FAIL: ${message}`);
    failed++;
  }
}

function approxEqual(a, b, tolerance, message) {
  const diff = Math.abs(a - b);
  assert(diff < tolerance, `${message} (${a} ≈ ${b}, diff=${diff})`);
}

// Helper: create mock pair data where base gains X% vs quote
function mockPairData(gains) {
  // gains is { 'EUR/USD': 0.10, ... } meaning EUR/USD up 10%
  const base = {
    'EUR/USD': { base: 'EUR', quote: 'USD' },
    'GBP/USD': { base: 'GBP', quote: 'USD' },
    'USD/JPY': { base: 'USD', quote: 'JPY' },
    'USD/CHF': { base: 'USD', quote: 'CHF' },
    'AUD/USD': { base: 'AUD', quote: 'USD' },
    'NZD/USD': { base: 'NZD', quote: 'USD' },
    'USD/CAD': { base: 'USD', quote: 'CAD' },
  };

  const result = {};
  for (const [symbol, info] of Object.entries(base)) {
    const g = gains[symbol] || 0;
    const prev = 1.0;
    const curr = prev * (1 + g);
    result[symbol] = { ...info, currentClose: curr, previousClose: prev };
  }
  return result;
}

// ========== Basic MTF Tests ==========
console.log('\n--- MTF Composite Tests ---');

// All timeframes agree: EUR strong, USD weak
const consistentTFs = {};
for (const tf of ['1h', '4h', '1d', '1w', '1m']) {
  const pairData = mockPairData({ 'EUR/USD': 0.05 });
  consistentTFs[tf] = computeStrength(pairData);
}

const mtf1 = computeMTFComposite(consistentTFs);

assert(mtf1.strongest_currency === 'EUR', `Consistent MTF: strongest = EUR (got ${mtf1.strongest_currency})`);
assert(mtf1.weakest_currency === 'USD', `Consistent MTF: weakest = USD (got ${mtf1.weakest_currency})`);
assert(mtf1.alignment.aligned_timeframes === 5, `Consistent MTF: alignment = 5/5 (got ${mtf1.alignment.display})`);
assert(mtf1.ranking[0] === 'EUR', `Consistent MTF: rank #1 = EUR`);
assert(mtf1.ranking[7] === 'USD', `Consistent MTF: rank #8 = USD`);
assert(mtf1.strength_spread > 0, `Consistent MTF: spread > 0 (${mtf1.strength_spread})`);

// ========== Mixed MTF Test ==========
console.log('\n--- Mixed MTF Alignment Tests ---');

const mixedTFs = {};
// 1h: EUR strong
mixedTFs['1h'] = computeStrength(mockPairData({ 'EUR/USD': 0.03 }));
// 4h: EUR strong
mixedTFs['4h'] = computeStrength(mockPairData({ 'EUR/USD': 0.03 }));
// 1d: USD strong (EUR drops)
mixedTFs['1d'] = computeStrength(mockPairData({ 'EUR/USD': -0.03 }));
// 1w: EUR strong
mixedTFs['1w'] = computeStrength(mockPairData({ 'EUR/USD': 0.03 }));
// 1m: USD strong
mixedTFs['1m'] = computeStrength(mockPairData({ 'EUR/USD': -0.03 }));

const mtf2 = computeMTFComposite(mixedTFs);

// 3 out of 5 timeframes agree with MTF direction
assert(mtf2.alignment.aligned_timeframes === 3, `Mixed MTF: alignment = 3/5 (got ${mtf2.alignment.display})`);
assert(mtf2.alignment.ratio === 0.6, `Mixed MTF: ratio = 0.6 (got ${mtf2.alignment.ratio})`);

// ========== Partial MTF (not all timeframes) ==========
console.log('\n--- Partial MTF Tests ---');

const partialTFs = {};
partialTFs['1d'] = computeStrength(mockPairData({ 'EUR/USD': 0.05 }));
partialTFs['1w'] = computeStrength(mockPairData({ 'EUR/USD': 0.05 }));

const mtf3 = computeMTFComposite(partialTFs);

assert(mtf3.alignment.total_timeframes === 2, `Partial MTF: 2 timeframes available (got ${mtf3.alignment.total_timeframes})`);
assert(mtf3.strongest_currency === 'EUR', `Partial MTF: strongest = EUR`);
assert(mtf3.weakest_currency === 'USD', `Partial MTF: weakest = USD`);
assert(mtf3.weights_used !== undefined, 'Partial MTF: weights_used exists');

// ========== Empty MTF Test ==========
console.log('\n--- Empty MTF Tests ---');

const mtf4 = computeMTFComposite({});
assert(mtf4.alignment.total_timeframes === 0, `Empty MTF: 0 timeframes (got ${mtf4.alignment.total_timeframes})`);
assert(mtf4.ranking.length === 8, `Empty MTF: 8 currencies ranked`);

// ========== Summary ==========
console.log(`\n${'='.repeat(50)}`);
console.log(`Tests: ${passed + failed} total, ${passed} passed, ${failed} failed`);
console.log(`${'='.repeat(50)}`);

process.exit(failed > 0 ? 1 : 0);
