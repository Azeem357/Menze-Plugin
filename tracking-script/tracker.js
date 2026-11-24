(function () {
  const PLUGIN_BACKEND = 'https://menze-plugin.onrender.com';

  // Generate or get session ID
  function getSessionId() {
    let sid = sessionStorage.getItem('menze_session_id');
    if (!sid) {
      sid = 'sess_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
      sessionStorage.setItem('menze_session_id', sid);
    }
    return sid;
  }

  function getAttribution() {
    const params = new URLSearchParams(window.location.search);
    const fields = ['utm_source', 'utm_medium', 'utm_campaign'];

    fields.forEach((field) => {
      const value = params.get(field);
      if (value) sessionStorage.setItem(`menze_${field}`, value);
    });

    return fields.reduce((attribution, field) => {
      attribution[field] = sessionStorage.getItem(`menze_${field}`) || '';
      return attribution;
    }, {});
  }

  // Send event to plugin backend
  function sendEvent(eventType, data = {}) {
    const payload = {
      session_id: getSessionId(),
      event_type: eventType,
      page_url: window.location.href,
      referrer: document.referrer || '',
      device_type: /mobile/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
      occurred_at: new Date().toISOString(),
      ...getAttribution(),
      ...data,
    };

    fetch(`${PLUGIN_BACKEND}/api/events/capture/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,
    }).then((response) => {
      if (!response.ok) {
        console.warn(
          `Menze analytics event was rejected (${response.status}).`
        );
      }
    }).catch((error) => {
      console.warn('Menze analytics event could not be sent.', error);
    });
  }

  // Track page view on load
  sendEvent('page_view');

  // Expose global tracker for manual events
  window.MenzeTracker = {
    trackAddToCart: function (productId) {
      sendEvent('add_to_cart', { product_id: productId });
    },
    trackCheckout: function () {
      sendEvent('checkout_start');
    },
    trackProductView: function (productId) {
      sendEvent('product_view', { product_id: productId });
    },
    trackPurchase: function (orderId, total, userId) {
      sendEvent('purchase', {
        order_id: String(orderId),
        revenue: total,
        user_id: userId == null ? getSessionId() : String(userId),
      });
    },
    trackRegistration: function (userId) {
      sendEvent('register', {
        user_id: userId == null ? getSessionId() : String(userId),
      });
    },
  };
})();