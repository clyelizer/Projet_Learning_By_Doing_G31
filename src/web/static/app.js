/**
 * Dashboard Agricole — SPA client-side logic.
 * v2: Ajout Analyse, Base Ref, Modeles ML, Explicabilite
 */
(function () {
    'use strict';

    // ── State ────────────────────────────────────────────────────
    let results = null;
    let currentPage = 'dashboard';
    let baseCache = null;

    // ── Navigation ───────────────────────────────────────────────
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const page = this.dataset.page;
            if (page) navigate(page);
        });
    });

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

    // ── Helpers ──────────────────────────────────────────────────
    async function fetchJSON(url, options) {
        try {
            const resp = options ? await fetch(url, options) : await fetch(url);
            return await resp.json();
        } catch (e) {
            return null;
        }
    }

    function loading(main) {
        main.innerHTML = '<div class="empty-state"><p>⏳ Chargement...</p></div>';
    }

    function errorMsg(main, msg) {
        main.innerHTML = `<div class="empty-state"><p>❌ ${msg}</p></div>`;
    }

    function sliderGroup(label, id, min, max, val, step, unit) {
        return `
            <div class="form-group">
                <label for="${id}">${label}: <strong id="${id}-val">${val}</strong>${unit || ''}</label>
                <input type="range" id="${id}" min="${min}" max="${max}" value="${val}" step="${step || 1}">
            </div>`;
    }

    // ── Page Loaders ─────────────────────────────────────────────
    async function loadPage(page) {
        const main = document.getElementById('main-content');
        if (!main) return;

        results = await fetchJSON('/api/results');
        const waypoints = results?.waypoints || [];

        switch (page) {
            case 'dashboard': renderDashboard(main, results, waypoints); break;
            case 'analyze': renderAnalyze(main); break;
            case 'reco': renderReco(main); break;
            case 'base-ref': renderBaseRef(main); break;
            case 'models': renderModels(main); break;
            case 'data': renderData(main, waypoints); break;
            case 'doctor': renderDoctor(main); break;
            case 'mission': renderMission(main); break;
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
            return `<tr>
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

    // ══════════════════════════════════════════════════════════════
    // PAGE: Analyse interactive
    // ══════════════════════════════════════════════════════════════
    function renderAnalyze(main) {
        main.innerHTML = `
            <h1>🧪 Test analyse du sol</h1>
            <p class="subtitle">Entrez les 4 mesures du robot → NPK estimé → classement cultures → impact</p>
            <div class="analyze-grid">
                <div class="analyze-controls card">
                    <h3>📏 Mesures robot</h3>
                    ${sliderGroup('pH', 'ph-slider', 3, 9, 6.5, 0.1)}
                    ${sliderGroup('Température', 'temp-slider', 10, 40, 25, 1, '°C')}
                    ${sliderGroup('Humidité', 'hum-slider', 10, 100, 65, 1, '%')}
                    ${sliderGroup('EC', 'ec-slider', 0, 3000, 500, 10, 'µS/cm')}
                    <button id="btn-analyze" class="btn-primary">🔬 Analyser le sol</button>
                </div>
                <div id="analyze-results" class="analyze-results">
                    <div class="empty-state"><p>Entrez les mesures et cliquez sur Analyser.</p></div>
                </div>
            </div>`;

        // Attach event listeners
        ['ph-slider', 'temp-slider', 'hum-slider', 'ec-slider'].forEach(id => {
            document.getElementById(id).addEventListener('input', function () {
                document.getElementById(id + '-val').textContent = this.value;
            });
        });
        document.getElementById('btn-analyze').addEventListener('click', doAnalyze);
    }

    async function doAnalyze() {
        const main = document.getElementById('main-content');
        const resDiv = document.getElementById('analyze-results');
        if (!resDiv) return;
        resDiv.innerHTML = '<div class="empty-state"><p>⏳ Analyse en cours...</p></div>';

        const data = {
            ec_us_cm: parseFloat(document.getElementById('ec-slider').value),
            ph: parseFloat(document.getElementById('ph-slider').value),
            humidity_pct: parseFloat(document.getElementById('hum-slider').value),
            temperature_c: parseFloat(document.getElementById('temp-slider').value),
            top_n: 5,
        };

        const result = await fetchJSON('/api/reco/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
        });

        if (!result) {
            resDiv.innerHTML = '<div class="empty-state"><p>❌ Erreur API</p></div>';
            return;
        }

        const npk = result.npk_estimes || {};
        const ranking = result.classement || [];

        let html = `
            <div class="card">
                <h3>📊 NPK estimés</h3>
                <div class="npk-display">
                    <div class="npk-card npk-n"><strong>N</strong><br>${npk.N_kg_ha || '?'} kg/ha</div>
                    <div class="npk-card npk-p"><strong>P₂O₅</strong><br>${npk.P2O5_kg_ha || '?'} kg/ha</div>
                    <div class="npk-card npk-k"><strong>K₂O</strong><br>${npk.K2O_kg_ha || '?'} kg/ha</div>
                </div>
            </div>

            <div class="card">
                <h3>🏆 Classement des cultures (${ranking.length})</h3>
                ${ranking.map((c, i) => {
                    const color = c.score >= 70 ? '#1b9e77' : c.score >= 40 ? '#e6ab02' : '#d95f02';
                    const matchStr = (c.parametres_match || []).join(', ');
                    const limitStr = (c.parametres_limites || []).join(', ');
                    const horsStr = (c.parametres_hors_plage || []).join(', ');

                    return `
                    <details class="culture-card" style="border-left: 4px solid ${color}">
                        <summary>
                            <span class="rank-num">#${i+1}</span>
                            <span class="rank-crop">${c.culture}</span>
                            <span class="rank-score" style="color:${color}">${c.score}%</span>
                            <span class="rank-tags">
                                ${matchStr ? `<span class="tag tag-good">${matchStr}</span>` : ''}
                                ${limitStr ? `<span class="tag tag-warn">${limitStr}</span>` : ''}
                                ${horsStr ? `<span class="tag tag-bad">${horsStr}</span>` : ''}
                            </span>
                        </summary>
                        <div class="culture-details">
                            ${c.justificatif ? `<p class="culture-justif">💡 ${c.justificatif}</p>` : ''}
                            ${c.impact_chart_b64
                                ? `<img src="data:image/png;base64,${c.impact_chart_b64}" alt="Impact ${c.culture}" class="impact-chart">`
                                : ''}
                            <table class="shap-table">
                                <tr><th>Paramètre</th><th>Compatibilité</th></tr>
                                ${Object.entries(c.scores_details || {}).filter(([k,v]) => v !== null).map(([k, v]) => {
                                    const pct = (v * 100).toFixed(0);
                                    const col = v >= 0.5 ? '#2ecc71' : v >= 0.25 ? '#f39c12' : '#e74c3c';
                                    return `<tr><td>${k}</td><td style="color:${col};font-weight:600">${pct}%</td></tr>`;
                                }).join('')}
                            </table>
                        </div>
                    </details>`;
                }).join('')}
            </div>`;

        if (result.fertilisation) {
            html += `<div class="card"><h3>🌱 Fertilisation recommandée</h3>
                <p>${result.fertilisation.NPK_recommandation || 'Non spécifiée'}</p></div>`;
        }

        resDiv.innerHTML = html;
    }

    // ══════════════════════════════════════════════════════════════
    // PAGE: Base de reference
    // ══════════════════════════════════════════════════════════════
    async function renderBaseRef(main) {
        loading(main);
        const base = await fetchJSON('/api/base-reference');
        if (!base) { errorMsg(main, 'Base non disponible'); return; }

        const zones = [...new Set((base.cultures || []).map(c => c.zone).filter(Boolean))];
        baseCache = base;

        main.innerHTML = `
            <h1>🌾 Base de référence (${base.metadata?.cultures_count || base.count} cultures)</h1>
            <div class="base-controls">
                <select id="base-zone-filter">
                    <option value="">Toutes les zones</option>
                    ${zones.map(z => `<option value="${z}">${z}</option>`).join('')}
                </select>
                <input type="text" id="base-search" placeholder="🔍 Rechercher une culture...">
            </div>
            <div id="base-list" class="base-list">${renderCultures(base.cultures)}</div>`;

        document.getElementById('base-zone-filter').addEventListener('change', filterBase);
        document.getElementById('base-search').addEventListener('input', filterBase);
    }

    function renderCultures(cultures) {
        if (!cultures || !cultures.length) return '<p class="no-data">Aucune culture trouvée.</p>';
        return cultures.map(c => {
            const sol = c.sol || {};
            const keys = ['pH', 'temperature', 'humidite', 'N', 'P2O5', 'K2O'];
            const details = keys.map(k => {
                const p = sol[k] || {};
                return p.min ? `<span class="base-detail"><strong>${k}:</strong> ${p.min}-${p.max} ${p.unite || ''}</span>` : '';
            }).filter(Boolean).join('');
            const fert = c.fertilisation?.NPK_recommandation || '';
            return `
                <details class="base-item">
                    <summary><strong>${c.culture}</strong> (${c.nom_scientifique || '?'}) — ${c.zone || 'Monde'}</summary>
                    <div class="base-details">${details}</div>
                    ${fert ? `<div class="base-fert">🌱 ${fert}</div>` : ''}
                </details>`;
        }).join('');
    }

    async function filterBase() {
        const zone = document.getElementById('base-zone-filter').value;
        const search = document.getElementById('base-search').value;
        const base = await fetchJSON(`/api/base-reference?zone=${encodeURIComponent(zone)}&search=${encodeURIComponent(search)}`);
        document.getElementById('base-list').innerHTML = renderCultures(base?.cultures);
    }

    // ══════════════════════════════════════════════════════════════
    // PAGE: Modeles ML
    // ══════════════════════════════════════════════════════════════
    async function renderModels(main) {
        loading(main);
        const [figData, metData] = await Promise.all([
            fetchJSON('/api/ml/figures'),
            fetchJSON('/api/ml/metrics'),
        ]);
        const figs = figData?.figures || [];

        main.innerHTML = `
            <h1>🤖 Modèles ML</h1>
            <p class="subtitle">Visualisations et métriques des modèles entraînés.</p>
            <div class="section">
                <h2>📈 Figures (${figs.length})</h2>
                ${figs.length ? `
                <select id="fig-select" class="fig-select">
                    ${figs.map((f, i) => `<option value="${f.name}">${f.name} (${f.size_kb} KB)</option>`).join('')}
                </select>
                <div class="fig-display"><img id="fig-img" src="/api/ml/figures/${encodeURIComponent(figs[0].name)}" alt="${figs[0].name}"></div>
                <script>
                    document.getElementById('fig-select')?.addEventListener('change', function() {
                        document.getElementById('fig-img').src = '/api/ml/figures/' + encodeURIComponent(this.value);
                    });
                <\/script>` : '<p class="no-data">Aucune figure disponible.</p>'}
            </div>
            ${metData?.content ? `
            <div class="section">
                <h2>📊 Métriques</h2>
                <pre class="metrics-block">${metData.content}</pre>
            </div>` : ''}
            <div class="section">
                <h2>🧠 Explicabilité interactive</h2>
                <p>Entrez les 6 paramètres pour une prédiction ML + SHAP :</p>
                <div class="explain-grid">
                    <div class="explain-controls">
                        ${sliderGroup('N (kg/ha)', 'exp-n', 0, 300, 80, 5)}
                        ${sliderGroup('P₂O₅ (kg/ha)', 'exp-p', 0, 200, 50, 5)}
                        ${sliderGroup('K₂O (kg/ha)', 'exp-k', 0, 300, 40, 5)}
                        ${sliderGroup('pH', 'exp-ph', 3, 9, 6.5, 0.1)}
                        ${sliderGroup('Température', 'exp-temp', 10, 40, 25, 1, '°C')}
                        ${sliderGroup('Humidité', 'exp-hum', 10, 100, 65, 1, '%')}
                        <button id="btn-predict" class="btn-primary">🔮 Prédire</button>
                    </div>
                    <div id="predict-results" class="predict-results">
                        <div class="empty-state"><p>Ajustez les valeurs et cliquez sur Prédire.</p></div>
                    </div>
                </div>
            </div>`;

        // Bind sliders
        ['exp-n', 'exp-p', 'exp-k', 'exp-ph', 'exp-temp', 'exp-hum'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', function () {
                document.getElementById(id + '-val').textContent = this.value;
            });
        });
        document.getElementById('btn-predict')?.addEventListener('click', doPredict);
        document.getElementById('fig-select')?.addEventListener('change', function () {
            document.getElementById('fig-img').src = '/api/ml/figures/' + encodeURIComponent(this.value);
        });
    }

    async function doPredict() {
        const resDiv = document.getElementById('predict-results');
        if (!resDiv) return;
        resDiv.innerHTML = '<div class="empty-state"><p>⏳ Prédiction...</p></div>';

        const data = {
            N: parseFloat(document.getElementById('exp-n').value),
            P2O5: parseFloat(document.getElementById('exp-p').value),
            K2O: parseFloat(document.getElementById('exp-k').value),
            pH: parseFloat(document.getElementById('exp-ph').value),
            temperature: parseFloat(document.getElementById('exp-temp').value),
            humidite: parseFloat(document.getElementById('exp-hum').value),
        };

        const result = await fetchJSON('/api/ml/predict', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
        });

        if (!result || !result.classement) {
            resDiv.innerHTML = `<div class="empty-state"><p>❌ ${result?.error || 'Erreur'}</p></div>`;
            return;
        }

        const ranking = result.classement;
        let html = `<div class="card"><h3>🔮 Résultat — Top: <strong>${result.top_culture}</strong> (${result.top_score}%)</h3>`;

        ranking.forEach((c, i) => {
            const color = c.score >= 70 ? '#1b9e77' : c.score >= 40 ? '#e6ab02' : '#d95f02';
            html += `
                <details class="culture-card" style="border-left:4px solid ${color}">
                    <summary>
                        <span class="rank-num">#${i+1}</span>
                        <span class="rank-crop">${c.culture}</span>
                        <span class="rank-score" style="color:${color}">${c.score}%</span>
                    </summary>
                    <div class="culture-details">
                        ${c.justificatif ? `<p class="culture-justif">💡 ${c.justificatif}</p>` : ''}
                        ${c.impact_chart_b64 ? `<img src="data:image/png;base64,${c.impact_chart_b64}" class="impact-chart">` : ''}
                        <table class="shap-table">
                            <tr><th>Paramètre</th><th>Compatibilité</th></tr>
                            ${Object.entries(c.scores_details || {}).filter(([k,v]) => v !== null).map(([k, v]) => {
                                const col = v >= 0.5 ? '#2ecc71' : v >= 0.25 ? '#f39c12' : '#e74c3c';
                                return `<tr><td>${k}</td><td style="color:${col};font-weight:600">${(v*100).toFixed(0)}%</td></tr>`;
                            }).join('')}
                        </table>
                    </div>
                </details>`;
        });

        html += '</div>';
        resDiv.innerHTML = html;
    }

    // ══════════════════════════════════════════════════════════════
    // PAGE: Recommandations
    // ══════════════════════════════════════════════════════════════
    let recoLang = 'fr';

    async function renderReco(main) {
        const data = await fetchJSON(`/api/recommendations?lang=${recoLang}`);
        const recos = data?.zones || [];
        const conseils = data?.conseils || {};
        const tts = data?.tts || {};

        if (!recos.length) {
            main.innerHTML = '<h1>🧪 Recommandations</h1><div class="empty-state"><p>Aucune donnee de mission disponible.</p></div>';
            return;
        }

        const summaryColor = conseils.urgence_globale === 'haute' ? '#c62828' : conseils.urgence_globale === 'moyenne' ? '#f57f17' : '#2e7d32';
        const langLabel = recoLang === 'fr' ? 'Français' : 'English';

        let html = `
            <h1>🧪 Recommandations agricoles</h1>
            <p class="subtitle">Conseils personnalises basees sur les mesures du robot.</p>

            <div class="card" style="text-align:center">
                <div style="display:flex;align-items:center;justify-content:center;gap:var(--spacing-sm);flex-wrap:wrap">
                    <span>🌐 Langue :</span>
                    <select id="lang-select" style="padding:var(--spacing-xs) var(--spacing-sm);border-radius:var(--radius-sm);border:1px solid var(--gray-300);font-size:var(--font-sm);max-width:280px">
                        <option value="fr" ${recoLang === 'fr' ? 'selected' : ''}>Français</option>
                        <option value="en" ${recoLang === 'en' ? 'selected' : ''}>English</option>
                        <option value="ha" ${recoLang === 'ha' ? 'selected' : ''}>Hausa (هَوُسَ)</option>
                        <option value="sw" ${recoLang === 'sw' ? 'selected' : ''}>Swahili (Kiswahili)</option>
                        <option value="af" ${recoLang === 'af' ? 'selected' : ''}>Afrikaans</option>
                        <option value="am" ${recoLang === 'am' ? 'selected' : ''}>Amharic (አማርኛ)</option>
                        <option value="ar" ${recoLang === 'ar' ? 'selected' : ''}>العربية</option>
                        <option value="yo" ${recoLang === 'yo' ? 'selected' : ''}>Yoruba (Èdè Yorùbá)</option>
                        <option value="ig" ${recoLang === 'ig' ? 'selected' : ''}>Igbo (Asụsụ Igbo)</option>
                        <option value="zu" ${recoLang === 'zu' ? 'selected' : ''}>Zulu (isiZulu)</option>
                        <option value="xh" ${recoLang === 'xh' ? 'selected' : ''}>Xhosa (isiXhosa)</option>
                        <option value="rw" ${recoLang === 'rw' ? 'selected' : ''}>Kinyarwanda</option>
                        <option value="mg" ${recoLang === 'mg' ? 'selected' : ''}>Malagasy</option>
                        <option value="sn" ${recoLang === 'sn' ? 'selected' : ''}>Shona (chiShona)</option>
                        <option value="so" ${recoLang === 'so' ? 'selected' : ''}>Somali (Soomaali)</option>
                        <option value="st" ${recoLang === 'st' ? 'selected' : ''}>Sesotho</option>
                        <option value="tn" ${recoLang === 'tn' ? 'selected' : ''}>Tswana (Setswana)</option>
                        <option value="ny" ${recoLang === 'ny' ? 'selected' : ''}>Chichewa (Nyanja)</option>
                        <option value="bm" ${recoLang === 'bm' ? 'selected' : ''}>Bamanankan (ߒߞߏ)</option>
                        <option value="wo" ${recoLang === 'wo' ? 'selected' : ''}>Wolof</option>
                        <option value="ff" ${recoLang === 'ff' ? 'selected' : ''}>Fulfulde</option>
                    </select>
                    <span id="lang-loading" style="display:none;font-size:var(--font-xs);color:var(--gray-500)">⏳ Regénération...</span>
                </div>
                <div style="font-size:var(--font-xs);color:var(--gray-500);margin-top:var(--spacing-xs)">
                    ${recoLang === 'ha' || recoLang === 'sw' || recoLang === 'af' || recoLang === 'am' || recoLang === 'ar' 
                        ? '⚡ Synthèse vocale par gTTS · Texte généré par IA'
                        : '⚡ Synthèse vocale par gTTS · Texte généré par IA (certaines langues experimental)'}
                </div>
            </div>

            ${conseils.resume_global ? `
            <div class="card" style="border-left: 4px solid ${summaryColor}">
                <h3>🌍 Vue d'ensemble du champ</h3>
                <p style="font-size:var(--font-md);line-height:1.6">${conseils.resume_global}</p>
            </div>` : ''}

            ${tts.url ? `
            <div class="card" style="text-align:center">
                <h3>🔊 Ecouter les recommandations</h3>
                <audio controls style="width:100%;margin-top:var(--spacing-sm)" autoplay key="${tts.url}">
                    <source src="${tts.url}">
                </audio>
                <span style="font-size:var(--font-xs);color:var(--gray-500)">Moteur: ${tts.engine || '?'} — ${langLabel}</span>
            </div>` : ''}`;

        recos.forEach((wp) => {
            const s = wp.sensor || {};
            const ml = wp.ml || {};
            const npk = ml.npk_estimes || {};
            const top = ml.top_culture || '—';
            const ranking = ml.classement || [];

            // Trouver le conseil LLM pour cette zone
            const zoneConseil = (conseils.zones || []).find(z => z.zone === wp.waypoint_id) || {};
            const urgColor = zoneConseil.urgence === 'haute' ? '#c62828' : zoneConseil.urgence === 'moyenne' ? '#f57f17' : '#2e7d32';
            const urgenceLabel = recoLang === 'fr'
                ? ({ haute: 'Haute', moyenne: 'Moyenne', faible: 'Faible' })[zoneConseil.urgence] || zoneConseil.urgence
                : ({ haute: 'High', moyenne: 'Medium', faible: 'Low' })[zoneConseil.urgence] || zoneConseil.urgence;

            html += `
                <div class="section rec-section" style="border-left: 4px solid ${urgColor}">
                    <h2>📍 Zone #${wp.waypoint_id}</h2>
                    <div class="rec-summary">
                        <span>💧 ${s.humidity_pct?.toFixed(1) || '?'}%</span>
                        <span>🌡️ ${s.temperature_c?.toFixed(1) || '?'}°C</span>
                        <span>⚡ ${s.ec_us_cm?.toFixed(0) || '?'} µS/cm</span>
                        <span>🧪 pH ${s.ph?.toFixed(1) || '?'}</span>
                    </div>

                    ${zoneConseil.explication ? `
                    <div style="background:var(--green-010);padding:var(--spacing-sm);border-radius:var(--radius-sm);margin-bottom:var(--spacing-sm)">
                        <p style="font-size:var(--font-sm);margin:0"><strong>💡 ${zoneConseil.culture_conseillee || ''}</strong> — ${zoneConseil.explication}</p>
                        ${zoneConseil.action ? `<p style="font-size:var(--font-sm);margin-top:var(--spacing-xs)"><strong>Action:</strong> ${zoneConseil.action}</p>` : ''}
                    </div>` : ''}

                    <div class="rec-cards">
                        ${npk.N_kg_ha ? `
                        <div class="rec-card rec-good">
                            <span class="rec-icon">🧪</span>
                            <div class="rec-body">
                                <h4>NPK estimes</h4>
                                <p>N = ${npk.N_kg_ha} kg/ha | P₂O₅ = ${npk.P2O5_kg_ha} kg/ha | K₂O = ${npk.K2O_kg_ha} kg/ha</p>
                            </div>
                        </div>` : ''}
                        <div class="rec-card ${ml.top_score >= 70 ? 'rec-good' : ml.top_score >= 40 ? 'rec-warning' : 'rec-danger'}">
                            <span class="rec-icon">🌾</span>
                            <div class="rec-body">
                                <h4>Top culture: ${top}</h4>
                                <p>Score: ${ml.top_score}% — ${ranking.slice(0, 3).map(c => `${c.culture} (${c.score}%)`).join(' → ')}</p>
                            </div>
                        </div>
                        ${ml.fertilisation?.NPK_recommandation ? `
                        <div class="rec-card rec-good">
                            <span class="rec-icon">🌱</span>
                            <div class="rec-body">
                                <h4>Fertilisation</h4>
                                <p>${ml.fertilisation.NPK_recommandation}</p>
                            </div>
                        </div>` : ''}
                    </div>
                </div>`;
        });

        main.innerHTML = html;

        // Language selector → auto-regeneration
        const langSelect = document.getElementById('lang-select');
        if (langSelect) {
            langSelect.addEventListener('change', async function() {
                const newLang = this.value;
                if (newLang === recoLang) return;
                recoLang = newLang;
                const loading = document.getElementById('lang-loading');
                if (loading) loading.style.display = 'inline';
                await renderReco(main);
            });
        }
    }

    // ══════════════════════════════════════════════════════════════
    // PAGE: Robot Doctor
    // ══════════════════════════════════════════════════════════════
    async function renderDoctor(main) {
        main.innerHTML = `
            <h1>🩺 Robot Doctor</h1>
            <p class="subtitle">Diagnostic et auto-réparation du robot</p>

            <div class="doctor-actions">
                <button id="doctor-check" class="btn-primary">🔍 Diagnostiquer</button>
                <button id="doctor-heal" class="btn-secondary" disabled>🔧 Auto-réparer</button>
                <label class="doctor-toggle">
                    <input type="checkbox" id="doctor-llm">
                    🤖 Avec analyse LLM (Qwen Code)
                </label>
            </div>

            <div class="doctor-progress" id="doctor-progress" style="display:none">
                <p class="doctor-status">⏳ Diagnostic en cours...</p>
                <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
            </div>

            <div id="doctor-results">
                <div class="empty-state"><p>Lancez un diagnostic pour vérifier l'état du robot.</p></div>
            </div>

            <div class="doctor-history-section">
                <h3>📋 Historique des diagnostics</h3>
                <button id="doctor-history" class="btn-small">🔄 Recharger</button>
                <div id="doctor-history-list"></div>
            </div>`;

        // Events
        document.getElementById('doctor-check').addEventListener('click', doDoctorCheck);
        document.getElementById('doctor-heal').addEventListener('click', doDoctorHeal);
        document.getElementById('doctor-history').addEventListener('click', loadDoctorHistory);
        loadDoctorHistory();
    }

    async function doDoctorCheck() {
        const btn = document.getElementById('doctor-check');
        const healBtn = document.getElementById('doctor-heal');
        const progress = document.getElementById('doctor-progress');
        const fill = document.getElementById('progress-fill');
        const results = document.getElementById('doctor-results');

        btn.disabled = true;
        healBtn.disabled = true;
        progress.style.display = 'block';
        results.innerHTML = '';
        fill.style.width = '10%';

        const withLlm = document.getElementById('doctor-llm')?.checked || false;

        // Anim progression
        let pct = 10;
        const anim = setInterval(() => {
            pct = Math.min(pct + 5, 85);
            fill.style.width = pct + '%';
        }, 800);

        const data = await fetchJSON('/api/doctor/check', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ with_llm: withLlm, auto_heal: false }),
        });

        clearInterval(anim);
        fill.style.width = '100%';
        progress.style.display = 'none';

        if (!data) {
            results.innerHTML = '<div class="empty-state"><p>❌ Erreur de connexion au Doctor</p></div>';
            btn.disabled = false;
            return;
        }

        btn.disabled = false;

        // Global status
        const statusEmoji = data.status === 'ok' ? '✅' : data.status === 'warning' ? '⚠️' : '❌';
        const summary = data.summary || {};
        const checks = data.checks || [];
        const healing = data.healing || [];
        const llm = data.llm_analysis || null;
        const sysInfo = data.system || {};

        // Enable heal if errors
        if (summary.error > 0) healBtn.disabled = false;

        let html = `
            <div class="doctor-summary">
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-icon">${statusEmoji}</span>
                        <span class="stat-value">${summary.total || 0}</span>
                        <span class="stat-label">Tests</span>
                    </div>
                    <div class="stat-card" style="border-top:3px solid #1b9e77">
                        <span class="stat-icon">✅</span>
                        <span class="stat-value">${summary.ok || 0}</span>
                        <span class="stat-label">OK</span>
                    </div>
                    <div class="stat-card" style="border-top:3px solid #e6ab02">
                        <span class="stat-icon">⚠️</span>
                        <span class="stat-value">${summary.warning || 0}</span>
                        <span class="stat-label">Avertissements</span>
                    </div>
                    <div class="stat-card" style="border-top:3px solid #d95f02">
                        <span class="stat-icon">❌</span>
                        <span class="stat-value">${summary.error || 0}</span>
                        <span class="stat-label">Erreurs</span>
                    </div>
                </div>
                <div class="doctor-ts"><small>${data.timestamp || ''}</small></div>
            </div>

            <div class="doctor-system card">
                <h3>💻 Système</h3>
                <div class="sys-grid">
                    ${sysInfo.cpu_temp_c != null ? `<div class="sys-item">🌡️ CPU: ${sysInfo.cpu_temp_c}°C</div>` : ''}
                    ${sysInfo.ram_available_mb != null ? `<div class="sys-item">🧠 RAM: ${sysInfo.ram_available_mb} Mo libre</div>` : ''}
                    ${sysInfo.disk_used_pct != null ? `<div class="sys-item">💾 Disque: ${sysInfo.disk_used_pct}%</div>` : ''}
                    ${sysInfo.uptime ? `<div class="sys-item">⏱️ ${sysInfo.uptime}</div>` : ''}
                </div>
            </div>

            <div class="doctor-checks card">
                <h3>🔍 Résultats des tests</h3>
                ${checks.map(c => {
                    const emoji = c.status === 'ok' ? '✅' : c.status === 'warning' ? '⚠️' : '❌';
                    const color = c.status === 'ok' ? '#1b9e77' : c.status === 'warning' ? '#e6ab02' : '#d95f02';
                    return `
                        <div class="check-row" style="border-left: 4px solid ${color}">
                            <div class="check-header">
                                <span class="check-icon">${emoji}</span>
                                <strong>${c.name}</strong>
                                <span class="check-status" style="color:${color}">${c.status.toUpperCase()}</span>
                            </div>
                            <div class="check-detail">${c.detail}</div>
                            ${c.suggested_action ? `<div class="check-action">💡 ${c.suggested_action}</div>` : ''}
                            ${c.value != null ? `<div class="check-value">Valeur: ${c.value}</div>` : ''}
                        </div>`;
                }).join('')}
            </div>`;

        // LLM analysis
        if (llm) {
            if (llm.error) {
                html += `<div class="doctor-llm card">
                    <h3>🤖 Analyse LLM</h3>
                    <p class="doctor-warn">⚠️ ${llm.error}</p>
                    ${llm.raw ? `<pre class="json-block"><code>${llm.raw}</code></pre>` : ''}
                </div>`;
            } else {
                const sevColor = llm.severite === 'critique' ? '#d95f02' : llm.severite === 'haute' ? '#e6ab02' : '#1b9e77';
                html += `<div class="doctor-llm card">
                    <h3>🤖 Analyse LLM (${llm.model || 'inconnu'})</h3>
                    <p><strong>Analyse:</strong> ${llm.analyse || 'N/A'}</p>
                    <p><strong>Sévérité:</strong> <span style="color:${sevColor}">${llm.severite || 'N/A'}</span></p>
                    ${(llm.priorites || []).length ? `
                        <h4>Priorités</h4>
                        <ul>${llm.priorites.map(p => `<li>🔴 ${p}</li>`).join('')}</ul>` : ''}
                    ${(llm.problemes || []).length ? `
                        <h4>Problèmes</h4>
                        ${llm.problemes.map(p => `
                            <div class="prob-item">
                                <strong>${p.composant || '?'}</strong> (${p.gravite || '?'})
                                <p>${p.cause || ''}</p>
                                ${p.correctif_auto ? `<code>${p.correctif_auto.commande || ''}</code>` : ''}
                                ${p.correctif_manuel ? `<p class="manual">👤 ${p.correctif_manuel}</p>` : ''}
                            </div>`).join('')}` : ''}
                </div>`;
            }
        }

        // Healing
        if (healing.length) {
            html += `<div class="doctor-healing card">
                <h3>🔧 Auto-healing</h3>
                ${healing.map(h => {
                    const emojiH = h.status === 'ok' ? '✅' : '❌';
                    const safe = h.safe ? '🔒' : '⚠️';
                    return `<div class="heal-row">
                        <span>${emojiH} [${safe}] <strong>${h.check_name || '?'}</strong></span>
                        <p>${h.detail}</p>
                    </div>`;
                }).join('')}
            </div>`;
        }

        // Report link
        if (data.report_path) {
            const reportName = data.report_path.split('/').pop();
            html += `<div class="doctor-report card">
                <h3>📄 Rapport</h3>
                <p>📁 <code>data/doctor/${reportName}</code></p>
                <button class="btn-small" onclick="showDoctorReport()">📖 Lire le rapport</button>
                <button class="btn-small" onclick="doctorDownloadReport()">⬇️ Télécharger</button>
                <div id="doctor-report-content" class="doctor-report-content" style="display:none">
                    <div class="empty-state"><p>⏳ Chargement...</p></div>
                </div>
            </div>`;
        }

        results.innerHTML = html;
    }

    async function doDoctorHeal() {
        const btn = document.getElementById('doctor-heal');
        const results = document.getElementById('doctor-results');

        if (!confirm('Lancer les correctifs automatiques ? Les actions non-safes seront ignorées.')) return;

        btn.disabled = true;
        results.innerHTML = '<div class="empty-state"><p>⏳ Auto-healing en cours...</p></div>';

        const data = await fetchJSON('/api/doctor/heal', {
            method: 'POST',
        });

        if (!data) {
            results.innerHTML += '<div class="empty-state"><p>❌ Échec de l\'auto-healing</p></div>';
            btn.disabled = false;
            return;
        }

        btn.disabled = false;
        // Re-afficher le diagnostic complet
        doDoctorCheck();
    }

    async function loadDoctorHistory() {
        const list = document.getElementById('doctor-history-list');
        if (!list) return;

        const data = await fetchJSON('/api/doctor/history');
        if (!data || !data.reports || !data.reports.length) {
            list.innerHTML = '<p class="no-data">Aucun historique.</p>';
            return;
        }

        list.innerHTML = data.reports.map(r =>
            `<div class="history-item" style="cursor:pointer" onclick="loadDoctorReport('${r.name}')">
                <span class="history-name">📄 ${r.name}</span>
                <span class="history-date">${r.date || ''}</span>
                <span class="history-size">${(r.size / 1024).toFixed(1)} KB</span>
            </div>`
        ).join('');
    }

    // ── Fonctions Doctor : rapport ───────────────────────────────
    async function showDoctorReport() {
        const content = document.getElementById('doctor-report-content');
        if (!content) return;

        if (content.style.display !== 'none' && content.innerHTML.includes('Rapport')) {
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
            return;
        }

        content.style.display = 'block';
        content.innerHTML = '<div class="empty-state"><p>⏳ Chargement...</p></div>';

        const data = await fetchJSON('/api/doctor/report');
        if (!data || !data.report) {
            content.innerHTML = '<div class="empty-state"><p>❌ Rapport non disponible</p></div>';
            return;
        }

        // Échapper HTML pour éviter les problèmes, puis afficher en markdown-like
        const escaped = data.report
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        content.innerHTML = `<pre class="doctor-report-pre">${escaped}</pre>`;
    }
    window.showDoctorReport = showDoctorReport;

    async function loadDoctorReport(name) {
        // Créer une modale simple pour afficher un rapport spécifique
        const main = document.getElementById('main-content');
        const overlay = document.createElement('div');
        overlay.className = 'doctor-modal-overlay';
        overlay.innerHTML = `
            <div class="doctor-modal">
                <div class="doctor-modal-header">
                    <h3>📄 ${name}</h3>
                    <button class="doctor-modal-close">&times;</button>
                </div>
                <div class="doctor-modal-body">
                    <div class="empty-state"><p>⏳ Chargement...</p></div>
                </div>
            </div>`;

        document.body.appendChild(overlay);

        // Fermeture
        overlay.querySelector('.doctor-modal-close').onclick = () => overlay.remove();
        overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

        // Charger le rapport via API (on utilise report pour le dernier; pour l'historique
        // on doit récupérer le fichier directement)
        const body = overlay.querySelector('.doctor-modal-body');
        try {
            const resp = await fetch('/api/doctor/report');
            const data = await resp.json();
            if (data && data.report) {
                const escaped = data.report
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
                body.innerHTML = `<pre class="doctor-report-pre">${escaped}</pre>`;
            } else {
                body.innerHTML = '<div class="empty-state"><p>❌ Rapport introuvable</p></div>';
            }
        } catch (e) {
            body.innerHTML = `<div class="empty-state"><p>❌ Erreur: ${e.message}</p></div>`;
        }
    }
    window.loadDoctorReport = loadDoctorReport;

    function doctorDownloadReport() {
        // Télécharger le rapport en tant que fichier .md
        const link = document.createElement('a');
        link.href = '/api/doctor/report/download';
        link.download = 'diagnostic_agroscan.md';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    window.doctorDownloadReport = doctorDownloadReport;

    // ══════════════════════════════════════════════════════════════
    // PAGE: Mission
    // ══════════════════════════════════════════════════════════════
    async function renderMission(main) {
        const config = await fetchJSON('/api/mission/config');
        const backups = await fetchJSON('/api/mission/backups');
        const status = await fetchJSON('/api/mission/status');
        const mapData = await fetchJSON('/api/mission/map');

        const W = mapData?.table?.width_cm || 150;
        const H = mapData?.table?.height_cm || 100;
        const start = mapData?.start || {x: 10, y: 10, heading_deg: 0};
        const waypoints = mapData?.waypoints || [];
        const ratio = H / W;

        // ── Helper: coords cm → % dans le rectangle ──
        function cmToPct(cx, cy) {
            return { left: (cx / W * 100).toFixed(1), bottom: (cy / H * 100).toFixed(1) };
        }

        // ── Rendu waypoint ──
        function wpHtml(wp) {
            const p = cmToPct(wp.x, wp.y);
            return `<div class="fw-wp" data-id="${wp.id}" style="left:${p.left}%;bottom:${p.bottom}%">
                <div class="fw-wp-dot">${wp.id}</div>
                <div class="fw-wp-info">#${wp.id} ${wp.x}×${wp.y}cm</div>
            </div>`;
        }

        // ── Start marker ──
        const sp = cmToPct(start.x, start.y);
        const startHtml = `<div class="fw-start" style="left:${sp.left}%;bottom:${sp.bottom}%">
            <div class="fw-start-dot" title="Départ cap:${start.heading_deg}°">▶</div>
        </div>`;

        // ── HTML ──
        const configHtml = config ? Object.entries(config).map(([name, info]) => `
            <div class="mission-config-item">
                <div class="config-header toggle-config">
                    <span class="config-toggle-icon">▶</span>
                    <strong>📄 ${name}</strong>
                    <span class="config-meta">${(info.size / 1024).toFixed(1)} Ko · ${info.modified || ''}</span>
                </div>
                ${info.content ? `<pre class="config-preview collapsed">${JSON.stringify(info.content, null, 2).slice(0, 300)}...</pre>` : ''}
            </div>
        `).join('') : '<p class="no-data">Aucune configuration</p>';

        const backuplist = backups?.backups?.length
            ? backups.backups.map(b => `
                <div class="backup-item">
                    <span class="backup-name">📁 ${b.name}</span>
                    <span class="backup-date">${b.modified || b.timestamp || ''}</span>
                    <button class="btn-small restore-btn" data-backup="${b.name}">🔄 Restaurer</button>
                </div>
            `).join('')
            : '<p class="no-data">Aucune backup</p>';

        const missionStatus = status?.running
            ? `<div class="mission-status running"><span class="blink-dot"></span> Mission en cours (PID ${status.pid})</div>`
            : '<div class="mission-status idle">⏸️ Aucune mission en cours</div>';

        const wpListHtml = waypoints.length
            ? waypoints.map(w => `
                <div class="wp-list-item" data-id="${w.id}">
                    <span class="wp-list-dot">🔵</span>
                    <span class="wp-list-coord">${w.x} × ${w.y} cm</span>
                    <span class="wp-list-opts">sonde:${w.probe?'✅':'❌'} 📸${w.photos||0}</span>
                    <button class="btn-small wp-delete" data-id="${w.id}" style="margin-left:auto">🗑️</button>
                </div>`).join('')
            : '<p class="no-data muted">Aucun point — clique sur le champ</p>';

        main.innerHTML = `
            <h1>Mission</h1>
            <p class="subtitle">Gérer les configurations, lancer et suivre les missions</p>

            <div class="mission-grid">
                <!-- ── État ── -->
                <div class="card mission-panel">
                    <h3 class="card-toggle"><span class="card-toggle-icon">▼</span> 📋 État</h3>
                    ${missionStatus}
                    ${status?.results?.mission ? `
                        <div class="last-mission">
                            <strong>Dernière mission:</strong> ${status.results.mission.start_time || 'N/A'}
                            <br>Waypoints: ${(status.results.waypoints || []).length}
                        </div>` : ''}
                    <div class="mission-actions">
                        <button id="btn-start-mission" class="btn-primary" ${status?.running ? 'disabled' : ''}>▶️ Lancer la mission</button>
                        <button id="btn-dry-run" class="btn-secondary" ${status?.running ? 'disabled' : ''}>🧪 Test (dry-run)</button>
                        <button id="btn-stop-mission" class="btn-danger" ${!status?.running ? 'disabled' : ''}>⏹️ Arrêter</button>
                        <button id="btn-refresh-status" class="btn-small">🔄</button>
                    </div>
                </div>

                <!-- ── Carte du champ ── -->
                <div class="card mission-panel" id="field-map-card">
                    <h3 class="card-toggle"><span class="card-toggle-icon">▼</span> 🗺️ Carte du champ</h3>
                    <div class="fw-controls">
                        <label>L × <input type="number" id="fw-width" value="${W}" class="fw-input" min="10" max="1000"> cm</label>
                        <label>H × <input type="number" id="fw-height" value="${H}" class="fw-input" min="10" max="1000"> cm</label>
                        <span style="color:var(--gray-500);font-size:var(--font-xs)">${waypoints.length} point(s)</span>
                    </div>
                    <div class="fw-container" id="fw-container" style="aspect-ratio:${W}/${H}">
                        ${startHtml}
                        ${waypoints.map(w => wpHtml(w)).join('')}
                    </div>
                    <div class="fw-legend">
                        <span>▶ Départ (${start.x}, ${start.y}cm cap ${start.heading_deg}°)</span>
                        <span>· 🔵 Clique sur le champ pour ajouter un point</span>
                    </div>
                    <div class="wp-list" id="wp-list">
                        <h4 style="margin:8px 0 4px;font-size:var(--font-sm)">📌 Points</h4>
                        ${wpListHtml}
                    </div>
                    <div id="wp-editor" class="wp-editor" style="display:none"></div>
                    <div class="fw-actions">
                        <button id="btn-save-map" class="btn-primary">💾 Sauvegarder map.json</button>
                        <span id="map-save-status" style="margin-left:8px;font-size:var(--font-sm)"></span>
                    </div>
                </div>

                <!-- ── Config ── -->
                <div class="card mission-panel collapsed">
                    <h3 class="card-toggle"><span class="card-toggle-icon">▶</span> ⚙️ Configuration actuelle</h3>
                    <div class="mission-config-list">${configHtml}</div>
                    <div class="upload-area">
                        <h4>📤 Upload un fichier</h4>
                        <form id="upload-form">
                            <input type="file" id="file-input" accept=".json" class="file-input">
                            <button type="submit" class="btn-small">⬆️ Upload</button>
                        </form>
                        <p class="upload-hint">Fichiers acceptés : map.json, calibration.json, config.json</p>
                    </div>
                    <button id="btn-backup" class="btn-small">💾 Sauvegarder la config actuelle</button>
                </div>

                <!-- ── Backups ── -->
                <div class="card mission-panel collapsed">
                    <h3 class="card-toggle"><span class="card-toggle-icon">▶</span> 📦 Backups</h3>
                    <div class="backup-list">${backuplist}</div>
                </div>

                <!-- ── Robot IP ── -->
                <div class="card mission-panel collapsed" id="robot-info-card">
                    <h3 class="card-toggle"><span class="card-toggle-icon">▶</span> 🌐 Accès au robot</h3>
                    <div id="robot-info-content"><p class="no-data">Chargement...</p></div>
                </div>

                <!-- ── Email ── -->
                <div class="card mission-panel collapsed" id="email-config-card">
                    <h3 class="card-toggle"><span class="card-toggle-icon">▶</span> 📧 Notification IP par email</h3>
                    <p class="subtitle">Reçois l'adresse du robot par email à chaque démarrage</p>
                    <div id="email-config-form">
                        <form id="email-form">
                            <label>Ton email (destinataire)</label>
                            <input type="email" id="email-recipient" placeholder="ton@email.com" class="email-input" required>
                            <label>Email expéditeur (Gmail recommandé)</label>
                            <input type="email" id="email-sender" placeholder="robot.agroscan@gmail.com" class="email-input" required>
                            <label>Mot de passe d'application Gmail</label>
                            <input type="password" id="email-password" placeholder="xxxx xxxx xxxx xxxx" class="email-input">
                            <p class="input-hint">Gmail → Compte → Sécurité → Mots de passe d'application</p>
                            <label>Serveur SMTP</label>
                            <input type="text" id="email-server" value="smtp.gmail.com" class="email-input">
                            <div class="inline-fields">
                                <div>
                                    <label>Port</label>
                                    <input type="number" id="email-port" value="587" class="email-input" style="width:80px">
                                </div>
                            </div>
                            <button type="submit" class="btn-primary" style="margin-top:12px">💾 Sauvegarder</button>
                            <span id="email-save-status" style="margin-left:10px"></span>
                        </form>
                        <div style="margin-top:12px">
                            <button id="btn-test-email" class="btn-secondary">📨 Tester l'envoi</button>
                            <span id="email-test-status" style="margin-left:10px"></span>
                        </div>
                    </div>
                </div>
            </div>`;

        // ══════════════════════════════════════════════════════════════
        // ÉVÉNEMENTS
        // ══════════════════════════════════════════════════════════════

        // ── Mission ──
        document.getElementById('btn-start-mission')?.addEventListener('click', () => launchMission(false));
        document.getElementById('btn-dry-run')?.addEventListener('click', () => launchMission(true));
        document.getElementById('btn-stop-mission')?.addEventListener('click', stopMission);
        document.getElementById('btn-refresh-status')?.addEventListener('click', () => renderMission(main));

        // ── Upload ──
        document.getElementById('upload-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fi = document.getElementById('file-input');
            if (!fi?.files?.length) return;
            const fd = new FormData();
            fd.append('file', fi.files[0]);
            const r = await (await fetch('/api/mission/config/upload', {method:'POST', body:fd})).json();
            if (r.success) renderMission(main); else alert('❌ '+(r.error||'Échec'));
        });

        // ── Toggle config ──
        document.querySelectorAll('.toggle-config').forEach(el => {
            el.addEventListener('click', () => {
                const preview = el.nextElementSibling;
                if (preview?.classList?.contains('config-preview')) {
                    preview.classList.toggle('collapsed');
                    const icon = el.querySelector('.config-toggle-icon');
                    if (icon) icon.textContent = preview.classList.contains('collapsed') ? '▶' : '▼';
                }
            });
        });

        // ── Toggle cards ──
        document.querySelectorAll('.card-toggle').forEach(el => {
            el.addEventListener('click', () => {
                const panel = el.closest('.mission-panel');
                if (!panel) return;
                panel.classList.toggle('collapsed');
                const icon = el.querySelector('.card-toggle-icon');
                if (icon) icon.textContent = panel.classList.contains('collapsed') ? '▶' : '▼';
            });
        });

        // ── Backup ──
        document.getElementById('btn-backup')?.addEventListener('click', async () => {
            const r = await (await fetch('/api/mission/backup', {method:'POST'})).json();
            if (r.success) renderMission(main); else alert('❌ '+(r.error||'Échec'));
        });

        // ── Restore ──
        document.querySelectorAll('.restore-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const b = btn.dataset.backup;
                if (!confirm(`Restaurer ${b} ?`)) return;
                const r = await (await fetch('/api/mission/restore', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({backup:b})})).json();
                if (r.success) renderMission(main); else alert('❌ '+(r.error||'Échec'));
            });
        });

        // ══════════════════════════════════════════════════════════════
        // CARTE DU CHAMP
        // ══════════════════════════════════════════════════════════════

        let currentMap = {...(mapData || {})};
        if (!currentMap.waypoints) currentMap.waypoints = [...waypoints];
        if (!currentMap.start) currentMap.start = {...start};
        if (!currentMap.table) currentMap.table = {width_cm: W, height_cm: H};

        const container = document.getElementById('fw-container');

        // ── Clique sur le champ → ajouter waypoint ──
        container?.addEventListener('click', (e) => {
            if (e.target.closest('.fw-wp') || e.target.closest('.fw-start')) return;
            const rect = container.getBoundingClientRect();
            const wCur = currentMap.table.width_cm;
            const hCur = currentMap.table.height_cm;
            const pctX = (e.clientX - rect.left) / rect.width;
            const pctY = 1 - (e.clientY - rect.top) / rect.height;
            const cx = Math.round(pctX * wCur);
            const cy = Math.round(pctY * hCur);
            const maxId = currentMap.waypoints.reduce((m, w) => Math.max(m, w.id), 0);
            const nw = {id: maxId + 1, x: cx, y: cy, probe: true, photos: 3};
            currentMap.waypoints.push(nw);
            // Ajout visuel
            const p = cmToPct(cx, cy);
            const dot = document.createElement('div');
            dot.className = 'fw-wp';
            dot.style.cssText = `left:${p.left}%;bottom:${p.bottom}%`;
            dot.dataset.id = nw.id;
            dot.innerHTML = `<div class="fw-wp-dot">${nw.id}</div><div class="fw-wp-info">#${nw.id} ${cx}×${cy}cm</div>`;
            container.appendChild(dot);
            // Mettre à jour la liste
            renderWpList();
            showSaveStatus('Non sauvegardé', '⚠️');
        });

        // ── Clique waypoint pour éditer ──
        container?.addEventListener('click', (e) => {
            const wpEl = e.target.closest('.fw-wp');
            if (!wpEl) return;
            e.stopPropagation();
            const id = parseInt(wpEl.dataset.id);
            const w = currentMap.waypoints.find(x => x.id === id);
            if (!w) return;
            document.querySelectorAll('.fw-wp').forEach(el => el.classList.remove('selected'));
            wpEl.classList.add('selected');
            const editor = document.getElementById('wp-editor');
            editor.style.display = 'block';
            editor.innerHTML = `
                <h4 style="margin:0 0 6px;font-size:var(--font-sm)">✏️ Point #${w.id}</h4>
                <div class="wp-edit-fields">
                    <label>X: <input type="number" id="wp-ex" value="${w.x}" class="fw-input" min="0" max="${currentMap.table.width_cm}"> cm</label>
                    <label>Y: <input type="number" id="wp-ey" value="${w.y}" class="fw-input" min="0" max="${currentMap.table.height_cm}"> cm</label>
                    <label>Sonde: <input type="checkbox" id="wp-eprobe" ${w.probe?'checked':''}></label>
                    <label>📸: <input type="number" id="wp-ephotos" value="${w.photos||0}" class="fw-input" min="0" max="20"></label>
                    <button id="wp-update" class="btn-small">✅ OK</button>
                    <button id="wp-delete" class="btn-small" style="background:#d95f02;color:white">🗑️ Supprimer</button>
                </div>`;
            document.getElementById('wp-update')?.addEventListener('click', () => {
                w.x = parseInt(document.getElementById('wp-ex').value) || 0;
                w.y = parseInt(document.getElementById('wp-ey').value) || 0;
                w.probe = document.getElementById('wp-eprobe').checked;
                w.photos = parseInt(document.getElementById('wp-ephotos').value) || 0;
                editor.style.display = 'none';
                renderWpDots();
                renderWpList();
                showSaveStatus('Non sauvegardé', '⚠️');
            });
            document.getElementById('wp-delete')?.addEventListener('click', () => {
                if (!confirm(`Supprimer le point #${w.id} ?`)) return;
                currentMap.waypoints = currentMap.waypoints.filter(x => x.id !== id);
                editor.style.display = 'none';
                renderWpDots();
                renderWpList();
                showSaveStatus('Non sauvegardé', '⚠️');
            });
        });

        // ── Suppression depuis la liste ──
        document.querySelectorAll('.wp-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = parseInt(btn.dataset.id);
                if (!confirm(`Supprimer le point #${id} ?`)) return;
                currentMap.waypoints = currentMap.waypoints.filter(x => x.id !== id);
                renderWpDots();
                renderWpList();
                document.getElementById('wp-editor').style.display = 'none';
                showSaveStatus('Non sauvegardé', '⚠️');
            });
        });

        function renderWpDots() {
            const old = container.querySelectorAll('.fw-wp');
            old.forEach(el => el.remove());
            currentMap.waypoints.forEach(w => {
                const p = cmToPct(w.x, w.y);
                const d = document.createElement('div');
                d.className = 'fw-wp';
                d.style.cssText = `left:${p.left}%;bottom:${p.bottom}%`;
                d.dataset.id = w.id;
                d.innerHTML = `<div class="fw-wp-dot">${w.id}</div><div class="fw-wp-info">#${w.id} ${w.x}×${w.y}cm</div>`;
                container.appendChild(d);
            });
        }

        function renderWpList() {
            const list = document.getElementById('wp-list');
            if (!list) return;
            const html = currentMap.waypoints.length
                ? currentMap.waypoints.map(w => `
                    <div class="wp-list-item" data-id="${w.id}">
                        <span class="wp-list-dot">🔵</span>
                        <span class="wp-list-coord">${w.x} × ${w.y} cm</span>
                        <span class="wp-list-opts">sonde:${w.probe?'✅':'❌'} 📸${w.photos||0}</span>
                        <button class="btn-small wp-delete" data-id="${w.id}" style="margin-left:auto">🗑️</button>
                    </div>`).join('')
                : '<p class="no-data muted">Aucun point — clique sur le champ</p>';
            list.innerHTML = `<h4 style="margin:8px 0 4px;font-size:var(--font-sm)">📌 Points (${currentMap.waypoints.length})</h4>` + html;
            // Rebinder les delete de la liste
            list.querySelectorAll('.wp-delete').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const id = parseInt(btn.dataset.id);
                    if (!confirm(`Supprimer le point #${id} ?`)) return;
                    currentMap.waypoints = currentMap.waypoints.filter(x => x.id !== id);
                    renderWpDots();
                    renderWpList();
                    document.getElementById('wp-editor').style.display = 'none';
                    showSaveStatus('Non sauvegardé', '⚠️');
                });
            });
        }

        function showSaveStatus(msg, icon) {
            const el = document.getElementById('map-save-status');
            if (el) el.textContent = (icon||'') + ' ' + msg;
        }

        // ── Appliquer dimensions ──
        document.getElementById('fw-width')?.addEventListener('change', () => {
            currentMap.table.width_cm = parseInt(document.getElementById('fw-width').value) || 150;
            container.style.aspectRatio = `${currentMap.table.width_cm}/${currentMap.table.height_cm}`;
            renderWpDots();
            showSaveStatus('Dimensions changées — sauvegarde requise', '⚠️');
        });
        document.getElementById('fw-height')?.addEventListener('change', () => {
            currentMap.table.height_cm = parseInt(document.getElementById('fw-height').value) || 100;
            container.style.aspectRatio = `${currentMap.table.width_cm}/${currentMap.table.height_cm}`;
            renderWpDots();
            showSaveStatus('Dimensions changées — sauvegarde requise', '⚠️');
        });

        // ── Sauvegarder map.json ──
        document.getElementById('btn-save-map')?.addEventListener('click', async () => {
            currentMap.table.width_cm = parseInt(document.getElementById('fw-width').value) || 150;
            currentMap.table.height_cm = parseInt(document.getElementById('fw-height').value) || 100;
            const payload = {
                table: {...currentMap.table},
                start: {...currentMap.start},
                waypoints: [...currentMap.waypoints],
            };
            const r = await (await fetch('/api/mission/map', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})).json();
            showSaveStatus(r.success ? '✅ Sauvegardé' : '❌ Erreur');
            if (r.success) setTimeout(() => document.getElementById('map-save-status').textContent = '', 2000);
        });

        // ── IP Robot ──
        fetchJSON('/api/network/ip').then(info => {
            const el = document.getElementById('robot-info-content');
            if (!el) return;
            if (info?.ip) {
                el.innerHTML = `
                    <div class="robot-ip-info">
                        <div class="ip-row"><span class="ip-label">IP</span><code class="ip-value">${info.ip}</code></div>
                        <div class="ip-row"><span class="ip-label">Hostname</span><code class="ip-value">${info.hostname}.local</code></div>
                        <div class="ip-row"><span class="ip-label">Dashboard</span><a href="${info.url}" target="_blank" class="ip-link">${info.url}</a></div>
                        <div class="ip-row"><span class="ip-label">mDNS</span><code class="ip-value muted">${info.mdns}</code></div>
                        <button id="btn-copy-ip" class="btn-small" style="margin-top:8px">📋 Copier l'URL</button>
                    </div>`;
                document.getElementById('btn-copy-ip')?.addEventListener('click', () => {
                    navigator.clipboard.writeText(info.url).then(() => {
                        const b = document.getElementById('btn-copy-ip');
                        b.textContent = '✅ Copié !';
                        setTimeout(() => { b.textContent = "📋 Copier l'URL"; }, 2000);
                    });
                });
            } else el.innerHTML = '<p class="no-data">IP impossible</p>';
        }).catch(() => { const el = document.getElementById('robot-info-content'); if(el) el.innerHTML = '<p class="no-data">Erreur réseau</p>'; });

        // ── Email form ──
        fetchJSON('/api/mission/email-config').then(cfg => {
            if (!cfg) return;
            document.getElementById('email-recipient').value = cfg.recipient_email || '';
            document.getElementById('email-sender').value = cfg.smtp_user || '';
            document.getElementById('email-server').value = cfg.smtp_server || 'smtp.gmail.com';
            document.getElementById('email-port').value = cfg.smtp_port || 587;
        });

        document.getElementById('email-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const st = document.getElementById('email-save-status');
            st.textContent = '⏳';
            const r = await (await fetch('/api/mission/email-config', {method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({
                    recipient_email: document.getElementById('email-recipient').value,
                    smtp_user: document.getElementById('email-sender').value,
                    smtp_password: document.getElementById('email-password').value,
                    smtp_server: document.getElementById('email-server').value,
                    smtp_port: parseInt(document.getElementById('email-port').value) || 587,
                })})).json();
            st.textContent = r.success ? '✅ Sauvegardé' : '❌ Erreur';
            document.getElementById('email-password').value = '';
            setTimeout(() => st.textContent = '', 3000);
        });

        document.getElementById('btn-test-email')?.addEventListener('click', async () => {
            const btn = document.getElementById('btn-test-email');
            const st = document.getElementById('email-test-status');
            btn.disabled = true; st.textContent = '⏳';
            await fetch('/api/mission/email-config', {method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({
                    recipient_email: document.getElementById('email-recipient').value,
                    smtp_user: document.getElementById('email-sender').value,
                    smtp_password: document.getElementById('email-password').value,
                    smtp_server: document.getElementById('email-server').value,
                    smtp_port: parseInt(document.getElementById('email-port').value) || 587,
                })});
            const r = await (await fetch('/api/mission/test-email', {method:'POST'})).json();
            st.textContent = r.success ? '✅ Envoyé ! Vérifie ta boîte' : '❌ ' + (r.error||'Échec');
            btn.disabled = false;
            setTimeout(() => st.textContent = '', 5000);
        });
    }

    async function launchMission(dryRun) {
        const resp = await fetch('/api/mission/launch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ dry_run: dryRun }),
        });
        const result = await resp.json();
        if (result.success) {
            // Recharger la page mission après 3s
            setTimeout(() => {
                const main = document.getElementById('main-content');
                if (main) renderMission(main);
            }, 3000);
        } else {
            alert('❌ ' + (result.error || 'Échec du lancement'));
        }
    }

    async function stopMission() {
        if (!confirm('Arrêter la mission en cours ?')) return;
        const resp = await fetch('/api/mission/stop', { method: 'POST' });
        const result = await resp.json();
        if (result.success) {
            const main = document.getElementById('main-content');
            if (main) renderMission(main);
        } else {
            alert('❌ ' + (result.error || 'Échec arrêt'));
        }
    }

    async function doBackup() {
        const resp = await fetch('/api/mission/backup', { method: 'POST' });
        const result = await resp.json();
        if (result.success) {
            const main = document.getElementById('main-content');
            if (main) renderMission(main);
        } else {
            alert('❌ ' + (result.error || 'Backup échoué'));
        }
    }

    // ══════════════════════════════════════════════════════════════
    // PAGE: Données
    async function renderData(main, waypoints) {
        const photosResp = await fetchJSON('/api/results');
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

    // ── Init ─────────────────────────────────────────────────────
    const hash = location.hash.replace('#', '') || 'dashboard';
    navigate(hash);
})();
