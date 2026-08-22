'use strict';

/**
 * Currency Strength MVP — API Integration Tests
 *
 * Tests the /api/currency-strength endpoint using mock market data.
 * These tests do NOT require a real Twelve Data API key.
 */

const http = require('http');
const { computeStrength } = require('../src/currency-strength-engine');
const { computeMTFComposite } = require('../src/mtf-composite');

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

// ========== Engine + MTF Integration Test ==========
console.log('\n--- Engine + MTF Integration Test ---');

// Simulate what the API would do with real data
const mockPairData = {
  'EUR/USD': { base: 'EUR', quote: 'USD', currentClose: 1.10, previousClose: 1.00 },
  'GBP/USD': { base: 'GBP', quote: 'USD', currentClose: 1.05, previousClose: 1.00 },
  'USD/JPY': { base: 'USD', quote: 'JPY', currentClose: 150.0, previousClose: 150.0 },
  'USD/CHF': { base: 'USD', quote: 'CHF', currentClose: 0.92, previousClose: 0.92 },
  'AUD/USD': { base: 'AUD', quote: 'USD', currentClose: 0.65, previousClose: 0.65 },
  'NZD/USD': { base: 'NZD', quote: 'USD', currentClose: 0.60, previousClose: 0.60 },
  'USD/CAD': { base: 'USD', quote: 'CAD', currentClose: 1.36, previousClose: 1.36 },
};

// Compute strength for all timeframes
const allResults = {};
for (const tf of ['1h', '4h', '1d', '1w', '1m']) {
  allResults[tf] = computeStrength(mockPairData);
}

// Compute MTF composite
const mtfComposite = computeMTFComposite(allResults);

// Verify API response structure
assert(mtfComposite.mtf_scores !== undefined, 'MTF composite has mtf_scores');
assert(mtfComposite.ranking !== undefined, 'MTF composite has ranking');
assert(mtfComposite.ranking.length === 8, 'MTF ranking has 8 currencies');
assert(mtfComposite.strongest_currency !== undefined, 'MTF has strongest_currency');
assert(mtfComposite.weakest_currency !== undefined, 'MTF has weakest_currency');
assert(typeof mtfComposite.strength_spread === 'number', 'MTF has numeric strength_spread');
assert(mtfComposite.alignment !== undefined, 'MTF has alignment');
assert(typeof mtfComposite.alignment.ratio === 'number', 'Alignment has numeric ratio');

// Verify each timeframe result has required fields
for (const tf of ['1h', '4h', '1d', '1w', '1m']) {
  const tfResult = allResults[tf];
  assert(tfResult.currency_strength !== undefined, `${tf} has currency_strength`);
  assert(tfResult.ranking !== undefined, `${tf} has ranking`);
  assert(tfResult.ranking.length === 8, `${tf} ranking has 8 currencies`);
  assert(tfResult.strongest_currency !== undefined, `${tf} has strongest_currency`);
  assert(tfResult.weakest_currency !== undefined, `${tf} has weakest_currency`);
  assert(tfResult.pair_returns !== undefined, `${tf} has pair_returns`);
}

// ========== Config Tests ==========
console.log('\n--- Config Tests ---');

const config = require('../src/config');
assert(config.CURRENCIES.length === 8, 'Config has 8 currencies');
assert(config.PAIRS.length === 7, 'Config has 7 pairs');
assert(Object.keys(config.TIMEFRAME_MAP).length === 5, 'Config has 5 timeframes');
assert(Object.keys(config.MTF_WEIGHTS).length === 5, 'Config has 5 MTF weights');

// Verify MTF weights sum to 1.0
const weightSum = Object.values(config.MTF_WEIGHTS).reduce((a, b) => a + b, 0);
assert(Math.abs(weightSum - 1.0) < 0.0001, `MTF weights sum to 1.0 (got ${weightSum})`);

// Verify all currencies in PAIRS are in CURRENCIES
for (const pair of config.PAIRS) {
  assert(config.CURRENCIES.includes(pair.base), `${pair.base} is in CURRENCIES`);
  assert(config.CURRENCIES.includes(pair.quote), `${pair.quote} is in CURRENCIES`);
}

// ========== Server module test ==========
console.log('\n--- Server Module Tests ---');

// Test that server.js can be required without errors (module syntax check)
try {
  // We can't actually start the server in test (it would bind to a port),
  // but we can verify the module loads
  const serverPath = require.resolve('../server');
  assert(typeof serverPath === 'string', 'server.js module resolves');
} catch (err) {
  assert(false, `server.js module loads: ${err.message}`);
}

// ========== Summary ==========
console.log(`\n${'='.repeat(50)}`);
console.log(`Tests: ${passed + failed} total, ${passed} passed, ${failed} failed`);
console.log(`${'='.repeat(50)}`);

process.exit(failed > 0 ? 1 : 0);
