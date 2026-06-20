const API = '/api';

/* ── Custom M-scrollbar (tri-color gradient like submit btn) ─ */
(function initMScrollbar() {
  const track = document.getElementById('mScrollbar');
  const thumb = document.getElementById('mScrollbarThumb');
  if (!track || !thumb) return;

  function update() {
    const doc = document.documentElement;
    const viewH = doc.clientHeight;
    const scrollH = doc.scrollHeight;
    const maxScroll = scrollH - viewH;

    if (maxScroll <= 0) {
      track.classList.remove('visible');
      return;
    }

    track.classList.add('visible');
    const trackH = track.clientHeight;
    const thumbH = Math.max(48, (viewH / scrollH) * trackH);
    const maxTop = trackH - thumbH;
    const top = (doc.scrollTop / maxScroll) * maxTop;

    thumb.style.height = thumbH + 'px';
    thumb.style.top = top + 'px';
  }

  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  update();
})();

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

/* ── Phone mask +7 (XXX)-XXX-XXXX ─────────────────── */
const phoneInput = document.getElementById('f-phone');
let phoneDigits = '';

function normalizePhoneDigits(raw) {
  let d = String(raw).replace(/\D/g, '');
  if (!d) return '';
  while (d.length > 10 && (d[0] === '7' || d[0] === '8')) d = d.slice(1);
  if (d.length === 11 && (d[0] === '7' || d[0] === '8')) d = d.slice(1);
  return d.slice(0, 10);
}

function getPhoneDigits(value) {
  return normalizePhoneDigits(value);
}

function formatPhone(digits) {
  if (!digits.length) return '';
  let masked = '+7';
  masked += ' (' + digits.slice(0, 3);
  if (digits.length >= 3) masked += ')';
  if (digits.length > 3) masked += '-' + digits.slice(3, 6);
  if (digits.length > 6) masked += '-' + digits.slice(6, 10);
  return masked;
}

function renderPhone() {
  const formatted = formatPhone(phoneDigits);
  phoneInput.value = formatted;
  phoneInput.setSelectionRange(formatted.length, formatted.length);
}

phoneInput.addEventListener('paste', e => {
  e.preventDefault();
  const text = (e.clipboardData || window.clipboardData).getData('text');
  phoneDigits = normalizePhoneDigits(text);
  renderPhone();
});

phoneInput.addEventListener('keydown', e => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;

  const hasSelection = phoneInput.selectionStart !== phoneInput.selectionEnd;

  if (e.key === 'Backspace' || e.key === 'Delete') {
    e.preventDefault();
    if (hasSelection) {
      phoneDigits = '';
    } else if (e.key === 'Backspace') {
      phoneDigits = phoneDigits.slice(0, -1);
    }
    renderPhone();
    return;
  }

  if (e.key.length === 1) {
    e.preventDefault();
    if (/\d/.test(e.key)) {
      if (hasSelection) phoneDigits = '';
      if (phoneDigits.length < 10) {
        phoneDigits += e.key;
        renderPhone();
      }
    }
  }
});

// Fallback for mobile keyboards that may skip keydown
phoneInput.addEventListener('input', () => {
  const parsed = normalizePhoneDigits(phoneInput.value);
  phoneDigits = parsed;
  const formatted = formatPhone(phoneDigits);
  if (phoneInput.value !== formatted) renderPhone();
});

phoneInput.addEventListener('blur', () => {
  const err = rules.phone(phoneInput.value);
  err ? setErr('phone', err) : setOk('phone');
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
const rules = {
  name: v => !v.trim() ? t('validation.nameRequired') : v.trim().length < 2 ? t('validation.nameMin') : v.trim().length > 100 ? t('validation.nameMax') : /[^a-zA-Zа-яА-ЯёЁ\s\-']/.test(v.trim()) ? t('validation.nameChars') : null,
  phone: v => {
    if (!v.trim() && !phoneDigits.length) return t('validation.phoneRequired');
    if (phoneDigits.length < 10) return t('validation.phoneIncomplete');
    return null;
  },
  email: v => !v.trim() ? t('validation.emailRequired') : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()) ? t('validation.emailInvalid') : null,
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

['name','email','comment'].forEach(id => {
  const el = document.getElementById('f-' + id);
  if (!el) return;
  el.addEventListener('blur', () => { const err = rules[id](el.value); err ? setErr(id, err) : setOk(id); });
  el.addEventListener('input', () => { if (document.getElementById('fg-'+id).classList.contains('has-err')) { if (!rules[id](el.value)) setOk(id); } });
});

// Phone: validate on input after mask applied
phoneInput.addEventListener('input', () => {
  if (document.getElementById('fg-phone').classList.contains('has-err')) {
    if (!rules.phone(phoneInput.value)) setOk('phone');
  }
});

/* ═══════════════════════════════════════════════════════
   FORM SUBMIT
═══════════════════════════════════════════════════════ */
const form        = document.getElementById('contactForm');
const submitBtn   = document.getElementById('submitBtn');
const formError   = document.getElementById('formError');
const formSuccess = document.getElementById('formSuccess');
const successText = document.getElementById('successText');
const resetBtn    = document.getElementById('resetBtn');

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

function showError(msg) {
  formError.textContent = msg;
  formError.hidden = false;
}

function cleanValidationMessage(msg) {
  return String(msg)
    .replace(/^Value error,\s*/i, '')
    .replace(/^value is not a valid email address:\s*/i, '')
    .trim();
}

form.addEventListener('submit', async e => {
  e.preventDefault();
  formError.hidden = true;

  const fields = ['name','phone','email','comment'];
  let hasErr = false;
  fields.forEach(id => {
    const el = document.getElementById('f-' + id);
    const err = rules[id](el.value);
    err ? (setErr(id, err), hasErr = true) : setOk(id);
  });
  if (hasErr) return;

  const body = {
    name:    document.getElementById('f-name').value.trim(),
    phone:   phoneDigits.length === 10 ? '+7' + phoneDigits : '',
    email:   document.getElementById('f-email').value.trim(),
    comment: document.getElementById('f-comment').value.trim(),
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
    } else if (res.status === 422 && data.details) {
      data.details.forEach(({ field, message }) => {
        const id = field.replace(/\s.*/, '').toLowerCase();
        if (rules[id]) setErr(id, cleanValidationMessage(message));
      });
    } else if (res.status === 429) {
      showError(data.error || t('errors.rateLimit'));
    } else {
      showError(data.error || t('errors.generic'));
    }
  } catch {
    showError(t('errors.network'));
  } finally {
    setLoading(false);
  }
});

resetBtn.addEventListener('click', () => {
  form.reset();
  phoneDigits = '';
  charCount.textContent = '0 / 2000';
  ['name','phone','email','comment'].forEach(clearState);
  form.hidden = false;
  formSuccess.hidden = true;
  successText.hidden = true;
  successText.textContent = '';
  formError.hidden = true;
});


