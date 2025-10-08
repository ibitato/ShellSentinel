(function () {
  const translations = window.TRANSLATIONS || {};
  const STORAGE_KEY = 'ahsa-language';

  const html = document.documentElement;
  const languageButtons = Array.from(document.querySelectorAll('.lang-option'));
  const menuToggle = document.querySelector('.menu-toggle');
  const navList = document.querySelector('.nav-list');

  function detectLanguage() {
    const params = new URLSearchParams(window.location.search);
    const paramLang = (params.get('lang') || '').toLowerCase();
    if (paramLang && translations[paramLang]) {
      return paramLang;
    }
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored && translations[stored]) {
      return stored;
    }
    const browser = navigator.language || navigator.userLanguage || 'en';
    const normalized = browser.slice(0, 2).toLowerCase();
    if (translations[normalized]) {
      return normalized;
    }
    return 'en';
  }

  function updateSimpleStrings(lang, map) {
    document.querySelectorAll('[data-i18n]').forEach((node) => {
      const key = node.getAttribute('data-i18n');
      const value = key.split('.').reduce((acc, part) => (acc ? acc[part] : undefined), map);
      if (typeof value === 'string') {
        node.textContent = value;
      }
    });
  }

  function renderList(containerSelector, items, renderer) {
    const container = document.querySelector(containerSelector);
    if (!container) return;
    container.innerHTML = '';
    if (!Array.isArray(items)) return;
    items.forEach((item, index) => {
      const element = renderer(item, index);
      if (element) {
        container.appendChild(element);
      }
    });
  }

  function buildCard(item) {
    const card = document.createElement('article');
    card.className = 'card';

    const icon = document.createElement('span');
    icon.className = 'card-icon';
    icon.textContent = item.icon || '✨';

    const title = document.createElement('h3');
    title.className = 'card-title';
    title.textContent = item.title || '';

    const body = document.createElement('p');
    body.className = 'card-body';
    body.textContent = item.body || '';

    card.append(icon, title, body);
    return card;
  }

  function buildGalleryItem(item) {
    const figure = document.createElement('figure');
    figure.className = 'gallery-item';

    if (item.src) {
      const img = document.createElement('img');
      img.src = item.src;
      img.alt = item.alt || '';
      img.loading = 'lazy';
      figure.appendChild(img);
    }

    if (item.caption) {
      const caption = document.createElement('figcaption');
      caption.className = 'gallery-caption';
      caption.textContent = item.caption;
      figure.appendChild(caption);
    }

    return figure;
  }

  function buildTimelineItem(item, index) {
    const wrapper = document.createElement('article');
    wrapper.className = 'timeline-item';

    const step = document.createElement('span');
    step.className = 'timeline-step';
    step.textContent = item.stepLabel || `${index + 1 < 10 ? '0' : ''}${index + 1}`;

    const title = document.createElement('h3');
    title.className = 'timeline-title';
    title.textContent = item.title || '';

    const body = document.createElement('p');
    body.className = 'timeline-body';
    body.textContent = item.body || '';

    wrapper.append(step, title, body);
    return wrapper;
  }

  function buildQuickstartItem(item) {
    const li = document.createElement('li');

    const strong = document.createElement('strong');
    strong.textContent = item.title || '';

    const description = document.createElement('p');
    description.textContent = item.body || '';

    li.append(strong, description);
    return li;
  }

  function buildHelpPanel(panel) {
    const wrapper = document.createElement('article');
    wrapper.className = 'info-panel';

    const title = document.createElement('h3');
    title.textContent = panel.title || '';
    wrapper.appendChild(title);

    if (panel.body) {
      const body = document.createElement('p');
      body.textContent = panel.body;
      wrapper.appendChild(body);
    }

    if (Array.isArray(panel.bullets) && panel.bullets.length > 0) {
      const list = document.createElement('ul');
      panel.bullets.forEach((bullet) => {
        const li = document.createElement('li');
        li.textContent = bullet;
        list.appendChild(li);
      });
      wrapper.appendChild(list);
    }

    return wrapper;
  }

  function buildFaqItem(item) {
    const details = document.createElement('details');
    details.className = 'faq-item';

    const summary = document.createElement('summary');
    summary.textContent = item.question || '';
    details.appendChild(summary);

    if (item.answer) {
      const answer = document.createElement('p');
      answer.textContent = item.answer;
      details.appendChild(answer);
    }

    return details;
  }

  function buildDocCard(doc) {
    const card = document.createElement('article');
    card.className = 'card doc-card';

    if (doc.language) {
      const badge = document.createElement('span');
      badge.className = 'doc-lang';
      badge.textContent = doc.language;
      card.appendChild(badge);
    }

    const title = document.createElement('h3');
    title.className = 'card-title';
    title.textContent = doc.title || '';
    card.appendChild(title);

    if (doc.summary) {
      const body = document.createElement('p');
      body.className = 'card-body';
      body.textContent = doc.summary;
      card.appendChild(body);
    }

    if (doc.href) {
      const btn = document.createElement('a');
      btn.className = 'btn btn-secondary';
      btn.href = doc.href;
      btn.textContent = doc.cta || 'Read online';
      card.appendChild(btn);
    }

    return card;
  }

  function setActiveLanguageButton(lang) {
    languageButtons.forEach((btn) => {
      if (btn.dataset.lang === lang) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  function applyLanguage(lang) {
    const map = translations[lang] || translations.en;
    if (!map) return;
    html.setAttribute('lang', lang);
    updateSimpleStrings(lang, map);
    const productBullets = map.product && Array.isArray(map.product.bullets)
      ? map.product.bullets
      : [];
    renderList('[data-region="product-bullets"]', productBullets, (text) => {
      const li = document.createElement('li');
      li.textContent = text;
      return li;
    });
    const featureCards = map.features && Array.isArray(map.features.cards)
      ? map.features.cards
      : [];
    renderList('[data-region="features-cards"]', featureCards, buildCard);
    const galleryItems = map.gallery && Array.isArray(map.gallery.items)
      ? map.gallery.items
      : [];
    renderList('[data-region="gallery-items"]', galleryItems, buildGalleryItem);
    const flowSteps = map.how && Array.isArray(map.how.steps) ? map.how.steps : [];
    renderList('[data-region="how-steps"]', flowSteps, (item, index) =>
      buildTimelineItem(item, index)
    );
    const quickStartSteps = map.quickstart && Array.isArray(map.quickstart.steps)
      ? map.quickstart.steps
      : [];
    renderList('[data-region="quickstart-steps"]', quickStartSteps, buildQuickstartItem);
    const docCards = map.docs && Array.isArray(map.docs.cards) ? map.docs.cards : [];
    renderList('[data-region="docs-cards"]', docCards, buildDocCard);
    const helpPanels = map.help && Array.isArray(map.help.panels) ? map.help.panels : [];
    renderList('[data-region="help-panels"]', helpPanels, buildHelpPanel);
    const faqItems = map.faq && Array.isArray(map.faq.items) ? map.faq.items : [];
    renderList('[data-region="faq-items"]', faqItems, buildFaqItem);
    setActiveLanguageButton(lang);
    localStorage.setItem(STORAGE_KEY, lang);
  }

  function initLanguageSelector() {
    languageButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const lang = btn.dataset.lang;
        if (!lang || !translations[lang]) return;
        applyLanguage(lang);
      });
    });
  }

  function initMenuToggle() {
    if (!menuToggle || !navList) return;
    menuToggle.addEventListener('click', () => {
      const expanded = menuToggle.getAttribute('aria-expanded') === 'true';
      const next = !expanded;
      menuToggle.setAttribute('aria-expanded', String(next));
      if (next) {
        navList.classList.add('open');
      } else {
        navList.classList.remove('open');
      }
    });

    navList.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 860) {
          navList.classList.remove('open');
          menuToggle.setAttribute('aria-expanded', 'false');
        }
      });
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    const lang = detectLanguage();
    initLanguageSelector();
    initMenuToggle();
    applyLanguage(lang);
  });
})();
