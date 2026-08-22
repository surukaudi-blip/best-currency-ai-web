'use strict';

/**
 * Currency Strength MVP — Configuration
 */

const CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'NZD', 'CAD'];

const PAIRS = [
  { symbol: 'EUR/USD', base: 'EUR', quote: 'USD' },
  { symbol: 'GBP/USD', base: 'GBP', quote: 'USD' },
  { symbol: 'USD/JPY', base: 'USD', quote: 'JPY' },
  { symbol: 'USD/CHF', base: 'USD', quote: 'CHF' },
  { symbol: 'AUD/USD', base: 'AUD', quote: 'USD' },
  { symbol: 'NZD/USD', base: 'NZD', quote: 'USD' },
  { symbol: 'USD/CAD', base: 'USD', quote: 'CAD' },
];

// Twelve Data interval mapping
const TIMEFRAME_MAP = {
  '1h': '1h',
  '4h': '4h',
  '1d': '1day',
  '1w': '1week',
  '1m': '1month',
};

// MTF composite weights
const MTF_WEIGHTS = {
  '1h': 0.10,
  '4h': 0.20,
  '1d': 0.30,
  '1w': 0.25,
  '1m': 0.15,
};

// Timeframe labels for display
const TIMEFRAME_LABELS = {
  '1h': '1 Hour',
  '4h': '4 Hour',
  '1d': '1 Day',
  '1w': '1 Week',
  '1m': '1 Month',
};

module.exports = {
  CURRENCIES,
  PAIRS,
  TIMEFRAME_MAP,
  MTF_WEIGHTS,
  TIMEFRAME_LABELS,
};
