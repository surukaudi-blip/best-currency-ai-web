'use strict';

/**
 * Currency Strength MVP — Express API Server
 *
 * Endpoints:
 *   GET /api/currency-strength?timeframe=1h|4h|1d|1w|1m|all
 *
 * Serves static frontend files from project root.
 */

require('dotenv').config();

const express = require('express');
const path = require('path');
const { fetchAllPairs } = require('./src/market-data');
const { computeStrength } = require('./src/currency-strength-engine');
const { computeMTFComposite } = require('./src/mtf-composite');
const { TIMEFRAME_MAP, TIMEFRAME_LABELS } = require('./src/config');

const app = express();
const PORT = process.env.PORT || 3000;
const API_KEY = process.env.TWELVE_DATA_API_KEY;

// Cache layer — store results for 5 minutes to avoid hitting rate limits
const cache = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

function getCacheKey(timeframe) {
  return `cs_${timeframe}`;
}

function getCached(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return entry.data;
}

function setCache(key, data) {
  cache.set(key, { data, timestamp: Date.now() });
}

// Serve static files from project root
app.use(express.static(path.join(__dirname)));

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Currency Strength MVP',
    timestamp: new Date().toISOString(),
    apiKeyConfigured: API_KEY && API_KEY !== 'your_twelve_data_api_key_here',
  });
});

/**
 * GET /api/currency-strength?timeframe=1h|4h|1d|1w|1m|all
 */
app.get('/api/currency-strength', async (req, res) => {
  try {
    if (!API_KEY || API_KEY === 'your_twelve_data_api_key_here') {
      return res.status(500).json({
        ok: false,
        error: 'TWELVE_DATA_API_KEY not configured. Set it in .env file.',
      });
    }

    const timeframe = (req.query.timeframe || 'all').toLowerCase();

    if (timeframe === 'all') {
      // Return all timeframes + MTF composite
      const cacheKey = getCacheKey('all');
      const cached = getCached(cacheKey);
      if (cached) {
        return res.json(cached);
      }

      const allResults = {};
      const timeframes = ['1h', '4h', '1d', '1w', '1m'];

      for (const tf of timeframes) {
        const tfCacheKey = getCacheKey(tf);
        const tfCached = getCached(tfCacheKey);

        if (tfCached) {
          allResults[tf] = tfCached;
          continue;
        }

        const pairData = await fetchAllPairs(tf, API_KEY);
        if (Object.keys(pairData).length === 0) {
          allResults[tf] = { error: `No data available for ${tf}` };
          continue;
        }

        const strengthResult = computeStrength(pairData);
        allResults[tf] = {
          timeframe: tf,
          timeframe_label: TIMEFRAME_LABELS[tf],
          ...strengthResult,
          generated_at: new Date().toISOString(),
        };
        setCache(tfCacheKey, allResults[tf]);
      }

      // Compute MTF composite
      const mtfComposite = computeMTFComposite(allResults);

      const response = {
        ok: true,
        generated_at: new Date().toISOString(),
        timeframes: allResults,
        mtf_composite: mtfComposite,
        meta: {
          source: 'Twelve Data',
          pairs: 7,
          currencies: 8,
          timeframes: 5,
          cache_ttl_seconds: CACHE_TTL_MS / 1000,
        },
      };

      setCache(cacheKey, response);
      return res.json(response);
    }

    // Single timeframe
    if (!TIMEFRAME_MAP[timeframe]) {
      return res.status(400).json({
        ok: false,
        error: `Invalid timeframe: ${timeframe}. Use one of: 1h, 4h, 1d, 1w, 1m, all`,
      });
    }

    const cacheKey = getCacheKey(timeframe);
    const cached = getCached(cacheKey);
    if (cached) {
      return res.json({
        ok: true,
        generated_at: cached.generated_at || new Date().toISOString(),
        timeframe,
        timeframe_label: TIMEFRAME_LABELS[timeframe],
        currency_strength: cached.currency_strength,
        ranking: cached.ranking,
        strongest_currency: cached.strongest_currency,
        strongest_score: cached.strongest_score,
        weakest_currency: cached.weakest_currency,
        weakest_score: cached.weakest_score,
        pair_returns: cached.pair_returns,
        source: 'Twelve Data',
        cached: true,
      });
    }

    const pairData = await fetchAllPairs(timeframe, API_KEY);
    if (Object.keys(pairData).length === 0) {
      return res.status(503).json({
        ok: false,
        error: `No market data available for timeframe ${timeframe}. Check API key and rate limits.`,
      });
    }

    const strengthResult = computeStrength(pairData);

    const response = {
      ok: true,
      generated_at: new Date().toISOString(),
      timeframe,
      timeframe_label: TIMEFRAME_LABELS[timeframe],
      currency_strength: strengthResult.currency_strength,
      ranking: strengthResult.ranking,
      strongest_currency: strengthResult.strongest_currency,
      strongest_score: strengthResult.strongest_score,
      weakest_currency: strengthResult.weakest_currency,
      weakest_score: strengthResult.weakest_score,
      pair_returns: strengthResult.pair_returns,
      source: 'Twelve Data',
      cached: false,
    };

    setCache(cacheKey, response);
    return res.json(response);

  } catch (err) {
    console.error('[api] Error:', err.message);
    return res.status(500).json({
      ok: false,
      error: err.message,
    });
  }
});

// Start server
app.listen(PORT, () => {
  console.log(`\n🚀 Currency Strength MVP server running at http://localhost:${PORT}`);
  console.log(`📊 API: http://localhost:${PORT}/api/currency-strength?timeframe=all`);
  console.log(`🔑 API Key: ${API_KEY && API_KEY !== 'your_twelve_data_api_key_here' ? 'Configured ✓' : 'NOT SET — add TWELVE_DATA_API_KEY to .env'}`);
  console.log(`\nEndpoints:`);
  console.log(`  GET /api/health`);
  console.log(`  GET /api/currency-strength?timeframe=1h`);
  console.log(`  GET /api/currency-strength?timeframe=4h`);
  console.log(`  GET /api/currency-strength?timeframe=1d`);
  console.log(`  GET /api/currency-strength?timeframe=1w`);
  console.log(`  GET /api/currency-strength?timeframe=1m`);
  console.log(`  GET /api/currency-strength?timeframe=all`);
});

module.exports = app;
