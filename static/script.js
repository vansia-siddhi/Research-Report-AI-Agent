let lastReport = null;
let lastTopic = null;
let history = JSON.parse(localStorage.getItem('research_agent_history') || '[]');

function setExample(topic) {
    document.getElementById('topicInput').value = topic;
}

function resetForm() {
    document.getElementById('topicInput').value = '';
    document.getElementById('feedSection').classList.remove('show');
    document.getElementById('reportCard').classList.remove('show');
    document.getElementById('errorBox').classList.remove('show');
    document.getElementById('topicInput').focus();
}

function showError(msg) {
    const box = document.getElementById('errorBox');
    box.innerHTML = '<span style="font-size:18px">⚠️</span><span>' + msg + '</span>';
    box.classList.add('show');
    document.getElementById('runBtn').disabled = false;
    document.getElementById('statusDot').classList.remove('running');
}

function addFeedItem(icon, html, phaseClass) {
    const card = document.getElementById('feedCard');
    const item = document.createElement('div');
    item.className = 'feed-item';
    item.innerHTML = `<div class="feed-icon">${icon}</div><div class="feed-text ${phaseClass || ''}">${html}</div>`;
    card.appendChild(item);
    card.scrollTop = card.scrollHeight;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// Minimal markdown -> HTML for the final report (headings, bold, bullet lists)
function renderMarkdown(md) {
    let html = escapeHtml(md);
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // bullet lists
    html = html.replace(/(^|\n)[\*\-] (.*)/g, '$1<li>$2</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, m => '<ul>' + m + '</ul>');
    html = html.replace(/\n{2,}/g, '</p><p>');
    html = '<p>' + html + '</p>';
    html = html.replace(/<p>(<h[1-3]>)/g, '$1').replace(/(<\/h[1-3]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1').replace(/(<\/ul>)<\/p>/g, '$1');
    return html;
}

async function runAgent() {
    const topic = document.getElementById('topicInput').value.trim();
    if (!topic) { showError('Please enter a research topic.'); return; }

    document.getElementById('errorBox').classList.remove('show');
    document.getElementById('reportCard').classList.remove('show');
    document.getElementById('feedCard').innerHTML = '';
    document.getElementById('feedSection').classList.add('show');
    document.getElementById('feedTitle').textContent = 'Agent working...';
    document.getElementById('statusDot').classList.add('running');
    document.getElementById('runBtn').disabled = true;
    lastTopic = topic;

    const es = new EventSource('/api/research?topic=' + encodeURIComponent(topic));

    es.onmessage = (event) => {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'status':
                addFeedItem('🚀', `<strong>Agent started</strong> — researching "${escapeHtml(topic)}"`);
                break;

            case 'plan': {
                const items = data.subquestions.map(q => `<div class="plan-item">${escapeHtml(q)}</div>`).join('');
                addFeedItem('🧠', `<strong>Plan created</strong><div class="plan-box"><div class="plan-box-title">Sub-questions</div>${items}</div>`, 'feed-phase-think');
                break;
            }

            case 'step':
                if (data.phase === 'think') {
                    addFeedItem('🧠', escapeHtml(data.message), 'feed-phase-think');
                } else {
                    addFeedItem('🔍', escapeHtml(data.message), 'feed-phase-act');
                }
                break;

            case 'finding': {
                const html = `<div class="finding-block"><div class="finding-q">Q: ${escapeHtml(data.question)}</div><div class="finding-a">${escapeHtml(data.findings)}</div></div>`;
                addFeedItem('✅', `<strong>Findings saved to memory</strong>${html}`);
                break;
            }

            case 'error':
                showError(data.message);
                es.close();
                break;

            case 'done':
                document.getElementById('feedTitle').textContent = 'Agent finished ✓';
                document.getElementById('statusDot').classList.remove('running');
                document.getElementById('runBtn').disabled = false;
                addFeedItem('🏁', '<strong>Research complete — report generated below.</strong>');

                lastReport = data.report;
                document.getElementById('reportContent').innerHTML = renderMarkdown(data.report);
                document.getElementById('reportCard').classList.add('show');
                document.getElementById('reportCard').scrollIntoView({ behavior: 'smooth', block: 'nearest' });

                saveHistory(topic, data.report);
                es.close();
                break;
        }
    };

    es.onerror = () => {
        showError('Connection to agent lost. Make sure the Flask server is running and GROQ_API_KEY is set.');
        es.close();
    };
}

function copyReport() {
    if (!lastReport) return;
    navigator.clipboard.writeText(lastReport).then(() => alert('Report copied to clipboard!'));
}

function downloadReport() {
    if (!lastReport) return;
    const blob = new Blob([`# Research Report: ${lastTopic}\n\n${lastReport}`], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (lastTopic || 'report').replace(/\s+/g, '_') + '.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function saveHistory(topic, report) {
    history.unshift({ topic, report, time: new Date().toLocaleString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' }) });
    history = history.slice(0, 8);
    localStorage.setItem('research_agent_history', JSON.stringify(history));
    renderHistory();
}

function renderHistory() {
    const section = document.getElementById('histSection');
    if (!history.length) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    document.getElementById('histGrid').innerHTML = history.map((h, i) => `
    <div class="hist-item" onclick="loadHistory(${i})">
      <div class="hist-name">📄 ${escapeHtml(h.topic)}</div>
      <div class="hist-time">${h.time}</div>
    </div>
  `).join('');
}

function loadHistory(i) {
    const h = history[i];
    lastTopic = h.topic;
    lastReport = h.report;
    document.getElementById('topicInput').value = h.topic;
    document.getElementById('feedSection').classList.remove('show');
    document.getElementById('reportContent').innerHTML = renderMarkdown(h.report);
    document.getElementById('reportCard').classList.add('show');
}

async function checkHealth() {
    try {
        const r = await fetch('/api/health');
        const data = await r.json();
        if (!data.api_key_set) document.getElementById('setupAlert').classList.add('show');
    } catch (e) {}
}

document.getElementById('topicInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') runAgent();
});

checkHealth();
renderHistory();
