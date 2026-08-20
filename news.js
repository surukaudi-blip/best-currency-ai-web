/* ============================================================
   BEST CURRENCY AI — NEWS FEED LOADER
   RSS feeds from Cointelegraph & Decrypt via rss2json API
   ============================================================ */
(function () {
  'use strict';

  /* ---------- configuration ---------- */
  var RSS2JSON = 'https://api.rss2json.com/v1/api.json?rss_url=';
  var FEEDS = {
    ct: { url: 'https://cointelegraph.com/rss',  listId: 'ct-news-list', max: 8 },
    dc: { url: 'https://decrypt.co/feed',         listId: 'dc-news-list', max: 8 }
  };

  /* ---------- helpers ---------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function timeAgo(dateStr) {
    var now = Date.now();
    var then = new Date(dateStr).getTime();
    if (!isFinite(then)) return '';
    var diff = Math.max(0, now - then);
    var mins  = Math.floor(diff / 60000);
    var hours = Math.floor(diff / 3600000);
    var days  = Math.floor(diff / 86400000);
    if (mins < 60)  return mins + 'm ago';
    if (hours < 24) return hours + 'h ago';
    return days + 'd ago';
  }

  function extractImage(item) {
    // Try media:content, then enclosure, then thumbnail
    if (item.enclosure && item.enclosure.link) return item.enclosure.link;
    if (item.thumbnail) return item.thumbnail;
    // Fallback: extract from description HTML
    var m = String(item.description || '').match(/<img[^>]+src="([^"]+)"/);
    return m ? m[1] : '';
  }

  /* ---------- render one feed ---------- */
  function renderFeed(key, data) {
    var cfg   = FEEDS[key];
    var el    = document.getElementById(cfg.listId);
    if (!el)  return;

    if (!data || data.status !== 'ok' || !data.items || !data.items.length) {
      el.innerHTML = '<p style="color:var(--muted);padding:12px 0;">No articles available right now. Try refreshing later.</p>';
      return;
    }

    var items = data.items.slice(0, cfg.max);
    var html  = '';

    for (var i = 0; i < items.length; i++) {
      var item   = items[i];
      var img    = extractImage(item);
      var title  = esc(item.title);
      var link   = esc(item.link);
      var source = esc(item.author || key === 'ct' ? 'Cointelegraph' : 'Decrypt');
      var time   = timeAgo(item.pubDate);

      html += '<a class="news-item" href="' + link + '" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">';

      if (img) {
        html += '<img class="news-item-img" src="' + esc(img) + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">';
      }

      html += '<div class="news-item-content">';
      html += '<div class="news-item-title">' + title + '</div>';
      html += '<div class="news-item-meta">' + source;
      if (time) html += ' · ' + time;
      html += '</div>';
      html += '</div>';
      html += '</a>';
    }

    el.innerHTML = html;
  }

  /* ---------- fetch one feed ---------- */
  function loadFeed(key) {
    var cfg = FEEDS[key];
    var el  = document.getElementById(cfg.listId);
    if (!el) return;

    var api = RSS2JSON + encodeURIComponent(cfg.url);

    fetch(api, { cache: 'no-store' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        renderFeed(key, data);
      })
      .catch(function (err) {
        console.warn('[news] Failed to load ' + key + ':', err);
        el.innerHTML = '<p style="color:var(--muted);padding:12px 0;">Failed to load feed. Please try again later.</p>';
      });
  }

  /* ---------- init ---------- */
  function init() {
    var keys = Object.keys(FEEDS);
    for (var i = 0; i < keys.length; i++) {
      loadFeed(keys[i]);
    }
  }

  // Run when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Auto-refresh every 5 minutes
  setInterval(function () {
    var keys = Object.keys(FEEDS);
    for (var i = 0; i < keys.length; i++) {
      loadFeed(keys[i]);
    }
  }, 300000);

})();
