(() => {
  const menuButton = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('site-navigation');
  const setMenu = open => {
    menuButton?.setAttribute('aria-expanded', String(open));
    navigation?.classList.toggle('is-open', open);
  };
  menuButton?.addEventListener('click', () => setMenu(menuButton.getAttribute('aria-expanded') !== 'true'));
  navigation?.addEventListener('click', event => {
    if (event.target.closest('a')) setMenu(false);
  });
  const page = location.pathname.split('/').pop() || 'index.html';
  navigation?.querySelectorAll('a').forEach(link => {
    if (link.getAttribute('href') === page) link.setAttribute('aria-current', 'page');
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('.site-header')) setMenu(false);
  });

  const overlay = document.getElementById('consent-overlay');
  const preferencesButton = document.getElementById('consent-button');
  const functional = document.getElementById('consent-functional');
  const closeButton = document.getElementById('consent-close');
  const key = 'nor-consent-v1';
  let preferences = { functional: false };
  try {
    const stored = JSON.parse(localStorage.getItem(key));
    if (stored && typeof stored.functional === 'boolean') preferences = stored;
  } catch (_) { /* Use essential-only defaults if browser storage is unavailable. */ }
  let returnFocus;
  const updateMap = () => {
    const host = document.querySelector('[data-map]');
    if (!host) return;
    host.replaceChildren();
    if (preferences.functional) {
      const iframe = document.createElement('iframe');
      iframe.title = 'Kart til Hamborggata 16, Drammen';
      iframe.loading = 'lazy';
      iframe.referrerPolicy = 'no-referrer-when-downgrade';
      iframe.src = 'https://www.google.com/maps?q=Hamborggata+16,+3018+Drammen&output=embed';
      host.append(iframe);
    } else {
      const message = document.createElement('p');
      message.textContent = 'Kartet leveres av Google Maps. Vis kartet for å tillate denne eksterne tjenesten.';
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'hc-btn';
      button.textContent = 'Vis kart (Google Maps)';
      button.addEventListener('click', () => save({ functional: true }));
      host.append(message, button);
    }
  };
  const close = () => {
    if (!overlay) return;
    overlay.hidden = true;
    document.body.classList.remove('consent-open');
    if (returnFocus?.isConnected) returnFocus.focus();
  };
  const save = choice => {
    preferences = choice;
    try { localStorage.setItem(key, JSON.stringify(choice)); } catch (_) { /* Choice still applies to this page. */ }
    updateMap();
    close();
  };
  preferencesButton?.addEventListener('click', () => {
    returnFocus = document.activeElement;
    functional.checked = preferences.functional;
    overlay.hidden = false;
    document.body.classList.add('consent-open');
    closeButton.focus();
  });
  closeButton?.addEventListener('click', close);
  overlay?.addEventListener('click', event => { if (event.target === overlay) close(); });
  document.getElementById('consent-reject')?.addEventListener('click', () => save({ functional: false }));
  document.getElementById('consent-save')?.addEventListener('click', () => save({ functional: functional.checked }));
  document.getElementById('consent-accept')?.addEventListener('click', () => save({ functional: true }));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') {
      if (overlay && !overlay.hidden) close();
      setMenu(false);
      document.querySelectorAll('.service-menu[open]').forEach(menu => menu.removeAttribute('open'));
    }
    if (event.key === 'Tab' && overlay && !overlay.hidden) {
      const controls = [...overlay.querySelectorAll('button, input, a[href]')];
      const first = controls[0], last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }
  });
  updateMap();

  const topButton = document.getElementById('top');
  const updateTop = () => topButton?.classList.toggle('show', scrollY > 300);
  window.addEventListener('scroll', updateTop, { passive: true });
  topButton?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  updateTop();
  document.querySelectorAll('[data-year]').forEach(element => { element.textContent = new Date().getFullYear(); });

  const form = document.getElementById('ctf');
  form?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const status = document.getElementById('contact-status');
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    button.textContent = 'Sender …';
    status.textContent = '';
    status.classList.remove('error');
    try {
      const tokenResponse = await fetch(form.action, { credentials: 'same-origin', cache: 'no-store' });
      if (!tokenResponse.ok) throw new Error('Skjemaet er utilgjengelig. Ring +47 900 12 461 eller send e-post til post@norrengjoring.no.');
      const { token } = await tokenResponse.json();
      if (typeof token !== 'string') throw new Error('Skjemaet er utilgjengelig. Kontakt post@norrengjoring.no.');
      const data = new FormData(form);
      data.set('token', token);
      const response = await fetch(form.action, { method: 'POST', body: data, credentials: 'same-origin' });
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.error || 'Meldingen ble ikke sendt. Prøv igjen senere.');
      status.textContent = result.message;
      if (!result.test_mode) form.reset();
    } catch (error) {
      status.classList.add('error');
      status.textContent = error instanceof TypeError ? 'Ingen forbindelse. Meldingen ble ikke sendt. Prøv igjen eller kontakt post@norrengjoring.no.' : error.message;
    } finally {
      button.disabled = false;
      button.textContent = 'Send melding';
    }
  });
})();
