/* analytics.js – 스마트 관수 시스템 데이터 분석 페이지 v2.0
   Stage 14: BUG-18 수정 (컬럼명 불일치) + 환경 데이터 시계열 차트 추가
*/
'use strict';

/* ─────────────────────────────────────────
   전역 상태
───────────────────────────────────────── */
const state = {
    sensorRows: [],
    irrRows:    [],
    filteredIrr:[],
    fromDate: '',
    toDate:   '',
};

const charts = {};

/* ─────────────────────────────────────────
   공통 줌/팬 옵션
───────────────────────────────────────── */
function zoomPlugin(axis = 'x') {
    return {
        zoom: { wheel:{enabled:true}, pinch:{enabled:true}, mode:axis,
                onZoomComplete({chart}){ chart.update('none'); } },
        pan:  { enabled:true, mode:axis }
    };
}

/* ─────────────────────────────────────────
   날짜 범위 빠른 선택
───────────────────────────────────────── */
function setRange(days) {
    const to   = new Date();
    const from = new Date();
    from.setDate(to.getDate() - (days - 1));
    document.getElementById('filter-from').value = fmtDate(from);
    document.getElementById('filter-to').value   = fmtDate(to);
}
function fmtDate(d) { return d.toISOString().slice(0, 10); }
function initDateDefaults() {
    const to   = new Date();
    const from = new Date();
    from.setDate(to.getDate() - 29);
    document.getElementById('filter-from').value = fmtDate(from);
    document.getElementById('filter-to').value   = fmtDate(to);
}

/* ─────────────────────────────────────────
   메인 진입: 전체 로드
───────────────────────────────────────── */
async function loadAll() {
    state.fromDate = document.getElementById('filter-from').value;
    state.toDate   = document.getElementById('filter-to').value;

    showLoading('tank-loading', true);
    showLoading('irr-loading',  true);

    await Promise.all([
        loadSensorData(),
        loadIrrigationHistory(),
    ]);

    showLoading('tank-loading', false);
    showLoading('irr-loading',  false);

    // 환경 탭이 활성화 상태면 환경 데이터도 로드
    const envTab = document.getElementById('tab-env');
    if (envTab && envTab.classList.contains('active')) {
        loadEnvData();
    }
}

/* ─────────────────────────────────────────
   탱크 수위 데이터 로드 & 렌더
───────────────────────────────────────── */
async function loadSensorData() {
    try {
        let url = '/api/analytics/sensor-data';
        const p = [];
        if (state.fromDate) p.push('from=' + state.fromDate);
        if (state.toDate)   p.push('to='   + state.toDate);
        if (p.length) url += '?' + p.join('&');

        const res  = await fetch(url);
        const json = await res.json();
        if (!json.success) { console.warn('sensor data:', json.error); return; }

        state.sensorRows = json.data || [];
        renderTankChart();
        renderTankStats(json.stats);
        updateSummary();
    } catch (e) { console.error('센서 데이터 로드 실패:', e); }
}

function renderTankChart() {
    const rows = state.sensorRows;
    if (!rows.length) return;
    const MAX  = 800;
    const step = Math.max(1, Math.floor(rows.length / MAX));
    const sampled = rows.filter((_, i) => i % step === 0);
    const labels  = sampled.map(r => r.timestamp);
    const t1      = sampled.map(r => parseFloat(r.tank1_level));
    const t2      = sampled.map(r => parseFloat(r.tank2_level));
    const ctx     = document.getElementById('tank-chart').getContext('2d');
    if (charts.tank) charts.tank.destroy();
    charts.tank = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets: [
            { label:'탱크1 수위 (%)', data:t1, borderColor:'#2196f3',
              backgroundColor:'rgba(33,150,243,0.08)', borderWidth:1.5,
              pointRadius:0, fill:true, tension:0.3 },
            { label:'탱크2 수위 (%)', data:t2, borderColor:'#4caf50',
              backgroundColor:'rgba(76,175,80,0.08)', borderWidth:1.5,
              pointRadius:0, fill:true, tension:0.3 }
        ]},
        options: {
            responsive:true,
            interaction:{ mode:'index', intersect:false },
            plugins:{ legend:{ position:'top' },
                      tooltip:{ callbacks:{ label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}%` }},
                      zoom: zoomPlugin('x') },
            scales:{
                x:{ ticks:{ maxTicksLimit:10, font:{size:11}, maxRotation:30,
                             callback(val,i){ const l=this.getLabelForValue(val); return l?l.slice(5,16):''; }},
                    grid:{color:'#f0f0f0'} },
                y:{ min:0, max:100,
                    ticks:{ callback: v => v+'%', font:{size:11} },
                    grid:{color:'#f0f0f0'} }
            }
        }
    });
}

function renderTankStats(stats) {
    if (!stats) return;
    function statHTML(s) {
        if (!s || s.count === 0) return '<div class="empty-state"><i class="bi bi-inbox"></i>데이터 없음</div>';
        return `<table class="table table-sm mb-0">
            <tr><td class="text-muted">측정 횟수</td><td class="fw-bold">${s.count.toLocaleString()}회</td></tr>
            <tr><td class="text-muted">평균 수위</td><td class="fw-bold text-primary">${s.avg.toFixed(1)}%</td></tr>
            <tr><td class="text-muted">최솟값</td><td class="fw-bold text-danger">${s.min.toFixed(1)}%</td></tr>
            <tr><td class="text-muted">최댓값</td><td class="fw-bold text-success">${s.max.toFixed(1)}%</td></tr>
            <tr><td class="text-muted">첫 기록</td><td class="text-muted">${(s.first_timestamp||'').slice(0,16)}</td></tr>
            <tr><td class="text-muted">마지막 기록</td><td class="text-muted">${(s.last_timestamp||'').slice(0,16)}</td></tr>
        </table>`;
    }
    document.getElementById('t1-stats-body').innerHTML = statHTML(stats.tank1);
    document.getElementById('t2-stats-body').innerHTML = statHTML(stats.tank2);
    if (stats.tank1 && stats.tank1.count > 0) setText('stat-t1-avg', stats.tank1.avg.toFixed(1) + '%');
    if (stats.tank2 && stats.tank2.count > 0) setText('stat-t2-avg', stats.tank2.avg.toFixed(1) + '%');
}

function resetTankZoom() { if (charts.tank) charts.tank.resetZoom(); }

/* ─────────────────────────────────────────
   관수 이력 로드 & 렌더
───────────────────────────────────────── */
async function loadIrrigationHistory() {
    try {
        let url = '/api/analytics/irrigation-history';
        const p = [];
        if (state.fromDate) p.push('from=' + state.fromDate);
        if (state.toDate)   p.push('to='   + state.toDate);
        if (p.length) url += '?' + p.join('&');

        const res  = await fetch(url);
        const json = await res.json();
        if (!json.success) { console.warn('irr history:', json.error); return; }

        state.irrRows     = json.data || [];
        state.filteredIrr = [...state.irrRows];

        buildZoneFilter();
        renderIrrBarChart();
        renderTriggerDonut();
        renderDurLineChart();
        renderZoneCharts();
        renderLogTable();
        updateSummary();
    } catch (e) { console.error('관수 이력 로드 실패:', e); }
}

/* 일별 관수 횟수 바 차트 */
function renderIrrBarChart() {
    const rows   = state.filteredIrr;
    const dayMap = {};
    rows.forEach(r => {
        const day = (r.timestamp || '').slice(0, 10);
        if (!day) return;
        dayMap[day] = (dayMap[day] || 0) + 1;
    });
    const labels = Object.keys(dayMap).sort();
    const data   = labels.map(d => dayMap[d]);
    const ctx    = document.getElementById('irr-bar-chart').getContext('2d');
    if (charts.irrBar) charts.irrBar.destroy();
    charts.irrBar = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{
            label:'관수 횟수', data, backgroundColor:'rgba(102,126,234,0.6)',
            borderColor:'#667eea', borderWidth:1, borderRadius:4
        }]},
        options:{
            responsive:true,
            plugins:{ legend:{display:false}, zoom:zoomPlugin('x') },
            scales:{
                x:{ ticks:{ font:{size:11}, maxRotation:30 }, grid:{color:'#f0f0f0'} },
                y:{ beginAtZero:true, ticks:{ stepSize:1, font:{size:11} }, grid:{color:'#f0f0f0'} }
            }
        }
    });
    setText('stat-irr-cnt', rows.length + '회');
    const totalSec = rows.reduce((s, r) => s + (parseInt(r.duration_sec) || 0), 0);
    setText('stat-irr-time', fmtSec(totalSec));
}

/* 트리거 비율 도넛
   BUG-18 수정: r.trigger → r.trigger_type */
function renderTriggerDonut() {
    const rows = state.filteredIrr;
    let manual = 0, auto = 0, other = 0;
    rows.forEach(r => {
        // BUG-18 FIX: SQLite 컬럼명은 trigger_type (CSV 폴백 호환: trigger)
        const t = (r.trigger_type || r.trigger || '').toLowerCase();
        if (t === 'manual') manual++;
        else if (t === 'auto') auto++;
        else other++;
    });
    const ctx = document.getElementById('trigger-donut').getContext('2d');
    if (charts.donut) charts.donut.destroy();
    charts.donut = new Chart(ctx, {
        type: 'doughnut',
        data: { labels:['수동','자동','기타'],
                datasets:[{ data:[manual,auto,other],
                            backgroundColor:['#ffc107','#4caf50','#9e9e9e'],
                            borderWidth:2 }]},
        options:{
            responsive:true,
            plugins:{ legend:{ position:'bottom', labels:{ font:{size:12} }},
                      tooltip:{ callbacks:{ label: ctx => {
                          const tot = rows.length || 1;
                          return ` ${ctx.label}: ${ctx.raw}회 (${(ctx.raw/tot*100).toFixed(1)}%)`;
                      }}}}
        }
    });
}

/* 관수 지속 시간 라인 */
function renderDurLineChart() {
    const rows   = [...state.filteredIrr].sort((a,b)=>(a.timestamp||'').localeCompare(b.timestamp||''));
    const labels = rows.map(r => (r.timestamp||'').slice(5,16));
    const data   = rows.map(r => parseInt(r.duration_sec) || 0);
    const ctx    = document.getElementById('dur-line-chart').getContext('2d');
    if (charts.durLine) charts.durLine.destroy();
    charts.durLine = new Chart(ctx, {
        type:'line',
        data:{ labels, datasets:[{
            label:'관수 시간(초)', data,
            borderColor:'#ff9800', backgroundColor:'rgba(255,152,0,0.1)',
            borderWidth:1.5, pointRadius:3, pointHoverRadius:5, fill:true, tension:0.3
        }]},
        options:{
            responsive:true,
            plugins:{ legend:{display:false}, zoom:zoomPlugin('x') },
            scales:{
                x:{ ticks:{ font:{size:10}, maxTicksLimit:12, maxRotation:30 }, grid:{color:'#f0f0f0'} },
                y:{ beginAtZero:true, ticks:{ font:{size:11}, callback: v=>v+'s' }, grid:{color:'#f0f0f0'} }
            }
        }
    });
}

function resetIrrZoom() { if (charts.irrBar)  charts.irrBar.resetZoom(); }
function resetDurZoom() { if (charts.durLine) charts.durLine.resetZoom(); }

/* ─────────────────────────────────────────
   구역별 통계
   BUG-18 수정: r.success → r.status
───────────────────────────────────────── */
function renderZoneCharts() {
    const rows   = state.filteredIrr;
    const zoneMap = {};
    for (let z = 1; z <= 12; z++) zoneMap[z] = { cnt:0, totalSec:0, lastTime:'', successCnt:0 };

    rows.forEach(r => {
        const z = parseInt(r.zone_id);
        if (!zoneMap[z]) return;
        zoneMap[z].cnt++;
        zoneMap[z].totalSec += parseInt(r.duration_sec) || 0;
        if ((r.timestamp||'') > zoneMap[z].lastTime) zoneMap[z].lastTime = r.timestamp || '';
        // BUG-18 FIX: SQLite는 status 컬럼 ('completed'/'failed'), CSV는 success('true'/'false')
        const st = (r.status || '').toLowerCase();
        const ok = r.status != null
            ? (st !== 'failed' && st !== 'false')
            : String(r.success).toLowerCase() !== 'false';
        if (ok) zoneMap[z].successCnt++;
    });

    const zones  = Object.keys(zoneMap).map(Number).sort((a,b)=>a-b);
    const labels = zones.map(z => '구역' + z);
    const cnts   = zones.map(z => zoneMap[z].cnt);
    const avgDur = zones.map(z => zoneMap[z].cnt ? Math.round(zoneMap[z].totalSec / zoneMap[z].cnt) : 0);

    const ctx1 = document.getElementById('zone-bar-chart').getContext('2d');
    if (charts.zoneBar) charts.zoneBar.destroy();
    charts.zoneBar = new Chart(ctx1, {
        type:'bar',
        data:{ labels, datasets:[{
            label:'관수 횟수', data:cnts,
            backgroundColor:'rgba(102,126,234,0.6)', borderColor:'#667eea',
            borderWidth:1, borderRadius:4
        }]},
        options:{ indexAxis:'y', responsive:true, plugins:{legend:{display:false}},
                  scales:{ x:{beginAtZero:true, ticks:{stepSize:1, font:{size:11}}},
                            y:{ticks:{font:{size:11}}} }}
    });

    const ctx2 = document.getElementById('zone-dur-chart').getContext('2d');
    if (charts.zoneDur) charts.zoneDur.destroy();
    charts.zoneDur = new Chart(ctx2, {
        type:'bar',
        data:{ labels, datasets:[{
            label:'평균 시간(초)', data:avgDur,
            backgroundColor:'rgba(255,152,0,0.6)', borderColor:'#ff9800',
            borderWidth:1, borderRadius:4
        }]},
        options:{ indexAxis:'y', responsive:true, plugins:{legend:{display:false}},
                  scales:{ x:{beginAtZero:true, ticks:{font:{size:11}, callback: v=>v+'s'}},
                            y:{ticks:{font:{size:11}}} }}
    });

    const tbody = document.getElementById('zone-stats-tbody');
    const activeZones = zones.filter(z => zoneMap[z].cnt > 0);
    if (!activeZones.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">관수 이력 없음</td></tr>';
        return;
    }
    const maxCnt = Math.max(...activeZones.map(z => zoneMap[z].cnt), 1);
    tbody.innerHTML = activeZones.map(z => {
        const d    = zoneMap[z];
        const avgS = d.cnt ? Math.round(d.totalSec / d.cnt) : 0;
        const sRate= d.cnt ? Math.round(d.successCnt / d.cnt * 100) : 0;
        const barW = Math.round(d.cnt / maxCnt * 100);
        return `<tr class="zone-row">
            <td class="ps-3 fw-bold">구역 ${z}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="zone-bar-wrap flex-grow-1"><div class="zone-bar-fill" style="width:${barW}%"></div></div>
                    <span class="fw-bold">${d.cnt}</span>
                </div>
            </td>
            <td>${d.totalSec.toLocaleString()}초</td>
            <td>${avgS}초</td>
            <td class="text-muted">${d.lastTime ? d.lastTime.slice(0,16) : '—'}</td>
            <td><span class="badge ${sRate===100?'bg-success':sRate>=80?'bg-warning text-dark':'bg-danger'}">${sRate}%</span></td>
        </tr>`;
    }).join('');
}

/* ─────────────────────────────────────────
   원시 로그 테이블
   BUG-18 수정: r.trigger→r.trigger_type, r.success→r.status, r.moisture_before→r.water_before
───────────────────────────────────────── */
function buildZoneFilter() {
    const sel   = document.getElementById('log-zone-filter');
    const zones = [...new Set(state.irrRows.map(r => r.zone_id).filter(Boolean))].sort((a,b)=>+a-+b);
    const cur   = sel.value;
    sel.innerHTML = '<option value="">전체 구역</option>' +
        zones.map(z => `<option value="${z}" ${z==cur?'selected':''}>구역 ${z}</option>`).join('');
}

function renderLogTable() {
    const zoneF    = document.getElementById('log-zone-filter').value;
    const triggerF = document.getElementById('log-trigger-filter').value;

    const rows = state.irrRows.filter(r => {
        if (zoneF    && String(r.zone_id) !== zoneF) return false;
        // BUG-18 FIX: trigger_type (SQLite) 또는 trigger (CSV) 모두 확인
        const tType = (r.trigger_type || r.trigger || '').toLowerCase();
        if (triggerF && tType !== triggerF) return false;
        return true;
    });

    const tbody = document.getElementById('log-tbody');
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">해당 데이터 없음</td></tr>';
        setText('log-count', '');
        return;
    }

    tbody.innerHTML = rows.map(r => {
        const dt   = r.timestamp ? new Date(r.timestamp) : null;
        const time = dt ? dt.toLocaleString('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}) : '—';

        // BUG-18 FIX: trigger_type (SQLite) 우선, trigger (CSV) 폴백
        const tType   = (r.trigger_type || r.trigger || '').toLowerCase();
        const trigger = tType === 'auto'
            ? '<span class="badge bg-success">자동</span>'
            : tType === 'manual'
            ? '<span class="badge bg-warning text-dark">수동</span>'
            : `<span class="badge bg-secondary">${tType||'—'}</span>`;

        // BUG-18 FIX: water_before (SQLite) 우선, moisture_before (CSV) 폴백
        const waterBefore = r.water_before != null ? r.water_before : r.moisture_before;
        const moist = waterBefore != null ? parseFloat(waterBefore).toFixed(1) + '%' : '—';

        // BUG-18 FIX: status (SQLite) 우선, success (CSV) 폴백
        const isFailed = r.status != null
            ? (r.status || '').toLowerCase() === 'failed'
            : String(r.success).toLowerCase() === 'false';
        const result = isFailed
            ? '<span class="text-danger"><i class="bi bi-x-circle"></i> 실패</span>'
            : '<span class="text-success"><i class="bi bi-check-circle"></i> 완료</span>';

        // zone_name 표시 (SQLite에서 제공)
        const zoneName = r.zone_name ? `${r.zone_name}` : `구역 ${r.zone_id||'—'}`;

        return `<tr>
            <td class="ps-3 text-muted">${time}</td>
            <td class="fw-bold">${zoneName}</td>
            <td>${r.duration_sec||'—'}초</td>
            <td>${trigger}</td>
            <td>${moist}</td>
            <td>${result}</td>
        </tr>`;
    }).join('');

    setText('log-count', `총 ${rows.length}건`);
}

/* ─────────────────────────────────────────
   환경 데이터 로드 & 시계열 차트 (Stage 14 신규)
───────────────────────────────────────── */
async function loadEnvData() {
    try {
        let url = '/api/analytics/environment';
        const p = [];
        if (state.fromDate) p.push('from=' + state.fromDate);
        if (state.toDate)   p.push('to='   + state.toDate);
        if (p.length) url += '?' + p.join('&');

        const res  = await fetch(url);
        const json = await res.json();
        if (!json.success) {
            console.warn('[ENV] 로드 실패:', json.error);
            return;
        }

        const airRows = (json.air  && json.air.data)     || [];
        const wxRows  = (json.weather && json.weather.data) || [];

        renderEnvAirChart(airRows);
        renderEnvWeatherChart(wxRows);
        updateEnvSummaryFromHistory(airRows, wxRows);

    } catch (e) { console.error('[ENV] 환경 데이터 로드 오류:', e); }
}

/* SHT30 온도·습도 시계열 차트 (타임스탬프별 유효 센서 평균) */
function renderEnvAirChart(airRows) {
    // 유효 데이터만 필터링 (valid = 1 or true)
    const validRows = airRows.filter(r => r.valid == 1 || r.valid === true);
    if (!validRows.length) {
        ['env-temp-chart','env-hum-chart'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.parentElement.innerHTML =
                '<div class="empty-state"><i class="bi bi-inbox"></i>SHT30 데이터 없음 (시뮬레이션 모드)</div>';
        });
        return;
    }

    // 타임스탬프별 집계
    const tsMap = {};
    validRows.forEach(r => {
        const ts = r.timestamp;
        if (!tsMap[ts]) tsMap[ts] = { temps:[], hums:[] };
        if (r.temperature != null) tsMap[ts].temps.push(Number(r.temperature));
        if (r.humidity    != null) tsMap[ts].hums.push(Number(r.humidity));
    });

    // 다운샘플 (최대 600 포인트)
    const allTs  = Object.keys(tsMap).sort();
    const MAX    = 600;
    const step   = Math.max(1, Math.floor(allTs.length / MAX));
    const labels = allTs.filter((_,i) => i % step === 0);
    const avg    = (arr) => arr.length ? arr.reduce((a,b)=>a+b,0)/arr.length : null;
    const temps  = labels.map(ts => { const v=avg(tsMap[ts].temps); return v!=null?+v.toFixed(1):null; });
    const hums   = labels.map(ts => { const v=avg(tsMap[ts].hums);  return v!=null?+v.toFixed(1):null; });
    const xLabels= labels.map(ts => ts.slice(5,16));  // MM-DD HH:MM

    // ── 온도 차트 ──
    const ctxT = document.getElementById('env-temp-chart');
    if (ctxT) {
        if (charts.envTemp) charts.envTemp.destroy();
        charts.envTemp = new Chart(ctxT.getContext('2d'), {
            type: 'line',
            data: { labels: xLabels, datasets: [{
                label: '평균 온도 (°C)', data: temps,
                borderColor: '#f44336', backgroundColor: 'rgba(244,67,54,0.08)',
                borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3,
                spanGaps: true
            }]},
            options: {
                responsive: true,
                interaction: { mode:'index', intersect:false },
                plugins: { legend:{ position:'top' },
                           tooltip:{ callbacks:{ label: c => ` ${c.dataset.label}: ${c.parsed.y?.toFixed(1)}°C` }},
                           zoom: zoomPlugin('x') },
                scales: {
                    x: { ticks:{ maxTicksLimit:10, font:{size:11}, maxRotation:30 }, grid:{color:'#f0f0f0'} },
                    y: { ticks:{ callback: v=>v+'°C', font:{size:11} }, grid:{color:'#f0f0f0'} }
                }
            }
        });
    }

    // ── 습도 차트 ──
    const ctxH = document.getElementById('env-hum-chart');
    if (ctxH) {
        if (charts.envHum) charts.envHum.destroy();
        charts.envHum = new Chart(ctxH.getContext('2d'), {
            type: 'line',
            data: { labels: xLabels, datasets: [{
                label: '평균 습도 (%)', data: hums,
                borderColor: '#2196f3', backgroundColor: 'rgba(33,150,243,0.08)',
                borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3,
                spanGaps: true
            }]},
            options: {
                responsive: true,
                interaction: { mode:'index', intersect:false },
                plugins: { legend:{ position:'top' },
                           tooltip:{ callbacks:{ label: c => ` ${c.dataset.label}: ${c.parsed.y?.toFixed(1)}%` }},
                           zoom: zoomPlugin('x') },
                scales: {
                    x: { ticks:{ maxTicksLimit:10, font:{size:11}, maxRotation:30 }, grid:{color:'#f0f0f0'} },
                    y: { min:0, max:100, ticks:{ callback: v=>v+'%', font:{size:11} }, grid:{color:'#f0f0f0'} }
                }
            }
        });
    }
}

/* WH65LP 날씨 시계열 차트 (기온, 습도, UV, 강수량) */
function renderEnvWeatherChart(wxRows) {
    if (!wxRows.length) {
        const el = document.getElementById('env-weather-chart');
        if (el) el.parentElement.innerHTML =
            '<div class="empty-state"><i class="bi bi-cloud-slash"></i>WH65LP 날씨 데이터 없음 (시뮬레이션 모드)</div>';
        return;
    }

    const MAX  = 600;
    const step = Math.max(1, Math.floor(wxRows.length / MAX));
    const rows = wxRows.filter((_,i) => i % step === 0);

    const labels = rows.map(r => (r.timestamp||'').slice(5,16));
    const temps  = rows.map(r => r.temperature  != null ? +Number(r.temperature).toFixed(1)  : null);
    const hums   = rows.map(r => r.humidity     != null ? +Number(r.humidity).toFixed(1)     : null);
    const uvIdx  = rows.map(r => r.uv_index     != null ? +Number(r.uv_index).toFixed(1)     : null);
    const rain   = rows.map(r => r.rainfall     != null ? +Number(r.rainfall).toFixed(1)     : null);

    const ctx = document.getElementById('env-weather-chart');
    if (!ctx) return;
    if (charts.envWx) charts.envWx.destroy();
    charts.envWx = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: { labels, datasets: [
            { label:'외기 온도 (°C)', data:temps,
              borderColor:'#f44336', backgroundColor:'transparent',
              borderWidth:1.5, pointRadius:0, tension:0.3, spanGaps:true, yAxisID:'yTemp' },
            { label:'외기 습도 (%)', data:hums,
              borderColor:'#2196f3', backgroundColor:'transparent',
              borderWidth:1.5, pointRadius:0, tension:0.3, spanGaps:true, yAxisID:'yHum',
              borderDash:[4,2] },
            { label:'UV 지수', data:uvIdx,
              borderColor:'#ff9800', backgroundColor:'transparent',
              borderWidth:1.5, pointRadius:0, tension:0.3, spanGaps:true, yAxisID:'yUV' },
            { label:'강수량 (mm)', data:rain,
              borderColor:'#00bcd4', backgroundColor:'rgba(0,188,212,0.15)',
              borderWidth:1, pointRadius:0, tension:0.1, spanGaps:true, fill:true, yAxisID:'yRain' }
        ]},
        options: {
            responsive: true,
            interaction: { mode:'index', intersect:false },
            plugins: { legend:{ position:'top' }, zoom: zoomPlugin('x') },
            scales: {
                x: { ticks:{ maxTicksLimit:10, font:{size:11}, maxRotation:30 }, grid:{color:'#f0f0f0'} },
                yTemp: { position:'left',  ticks:{ callback:v=>v+'°C', font:{size:10} }, grid:{color:'#f0f0f0'} },
                yHum:  { position:'right', ticks:{ callback:v=>v+'%',  font:{size:10} }, grid:{display:false} },
                yUV:   { position:'right', display:false },
                yRain: { position:'right', display:false }
            }
        }
    });
}

/* 환경 요약 카드 업데이트 (히스토리 기반) */
function updateEnvSummaryFromHistory(airRows, wxRows) {
    const validAir = airRows.filter(r => r.valid == 1 || r.valid === true);
    if (validAir.length) {
        const avgT = validAir.reduce((a,r)=>a+Number(r.temperature||0),0)/validAir.length;
        const avgH = validAir.reduce((a,r)=>a+Number(r.humidity||0),0)/validAir.length;
        setText('env-avg-temp', avgT.toFixed(1));
        setText('env-avg-hum',  avgH.toFixed(0));
    }
    if (wxRows.length) {
        const last = wxRows[wxRows.length - 1];
        setText('env-out-temp', last.temperature != null ? Number(last.temperature).toFixed(1) : '--');
        setText('env-uv',       last.uv_index    != null ? Number(last.uv_index).toFixed(1)    : '--');
        setText('aw-temp',  (last.temperature!=null?Number(last.temperature).toFixed(1):'--') + ' °C');
        setText('aw-hum',   (last.humidity!=null?Number(last.humidity).toFixed(0):'--')       + ' %');
        setText('aw-wind',  (last.wind_speed!=null?Number(last.wind_speed).toFixed(1):'--')   + ' m/s');
        setText('aw-pres',  (last.pressure!=null?Number(last.pressure).toFixed(0):'--')       + ' hPa');
        setText('aw-uv',    'UV ' + (last.uv_index!=null?Number(last.uv_index).toFixed(1):'--'));
        setText('aw-rain',  (last.rainfall!=null?Number(last.rainfall).toFixed(1):'--')       + ' mm');
    }
}

function resetEnvZoom() {
    if (charts.envTemp) charts.envTemp.resetZoom();
    if (charts.envHum)  charts.envHum.resetZoom();
    if (charts.envWx)   charts.envWx.resetZoom();
}

/* ─────────────────────────────────────────
   CSV 다운로드
───────────────────────────────────────── */
function downloadSensorCSV() {
    let url = '/api/download/sensor-data';
    const p = [];
    if (state.fromDate) p.push('from=' + encodeURIComponent(state.fromDate));
    if (state.toDate)   p.push('to='   + encodeURIComponent(state.toDate));
    if (p.length) url += '?' + p.join('&');
    triggerDownload(url);
}
function downloadIrrCSV() {
    let url = '/api/download/irrigation-history';
    const p = [];
    if (state.fromDate) p.push('from=' + encodeURIComponent(state.fromDate));
    if (state.toDate)   p.push('to='   + encodeURIComponent(state.toDate));
    if (p.length) url += '?' + p.join('&');
    triggerDownload(url);
}
function triggerDownload(url) {
    const a = document.createElement('a');
    a.href = url; a.download = '';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
}

/* ─────────────────────────────────────────
   유틸
───────────────────────────────────────── */
function updateSummary() {
    const s    = state.sensorRows.length;
    const i    = state.filteredIrr.length;
    const from = state.fromDate || '—';
    const to   = state.toDate   || '—';
    setText('data-summary', `${from} ~ ${to} | 수위 ${s.toLocaleString()}건 · 관수 ${i}건`);
}
function fmtSec(sec) {
    if (sec < 60)   return sec + '초';
    if (sec < 3600) return Math.floor(sec/60) + '분 ' + (sec%60) + '초';
    return Math.floor(sec/3600) + 'h ' + Math.floor((sec%3600)/60) + 'm';
}
function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}
function showLoading(id, show) {
    const el = document.getElementById(id);
    if (!el) return;
    if (show) el.classList.add('show'); else el.classList.remove('show');
}

/* ─────────────────────────────────────────
   초기화
───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    initDateDefaults();
    loadAll();

    // 환경 탭 클릭 시 데이터 로드
    const envBtn = document.getElementById('tab-env-btn');
    if (envBtn) {
        envBtn.addEventListener('shown.bs.tab', () => {
            loadEnvData();
        });
    }
});
