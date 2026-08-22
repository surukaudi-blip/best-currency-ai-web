'use strict';

/**
 * Currency Strength MVP — Unit Tests for Calculation Engine
 */

const { logReturn, mean, standardDeviation, computeStrength } = require('../src/currency-strength-engine');

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

// ========== logReturn Tests ==========
console.log('\n--- logReturn Tests ---');

// ln(1.10 / 1.00) ≈ 0.09531
approxEqual(logReturn(1.10, 1.00), Math.log(1.10), 0.0001, 'logReturn(1.10, 1.00) ≈ ln(1.1)');

// ln(1.00 / 1.10) ≈ -0.09531
approxEqual(logReturn(1.00, 1.10), Math.log(1.0 / 1.1), 0.0001, 'logReturn(1.00, 1.10) ≈ ln(1/1.1)');

// ln(1.00 / 1.00) = 0
assert(logReturn(1.00, 1.00) === 0, 'logReturn(1.00, 1.00) = 0');

// Edge cases
assert(logReturn(0, 1) === 0, 'logReturn(0, 1) = 0 (zero current)');
assert(logReturn(1, 0) === 0, 'logReturn(1, 0) = 0 (zero previous)');
assert(logReturn(null, 1) === 0, 'logReturn(null, 1) = 0');
assert(logReturn(1, null) === 0, 'logReturn(1, null) = 0');

// ========== mean Tests ==========
console.log('\n--- mean Tests ---');

approxEqual(mean([1, 2, 3, 4, 5]), 3.0, 0.0001, 'mean([1,2,3,4,5]) = 3');
approxEqual(mean([10, 20]), 15.0, 0.0001, 'mean([10, 20]) = 15');
assert(mean([]) === 0, 'mean([]) = 0');
approxEqual(mean([42]), 42.0, 0.0001, 'mean([42]) = 42');

// ========== standardDeviation Tests ==========
console.log('\n--- standardDeviation Tests ---');

// For [2, 4, 4, 4, 5, 5, 7, 9], stddev (population) ≈ 2.0
approxEqual(standardDeviation([2, 4, 4, 4, 5, 5, 7, 9]), 2.0, 0.01, 'stddev([2,4,4,4,5,5,7,9]) ≈ 2.0');

// All same values → stddev = 0
assert(standardDeviation([5, 5, 5]) === 0, 'stddev([5,5,5]) = 0');

// Two values: stddev of [0, 10] = 5
approxEqual(standardDeviation([0, 10]), 5.0, 0.01, 'stddev([0,10]) = 5');

assert(standardDeviation([]) === 0, 'stddev([]) = 0');

// ========== computeStrength Tests ==========
console.log('\n--- computeStrength Tests ---');

// Test with known data: EUR/USD up 10%, GBP/USD up 5%
// EUR/USD: base EUR gets +ln(1.10), quote USD gets -ln(1.10)
// GBP/USD: base GBP gets +ln(1.05), quote USD gets -ln(1.05)
// USD/JPY: flat → ln(1) = 0
// USD/CHF: flat → ln(1) = 0
// AUD/USD: flat → ln(1) = 0
// NZD/USD: flat → ln(1) = 0
// USD/CAD: flat → ln(1) = 0

const mockData1 = {
  'EUR/USD': { base: 'EUR', quote: 'USD', currentClose: 1.10, previousClose: 1.00 },
  'GBP/USD': { base: 'GBP', quote: 'USD', currentClose: 1.05, previousClose: 1.00 },
  'USD/JPY': { base: 'USD', quote: 'JPY', currentClose: 150.0, previousClose: 150.0 },
  'USD/CHF': { base: 'USD', quote: 'CHF', currentClose: 0.92, previousClose: 0.92 },
  'AUD/USD': { base: 'AUD', quote: 'USD', currentClose: 0.65, previousClose: 0.65 },
  'NZD/USD': { base: 'NZD', quote: 'USD', currentClose: 0.60, previousClose: 0.60 },
  'USD/CAD': { base: 'USD', quote: 'CAD', currentClose: 1.36, previousClose: 1.36 },
};

const result1 = computeStrength(mockData1);

// EUR should be strongest (it gained 10% vs USD)
assert(result1.strongest_currency === 'EUR', `Strongest = EUR (got ${result1.strongest_currency})`);

// USD should be weakest (it lost against both EUR and GBP)
assert(result1.weakest_currency === 'USD', `Weakest = USD (got ${result1.weakest_currency})`);

// Ranking should have EUR first and USD last
assert(result1.ranking[0] === 'EUR', `Ranking #1 = EUR (got ${result1.ranking[0]})`);
assert(result1.ranking[7] === 'USD', `Ranking #8 = USD (got ${result1.ranking[7]})`);

// GBP should be second (gained 5%)
assert(result1.ranking[1] === 'GBP', `Ranking #2 = GBP (got ${result1.ranking[1]})`);

// All scores should be numbers
for (const c of Object.keys(result1.currency_strength)) {
  assert(typeof result1.currency_strength[c] === 'number', `${c} score is a number: ${result1.currency_strength[c]}`);
}

// Scores should be around 50 center
// Strong currencies > 50, weak currencies < 50
assert(result1.currency_strength.EUR > 50, `EUR score > 50: ${result1.currency_strength.EUR}`);
assert(result1.currency_strength.USD < 50, `USD score < 50: ${result1.currency_strength.USD}`);

// ========== Symmetry Test ==========
console.log('\n--- Symmetry Tests ---');

// If all pairs are flat, all currencies should score 50
const mockFlat = {
  'EUR/USD': { base: 'EUR', quote: 'USD', currentClose: 1.10, previousClose: 1.10 },
  'GBP/USD': { base: 'GBP', quote: 'USD', currentClose: 1.25, previousClose: 1.25 },
  'USD/JPY': { base: 'USD', quote: 'JPY', currentClose: 150.0, previousClose: 150.0 },
  'USD/CHF': { base: 'USD', quote: 'CHF', currentClose: 0.92, previousClose: 0.92 },
  'AUD/USD': { base: 'AUD', quote: 'USD', currentClose: 0.65, previousClose: 0.65 },
  'NZD/USD': { base: 'NZD', quote: 'USD', currentClose: 0.60, previousClose: 0.60 },
  'USD/CAD': { base: 'USD', quote: 'CAD', currentClose: 1.36, previousClose: 1.36 },
};

const flatResult = computeStrength(mockFlat);
for (const c of Object.keys(flatResult.currency_strength)) {
  assert(flatResult.currency_strength[c] === 50, `${c} flat = 50 (got ${flatResult.currency_strength[c]})`);
}

// ========== Negative Returns Test ==========
console.log('\n--- Negative Returns Test ---');

// EUR/USD drops 5%, USD/JPY drops 3%
const mockData2 = {
  'EUR/USD': { base: 'EUR', quote: 'USD', currentClose: 0.95, previousClose: 1.00 },
  'GBP/USD': { base: 'GBP', quote: 'USD', currentClose: 1.00, previousClose: 1.00 },
  'USD/JPY': { base: 'USD', quote: 'JPY', currentClose: 145.0, previousClose: 150.0 },
  'USD/CHF': { base: 'USD', quote: 'CHF', currentClose: 0.92, previousClose: 0.92 },
  'AUD/USD': { base: 'AUD', quote: 'USD', currentClose: 0.65, previousClose: 0.65 },
  'NZD/USD': { base: 'NZD', quote: 'USD', currentClose: 0.60, previousClose: 0.60 },
  'USD/CAD': { base: 'USD', quote: 'CAD', currentClose: 1.36, previousClose: 1.36 },
};

const result2 = computeStrength(mockData2);

// EUR lost 5% → weakest
assert(result2.weakest_currency === 'EUR', `Negative: Weakest = EUR (got ${result2.weakest_currency})`);
// USD gained vs EUR and JPY → should be strong
assert(result2.currency_strength.USD > 50, `USD strong when EUR drops: ${result2.currency_strength.USD}`);

// ========== Summary ==========
console.log(`\n${'='.repeat(50)}`);
console.log(`Tests: ${passed + failed} total, ${passed} passed, ${failed} failed`);
console.log(`${'='.repeat(50)}`);

process.exit(failed > 0 ? 1 : 0);
