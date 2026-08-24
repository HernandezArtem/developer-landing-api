const API = '/api';

/* ── Scroll reveal ───────────────────────────────────── */
const revealEls = document.querySelectorAll('.reveal');
if (revealEls.length) {
  const revealObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        revealObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  revealEls.forEach(el => revealObs.observe(el));
}

/* ── Nav scroll ──────────────────────────────────────── */
window.addEventListener('scroll', () => {
  const nav = document.getElementById('nav');
  nav.classList.toggle('scrolled', window.scrollY > 10);
}, { passive: true });

/* ── Burger ──────────────────────────────────────────── */
const burger   = document.getElementById('burger');
const navLinks = document.getElementById('navLinks');
burger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});
navLinks.querySelectorAll('a').forEach(a =>
  a.addEventListener('click', () => navLinks.classList.remove('open'))
);

/* ── Char counter ────────────────────────────────────── */
const textarea  = document.getElementById('f-comment');
const charCount = document.getElementById('charCount');
textarea.addEventListener('input', () => {
  const n = textarea.value.length;
  charCount.textContent = n + ' / 2000';
  charCount.style.color = n > 1800 ? 'var(--red)' : '';
});

/* ── Smooth scroll with nav offset ──────────────────── */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const t = document.querySelector(a.getAttribute('href'));
    if (!t) return;
    e.preventDefault();
    window.scrollTo({ top: t.getBoundingClientRect().top + scrollY - 70, behavior: 'smooth' });
  });
});

/* ═══════════════════════════════════════════════════════
   VALIDATION
═══════════════════════════════════════════════════════ */
const ASCII_EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,63}$/;

const rules = {
  name: v => !v.trim() ? t('validation.nameRequired') : v.trim().length < 2 ? t('validation.nameMin') : v.trim().length > 100 ? t('validation.nameMax') : /[^a-zA-Zа-яА-ЯёЁ\s\-']/.test(v.trim()) ? t('validation.nameChars') : null,
  email: v => {
    const s = v.trim();
    if (!s) return t('validation.emailRequired');
    if (/[^\x00-\x7F]/.test(s)) return t('validation.emailLatin');
    if (!ASCII_EMAIL_RE.test(s)) return t('validation.emailInvalid');
    return null;
  },
  comment: v => !v.trim() ? t('validation.commentRequired') : v.trim().length < 10 ? t('validation.commentMin') : v.trim().length > 2000 ? t('validation.commentMax') : null,
};

function setErr(id, msg) {
  const g = document.getElementById('fg-' + id);
  const e = document.getElementById('e-' + id);
  if (!g || !e) return;
  g.classList.add('has-err'); g.classList.remove('is-ok');
  e.textContent = msg;
}
function setOk(id) {
  const g = document.getElementById('fg-' + id);
  const e = document.getElementById('e-' + id);
  if (!g || !e) return;
  g.classList.remove('has-err'); g.classList.add('is-ok');
  e.textContent = '';
}
function clearState(id) {
  const g = document.getElementById('fg-' + id);
  const e = document.getElementById('e-' + id);
  if (!g || !e) return;
  g.classList.remove('has-err', 'is-ok');
  e.textContent = '';
}

function refreshVisibleErrors() {
  ['name', 'email', 'comment'].forEach(id => {
    const g = document.getElementById('fg-' + id);
    if (!g || !g.classList.contains('has-err')) return;
    const el = document.getElementById('f-' + id);
    if (!el) return;
    const err = rules[id](el.value);
    if (err) setErr(id, err);
  });

  const consentGroup = document.getElementById('fg-consent');
  if (consentGroup && consentGroup.classList.contains('has-err')) {
    setErr('consent', t('validation.consentRequired'));
  }

  if (formError && !formError.hidden && formErrorKind) {
    if (formErrorKind === 'rateLimit') {
      showError(formatRateLimitError(formErrorRetryAfter), 'rateLimit', formErrorRetryAfter);
    } else {
      showError(t('errors.' + formErrorKind), formErrorKind);
    }
  }
}

document.addEventListener('langchange', refreshVisibleErrors);

['name','email','comment'].forEach(id => {
  const el = document.getElementById('f-' + id);
  if (!el) return;
  el.addEventListener('blur', () => { const err = rules[id](el.value); err ? setErr(id, err) : setOk(id); });
  el.addEventListener('input', () => { if (document.getElementById('fg-'+id).classList.contains('has-err')) { if (!rules[id](el.value)) setOk(id); } });
});

const consentInput = document.getElementById('f-consent');
if (consentInput) {
  consentInput.addEventListener('change', () => {
    if (consentInput.checked) setOk('consent');
  });
}

/* ═══════════════════════════════════════════════════════
   COOKIE BANNER (stub)
═══════════════════════════════════════════════════════ */
const COOKIE_KEY = 'cookie_consent';
const cookieBanner = document.getElementById('cookieBanner');
const cookieAccept = document.getElementById('cookieAccept');
const cookieReject = document.getElementById('cookieReject');

function hideCookieBanner() {
  if (!cookieBanner) return;
  cookieBanner.hidden = true;
  cookieBanner.classList.remove('is-visible', 'is-leaving', 'is-accepted');
}

function showCookieBanner() {
  if (!cookieBanner) return;
  cookieBanner.hidden = false;
  cookieBanner.classList.remove('is-leaving', 'is-accepted');
  requestAnimationFrame(() => {
    cookieBanner.classList.add('is-visible');
  });
}

function dismissCookieBanner(animated) {
  if (!cookieBanner) return;
  if (!animated) {
    hideCookieBanner();
    return;
  }
  cookieBanner.classList.add('is-leaving');
  cookieBanner.classList.remove('is-visible');
  const done = () => hideCookieBanner();
  cookieBanner.addEventListener('transitionend', done, { once: true });
  setTimeout(done, 450);
}

function setCookieConsent(value) {
  try {
    localStorage.setItem(COOKIE_KEY, value);
  } catch (_) { /* ignore */ }

  if (value === 'accepted' && cookieBanner) {
    cookieBanner.classList.add('is-accepted');
    setTimeout(() => dismissCookieBanner(true), 1100);
    return;
  }
  dismissCookieBanner(true);
}

(function initCookieBanner() {
  if (!cookieBanner) return;
  let stored = null;
  try {
    stored = localStorage.getItem(COOKIE_KEY);
  } catch (_) { /* ignore */ }
  if (stored === 'accepted' || stored === 'rejected') {
    hideCookieBanner();
    return;
  }
  showCookieBanner();
  if (cookieAccept) cookieAccept.addEventListener('click', () => setCookieConsent('accepted'));
  if (cookieReject) cookieReject.addEventListener('click', () => setCookieConsent('rejected'));
})();

/* ═══════════════════════════════════════════════════════
   FORM SUBMIT
═══════════════════════════════════════════════════════ */
const form        = document.getElementById('contactForm');
const submitBtn   = document.getElementById('submitBtn');
const formError   = document.getElementById('formError');
const formSuccess = document.getElementById('formSuccess');
const successText = document.getElementById('successText');
const resetBtn    = document.getElementById('resetBtn');
let formErrorKind = null;
let formErrorRetryAfter = 0;

function setLoading(on) {
  submitBtn.disabled = on;
  submitBtn.classList.toggle('loading', on);
}

const PROMPT_LEAK_MARKERS = [
  '2-3 предложения',
  'обратись к отправителю',
  'ответ от лица',
  'на русском языке',
  'я помощник',
  'меня зовут',
  'assistant of artem',
  'помощник артёма',
  'помощник артем',
];

function sanitizeAutoReply(reply) {
  if (!reply || typeof reply !== 'string') return '';
  const text = reply.trim();
  if (!text) return '';
  const lower = text.toLowerCase();
  if (PROMPT_LEAK_MARKERS.some(m => lower.includes(m))) return '';
  return text;
}

function showSuccess(reply) {
  form.hidden = true;
  formSuccess.hidden = false;
  const clean = sanitizeAutoReply(reply);
  if (clean) {
    successText.textContent = clean;
    successText.hidden = false;
  } else {
    successText.textContent = '';
    successText.hidden = true;
  }
  formSuccess.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showError(msg, kind, retryAfter) {
  formErrorKind = kind || null;
  formErrorRetryAfter = Number(retryAfter) || 0;
  formError.textContent = msg;
  formError.hidden = false;
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  formError.hidden = true;
  formErrorKind = null;
  formErrorRetryAfter = 0;

  const fields = ['name','email','comment'];
  let hasErr = false;
  fields.forEach(id => {
    const el = document.getElementById('f-' + id);
    const err = rules[id](el.value);
    err ? (setErr(id, err), hasErr = true) : setOk(id);
  });

  if (!consentInput || !consentInput.checked) {
    setErr('consent', t('validation.consentRequired'));
    hasErr = true;
  } else {
    setOk('consent');
  }

  if (hasErr) return;

  const body = {
    name:    document.getElementById('f-name').value.trim(),
    email:   document.getElementById('f-email').value.trim(),
    comment: document.getElementById('f-comment').value.trim(),
    privacy_consent: true,
    locale:  getLang(),
  };

  setLoading(true);
  try {
    const res  = await fetch(API + '/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (res.ok && data.success) {
      showSuccess(data.ai_analysis?.auto_reply);
    } else if (res.status === 422) {
      showError(data.error || t('errors.generic'), data.error ? null : 'generic');
    } else if (res.status === 429) {
      showError(formatRateLimitError(data.retry_after_seconds), 'rateLimit', data.retry_after_seconds);
    } else {
      showError(data.error || t('errors.generic'), data.error ? null : 'generic');
    }
  } catch {
    showError(t('errors.network'), 'network');
  } finally {
    setLoading(false);
  }
});

resetBtn.addEventListener('click', () => {
  form.reset();
  charCount.textContent = '0 / 2000';
  ['name','email','comment','consent'].forEach(clearState);
  form.hidden = false;
  formSuccess.hidden = true;
  successText.hidden = true;
  successText.textContent = '';
  formError.hidden = true;
  formErrorKind = null;
  formErrorRetryAfter = 0;
});
