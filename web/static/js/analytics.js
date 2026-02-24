/* analytics.js – 스마트 관수 시스템 데이터 분석 페이지 v1.0 */
'use strict';

/* ─────────────────────────────────────────
   전역 상태
───────────────────────────────────────── */
const state = {
    sensorRows: [],      // 탱크 수위 CSV 로우
    irrRows:    [],      // 관수 이력 로우 (전체)
    filteredIrr:[],      // 날짜 필터 적용 후
    fromDate: '',
    toDate:   '',
};

/* Chart 인스턴스 */
const charts = {};

/* ─────────────────────────────────────────
   공통 줌/팬 옵션 팩토리
───────────────────────────────────────── */
function zoomPlugin(axis = 'x') {
    return {
        zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: axis,
            onZoomComplete({ chart }) { chart.update('none'); }
        },
        pan: {
            enabled: true,
            mode: axis,
        }
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

function fmtDate(d) {
    return d.toISOString().slice(0, 10);
}

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
}

/* ─────────────────────────────────────────
   탱크 수위 데이터 로드 & 렌더
───────────────────────────────────────── */
async function loadSensorData() {
    try {
        const from = state.fromDate;
        const to   = state.toDate;
        let url = '/api/analytics/sensor-data';
        const p = [];
        if (from) p.push('from=' + from);
        if (to)   p.push('to='   + to);
        if (p.length) url += '?' + p.join('&');

        const res = await fetch(url);
        const json = await res.json();
        if (!json.success) { console.warn('sensor data:', json.error); return; }

        state.sensorRows = json.data || [];

        renderTankChart();
        renderTankStats(json.stats);
        updateSummary();
    } catch (e) {
        console.error('센서 데이터 로드 실패:', e);
    }
}

function renderTankChart() {
    const rows = state.sensorRows;
    if (!rows.length) return;

    // 데이터 포인트가 많으면 다운샘플 (최대 800pt)
    const MAX = 800;
    const step = Math.max(1, Math.floor(rows.length / MAX));
    const sampled = rows.filter((_, i) => i % step === 0);

    const labels = sampled.map(r => r.timestamp);
    const t1     = sampled.map(r => parseFloat(r.tank1_level));
    const t2     = sampled.map(r => parseFloat(r.tank2_level));

    const ctx = document.getElementById('tank-chart').getContext('2d');
    if (charts.tank) charts.tank.destroy();

    charts.tank = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: '탱크1 수위 (%)',
                    data: t1,
                    borderColor: '#2196f3',
                    backgroundColor: 'rgba(33,150,243,0.08)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.3,
                },
                {
                    label: '탱크2 수위 (%)',
                    data: t2,
                    borderColor: '#4caf50',
                    backgroundColor: 'rgba(76,175,80,0.08)',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.3,
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}%`
                    }
                },
                zoom: zoomPlugin('x'),
            },
            scales: {
                x: {
                    ticks: {
                        maxTicksLimit: 10,
                        font: { size: 11 },
                        maxRotation: 30,
                        callback(val, i) {
                            const lbl = this.getLabelForValue(val);
                            return lbl ? lbl.slice(5, 16) : '';  // MM-DD HH:MM
                        }
                    },
                    grid: { color: '#f0f0f0' }
                },
                y: {
                    min: 0, max: 100,
                    ticks: { callback: v => v + '%', font: { size: 11 } },
                    grid: { color: '#f0f0f0' }
                }
            }
        }
    });
}

function renderTankStats(stats) {
    if (!stats) return;

    function statHTML(s) {
        if (!s || s.count === 0) return '<div class="empty-state"><i class="bi bi-inbox"></i>데이터 없음</div>';
        return `
        <table class="table table-sm mb-0">
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

function resetTankZoom()  { if (charts.tank)  charts.tank.resetZoom();  }

/* ─────────────────────────────────────────
   관수 이력 로드 & 렌더
───────────────────────────────────────── */
async function loadIrrigationHistory() {
    try {
        const from = state.fromDate;
        const to   = state.toDate;
        let url = '/api/analytics/irrigation-history';
        const p = [];
        if (from) p.push('from=' + from);
        if (to)   p.push('to='   + to);
        if (p.length) url += '?' + p.join('&');

        const res  = await fetch(url);
        const json = await res.json();
        if (!json.success) { console.warn('irr history:', json.error); return; }

        state.irrRows     = json.data || [];
        state.filteredIrr = [...state.irrRows];

        // 구역 필터 드롭다운 채우기
        buildZoneFilter();

        renderIrrBarChart();
        renderTriggerDonut();
        renderDurLineChart();
        renderZoneCharts();
        renderLogTable();
        updateSummary();
    } catch (e) {
        console.error('관수 이력 로드 실패:', e);
    }
}

/* 일별 관수 횟수 바 차트 */
function renderIrrBarChart() {
    const rows = state.filteredIrr;
    const dayMap = {};
    rows.forEach(r => {
        const day = (r.timestamp || '').slice(0, 10);
        if (!day) return;
        dayMap[day] = (dayMap[day] || 0) + 1;
    });
    const labels = Object.keys(dayMap).sort();
    const data   = labels.map(d => dayMap[d]);

    const ctx = document.getElementById('irr-bar-chart').getContext('2d');
    if (charts.irrBar) charts.irrBar.destroy();
    charts.irrBar = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '관수 횟수',
                data,
                backgroundColor: 'rgba(102,126,234,0.6)',
                borderColor: '#667eea',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                zoom: zoomPlugin('x'),
            },
            scales: {
                x: { ticks: { font: { size: 11 }, maxRotation: 30 }, grid: { color: '#f0f0f0' } },
                y: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 11 } }, grid: { color: '#f0f0f0' } }
            }
        }
    });

    // 요약 통계 카드 업데이트
    setText('stat-irr-cnt', rows.length + '회');
    const totalSec = rows.reduce((s, r) => s + (parseInt(r.duration_sec) || 0), 0);
    setText('stat-irr-time', fmtSec(totalSec));
}

/* 트리거 비율 도넛 */
function renderTriggerDonut() {
    const rows = state.filteredIrr;
    let manual = 0, auto = 0, other = 0;
    rows.forEach(r => {
        const t = (r.trigger || '').toLowerCase();
        if (t === 'manual') manual++;
        else if (t === 'auto') auto++;
        else other++;
    });

    const ctx = document.getElementById('trigger-donut').getContext('2d');
    if (charts.donut) charts.donut.destroy();
    charts.donut = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['수동', '자동', '기타'],
            datasets: [{
                data: [manual, auto, other],
                backgroundColor: ['#ffc107', '#4caf50', '#9e9e9e'],
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom', labels: { font: { size: 12 } } },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const tot = rows.length || 1;
                            return ` ${ctx.label}: ${ctx.raw}회 (${(ctx.raw/tot*100).toFixed(1)}%)`;
                        }
                    }
                }
            }
        }
    });
}

/* 관수 지속 시간 라인 */
function renderDurLineChart() {
    const rows = [...state.filteredIrr].sort((a, b) => (a.timestamp||'').localeCompare(b.timestamp||''));
    const labels = rows.map(r => (r.timestamp||'').slice(5, 16));
    const data   = rows.map(r => parseInt(r.duration_sec) || 0);

    const ctx = document.getElementById('dur-line-chart').getContext('2d');
    if (charts.durLine) charts.durLine.destroy();
    charts.durLine = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: '관수 시간(초)',
                data,
                borderColor: '#ff9800',
                backgroundColor: 'rgba(255,152,0,0.1)',
                borderWidth: 1.5,
                pointRadius: 3,
                pointHoverRadius: 5,
                fill: true,
                tension: 0.3,
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false },
                zoom: zoomPlugin('x'),
            },
            scales: {
                x: { ticks: { font: { size: 10 }, maxTicksLimit: 12, maxRotation: 30 }, grid: { color: '#f0f0f0' } },
                y: { beginAtZero: true, ticks: { font: { size: 11 }, callback: v => v + 's' }, grid: { color: '#f0f0f0' } }
            }
        }
    });
}

function resetIrrZoom() { if (charts.irrBar)  charts.irrBar.resetZoom();  }
function resetDurZoom() { if (charts.durLine) charts.durLine.resetZoom(); }

/* ─────────────────────────────────────────
   구역별 통계
───────────────────────────────────────── */
function renderZoneCharts() {
    const rows = state.filteredIrr;

    // 구역별 집계
    const zoneMap = {};
    for (let z = 1; z <= 12; z++) zoneMap[z] = { cnt: 0, totalSec: 0, lastTime: '', successCnt: 0 };

    rows.forEach(r => {
        const z = parseInt(r.zone_id);
        if (!zoneMap[z]) return;
        zoneMap[z].cnt++;
        zoneMap[z].totalSec += parseInt(r.duration_sec) || 0;
        if ((r.timestamp||'') > zoneMap[z].lastTime) zoneMap[z].lastTime = r.timestamp || '';
        if (String(r.success).toLowerCase() !== 'false') zoneMap[z].successCnt++;
    });

    const zones  = Object.keys(zoneMap).map(Number).sort((a,b)=>a-b);
    const labels = zones.map(z => '구역' + z);
    const cnts   = zones.map(z => zoneMap[z].cnt);
    const avgDur = zones.map(z => zoneMap[z].cnt ? Math.round(zoneMap[z].totalSec / zoneMap[z].cnt) : 0);

    // 횟수 가로 바
    const ctx1 = document.getElementById('zone-bar-chart').getContext('2d');
    if (charts.zoneBar) charts.zoneBar.destroy();
    charts.zoneBar = new Chart(ctx1, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '관수 횟수',
                data: cnts,
                backgroundColor: 'rgba(102,126,234,0.6)',
                borderColor: '#667eea',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, ticks: { stepSize: 1, font: { size: 11 } } },
                y: { ticks: { font: { size: 11 } } }
            }
        }
    });

    // 평균 관수 시간
    const ctx2 = document.getElementById('zone-dur-chart').getContext('2d');
    if (charts.zoneDur) charts.zoneDur.destroy();
    charts.zoneDur = new Chart(ctx2, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: '평균 시간(초)',
                data: avgDur,
                backgroundColor: 'rgba(255,152,0,0.6)',
                borderColor: '#ff9800',
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, ticks: { font: { size: 11 }, callback: v => v + 's' } },
                y: { ticks: { font: { size: 11 } } }
            }
        }
    });

    // 구역 상세 테이블
    const tbody = document.getElementById('zone-stats-tbody');
    const activeZones = zones.filter(z => zoneMap[z].cnt > 0);
    if (!activeZones.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">관수 이력 없음</td></tr>';
        return;
    }
    const maxCnt = Math.max(...activeZones.map(z => zoneMap[z].cnt), 1);
    tbody.innerHTML = activeZones.map(z => {
        const d = zoneMap[z];
        const avgS = d.cnt ? Math.round(d.totalSec / d.cnt) : 0;
        const sRate = d.cnt ? Math.round(d.successCnt / d.cnt * 100) : 0;
        const barW  = Math.round(d.cnt / maxCnt * 100);
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
───────────────────────────────────────── */
function buildZoneFilter() {
    const sel = document.getElementById('log-zone-filter');
    const zones = [...new Set(state.irrRows.map(r => r.zone_id).filter(Boolean))].sort((a,b)=>+a-+b);
    const cur = sel.value;
    sel.innerHTML = '<option value="">전체 구역</option>' +
        zones.map(z => `<option value="${z}" ${z==cur?'selected':''}>구역 ${z}</option>`).join('');
}

function renderLogTable() {
    const zoneF    = document.getElementById('log-zone-filter').value;
    const triggerF = document.getElementById('log-trigger-filter').value;

    const rows = state.irrRows.filter(r => {
        if (zoneF    && String(r.zone_id) !== zoneF) return false;
        if (triggerF && (r.trigger||'').toLowerCase() !== triggerF) return false;
        return true;
    });

    const tbody = document.getElementById('log-tbody');
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">해당 데이터 없음</td></tr>';
        setText('log-count', '');
        return;
    }

    tbody.innerHTML = rows.map(r => {
        const dt = r.timestamp ? new Date(r.timestamp) : null;
        const time = dt ? dt.toLocaleString('ko-KR', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit' }) : '—';
        const trigger = r.trigger === 'auto'
            ? '<span class="badge bg-success">자동</span>'
            : r.trigger === 'manual'
            ? '<span class="badge bg-warning text-dark">수동</span>'
            : `<span class="badge bg-secondary">${r.trigger||'—'}</span>`;
        const moist = r.moisture_before ? parseFloat(r.moisture_before).toFixed(1) + '%' : '—';
        const result = String(r.success).toLowerCase() === 'false'
            ? '<span class="text-danger"><i class="bi bi-x-circle"></i> 실패</span>'
            : '<span class="text-success"><i class="bi bi-check-circle"></i> 완료</span>';
        return `<tr>
            <td class="ps-3 text-muted">${time}</td>
            <td class="fw-bold">구역 ${r.zone_id||'—'}</td>
            <td>${r.duration_sec||'—'}초</td>
            <td>${trigger}</td>
            <td>${moist}</td>
            <td>${result}</td>
        </tr>`;
    }).join('');

    setText('log-count', `총 ${rows.length}건`);
}

/* ─────────────────────────────────────────
   CSV 다운로드 버튼
───────────────────────────────────────── */
function downloadSensorCSV() {
    const from = state.fromDate;
    const to   = state.toDate;
    let url = '/api/download/sensor-data';
    const p = [];
    if (from) p.push('from=' + encodeURIComponent(from));
    if (to)   p.push('to='   + encodeURIComponent(to));
    if (p.length) url += '?' + p.join('&');
    triggerDownload(url);
}

function downloadIrrCSV() {
    const from = state.fromDate;
    const to   = state.toDate;
    let url = '/api/download/irrigation-history';
    const p = [];
    if (from) p.push('from=' + encodeURIComponent(from));
    if (to)   p.push('to='   + encodeURIComponent(to));
    if (p.length) url += '?' + p.join('&');
    triggerDownload(url);
}

function triggerDownload(url) {
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

/* ─────────────────────────────────────────
   유틸
───────────────────────────────────────── */
function updateSummary() {
    const s = state.sensorRows.length;
    const i = state.filteredIrr.length;
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
    if (show) el.classList.add('show');
    else      el.classList.remove('show');
}

/* ─────────────────────────────────────────
   초기화
───────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    initDateDefaults();
    loadAll();
});
