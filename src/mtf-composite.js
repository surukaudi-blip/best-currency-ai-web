'use strict';

/**
 * Currency Strength MVP — Multi-Timeframe Composite
 *
 * MTF Score = (1H × 0.10) + (4H × 0.20) + (1D × 0.30) + (1W × 0.25) + (1M × 0.15)
 *
 * MTF Alignment: count how many timeframes agree on strongest > weakest direction
 */

const { CURRENCIES, MTF_WEIGHTS, TIMEFRAME_LABELS } = require('./config');

/**
 * Compute MTF composite score for each currency
 *
 * @param {Object} timeframeResults - { '1h': { currency_strength, ranking, ... }, ... }
 * @returns {Object} - { mtf_scores, ranking, strongest, weakest, spread, alignment }
 */
function computeMTFComposite(timeframeResults) {
  const mtfScores = {};
  CURRENCIES.forEach(c => { mtfScores[c] = 0; });

  let availableTimeframes = 0;
  const availableWeights = {};

  // Weighted sum across timeframes
  for (const [tf, weight] of Object.entries(MTF_WEIGHTS)) {
    const tfResult = timeframeResults[tf];
    if (!tfResult || !tfResult.currency_strength) continue;

    availableTimeframes++;
    availableWeights[tf] = weight;

    for (const c of CURRENCIES) {
      mtfScores[c] += (tfResult.currency_strength[c] || 50) * weight;
    }
  }

  // Normalize if not all timeframes available
  if (availableTimeframes > 0 && availableTimeframes < Object.keys(MTF_WEIGHTS).length) {
    const totalWeight = Object.values(availableWeights).reduce((a, b) => a + b, 0);
    for (const c of CURRENCIES) {
      mtfScores[c] = parseFloat((mtfScores[c] / totalWeight).toFixed(4));
    }
  }

  // Round scores
  for (const c of CURRENCIES) {
    mtfScores[c] = parseFloat(mtfScores[c].toFixed(4));
  }

  // Rank by MTF score
  const ranking = [...CURRENCIES].sort((a, b) => mtfScores[b] - mtfScores[a]);
  const strongest = ranking[0];
  const weakest = ranking[ranking.length - 1];

  // Strength spread (difference between strongest and weakest)
  const spread = parseFloat((mtfScores[strongest] - mtfScores[weakest]).toFixed(4));

  // MTF Alignment: count timeframes where strongest > weakest
  let alignedCount = 0;
  let totalTFCount = 0;
  const alignmentDetails = {};

  for (const [tf, tfResult] of Object.entries(timeframeResults)) {
    if (!tfResult || !tfResult.strongest_currency || !tfResult.weakest_currency) continue;

    totalTFCount++;
    const tfStrongest = tfResult.strongest_currency;
    const tfWeakest = tfResult.weakest_currency;
    const tfStrongScore = tfResult.currency_strength[tfStrongest] || 50;
    const tfWeakScore = tfResult.currency_strength[tfWeakest] || 50;

    // Check if this timeframe agrees with the MTF strongest/weakest direction
    const mtfStrongScore = mtfScores[strongest];
    const mtfWeakScore = mtfScores[weakest];

    const tfAgrees = (tfResult.currency_strength[strongest] || 50) > (tfResult.currency_strength[weakest] || 50);
    if (tfAgrees) alignedCount++;

    alignmentDetails[tf] = {
      label: TIMEFRAME_LABELS[tf] || tf,
      strongest: tfStrongest,
      strongest_score: tfStrongScore,
      weakest: tfWeakest,
      weakest_score: tfWeakScore,
      agrees_with_mtf: tfAgrees,
    };
  }

  const alignmentRatio = totalTFCount > 0 ? alignedCount / totalTFCount : 0;

  return {
    mtf_scores: mtfScores,
    ranking,
    strongest_currency: strongest,
    strongest_score: mtfScores[strongest],
    weakest_currency: weakest,
    weakest_score: mtfScores[weakest],
    strength_spread: spread,
    alignment: {
      aligned_timeframes: alignedCount,
      total_timeframes: totalTFCount,
      ratio: parseFloat(alignmentRatio.toFixed(4)),
      display: `${alignedCount}/${totalTFCount}`,
      details: alignmentDetails,
    },
    weights_used: MTF_WEIGHTS,
    available_timeframes: Object.keys(availableWeights),
  };
}

module.exports = {
  computeMTFComposite,
};
