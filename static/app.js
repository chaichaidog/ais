/* ARCHIVE_001 — frontend. The puzzle answer lives ONLY on the Python server. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const dialog = $('#fileDialog');
  const entries = $('#entryList');
  const state = { posts: [], filter: 'all', query: '', scareTimeout: null };

  const projects = {
    project1: { ref: 'PROJECT_001 / STUDENT WORK', title: '《歸來者》互動 Blog', date: '作者：暄、阿卉', body: '這部偽紀錄片式互動 Blog 由暄與阿卉共同創作。\n\n故事中的 Blog 記錄者與學生作者不是同一人。\n\n網站包含虛構日誌、森林失蹤事件、解謎和驚嚇彩蛋。' },
    project2: { ref: 'CASE_002 / FOREST', title: '森林失蹤事件', date: 'STATUS: UNRESOLVED', body: '有人讀小說讀得太入迷，深信森林裡的獻祭儀式是真實的。\n\n他企圖把同行的人當成祭品，於是兩人一起走進森林。\n\n儀式沒有完成，樹林裡卻先出現了兩個不自然的人影。\n\n數日後，兩人回來了。' },
    project3: { ref: 'CASE_003 / THE RETURNED', title: '回來的兩個人', date: 'IDENTITY: UNVERIFIED', body: '兩人回來後臉上總帶著僵硬的表情。\n\n他們逐漸忘記原本的習慣，回答問題時也像是在背誦別人的人生。\n\n最後的影像暗示：兩名真正的人類在森林中遭偽人吞噬，之後被偽人取代。' },
    secret: { ref: 'REDACTED_000 / RESTRICTED', date: 'DATE LOST', title: '第零號檔案：模仿紀錄', body: '[森林訊號中斷]\n\n兩名入侵者已進入觀測範圍。\n\n原有身分資訊讀取中。\n\n行為模仿尚未完成，請使用日誌中的時間 04 和最後一格影像 17 修復紀錄。\n\n不要在他們面前問起從前。', warning: 'REPLACEMENT STATUS: INCOMPLETE' }
  };

  function openFile(item) {
    if (!item) return;
    $('#modalRef').textContent = item.ref || 'PERSONAL RECORD';
    $('#modalDate').textContent = item.date || '';
    $('#modalTitle').textContent = item.title || '';
    $('#modalBody').textContent = item.body || '';
    $('#modalWarning').textContent = item.warning || 'END OF RECORD // FILE CLOSED';
    if (!dialog.open) dialog.showModal();
  }
  $('#closeDialog').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
  document.querySelectorAll('.project').forEach((item) => item.addEventListener('click', () => openFile(projects[item.dataset.id])));

  function make(tag, className, content) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (content !== undefined) element.textContent = content;
    return element;
  }

  function renderPosts() {
    entries.replaceChildren();
    const found = state.posts.filter((post) =>
      (state.filter === 'all' || post.category === state.filter) &&
      `${post.title} ${post.excerpt} ${post.content}`.toLocaleLowerCase().includes(state.query)
    );
    found.forEach((post, index) => {
      const item = make('button', 'entry');
      item.type = 'button';
      item.append(make('span', 'file-no', `LOG_${String(state.posts.length - index).padStart(3, '0')} / ${post.category}`));
      const body = make('span', 'body');
      body.append(make('h3', '', post.title), make('p', '', post.excerpt));
      item.append(body);
      const tail = make('span', 'tail');
      tail.append(make('span', 'date', post.created_at.replaceAll('-', '.')), make('span', 'arrow', '↗'));
      item.append(tail);
      item.addEventListener('click', () => openFile({
        ref: `LOG / ${post.category}`, date: post.created_at, title: post.title, body: post.content
      }));
      entries.append(item);
    });
    $('#empty').style.display = found.length ? 'none' : 'block';
  }
  async function loadPosts() {
    try {
      const response = await fetch('/api/posts', { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      state.posts = Array.isArray(data.posts) ? data.posts : [];
      renderPosts();
    } catch (_) {
      entries.replaceChildren(make('p', 'muted-small', '資料庫暫時無法讀取。請重新整理。'));
    }
  }
  document.querySelectorAll('.filter').forEach((button) => button.addEventListener('click', () => {
    state.filter = button.dataset.filter;
    document.querySelectorAll('.filter').forEach((b) => {
      b.classList.toggle('active', b === button);
      b.setAttribute('aria-pressed', String(b === button));
    });
    renderPosts();
  }));
  $('#search').addEventListener('input', (event) => {
    state.query = event.target.value.trim().toLocaleLowerCase();
    renderPosts();
  });
  loadPosts();

  // Optional analog overlay; never use strobing/high-frequency flashing effects.
  $('#visualToggle').addEventListener('click', (event) => {
    const clean = document.body.classList.toggle('clean');
    event.currentTarget.textContent = clean ? 'SCANLINES: OFF' : 'SCANLINES: ON';
    event.currentTarget.setAttribute('aria-pressed', String(!clean));
  });
  let clicks = 0;
  $('#secretClock').addEventListener('click', () => {
    clicks += 1;
    if (clicks >= 3) { clicks = 0; openFile(projects.secret); }
  });

  const status = $('#statusSignal');
  const glitch = $('#glitchMessage');
  const anomalyTexts = [
    'CAM_02: TWO FIGURES RETURNED',
    'FOREST RECORD: SIGNAL INTERRUPTED',
    'UNLISTED SIGNAL: IDENTITIES DO NOT MATCH',
    'ERROR: ORIGINAL SUBJECTS NOT FOUND'
  ];
  let anomalyIndex = 0;
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.setInterval(() => {
      anomalyIndex += 1;
      if (anomalyIndex % 2 === 0) return;
      status.textContent = 'UNKNOWN';
      status.style.color = '#d56c68';
      glitch.textContent = `[${anomalyTexts[(anomalyIndex / 2 | 0) % anomalyTexts.length]}]`;
      window.setTimeout(() => {
        status.textContent = 'CONNECTED';
        status.style.color = '';
        glitch.textContent = '[無法辨識的頻道仍在接收訊號]';
      }, 3600);
    }, 16000);
  }

  const scare = $('#scareLayer');
  const scareClose = $('#scareClose');
  let previousFocus = null;
  function hideScare() {
    if (state.scareTimeout) window.clearTimeout(state.scareTimeout);
    scare.classList.remove('active');
    scare.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (previousFocus) previousFocus.focus();
  }
  function showScare() {
    previousFocus = document.activeElement;
    scare.setAttribute('aria-hidden', 'false');
    scare.classList.add('active');
    document.body.style.overflow = 'hidden';
    scareClose.focus();
    state.scareTimeout = window.setTimeout(hideScare, 2300);
  }
  scareClose.addEventListener('click', hideScare);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && scare.classList.contains('active')) hideScare();
  });

  $('#puzzleForm').addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = $('#puzzleCode');
    const feedback = $('#puzzleFeedback');
    const button = $('#puzzleSubmit');
    const answer = input.value.trim();
    if (!/^\d{4}$/.test(answer)) {
      feedback.textContent = '請輸入四位數字。';
      feedback.classList.add('error');
      return;
    }
    button.disabled = true;
    feedback.textContent = 'VERIFYING / 正在比對錄影時間…';
    feedback.classList.remove('error');
    try {
      const response = await fetch('/api/puzzle/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ answer }),
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        feedback.textContent = result.message || '存取失敗';
        feedback.classList.add('error');
        return;
      }
      feedback.textContent = result.message;
      $('#revealPanel').classList.add('visible');
      if ($('#scareEnabled').checked) {
        window.setTimeout(showScare, 460);
      }
    } catch (_) {
      feedback.textContent = '連線失敗。請確認 Python 後端已啟動。';
      feedback.classList.add('error');
    } finally {
      button.disabled = false;
    }
  });
})();
