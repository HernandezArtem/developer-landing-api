const I18N = {
  ru: {
    meta: {
      title: 'Бэкенд-сервис для лендинг-презентации разработчика',
      description: 'Backend-разработчик. Пишу REST API, проектирую архитектуру, интегрирую сервисы.',
    },
    nav: { about: 'Обо мне', stack: 'Стек', projects: 'Проекты', contact: 'Связаться', menu: 'Меню' },
    hero: {
      badge: 'Открыт для проектов',
      greeting: 'Привет, я',
      role: 'Backend Developer / DBA',
      bio: 'Занимаюсь серверной частью — строю API, проектирую базы данных и слежу, чтобы всё не падало в продакшене. Люблю Python/PHP и чистый код, не люблю таблицы без индексов.',
      exp: 'года опыта',
      projects: 'проектов',
      coffee: 'кофе',
      write: 'Написать',
      viewProjects: 'Проекты',
      location: 'Россия',
      scroll: 'Вниз',
    },
    stack: {
      eyebrow: '/// Стек',
      title: 'Что использую',
      subtitle: 'Не весь список — только то, с чем работаю регулярно',
      python: 'FastAPI, asyncio, Pydantic — каждый день',
      php: 'Выше среднего. Eloquent, Queues',
      bitrix: 'Создание сайтов, интеграции с CRM, кастомные модули',
      pg: 'SQL вручную, EXPLAIN ANALYZE — знакомый',
      mysql: 'SQLAlchemy, схемы и индексы — в продакшене на этом проекте',
      api: 'Проектирование, документация, Swagger — основной фокус',
    },
    projects: {
      eyebrow: '/// Проекты',
      title: 'Проекты',
      subtitle: 'Три проекта, где я принимал полноценное участие в разработке:',
      p1title: 'CRM для медицинской клиники',
      p1text: 'REST API для записи пациентов, история визитов, JWT-авторизация, разграничение ролей. 60+ эндпоинтов, интеграция с расписанием врачей.',
      p1note: '<span class="mono">// Что было сложно:</span> конкурентные записи к одному врачу — решили через SELECT FOR UPDATE + advisory locks.',
      p2title: 'Сайт по теме — «Недвижимость»',
      p2text: 'Сайт на 1С-Битрикс: каталог объектов на продажу и аренду, интеграция с самописной CRM заказчика.',
      p3title: 'Telegram-бот для VPS',
      p3text: 'Приём оплаты, уведомления, интеграция с учётной системой через REST.',
    },
    contact: {
      eyebrow: '/// Связь',
      title: 'Напишите мне',
      intro: 'Есть проект, вопрос или просто хотите поговорить о коде — заполните форму. Обычно отвечаю в течение дня.',
      formTitle: 'Форма обращения',
      formSub: 'AI проанализирует сообщение и предложит персональный ответ',
      name: 'Имя',
      phone: 'Телефон',
      email: 'Email',
      message: 'Сообщение',
      namePh: 'Иван Иванов',
      phonePh: '+7 (ХХХ)-ХХХ-ХХХХ',
      emailPh: 'ivan@example.com',
      commentPh: 'Расскажите о задаче или проекте...',
      submit: 'Отправить сообщение',
      loading: 'Сообщение набирается',
      successTitle: 'Сообщение отправлено!',
      successNote: 'Копия письма отправлена на ваш email.',
      reset: 'Отправить ещё',
    },
    footer: { copy: '© 2026 Артём Hernandez', tagline: 'Люблю BMW и только!' },
    heroFirstName: 'Артём',
    heroLastName: 'Hernandez',
    heroFullName: 'Артём Hernandez',
    heroInitials: 'АН',
    validation: {
      nameRequired: 'Укажите имя',
      nameMin: 'Минимум 2 символа',
      nameMax: 'Максимум 100 символов',
      nameChars: 'Только буквы и дефис',
      phoneRequired: 'Укажите телефон',
      phoneIncomplete: 'Введите номер полностью',
      emailRequired: 'Укажите email',
      emailInvalid: 'Неверный email',
      emailLatin: 'Email только латинскими буквами и цифрами (a-z, 0-9, @, точка)',
      commentRequired: 'Напишите сообщение',
      commentMin: 'Минимум 10 символов',
      commentMax: 'Максимум 2000 символов',
    },
    errors: {
      rateLimit: 'Слишком много запросов. Попробуйте позже.',
      generic: 'Что-то пошло не так. Попробуйте ещё раз.',
      network: 'Нет соединения с сервером. Проверьте интернет.',
    },
  },
  en: {
    meta: {
      title: 'Developer Landing API — Portfolio',
      description: 'Backend developer. REST APIs, architecture, service integrations.',
    },
    nav: { about: 'About', stack: 'Stack', projects: 'Projects', contact: 'Contact', menu: 'Menu' },
    hero: {
      badge: 'Open to projects',
      greeting: 'Hi, I\'m',
      role: 'Backend Developer / DBA',
      bio: 'I build server-side systems — APIs, database design, and keeping production stable. I like Python/PHP and clean code; I dislike tables without indexes.',
      exp: 'years experience',
      projects: 'projects',
      coffee: 'coffee',
      write: 'Get in touch',
      viewProjects: 'Projects',
      location: 'Russia',
      scroll: 'Scroll down',
    },
    stack: {
      eyebrow: '/// Stack',
      title: 'What I use',
      subtitle: 'Not the full list — only what I work with regularly',
      python: 'FastAPI, asyncio, Pydantic — daily',
      php: 'Above average. Eloquent, Queues',
      bitrix: 'Sites, CRM integrations, custom modules',
      pg: 'Hand-written SQL, EXPLAIN ANALYZE',
      mysql: 'SQLAlchemy, schemas and indexes — production on this project',
      api: 'Design, documentation, Swagger — main focus',
    },
    projects: {
      eyebrow: '/// Projects',
      title: 'Projects',
      subtitle: 'Three projects where I had a full development role:',
      p1title: 'Medical clinic CRM',
      p1text: 'REST API for appointments, visit history, JWT auth, role-based access. 60+ endpoints, doctor schedule integration.',
      p1note: '<span class="mono">// Hard part:</span> concurrent bookings for one doctor — solved with SELECT FOR UPDATE + advisory locks.',
      p2title: 'Real estate website',
      p2text: '1C-Bitrix site with sale/rent listings and integration with the client\'s custom CRM.',
      p3title: 'Telegram bot for VPS',
      p3text: 'Payments, notifications, integration with billing via REST.',
    },
    contact: {
      eyebrow: '/// Contact',
      title: 'Write to me',
      intro: 'Have a project, a question, or want to talk code — fill out the form. I usually reply within a day.',
      formTitle: 'Contact form',
      formSub: 'AI will analyze your message and suggest a personal reply',
      name: 'Name',
      phone: 'Phone',
      email: 'Email',
      message: 'Message',
      namePh: 'John Smith',
      phonePh: '+7 (XXX)-XXX-XXXX',
      emailPh: 'john@example.com',
      commentPh: 'Tell me about your task or project...',
      submit: 'Send message',
      loading: 'Composing reply',
      successTitle: 'Message sent!',
      successNote: 'A copy was sent to your email.',
      reset: 'Send another',
    },
    footer: { copy: '© 2026 Artem Hernandez', tagline: 'BMW M colors only!' },
    heroFirstName: 'Artem',
    heroLastName: 'Hernandez',
    heroFullName: 'Artem Hernandez',
    heroInitials: 'AH',
    validation: {
      nameRequired: 'Enter your name',
      nameMin: 'At least 2 characters',
      nameMax: 'Maximum 100 characters',
      nameChars: 'Letters and hyphens only',
      phoneRequired: 'Enter your phone',
      phoneIncomplete: 'Enter the full number',
      emailRequired: 'Enter your email',
      emailInvalid: 'Invalid email',
      emailLatin: 'Email must use Latin letters and digits only (a-z, 0-9, @, dot)',
      commentRequired: 'Write a message',
      commentMin: 'At least 10 characters',
      commentMax: 'Maximum 2000 characters',
    },
    errors: {
      rateLimit: 'Too many requests. Please try again later.',
      generic: 'Something went wrong. Please try again.',
      network: 'No connection to the server. Check your internet.',
    },
  },
};

let currentLang = localStorage.getItem('lang') || 'ru';
if (!I18N[currentLang]) currentLang = 'ru';

function t(key) {
  const parts = key.split('.');
  let node = I18N[currentLang];
  for (const p of parts) {
    if (!node || node[p] === undefined) return key;
    node = node[p];
  }
  return node;
}

function getLang() {
  return currentLang;
}

function formatRateLimitError(seconds) {
  const s = Math.max(1, Number(seconds) || 0);
  if (s >= 60) {
    const m = Math.max(1, Math.round(s / 60));
    return currentLang === 'en'
      ? `Too many requests. Try again in ${m} min.`
      : `Слишком много запросов. Попробуйте через ${m} мин.`;
  }
  return currentLang === 'en'
    ? `Too many requests. Try again in ${s} sec.`
    : `Слишком много запросов. Попробуйте через ${s} сек.`;
}

function setLang(lang) {
  if (!I18N[lang]) return;
  currentLang = lang;
  localStorage.setItem('lang', lang);
  document.documentElement.lang = lang;
  const sw = document.getElementById('langSwitch');
  if (sw) sw.dataset.lang = lang;
  applyI18n();
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
}

function applyI18n() {
  document.title = t('meta.title');
  const metaDesc = document.querySelector('meta[name="description"]');
  if (metaDesc) metaDesc.content = t('meta.description');

  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (!key) return;
    const text = t(key);
    if (text && text !== key) el.textContent = text;
  });
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    if (!key) return;
    const html = t(key);
    if (html && html !== key) el.innerHTML = html;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (!key) return;
    const ph = t(key);
    if (ph && ph !== key) el.placeholder = ph;
  });
  document.querySelectorAll('[data-i18n-aria]').forEach(el => {
    const key = el.getAttribute('data-i18n-aria');
    if (!key) return;
    const label = t(key);
    if (label && label !== key) el.setAttribute('aria-label', label);
  });

  const charCount = document.getElementById('charCount');
  const textarea = document.getElementById('f-comment');
  if (charCount && textarea) {
    charCount.textContent = textarea.value.length + ' / 2000';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => setLang(btn.dataset.lang));
  });
  setLang(currentLang);
});
