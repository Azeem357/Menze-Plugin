(function () {
  const PLUGIN_BACKEND = 'https://menze-plugin.onrender.com'; // change to live URL later
  const STORE_ID = 'menz-store'; // unique ID for your store

  // Generate or get session ID
  function getSessionId() {
    let sid = sessionStorage.getItem('menze_session_id');
    if (!sid) {
      sid = 'sess_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      sessionStorage.setItem('menze_session_id', sid);
    }
    return sid;
  }

  // Send event to plugin backend
  function sendEvent(eventType, data = {}) {
    const payload = {
      store_id: STORE_ID,
      session_id: getSessionId(),
      event_type: eventType,
      page_url: window.location.href,
      referrer: document.referrer || '',
      user_agent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      ...data,
    };

    fetch(`${PLUGIN_BACKEND}/api/events/capture/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {}); // silent fail
  }

  // Track page view on load
  sendEvent('page_view');

  // Expose global tracker for manual events
  window.MenzeTracker = {
    trackAddToCart: function (productId, productName, price) {
      sendEvent('add_to_cart', {
        product_id: productId,
        product_name: productName,
        price: price,
      });
    },
    trackCheckout: function (orderId, total) {
      sendEvent('checkout', {
        order_id: orderId,
        total: total,
      });
    },
    trackProductView: function(productId, productName, price) {
    sendEvent('product_view', { product_id: productId, product_name: productName, price: price });
  },
    trackPurchase: function (orderId, total, items) {
      sendEvent('purchase', {
        order_id: orderId,
        total: total,
        items: items,
      });
    },
  };
})();