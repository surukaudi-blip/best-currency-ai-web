'use strict';

/**
 * Currency Strength MVP — Calculation Engine
 *
 * Formula:
 *   1. For each pair, compute log return: R = ln(current_close / previous_close)
 *   2. BASE currency gets +R contribution, QUOTE currency gets -R contribution
 *   3. Sum all pair contributions per currency → raw_strength
 *   4. Normalize: z = (raw_strength - mean) / stddev
 *   5. Score: strength_score = 50 + (10 × z)
 */

const { CURRENCIES } = require('./config');

/**
 * Calculate log return for a pair
 * @param {number} currentClose
 * @param {number} previousClose
 * @returns {number} log return
 */
function logReturn(currentClose, previousClose) {
  if (!previousClose || previousClose === 0 || !currentClose || currentClose === 0) {
    return 0;
  }
  return Math.log(currentClose / previousClose);
}

/**
 * Calculate mean of an array of numbers
 * @param {number[]} arr
 * @returns {number}
 */
function mean(arr) {
  if (arr.length === 0) return 0;
  const sum = arr.reduce((a, b) => a + b, 0);
  return sum / arr.length;
}

/**
 * Calculate population standard deviation
 * @param {number[]} arr
 * @returns {number}
 */
function standardDeviation(arr) {
  if (arr.length === 0) return 0;
  const m = mean(arr);
  const variance = arr.reduce((sum, val) => sum + Math.pow(val - m, 2), 0) / arr.length;
  return Math.sqrt(variance);
}

/**
 * Compute currency strength from pair data for a single timeframe
 *
 * @param {Object} pairData - { 'EUR/USD': { base, quote, currentClose, previousClose }, ... }
 * @returns {Object} - { currency_strength, ranking, strongest, weakest, pair_returns }
 */
function computeStrength(pairData) {
  // Step 1-2: Calculate log returns and accumulate contributions
  const rawStrength = {};
  CURRENCIES.forEach(c => { rawStrength[c] = 0; });

  const pairReturns = {};

  for (const [symbol, data] of Object.entries(pairData)) {
    const R = logReturn(data.currentClose, data.previousClose);
    const pairKey = symbol.replace('/', '');

    // BASE gets +R, QUOTE gets -R
    if (rawStrength[data.base] !== undefined) {
      rawStrength[data.base] += R;
    }
    if (rawStrength[data.quote] !== undefined) {
      rawStrength[data.quote] -= R;
    }

    pairReturns[pairKey] = R;
  }

  // Step 3: Get raw strength values
  const rawValues = CURRENCIES.map(c => rawStrength[c]);

  // Step 4: Normalize (z-score)
  const m = mean(rawValues);
  const sd = standardDeviation(rawValues);

  const normalizedStrength = {};
  const strengthScores = {};

  CURRENCIES.forEach(c => {
    if (sd > 0) {
      const z = (rawStrength[c] - m) / sd;
      // Step 5: Convert to score centered at 50
      strengthScores[c] = parseFloat((50 + 10 * z).toFixed(4));
    } else {
      // All currencies have same raw strength → all neutral at 50
      strengthScores[c] = 50;
    }
    normalizedStrength[c] = strengthScores[c];
  });

  // Step 6: Rank currencies by score (highest first)
  const ranking = [...CURRENCIES].sort((a, b) => strengthScores[b] - strengthScores[a]);

  const strongestCurrency = ranking[0];
  const weakestCurrency = ranking[ranking.length - 1];

  return {
    currency_strength: strengthScores,
    raw_strength: rawStrength,
    ranking,
    strongest_currency: strongestCurrency,
    strongest_score: strengthScores[strongestCurrency],
    weakest_currency: weakestCurrency,
    weakest_score: strengthScores[weakestCurrency],
    pair_returns: pairReturns,
    mean: parseFloat(m.toFixed(8)),
    std_dev: parseFloat(sd.toFixed(8)),
  };
}

module.exports = {
  logReturn,
  mean,
  standardDeviation,
  computeStrength,
};
