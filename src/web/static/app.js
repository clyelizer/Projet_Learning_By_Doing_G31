/**
 * Dashboard Agricole — SPA client-side logic.
 * Chargement des données API, rendu des pages, navigation.
 */
(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────
    let results = null;
    let currentPage = 'dashboard';

    // ── Navigation ───────────────────────────────────────────────
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const page = this.dataset.page;
            if (page) navigate(page);
        });
    });

    // Hamburger
    const toggle = document.getElementById('nav-toggle');
    const links = document.getElementById('nav-links');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('open');
            toggle.textContent = links.classList.contains('open') ? '✕' : '☰';
        });
        document.addEventListener('click', e => {
            if (!toggle.contains(e.target) && !links.contains(e.target)) {
                links.classList.remove('open');
                toggle.textContent = '☰';
            }
        });
    }

    function navigate(page) {
        currentPage = page;
        document.querySelectorAll('.nav-link').forEach(l => {
            l.classList.toggle('active', l.dataset.page === page);
        });
        history.pushState(null, '', '#' + page);
        loadPage(page);
    }

    window.addEventListener('popstate', () => {
        const page = location.hash.replace('#', '') || 'dashboard';
        navigate(page);
    });

    // ── API ──────────────────────────────────────────────────────
    async function fetchJSON(url) {
        try {
            const resp = await fetch(url);
            return await resp.json();
        } catch (e) {
            return null;
        }
    }

    // ── Page Loaders ─────────────────────────────────────────────
    async function loadPage(page) {
        const main = document.getElementById('main-content');
        if (!main) return;

        results = await fetchJSON('/api/results');
        const waypoints = results?.waypoints || [];

        switch (page) {
            case 'dashboard': renderDashboard(main, results, waypoints); break;
            case 'data': renderData(main, waypoints); break;
            case 'reco': renderReco(main); break;
            default: renderDashboard(main, results, waypoints);
        }
    }

    // ── Dashboard ────────────────────────────────────────────────
    function renderDashboard(main, results, waypoints) {
        const mission = results?.mission || {};
        const withSensor = waypoints.filter(w => w.sensor).length;
        const totalPhotos = waypoints.reduce((s, w) => s + (w.photos?.length || 0), 0);

        main.innerHTML = `
            <h1>📊 Dashboard Mission</h1>
            <div class="stats-grid">
                <div class="stat-card">
                    <span class="stat-icon">📍</span>
                    <span class="stat-value">${waypoints.length}</span>
                    <span class="stat-label">Waypoints</span>
                </div>
                <div class="stat-card">
                    <span class="stat-icon">🧪</span>
                    <span class="stat-value">${withSensor}</span>
                    <span class="stat-label">Mesures</span>
                </div>
                <div class="stat-card">
                    <span class="stat-icon">📸</span>
                    <span class="stat-value">${totalPhotos}</span>
                    <span class="stat-label">Photos</span>
                </div>
                <div class="stat-card">
                    <span class="stat-icon">📅</span>
                    <span class="stat-value">${(mission.start_time || '—').slice(0, 10)}</span>
                    <span class="stat-label">Date</span>
                </div>
            </div>
            ${waypoints.length ? renderTable(waypoints) : '<div class="empty-state"><p>Aucune donnée. Lancez une mission.</p></div>'}
        `;
    }

    function renderTable(waypoints) {
        let rows = waypoints.map(wp => {
            const s = wp.sensor;
            return `
                <tr>
                    <td>${wp.waypoint_id}</td>
                    <td>${s ? `${s.humidity_pct?.toFixed(1) || '—'} %` : '—'}</td>
                    <td>${s ? `${s.temperature_c?.toFixed(1) || '—'} °C` : '—'}</td>
                    <td>${s ? `${s.ec_us_cm?.toFixed(0) || '—'}` : '—'}</td>
                    <td>${s ? `${s.ph?.toFixed(1) || '—'}` : '—'}</td>
                    <td>${wp.photos?.length || 0}</td>
                </tr>`;
        }).join('');

        return `
            <div class="section">
                <h2>📋 Résultats</h2>
                <div class="table-wrapper">
                    <table>
                        <thead><tr><th>#</th><th>💧 Humidité</th><th>🌡️ Temp</th><th>⚡ EC</th><th>🧪 pH</th><th>📸</th></tr></thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </div>`;
    }

    // ── Data ─────────────────────────────────────────────────────
    async function renderData(main, waypoints) {
        const photosResp = await fetchJSON('/api/results');
        // Construire galerie photos
        const allPhotos = [];
        (photosResp?.waypoints || []).forEach(wp => {
            (wp.photos || []).forEach(p => {
                allPhotos.push({ wp: wp.waypoint_id, path: p });
            });
        });

        const gallery = allPhotos.length ? `
            <div class="section">
                <h2>📸 Galerie (${allPhotos.length} photos)</h2>
                <div class="photo-grid">
                    ${allPhotos.map(p => `
                        <div class="photo-card" onclick="window.open('/photos/${encodeURIComponent(p.path.split('/').pop())}', '_blank')">
                            <img src="/photos/${encodeURIComponent(p.path.split('/').pop())}" alt="WP${p.wp}" loading="lazy">
                        </div>`).join('')}
                </div>
            </div>` : '';

        const jsonBlock = results ? `
            <div class="section">
                <h2>📄 JSON Brut</h2>
                <div class="json-block"><code>${JSON.stringify(results, null, 2)}</code></div>
            </div>` : '';

        main.innerHTML = `<h1>📁 Données</h1>${gallery}${jsonBlock}`;
    }

    // ── Recommandations ──────────────────────────────────────────
    async function renderReco(main) {
        const recos = await fetchJSON('/api/recommendations');
        if (!recos || !recos.length) {
            main.innerHTML = '<h1>🧪 Recommandations</h1><div class="empty-state"><p>Aucune recommandation disponible.</p></div>';
            return;
        }

        let html = '<h1>🧪 Recommandations</h1>';

        recos.forEach((wp, i) => {
            const reco = wp.recommendations;
            if (!reco) return;

            const crops = (reco.crops || []).join(', ');
            const fert = reco.fertilizer || {};
            const amend = (reco.soil_amendments || []).join(', ');
            const irrig = reco.irrigation || {};
            const warns = reco.warnings || [];

            html += `
                <div class="section rec-section">
                    <h2>📍 Waypoint ${wp.waypoint_id}</h2>
                    <div class="rec-summary">
                        ${crops ? `<span>🌾 ${crops}</span>` : ''}
                    </div>
                    <div class="rec-cards">
                        ${fert.type ? `
                        <div class="rec-card rec-good">
                            <span class="rec-icon">🧪</span>
                            <div class="rec-body">
                                <h4>Fertilisation</h4>
                                <p><strong>${fert.type}</strong> — ${fert.rate || 'N/A'} — ${fert.frequency || ''}</p>
                            </div>
                        </div>` : ''}
                        ${amend ? `
                        <div class="rec-card rec-warning">
                            <span class="rec-icon">🪨</span>
                            <div class="rec-body">
                                <h4>Amendements</h4>
                                <p>${amend}</p>
                            </div>
                        </div>` : ''}
                        ${irrig.frequency ? `
                        <div class="rec-card rec-good">
                            <span class="rec-icon">💧</span>
                            <div class="rec-body">
                                <h4>Irrigation</h4>
                                <p>${irrig.frequency} — ${irrig.amount || ''}</p>
                            </div>
                        </div>` : ''}
                        ${warns.map(w => `
                        <div class="rec-card rec-danger">
                            <span class="rec-icon">⚠️</span>
                            <div class="rec-body"><p>${w}</p></div>
                        </div>`).join('')}
                    </div>
                    ${reco.summary ? `
                    <div style="margin-top:16px">
                        <button onclick="replayTTS('${reco.summary.replace(/'/g, "\\'")}', 'fr')" class="rec-summary" style="cursor:pointer;border:none;background:var(--green-025);padding:8px 16px;border-radius:20px;font-size:0.9rem">
                            🔊 Écouter les recommandations
                        </button>
                    </div>` : ''}
                </div>`;
        });

        main.innerHTML = html;
    }

    // ── Init ─────────────────────────────────────────────────────
    const hash = location.hash.replace('#', '') || 'dashboard';
    navigate(hash);
})();
