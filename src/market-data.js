'use strict';

/**
 * Currency Strength MVP — Twelve Data Market Data Integration
 *
 * Fetches OHLC data for 7 major Forex pairs using Twelve Data /time_series endpoint.
 * See: https://twelvedata.com/docs#time-series
 */

const fetch = require('node-fetch');
const { PAIRS, TIMEFRAME_MAP } = require('./config');

const BASE_URL = 'https://api.twelvedata.com';

// Rate limit: Twelve Data free tier = 800 req/day, 8 req/min
// Use 2000ms delay to be safe (stays well under 8 req/min = 1 req per 7.5s)
const RATE_LIMIT_MS = 2000;
const MAX_RETRIES = 3;
const RETRY_BASE_MS = 3000;

let lastRequestTime = 0;

/**
 * Wait to respect rate limits
 */
async function rateLimitWait() {
  const now = Date.now();
  const elapsed = now - lastRequestTime;
  if (elapsed < RATE_LIMIT_MS) {
    await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_MS - elapsed));
  }
  lastRequestTime = Date.now();
}

/**
 * Sleep helper
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Fetch time_series data for a single pair with retry on 429
 * @param {string} symbol - e.g. 'EUR/USD'
 * @param {string} interval - Twelve Data interval: '1h', '4h', '1day', '1week', '1month'
 * @param {string} apiKey - Twelve Data API key
 * @param {number} outputsize - Number of data points (default 2 for log return calculation)
 * @returns {Promise<Object>} - Twelve Data response
 */
async function fetchTimeSeries(symbol, interval, apiKey, outputsize = 2) {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    await rateLimitWait();

    const params = new URLSearchParams({
      symbol,
      interval,
      outputsize: String(outputsize),
      apikey: apiKey,
      order: 'ASC',
    });

    const url = `${BASE_URL}/time_series?${params.toString()}`;
    const response = await fetch(url);

    // Rate limited — wait and retry with exponential backoff
    if (response.status === 429) {
      const retryMs = RETRY_BASE_MS * Math.pow(2, attempt);
      console.warn(`[market-data] 429 rate limit for ${symbol} (${interval}), retry ${attempt + 1}/${MAX_RETRIES} in ${retryMs}ms`);
      lastRequestTime = Date.now();
      await sleep(retryMs);
      continue;
    }

    if (!response.ok) {
      throw new Error(`Twelve Data HTTP ${response.status} for ${symbol}`);
    }

    const data = await response.json();

    if (data.status === 'error') {
      throw new Error(`Twelve Data error for ${symbol}: ${data.message || 'Unknown error'}`);
    }

    return data;
  }

  throw new Error(`Twelve Data: max retries exceeded for ${symbol} (${interval})`);
}

/**
 * Fetch OHLC data for all 7 major pairs for a given timeframe
 * @param {string} timeframe - '1h', '4h', '1d', '1w', '1m'
 * @param {string} apiKey - Twelve Data API key
 * @returns {Promise<Object>} - { pairSymbol: { close: number, previousClose: number }[] }
 */
async function fetchAllPairs(timeframe, apiKey) {
  const interval = TIMEFRAME_MAP[timeframe];
  if (!interval) {
    throw new Error(`Invalid timeframe: ${timeframe}. Use one of: ${Object.keys(TIMEFRAME_MAP).join(', ')}`);
  }

  const results = {};

  for (const pair of PAIRS) {
    try {
      const data = await fetchTimeSeries(pair.symbol, interval, apiKey, 2);

      if (data.values && data.values.length >= 2) {
        // values[0] = most recent, values[1] = previous
        // We requested ASC order, so values[0] = oldest, values[1] = newest
        results[pair.symbol] = {
          base: pair.base,
          quote: pair.quote,
          currentClose: parseFloat(data.values[1].close),
          previousClose: parseFloat(data.values[0].close),
          datetime: data.values[1].datetime,
          previousDatetime: data.values[0].datetime,
        };
      } else if (data.values && data.values.length === 1) {
        // Only one data point available — use it with a fallback
        results[pair.symbol] = {
          base: pair.base,
          quote: pair.quote,
          currentClose: parseFloat(data.values[0].close),
          previousClose: parseFloat(data.values[0].close), // No previous data
          datetime: data.values[0].datetime,
          previousDatetime: data.values[0].datetime,
          insufficientData: true,
        };
      } else {
        console.warn(`[market-data] No data for ${pair.symbol} (${timeframe})`);
      }
    } catch (err) {
      console.error(`[market-data] Failed to fetch ${pair.symbol} (${timeframe}):`, err.message);
    }
  }

  return results;
}

/**
 * Fetch all timeframes for all pairs
 * @param {string} apiKey - Twelve Data API key
 * @returns {Promise<Object>} - { timeframe: { pairData } }
 */
async function fetchAllTimeframes(apiKey) {
  const timeframes = ['1h', '4h', '1d', '1w', '1m'];
  const results = {};

  for (const tf of timeframes) {
    try {
      results[tf] = await fetchAllPairs(tf, apiKey);
      console.log(`[market-data] Fetched ${tf} data for ${Object.keys(results[tf]).length} pairs`);
    } catch (err) {
      console.error(`[market-data] Failed to fetch timeframe ${tf}:`, err.message);
      results[tf] = {};
    }
  }

  return results;
}

module.exports = {
  fetchTimeSeries,
  fetchAllPairs,
  fetchAllTimeframes,
};
