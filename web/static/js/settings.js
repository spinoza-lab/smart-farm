// ========================================
// 설정 페이지 JavaScript
// ========================================

let currentValues = {
    tank1: null,
    tank2: null
};

// 중복 방지를 위한 interval ID 저장
let sensorUpdateInterval = null;

// ========================================
// 페이지 로드 시 초기화
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('설정 페이지 로드됨');
    
    // 캘리브레이션 설정 로드 (JSON 파일만 읽음)
    loadCalibration();
    
    // 호스건 상태 로드
    loadHoseGunStatus();
    
    // 🔥 페이지 로드 시에는 updateCurrentValues() 호출 안 함!
    // (캘리브레이션 탭 활성화 시에만 호출)
    
    // Bootstrap 탭 이벤트 리스너 등록
    const calibrationTab = document.querySelector('button[data-bs-target="#calibration"]');
    
    if (calibrationTab) {
        // 페이지 로드 시 캘리브레이션 탭이 활성화되어 있는지 확인
        const calibrationPane = document.getElementById('calibration');
        if (calibrationPane && calibrationPane.classList.contains('active')) {
            console.log('캘리브레이션 탭이 기본 활성 → 센서 값 로드');
            updateCurrentValues();
            
            // 5초마다 갱신 시작
            if (window.sensorUpdateInterval) {
                clearInterval(window.sensorUpdateInterval);
            }
            window.sensorUpdateInterval = setInterval(updateCurrentValues, 5000);
        }
        
        // 캘리브레이션 탭 활성화 시
        calibrationTab.addEventListener('shown.bs.tab', function() {
            console.log('캘리브레이션 탭 활성화 → 센서 갱신 시작');
            updateCurrentValues();
            
            if (window.sensorUpdateInterval) {
                clearInterval(window.sensorUpdateInterval);
            }
            window.sensorUpdateInterval = setInterval(updateCurrentValues, 5000);
        });
        
        // 다른 탭으로 전환 시 갱신 중지
        document.querySelectorAll('button[data-bs-toggle="tab"]').forEach(tab => {
            if (tab !== calibrationTab) {
                tab.addEventListener('shown.bs.tab', function() {
                    console.log('다른 탭으로 전환 → 센서 갱신 중지');
                    if (window.sensorUpdateInterval) {
                        clearInterval(window.sensorUpdateInterval);
                        window.sensorUpdateInterval = null;
                    }
                });
            }
        });
    }
});

// ========================================
// 숫자 입력 조절 (+/- 버튼)
// ========================================
function adjustValue(inputId, delta) {
    const input = document.getElementById(inputId);
    let value = Number(input.value) || 0;
    value = Math.round((value + delta) * 10) / 10;
    value = Math.max(0, Math.min(5, value));
    input.value = value.toFixed(3);
}

// ========================================
// 현재 센서 값 갱신
// ========================================
function updateCurrentValues() {
    fetch('/api/calibration/current')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentValues.tank1 = data.tank1_value;
                currentValues.tank2 = data.tank2_value;
                
                const unit = ' V';
                
                document.getElementById('tank1CurrentValue').textContent = 
                    currentValues.tank1.toFixed(3) + unit;
                document.getElementById('tank2CurrentValue').textContent = 
                    currentValues.tank2.toFixed(3) + unit;
            }
        })
        .catch(error => {
            console.error('센서 값 갱신 실패:', error);
            document.getElementById('tank1CurrentValue').textContent = '-- V';
            document.getElementById('tank2CurrentValue').textContent = '-- V';
        });
}

// ========================================
// 캘리브레이션 설정 로드
// ========================================
function loadCalibration() {
    fetch('/api/calibration')
        .then(response => response.json())
        .then(data => {
            if (data) {
                // sensor_type은 'voltage'로 고정됨
                
                if (data.tank1_water) {
                    document.getElementById('tank1Empty').value = 
                        Number(data.tank1_water.empty_value || 0.5).toFixed(3);
                    document.getElementById('tank1Full').value = 
                        Number(data.tank1_water.full_value || 4.5).toFixed(3);
                }
                
                if (data.tank2_nutrient) {
                    document.getElementById('tank2Empty').value = 
                        Number(data.tank2_nutrient.empty_value || 0.5).toFixed(3);
                    document.getElementById('tank2Full').value = 
                        Number(data.tank2_nutrient.full_value || 4.5).toFixed(3);
                }
                
                console.log('캘리브레이션 설정 로드 완료');
            }
        })
        .catch(error => {
            console.error('캘리브레이션 로드 실패:', error);
            showAlert('캘리브레이션 설정을 불러오는데 실패했습니다.', 'danger');
        });
}

function setCurrentAsEmpty(tank) {
    const value = tank === 1 ? currentValues.tank1 : currentValues.tank2;
    const inputId = tank === 1 ? 'tank1Empty' : 'tank2Empty';
    
    if (value === null) {
        showAlert('현재 센서 값을 가져올 수 없습니다.', 'warning');
        return;
    }
    
    document.getElementById(inputId).value = value.toFixed(3);
    showAlert(`Tank ${tank} 공탱크 값을 ${value.toFixed(3)}로 설정했습니다.`, 'success');
}

function setCurrentAsFull(tank) {
    const value = tank === 1 ? currentValues.tank1 : currentValues.tank2;
    const inputId = tank === 1 ? 'tank1Full' : 'tank2Full';
    
    if (value === null) {
        showAlert('현재 센서 값을 가져올 수 없습니다.', 'warning');
        return;
    }
    
    document.getElementById(inputId).value = value.toFixed(3);
    showAlert(`Tank ${tank} 만수 값을 ${value.toFixed(3)}로 설정했습니다.`, 'success');
}


// 전압 입력값 검증 (0~5V)
function validateVoltage(value, fieldName) {
    const num = parseFloat(value);
    if (isNaN(num)) {
        alert(`${fieldName}는 숫자여야 합니다`);
        return false;
    }
    if (num < 0 || num > 5.0) {
        alert(`${fieldName}는 0V ~ 5.0V 범위여야 합니다 (현재: ${num}V)`);
        return false;
    }
    return true;
}

function saveCalibration() {
    // ✅ 입력값 소수점 3자리로 반올림
    const roundTo3Decimals = (value) => {
        const num = parseFloat(value);
        if (isNaN(num)) return 0;
        return Math.round(num * 1000) / 1000;
    };
    
    const tank1Empty = roundTo3Decimals(document.getElementById('tank1Empty').value);
    if (!validateVoltage(tank1Empty, "Tank 1 Empty")) return;
    const tank1Full = roundTo3Decimals(document.getElementById('tank1Full').value);
    if (!validateVoltage(tank1Full, "Tank 1 Full")) return;
    const tank2Empty = roundTo3Decimals(document.getElementById('tank2Empty').value);
    if (!validateVoltage(tank2Empty, "Tank 2 Empty")) return;
    const tank2Full = roundTo3Decimals(document.getElementById('tank2Full').value);
    if (!validateVoltage(tank2Full, "Tank 2 Full")) return;
    
    if (tank1Empty >= tank1Full) {
        showAlert('물탱크: 공탱크 값이 만수 값보다 작아야 합니다.', 'danger');
        return;
    }
    
    if (tank2Empty >= tank2Full) {
        showAlert('양액탱크: 공탱크 값이 만수 값보다 작아야 합니다.', 'danger');
        return;
    }
    
    
    
    const calibrationData = {
        sensor_type: 'voltage',
        tank1_water: {empty_value: tank1Empty, full_value: tank1Full},
        tank2_nutrient: {empty_value: tank2Empty, full_value: tank2Full}
    };
    
    fetch('/api/calibration', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(calibrationData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('캘리브레이션 설정이 저장되었습니다!', 'success');
            loadCalibration();
        } else {
            showAlert('저장 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(error => {
        console.error('저장 오류:', error);
        showAlert('저장 중 오류가 발생했습니다.', 'danger');
    });
}

function loadHoseGunStatus() {
    fetch('/api/hose-gun/status')
        .then(response => response.json())
        .then(data => {updateHoseGunUI(data.active);})
        .catch(error => {console.error('호스건 상태 로드 실패:', error);});
}

function activateHoseGun() {
    if (confirm('호스건을 시작하시겠습니까?\n\n물탱크와 양액탱크가 자동으로 차단됩니다.')) {
        fetch('/api/hose-gun/activate', {method: 'POST'})
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('호스건이 시작되었습니다.', 'success');
                updateHoseGunUI(true);
            } else {
                showAlert('호스건 시작 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
            }
        })
        .catch(error => {
            console.error('호스건 시작 오류:', error);
            showAlert('호스건 시작 중 오류가 발생했습니다.', 'danger');
        });
    }
}

function deactivateHoseGun() {
    fetch('/api/hose-gun/deactivate', {method: 'POST'})
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('호스건이 종료되었습니다.', 'info');
            updateHoseGunUI(false);
        } else {
            showAlert('호스건 종료 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(error => {
        console.error('호스건 종료 오류:', error);
        showAlert('호스건 종료 중 오류가 발생했습니다.', 'danger');
    });
}

function updateHoseGunUI(isActive) {
    const badge = document.getElementById('hoseGunStatus');
    
    if (isActive) {
        badge.textContent = 'ON';
        badge.className = 'badge bg-success';
    } else {
        badge.textContent = 'OFF';
        badge.className = 'badge bg-secondary';
    }
}

function showAlert(message, type = 'info') {
    const existingAlert = document.querySelector('.floating-alert');
    if (existingAlert) existingAlert.remove();
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} floating-alert`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        font-size: 18px;
        padding: 20px;
    `;
    alertDiv.innerHTML = `
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        ${message}
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentElement) alertDiv.remove();
    }, 3000);
}


// ========================================
// 자동 관수 설정 탭 JavaScript (settings.js에 추가)
// ========================================

// ── 자동 관수 탭 활성화 시 초기화 ──────────────────────────
const autoControlTab = document.querySelector('button[data-bs-target="#auto-control"]');
if (autoControlTab) {
    autoControlTab.addEventListener('shown.bs.tab', function () {
        loadAutoControlSettings();
    });
}

// ── 초기 로드 (페이지 열릴 때 미리 로드) ──────────────────
document.addEventListener('DOMContentLoaded', function () {
    // 기존 DOMContentLoaded 로직에 추가
    buildZoneThresholdGrid();
    loadAutoControlSettings();
});

// ── 전체 설정 로드 ─────────────────────────────────────────
function loadAutoControlSettings() {
    loadIrrigationConfig();
    loadSchedules();
}

// ── ① 시스템 설정 로드 ────────────────────────────────────
function loadIrrigationConfig() {
    fetch('/api/irrigation/config')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            const cfg = data.config;
            document.getElementById('checkInterval').value      = Math.round((cfg.check_interval ?? 600) / 60);
            document.getElementById('irrigationDuration').value = Math.round((cfg.irrigation_duration ?? 300) / 60);
            document.getElementById('minTankLevel').value       = cfg.min_tank_level       ?? 20;
            document.getElementById('zoneInterval').value       = cfg.zone_interval        ?? 10;
            updateConfigLabels();

            // 현재 모드 반영
            if (cfg.mode) updateModeButtons(cfg.mode);
        })
        .catch(e => console.error('설정 로드 실패:', e));

    // 임계값 로드
    fetch('/api/irrigation/thresholds')
        .then(r => r.json())
        .then(data => {
            if (!data.success) return;
            data.thresholds.forEach(item => {
                const el = document.getElementById(`threshold_${item.zone_id}`);
                if (el) {
                    el.value = item.threshold;
                    const lbl = document.getElementById(`thresholdLbl_${item.zone_id}`);
                    if (lbl) lbl.textContent = item.threshold + '%';
                }
            });
        })
        .catch(e => console.error('임계값 로드 실패:', e));

    // 현재 모드 로드
    fetch('/api/irrigation/status')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.data) updateModeButtons(data.data.mode);
        })
        .catch(() => {});
}

// ── ② 설정 저장 ───────────────────────────────────────────
function saveIrrigationConfig() {
    const cfg = {
        check_interval:      parseInt(document.getElementById('checkInterval').value) * 60,
        irrigation_duration: parseInt(document.getElementById('irrigationDuration').value) * 60,
        min_tank_level:      parseFloat(document.getElementById('minTankLevel').value),
        zone_interval:       parseInt(document.getElementById('zoneInterval').value)
    };

    // 유효성 검증
    if (cfg.check_interval < 60)      { showAlert('체크 주기는 60초 이상이어야 합니다.', 'warning'); return; }
    if (cfg.irrigation_duration < 60) { showAlert('관수 시간은 1분 이상이어야 합니다.', 'warning'); return; }
    if (cfg.min_tank_level < 5)       { showAlert('최소 탱크 수위는 5% 이상이어야 합니다.', 'warning'); return; }

    fetch('/api/irrigation/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showAlert('✅ 시스템 설정이 저장되었습니다.', 'success');
            updateConfigLabels();
        } else {
            showAlert('저장 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(e => { showAlert('저장 중 오류: ' + e.message, 'danger'); });
}

// ── ③ 모드 변경 ───────────────────────────────────────────
function setIrrigationMode(mode) {
    fetch('/api/irrigation/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            updateModeButtons(mode);
            showAlert(`모드가 [${modeLabel(mode)}]으로 변경되었습니다.`, 'success');
        } else {
            showAlert('모드 변경 실패: ' + (data.error || data.message), 'danger');
        }
    })
    .catch(e => showAlert('모드 변경 오류: ' + e.message, 'danger'));
}

function updateModeButtons(mode) {
    if (mode === 'schedule') mode = 'auto'; // patch_v4d: schedule→auto
    const map = { manual: 'modeManualBtn', auto: 'modeAutoBtn' };
    Object.entries(map).forEach(([m, id]) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.className = btn.className.replace(/btn-(outline-)?(secondary|primary|success|warning)/g, '');
        if (m === mode) {
            const colorMap = { manual: 'btn-secondary', auto: 'btn-primary', schedule: 'btn-success' };
            btn.classList.add(colorMap[m]);
        } else {
            const outlineMap = { manual: 'btn-outline-secondary', auto: 'btn-outline-primary', schedule: 'btn-outline-success' };
            btn.classList.add(outlineMap[m]);
        }
    });
    const lbl = document.getElementById('currentModeLabel');
    if (lbl) lbl.textContent = modeLabel(mode);
}

function modeLabel(mode) {
    if (mode === 'schedule') mode = 'auto';
    return { manual: '수동 (Manual)', auto: '자동 (Auto)' }[mode] || mode;
}

// ── ④ 설정값 +/- 조절 + 레이블 갱신 ──────────────────────
function adjustConfigValue(fieldId, delta) {
    const el = document.getElementById(fieldId);
    if (!el) return;
    let v = parseInt(el.value) + delta;
    v = Math.max(parseInt(el.min), Math.min(parseInt(el.max), v));
    el.value = v;
    updateConfigLabels();
}

function updateConfigLabels() {
    const ci  = parseInt(document.getElementById('checkInterval')?.value || 10);
    const dur = parseInt(document.getElementById('irrigationDuration')?.value || 5);

    const ciLbl = document.getElementById('checkIntervalMin');
    if (ciLbl) ciLbl.textContent = ci >= 60 ? Math.floor(ci / 60) + '분' : ci + '초';

    const dLbl = document.getElementById('irrigationDurationMin');
    if (dLbl) {
        const m = Math.floor(dur / 60), s = dur % 60;
        dLbl.textContent = m > 0 ? `${m}분 ${s > 0 ? s + '초' : ''}`.trim() : `${s}초`;
    }
}

// ── ⑤ 12구역 임계값 그리드 빌드 ──────────────────────────
function buildZoneThresholdGrid() {
    const grid = document.getElementById('zoneThresholdGrid');
    if (!grid) return;
    grid.innerHTML = '';
    for (let i = 1; i <= 12; i++) {
        grid.innerHTML += `
        <div class="col-6 col-md-4 col-lg-3">
            <div class="card card-body p-2 text-center">
                <small class="fw-bold text-primary">구역 ${i}</small>
                <div class="fw-bold" id="thresholdLbl_${i}">40%</div>
                <input type="range" class="form-range" id="threshold_${i}"
                       min="10" max="80" value="40"
                       oninput="document.getElementById('thresholdLbl_${i}').textContent=this.value+'%'">
            </div>
        </div>`;
    }
}

// ── ⑥ 일괄 설정 ───────────────────────────────────────────
function updateBulkThreshold(val) {
    document.getElementById('bulkThresholdVal').textContent = val;
}

function applyBulkThreshold() {
    const val = document.getElementById('bulkThreshold').value;
    for (let i = 1; i <= 12; i++) {
        const el = document.getElementById(`threshold_${i}`);
        if (el) {
            el.value = val;
            const lbl = document.getElementById(`thresholdLbl_${i}`);
            if (lbl) lbl.textContent = val + '%';
        }
    }
    showAlert(`전체 12구역 임계값을 ${val}%로 설정했습니다. [전체 저장] 버튼을 눌러 적용하세요.`, 'info');
}

// ── ⑦ 임계값 전체 저장 ────────────────────────────────────
function saveAllThresholds() {
    const thresholds = [];
    for (let i = 1; i <= 12; i++) {
        const el = document.getElementById(`threshold_${i}`);
        if (el) thresholds.push({ zone_id: i, threshold: parseFloat(el.value) });
    }

    fetch('/api/irrigation/thresholds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ thresholds })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showAlert('✅ 12구역 임계값이 저장되었습니다.', 'success');
        } else {
            showAlert('저장 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(e => showAlert('저장 오류: ' + e.message, 'danger'));
}

// ── ⑧ 스케줄 목록 로드 ────────────────────────────────────
const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일'];

function loadSchedules() {
    fetch('/api/schedules')
        .then(r => r.json())
        .then(data => {
            const tbody = document.getElementById('scheduleTableBody');
            if (!tbody) return;

            const schedules = data.schedules || [];
            if (schedules.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">
                    <i class="bi bi-calendar-x"></i> 등록된 스케줄이 없습니다</td></tr>`;
                return;
            }

            // 스케줄 데이터 전역 캐시 (편집용)
            window._scheduleCache = {};
            schedules.forEach(s => { window._scheduleCache[s.id] = s; });

            tbody.innerHTML = schedules.map(s => {
                const dur    = s.duration || 0;
                const m = Math.floor(dur / 60), sec = dur % 60;
                const durStr = m > 0 ? `${m}분 ${sec > 0 ? sec + '초' : ''}`.trim() : `${sec}초`;

                // 타입 뱃지
                const isRoutine = s.type === 'routine' || (s.interval_days != null && s.interval_days > 0 && s.type !== 'schedule');
                const typeBadge = isRoutine
                    ? `<span class="badge bg-info text-dark">루틴</span>`
                    : `<span class="badge bg-primary">스케줄</span>`;

                // 조건 표시
                let condition;
                if (isRoutine) {
                    const startDate   = s.start_date || '미설정';
                    const intervalDay = s.interval_days || 1;
                    const timeStr     = s.start_time   || '';
                    condition = `<i class="bi bi-calendar-event"></i> ${startDate}<br><small class="text-muted">매 ${intervalDay}일 · ${timeStr}</small>`;
                } else {
                    const days = s.days && s.days.length > 0
                        ? s.days.map(d => DAY_NAMES[d]).join('/')
                        : '매일';
                    condition = `<i class="bi bi-clock"></i> ${s.start_time}<br><small class="text-muted">${days}</small>`;
                }

                // 수분체크
                const moistureChk = s.check_moisture
                    ? `<i class="bi bi-check-circle-fill text-success"></i>`
                    : `<span class="text-muted small">—</span>`;

                // 상태 뱃지
                const badge = s.enabled
                    ? `<span class="badge bg-success">활성</span>`
                    : `<span class="badge bg-secondary">중지</span>`;

                return `
                <tr id="schedRow_${s.id}">
                    <td>${typeBadge}</td>
                    <td><strong>구역 ${s.zone_id === 0 ? '전체' : s.zone_id}</strong></td>
                    <td><small>${condition}</small></td>
                    <td>${durStr}</td>
                    <td class="text-center">${moistureChk}</td>
                    <td>${badge}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-secondary me-1"
                                onclick="editSchedule(${s.id})" title="편집">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm ${s.enabled ? 'btn-outline-warning' : 'btn-outline-success'} me-1"
                                onclick="toggleSchedule(${s.id}, ${s.enabled})" title="${s.enabled ? '중지' : '시작'}">
                            ${s.enabled ? '<i class="bi bi-pause"></i>' : '<i class="bi bi-play"></i>'}
                        </button>
                        <button class="btn btn-sm btn-outline-danger"
                                onclick="deleteSchedule(${s.id})" title="삭제">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>`;
            }).join('');
        })
        .catch(e => console.error('스케줄 로드 실패:', e));
    loadNextSchedule(); // Fix E – patch_v4f
}

// ── ⑨ 스케줄 모달 열기 ────────────────────────────────────
function openScheduleModal() {
    document.getElementById('schedZone').value   = '';
    document.getElementById('schedTime').value   = '06:00';
    document.getElementById('schedDurMin').value = '5';
    document.getElementById('schedDurSec').value = '0';
    document.getElementById('dayAll').checked    = false;
    document.querySelectorAll('.day-check').forEach(cb => cb.checked = false);
    updateSchedDurLabel();
    new bootstrap.Modal(document.getElementById('scheduleModal')).show();
}

function toggleAllDays(checked) {
    document.querySelectorAll('.day-check').forEach(cb => cb.checked = checked);
}

function updateSchedDurLabel() {
    const m   = parseInt(document.getElementById('schedDurMin')?.value || 0);
    const s   = parseInt(document.getElementById('schedDurSec')?.value || 0);
    const lbl = document.getElementById('schedDurLabel');
    if (lbl) lbl.textContent = `${m}분 ${s}초`;
}

// ── ⑩ 스케줄 저장 ─────────────────────────────────────────
function saveSchedule() {
    const zone_id = parseInt(document.getElementById('schedZone').value);
    if (zone_id === null || isNaN(zone_id) || document.getElementById('schedZone').value === '') { showAlert('구역을 선택하세요.', 'warning'); return; }

    const time    = document.getElementById('schedTime').value;
    if (!time)    { showAlert('시작 시간을 입력하세요.', 'warning'); return; }

    const durMin  = parseInt(document.getElementById('schedDurMin').value || 0);
    const durSec  = parseInt(document.getElementById('schedDurSec').value || 0);
    const duration = durMin * 60 + durSec;
    if (duration < 10) { showAlert('관수 시간은 10초 이상이어야 합니다.', 'warning'); return; }

    // 선택된 요일 (0=월 ~ 6=일)
    const days = [];
    document.querySelectorAll('.day-check:checked').forEach(cb => days.push(parseInt(cb.value)));

    fetch('/api/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone_id, start_time: time, duration, days })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('scheduleModal')).hide();
            showAlert(`✅ 스케줄이 추가되었습니다. (구역 ${zone_id}, ${time})`, 'success');
            loadSchedules();
        } else {
            showAlert('저장 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(e => showAlert('저장 오류: ' + e.message, 'danger'));
}

// ── ⑪ 스케줄 활성화/비활성화 ─────────────────────────────
function toggleSchedule(id, currentEnabled) {
    fetch(`/api/schedules/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !currentEnabled })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showAlert(currentEnabled ? '스케줄이 중지되었습니다.' : '스케줄이 활성화되었습니다.', 'info');
            loadSchedules();
        } else {
            showAlert('변경 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(e => showAlert('오류: ' + e.message, 'danger'));
}

// ── ⑫ 스케줄 삭제 ─────────────────────────────────────────
function deleteSchedule(id) {
    if (!confirm(`스케줄 #${id}를 삭제하시겠습니까?`)) return;

    fetch(`/api/schedules/${id}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showAlert(`스케줄 #${id}가 삭제되었습니다.`, 'info');
                loadSchedules();
            } else {
                showAlert('삭제 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
            }
        })
        .catch(e => showAlert('삭제 오류: ' + e.message, 'danger'));
}

// ─────────────────────────────────────────────────
// 다음 실행 스케줄 조회
// ─────────────────────────────────────────────────
// Fix E – patch_v4f: 스케줄 탭 진입 / loadSchedules 완료 후 자동 호출
async function loadNextSchedule() {
    try {
        const res = await fetch('/api/schedules/next');
        const json = await res.json();
        const el = document.getElementById('nextScheduleInfo');
        if (!el) return;
        if (json.success && json.next_schedule) {
            const s = json.next_schedule;
            const days = s.days && s.days.length
                ? s.days.map(d=>['월','화','수','목','금','토','일'][d]).join('/')
                : '매일';
            el.textContent =
                `구역 ${s.zone_id} · ${s.start_time} · ${Math.round(s.duration/60)}분 (${days}) — 약 ${s.minutes_until}분 후`;
        } else {
            el.textContent = '예정된 스케줄 없음';
        }
    } catch(e) {
        console.warn('다음 스케줄 조회 실패:', e);
    }
}



// ── 스케줄 모달 함수 (patch_v3b) ────────────────────────────────────────────
function openScheduleModal() {
    // 폼 초기화
    document.getElementById('newScheduleType').value = 'schedule';
    document.getElementById('newScheduleZone').value = '1';
    document.getElementById('newScheduleDuration').value = '300';
    document.getElementById('newScheduleTime').value = '06:00';
    document.getElementById('newRoutineTime').value = '06:00';
    document.getElementById('newRoutineInterval').value = '1';
    document.getElementById('newRoutineCheckMoisture').checked = false;
    // 오늘 날짜 기본값
    const today = new Date().toISOString().slice(0,10);
    document.getElementById('newRoutineDate').value = today;
    // 요일 버튼 초기화
    document.querySelectorAll('.day-sel-btn').forEach(b => b.classList.remove('active','btn-primary'));
    document.querySelectorAll('.day-sel-btn').forEach(b => {
        b.classList.remove('btn-primary'); b.classList.add('btn-outline-secondary');
    });
    // 타입 UI 초기화
    selectScheduleType('schedule');
    new bootstrap.Modal(document.getElementById('addScheduleModal')).show();
}

function selectScheduleType(type) {
    document.getElementById('newScheduleType').value = type;
    const isSched = (type === 'schedule');
    document.getElementById('scheduleOnlyFields').style.display = isSched ? '' : 'none';
    document.getElementById('routineOnlyFields').style.display  = isSched ? 'none' : '';
    document.getElementById('btnTypeSchedule').className =
        'btn ' + (isSched ? 'btn-primary' : 'btn-outline-primary');
    document.getElementById('btnTypeRoutine').className =
        'btn ' + (!isSched ? 'btn-success' : 'btn-outline-success');
}


// ── 스케줄 편집 (patch_v4) ────────────────────────────────────
function editSchedule(id) {
    const row = document.querySelector(`tr[data-id="${id}"]`);
    if (!row) return;
    let sched;
    try { sched = JSON.parse(row.getAttribute('data-sched')); } catch(e) { return; }
    document.getElementById('editScheduleId').value         = id;
    document.getElementById('editScheduleZone').value       = sched.zone_id;
    const rawType = sched.type || 'daily';
    const type    = (rawType === 'schedule') ? 'interval' : rawType;
    document.getElementById('editScheduleType').value       = type;
    document.getElementById('editScheduleTime').value       = sched.start_time || '08:00';
    document.getElementById('editScheduleDuration').value   = Math.round((sched.duration || 300) / 60);
    document.getElementById('editScheduleInterval').value   = sched.interval || 3;
    document.getElementById('editScheduleStartDate').value  = sched.start_date || '';
    onEditTypeChange();
    new bootstrap.Modal(document.getElementById('editScheduleModal')).show();
}

function onEditTypeChange() {
    const type = document.getElementById('editScheduleType').value;
    document.getElementById('editStartDateContainer').style.display  = (type === 'interval' || type === 'specific') ? '' : 'none';
    document.getElementById('editIntervalContainer').style.display   = (type === 'interval') ? '' : 'none';
}

function saveEditSchedule() {
    const id     = document.getElementById('editScheduleId').value;
    const durMin = parseInt(document.getElementById('editScheduleDuration').value);
    if (!durMin || durMin < 1) { showSettingsAlert('관수 시간을 1분 이상 입력하세요.', 'danger'); return; }
    const type    = document.getElementById('editScheduleType').value;
    const payload = {
        zone_id:    parseInt(document.getElementById('editScheduleZone').value),
        type:       type,
        start_time: document.getElementById('editScheduleTime').value,
        duration:   durMin * 60
    };
    if (type === 'interval') {
        payload.interval   = parseInt(document.getElementById('editScheduleInterval').value);
        payload.start_date = document.getElementById('editScheduleStartDate').value;
    } else if (type === 'specific') {
        payload.start_date = document.getElementById('editScheduleStartDate').value;
    }
    fetch(`/api/schedules/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    }).then(r => r.json()).then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('editScheduleModal')).hide();
            if (typeof loadSchedules === 'function') loadSchedules();
            showSettingsAlert('스케줄이 수정되었습니다.', 'success');
        } else {
            showSettingsAlert(data.error || '수정 실패', 'danger');
        }
    }).catch(() => showSettingsAlert('서버 오류', 'danger'));
}
// ── /스케줄 편집 ──────────────────────────────────────────────

function saveNewSchedule() {
    const type     = document.getElementById('newScheduleType').value;
    const zone_id  = parseInt(document.getElementById('newScheduleZone').value);
    const duration = parseInt(document.getElementById('newScheduleDuration').value) * 60;

    if (!duration || duration < 60) {
        showSettingsAlert('관수 시간을 1분 이상 입력하세요.', 'danger'); return;
    }

    let payload = { type, zone_id, duration };

    if (type === 'schedule') {
        const start_time = document.getElementById('newScheduleTime').value;
        const days = [...document.querySelectorAll('.day-sel-btn.active')]
                         .map(b => parseInt(b.dataset.day));
        if (!start_time) { showSettingsAlert('시작 시간을 입력하세요.', 'danger'); return; }
        if (!days.length){ showSettingsAlert('요일을 1개 이상 선택하세요.', 'danger'); return; }
        payload = { ...payload, start_time, days };
    } else {
        const start_date    = document.getElementById('newRoutineDate').value;
        const start_time    = document.getElementById('newRoutineTime').value;
        const interval_days = parseInt(document.getElementById('newRoutineInterval').value);
        const check_moisture= document.getElementById('newRoutineCheckMoisture').checked;
        if (!start_date || !start_time) {
            showSettingsAlert('시작 날짜와 시간을 입력하세요.', 'danger'); return;
        }
        if (!interval_days || interval_days < 1) {
            showSettingsAlert('반복 간격을 1일 이상으로 설정하세요.', 'danger'); return;
        }
        payload = { ...payload, start_date, start_time, interval_days, check_moisture };
    }

    fetch('/api/schedules', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            bootstrap.Modal.getInstance(
                document.getElementById('addScheduleModal'))?.hide();
            loadSchedules();
            showSettingsAlert('스케줄이 저장되었습니다.', 'success');
        } else {
            showSettingsAlert(data.message || '저장 실패', 'danger');
        }
    })
    .catch(e => showSettingsAlert('오류: ' + e.message, 'danger'));
}

// 요일 버튼 토글 (이벤트 위임)
document.addEventListener('click', e => {
    const btn = e.target.closest('.day-sel-btn');
    if (!btn) return;
    const isActive = btn.classList.contains('active');
    btn.classList.toggle('active', !isActive);
    btn.classList.toggle('btn-primary', !isActive);
    btn.classList.toggle('btn-outline-secondary', isActive);
});

function showSettingsAlert(msg, type='info') {
    // 기존 showAlert 있으면 사용, 없으면 alert
    if (typeof showAlert === 'function') { showAlert(msg, type); return; }
    const container = document.querySelector('.container-fluid') || document.body;
    const div = document.createElement('div');
    div.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-2`;
    div.style.zIndex = '9999';
    div.innerHTML = msg + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    container.prepend(div);
    setTimeout(() => div.remove(), 4000);
}
// ── 스케줄 편집 함수 ────────────────────────────────────────────────────────
function _ensureEditModal() {
    if (document.getElementById('editScheduleModal')) return;
    // 모달 DOM이 없으면 동적으로 주입
    const MODAL_HTML = [
        '<div class="modal fade" id="editScheduleModal" tabindex="-1" aria-hidden="true">',
        '<div class="modal-dialog modal-dialog-centered">',
        '<div class="modal-content">',
        '<div class="modal-header"><h5 class="modal-title"><i class="bi bi-pencil-square"></i> 스케줄 편집</h5>',
        '<button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>',
        '<div class="modal-body">',
        '<input type="hidden" id="editSchedId"><input type="hidden" id="editSchedType">',
        '<div class="row mb-3">',
        '<div class="col-6"><label class="form-label fw-bold">관수 구역</label>',
        '<select class="form-select form-select-sm" id="editSchedZone">',
        '<option value="0">전체 구역</option>',
        ...Array.from({length:12},(_,i)=>`<option value="${i+1}">구역 ${i+1}</option>`),
        '</select></div>',
        '<div class="col-6"><label class="form-label fw-bold">관수 시간: <span id="editSchedDurLabel">5분 0초</span></label>',
        '<div class="row g-1">',
        '<div class="col-6"><div class="input-group input-group-sm">',
        '<input type="number" class="form-control" id="editSchedDurMin" value="5" min="0" max="60" oninput="updateEditDurLabel()">',
        '<span class="input-group-text">분</span></div></div>',
        '<div class="col-6"><div class="input-group input-group-sm">',
        '<input type="number" class="form-control" id="editSchedDurSec" value="0" min="0" max="59" oninput="updateEditDurLabel()">',
        '<span class="input-group-text">초</span></div></div>',
        '</div></div></div>',
        '<div id="editSchedWeekFields">',
        '<div class="mb-3"><label class="form-label fw-bold">시작 시간</label>',
        '<input type="time" class="form-control form-control-sm" id="editSchedWeekTime" value="06:00"></div>',
        '<div class="mb-3"><label class="form-label fw-bold">반복 요일</label>',
        '<div class="d-flex gap-1 flex-wrap">',
        ...[['월',0],['화',1],['수',2],['목',3],['금',4],['토',5],['일',6]].map(([n,d])=>`<button type="button" class="btn btn-sm btn-outline-secondary edit-day-btn" data-day="${d}">${n}</button>`),
        '</div></div></div>',
        '<div id="editSchedRoutineFields" style="display:none;">',
        '<div class="row mb-3">',
        '<div class="col-6"><label class="form-label fw-bold">시작 날짜</label>',
        '<input type="date" class="form-control form-control-sm" id="editSchedStartDate"></div>',
        '<div class="col-6"><label class="form-label fw-bold">시작 시간</label>',
        '<input type="time" class="form-control form-control-sm" id="editSchedRoutineTime" value="06:00"></div>',
        '</div><div class="mb-3"><label class="form-label fw-bold">반복 간격</label>',
        '<div class="input-group input-group-sm">',
        '<input type="number" class="form-control" id="editSchedInterval" value="1" min="1" max="365">',
        '<span class="input-group-text">일마다</span></div></div>',
        '<div class="form-check mb-2"><input class="form-check-input" type="checkbox" id="editSchedMoisture">',
        '<label class="form-check-label" for="editSchedMoisture">수분 부족 시에만 실행</label></div>',
        '</div></div>',
        '<div class="modal-footer">',
        '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>',
        '<button type="button" class="btn btn-primary" onclick="saveEditSchedule()"><i class="bi bi-check-circle"></i> 저장</button>',
        '</div></div></div></div>'
    ].join('');
    const wrap = document.createElement('div');
    wrap.innerHTML = MODAL_HTML;
    document.body.appendChild(wrap.firstChild);
    document.querySelectorAll('.edit-day-btn').forEach(b => b.addEventListener('click', () => {
        b.classList.toggle('btn-primary'); b.classList.toggle('btn-outline-secondary'); b.classList.toggle('active');
    }));
}

function editSchedule(id) {
    _ensureEditModal();
    const s = window._scheduleCache && window._scheduleCache[id];
    if (!s) { showAlert('스케줄 데이터를 찾을 수 없습니다.', 'warning'); return; }

    const isRoutine = s.type === 'routine' || (s.interval_days != null && s.interval_days > 0 && s.type !== 'schedule');

    // null-safe 헬퍼
    const $v = (id, v) => { const e=document.getElementById(id); if(e) e.value=v; };
    const $c = (id, v) => { const e=document.getElementById(id); if(e) e.checked=v; };
    const $t = (id, v) => { const e=document.getElementById(id); if(e) e.textContent=v; };
    const $d = (id, v) => { const e=document.getElementById(id); if(e) e.style.display=v; };

    $v('editSchedId',   s.id);
    $v('editSchedZone', s.zone_id || 1);
    const durMin = Math.floor((s.duration || 300) / 60);
    const durSec = (s.duration || 300) % 60;
    $v('editSchedDurMin', durMin);
    $v('editSchedDurSec', durSec);
    $t('editSchedDurLabel', `${durMin}분 ${durSec}초`);

    $v('editSchedType', isRoutine ? 'routine' : 'schedule');
    if (isRoutine) {
        $d('editSchedRoutineFields', '');
        $d('editSchedWeekFields',    'none');
        $v('editSchedStartDate',    s.start_date || '');
        $v('editSchedRoutineTime',  s.start_time || '06:00');
        $v('editSchedInterval',     s.interval_days || 1);
        $c('editSchedMoisture',     !!s.check_moisture);
    } else {
        $d('editSchedRoutineFields', 'none');
        $d('editSchedWeekFields',    '');
        $v('editSchedWeekTime', s.start_time || '06:00');
        document.querySelectorAll('.edit-day-btn').forEach(btn => {
            const day = parseInt(btn.dataset.day);
            const active = s.days && s.days.includes(day);
            btn.classList.toggle('btn-primary', active);
            btn.classList.toggle('btn-outline-secondary', !active);
            btn.classList.toggle('active', active);
        });
    }

    new bootstrap.Modal(document.getElementById('editScheduleModal')).show();
}

function updateEditDurLabel() {
    const m = parseInt(document.getElementById('editSchedDurMin')?.value || 0);
    const s = parseInt(document.getElementById('editSchedDurSec')?.value || 0);
    const lbl = document.getElementById('editSchedDurLabel');
    if (lbl) lbl.textContent = `${m}분 ${s}초`;
}

async function saveEditSchedule() {
    const id       = parseInt(document.getElementById('editSchedId').value);
    const type     = document.getElementById('editSchedType').value;
    const zone_id  = parseInt(document.getElementById('editSchedZone').value);
    const durMin   = parseInt(document.getElementById('editSchedDurMin').value || 0);
    const durSec   = parseInt(document.getElementById('editSchedDurSec').value || 0);
    const duration = durMin * 60 + durSec;

    if (duration < 10) { showAlert('관수 시간은 10초 이상이어야 합니다.', 'warning'); return; }

    let payload = { type, zone_id, duration };

    if (type === 'routine') {
        const start_date    = document.getElementById('editSchedStartDate').value;
        const start_time    = document.getElementById('editSchedRoutineTime').value;
        const interval_days = parseInt(document.getElementById('editSchedInterval').value);
        const check_moisture= document.getElementById('editSchedMoisture').checked;
        if (!start_date || !start_time) { showAlert('시작 날짜와 시간을 입력하세요.', 'warning'); return; }
        if (!interval_days || interval_days < 1) { showAlert('반복 간격을 1일 이상으로 설정하세요.', 'warning'); return; }
        payload = { ...payload, start_date, start_time, interval_days, check_moisture };
    } else {
        const start_time = document.getElementById('editSchedWeekTime').value;
        const days = [...document.querySelectorAll('.edit-day-btn.active')].map(b => parseInt(b.dataset.day));
        if (!start_time) { showAlert('시작 시간을 입력하세요.', 'warning'); return; }
        if (!days.length) { showAlert('요일을 1개 이상 선택하세요.', 'warning'); return; }
        payload = { ...payload, start_time, days };
    }

    try {
        const res  = await fetch(`/api/schedules/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            bootstrap.Modal.getInstance(document.getElementById('editScheduleModal'))?.hide();
            loadSchedules();
            showAlert('✅ 스케줄이 수정되었습니다.', 'success');
        } else {
            showAlert('수정 실패: ' + (data.message || data.error || '알 수 없는 오류'), 'danger');
        }
    } catch (e) {
        showAlert('오류: ' + e.message, 'danger');
    }
}

// 편집 모달 요일 버튼 토글 (이벤트 위임)
document.addEventListener('click', e => {
    const btn = e.target.closest('.edit-day-btn');
    if (!btn) return;
    const isActive = btn.classList.contains('active');
    btn.classList.toggle('active', !isActive);
    btn.classList.toggle('btn-primary', !isActive);
    btn.classList.toggle('btn-outline-secondary', isActive);
});

// patch_v3b_modal_js

/* ════════════════════════════════════════════════════
   Stage 8 – 알림 설정 탭 JS
   ════════════════════════════════════════════════════ */

// 페이지 로드 시 알림 설정 탭이 활성화되면 자동 로드
document.addEventListener('DOMContentLoaded', () => {
    const alertsTab = document.querySelector('button[data-bs-target="#alerts"]');
    if (alertsTab) {
        alertsTab.addEventListener('shown.bs.tab', () => {
            loadBotStatus();
            loadAlertConfig();
        });
    }
});

function loadBotStatus() {
    fetch('/api/notifications/status')
        .then(r => r.json())
        .then(d => {
            const badge = document.getElementById('botStatusBadge');
            const muteInfo = document.getElementById('botMuteInfo');
            if (!badge) return;
            if (d.connected && d.polling) {
                badge.className = 'badge bg-success fs-6 px-3 py-2';
                badge.textContent = '✅ 연결됨 (폴링 중)';
            } else if (d.connected) {
                badge.className = 'badge bg-warning fs-6 px-3 py-2';
                badge.textContent = '⚠️ 연결됨 (폴링 중지)';
            } else {
                badge.className = 'badge bg-danger fs-6 px-3 py-2';
                badge.textContent = '❌ 미연결';
            }
            if (d.is_muted && d.mute_until) {
                const until = new Date(d.mute_until * 1000).toLocaleTimeString('ko-KR');
                muteInfo.textContent = `🔇 무음 중 (${until}까지)`;
            } else {
                muteInfo.textContent = '';
            }
        })
        .catch(() => {
            const badge = document.getElementById('botStatusBadge');
            if (badge) { badge.className = 'badge bg-secondary fs-6 px-3 py-2'; badge.textContent = '확인 실패'; }
        });
}

function loadAlertConfig() {
    fetch('/api/notifications/config')
        .then(r => r.json())
        .then(cfg => {
            const alerts = cfg.alerts || {};
            const map = {
                'alert_server_start':      'server_start',
                'alert_irrigation_start':  'irrigation_start',
                'alert_irrigation_done':   'irrigation_done',
                'alert_water_level_low':   'water_level_low',
                'alert_water_level_high':  'water_level_high',
                'alert_sensor_error':      'sensor_error',
            };
            Object.entries(map).forEach(([elId, key]) => {
                const el = document.getElementById(elId);
                if (el) el.checked = alerts[key] !== false;
            });
            // 임계값
            const th = cfg.thresholds || {};
            setSlider('tank1Min', 'tank1MinVal', th.tank1_min ?? 20);
            setSlider('tank1Max', 'tank1MaxVal', th.tank1_max ?? 90);
            setSlider('tank2Min', 'tank2MinVal', th.tank2_min ?? 20);
            setSlider('tank2Max', 'tank2MaxVal', th.tank2_max ?? 90);
        });
}

function setSlider(sliderId, labelId, value) {
    const sl = document.getElementById(sliderId);
    const lb = document.getElementById(labelId);
    if (sl) sl.value = value;
    if (lb) lb.textContent = value;
}

function saveAlertConfig() {
    const map = {
        'alert_server_start':     'server_start',
        'alert_irrigation_start': 'irrigation_start',
        'alert_irrigation_done':  'irrigation_done',
        'alert_water_level_low':  'water_level_low',
        'alert_water_level_high': 'water_level_high',
        'alert_sensor_error':     'sensor_error',
    };
    const alerts = {};
    Object.entries(map).forEach(([elId, key]) => {
        const el = document.getElementById(elId);
        if (el) alerts[key] = el.checked;
    });
    fetch('/api/notifications/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ alerts })   // ✅ alerts 섹션만 전송 (telegram 없음)
    })
    .then(r => r.json())
    .then(d => { if (d.success) showMsg('alertSaveMsg'); });
}

function saveThresholdConfig() {
    const thresholds = {
        tank1_min: parseInt(document.getElementById('tank1Min')?.value  || 20),
        tank1_max: parseInt(document.getElementById('tank1Max')?.value  || 90),
        tank2_min: parseInt(document.getElementById('tank2Min')?.value  || 20),
        tank2_max: parseInt(document.getElementById('tank2Max')?.value  || 90),
    };
    fetch('/api/notifications/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ thresholds })  // ✅ thresholds 섹션만 전송 (telegram 없음)
    })
    .then(r => r.json())
    .then(d => { if (d.success) showMsg('threshSaveMsg'); });
}

function sendTestMessage() {
    const btn = event.target;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> 전송 중...';
    fetch('/api/notifications/test', { method: 'POST' })
        .then(r => r.json())
        .then(d => {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-send"></i> 테스트 메시지 전송';
            alert(d.success ? '✅ 테스트 메시지 전송 완료!\n텔레그램을 확인하세요.' : '❌ 전송 실패: ' + (d.message || d.error));
        })
        .catch(() => { btn.disabled = false; btn.innerHTML = '<i class="bi bi-send"></i> 테스트 메시지 전송'; });
}

function showMsg(elId, duration = 3000) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.classList.remove('d-none');
    setTimeout(() => el.classList.add('d-none'), duration);
}

// ═══════════════════════════════════════════════════════
// v3.6: 알림 설정 탭 초기화 + cooldown UI
// ═══════════════════════════════════════════════════════
(function () {
    const _alertsTab = document.querySelector('button[data-bs-target="#alerts"]');
    if (_alertsTab) {
        _alertsTab.addEventListener('shown.bs.tab', function () {
            loadNotificationConfig();
            loadBotStatus();
        });
    }
    // URL ?tab=alerts 로 직접 진입한 경우
    document.addEventListener('DOMContentLoaded', function () {
        if (document.querySelector('#alerts.show.active')) {
            loadNotificationConfig();
            loadBotStatus();
        }
    });
})();

function loadNotificationConfig() {
    fetch('/api/notifications/config')
        .then(r => r.json())
        .then(data => {
            // ① 알림 토글
            const alertMap = {
                server_start:      'alert_server_start',
                irrigation_start:  'alert_irrigation_start',
                irrigation_done:   'alert_irrigation_done',
                water_level_low:   'alert_water_level_low',
                water_level_high:  'alert_water_level_high',
                sensor_error:      'alert_sensor_error',
            };
            const alerts = data.alerts || {};
            Object.entries(alertMap).forEach(([key, elId]) => {
                const el = document.getElementById(elId);
                if (el) el.checked = (alerts[key] !== false);
            });
            // ② 수위 임계값
            const thr = data.thresholds || {};
            [['tank1Min','tank1MinVal', thr.tank1_min, 20],
             ['tank1Max','tank1MaxVal', thr.tank1_max, 90],
             ['tank2Min','tank2MinVal', thr.tank2_min, 20],
             ['tank2Max','tank2MaxVal', thr.tank2_max, 90]
            ].forEach(([inId, lblId, val, def]) => {
                const el = document.getElementById(inId);
                const lb = document.getElementById(lblId);
                const v  = (val != null) ? val : def;
                if (el) el.value = v;
                if (lb) lb.textContent = v;
            });
            // ③ 쿨다운
            const cd = data.cooldown_seconds ?? 300;
            updateCooldownLabel(cd);
        })
        .catch(e => console.error('알림 설정 로드 실패:', e));
}

// 분 → 총 초
function _getCooldownTotal() {
    const m = parseInt(document.getElementById('cooldownMin')?.value || 5);
    return Math.max(60, m * 60);
}
// 총 초 → 분 입력 + 배지 동기화
function updateCooldownLabel(totalSec) {
    const t   = Math.max(60, parseInt(totalSec));
    const m   = Math.round(t / 60);
    const mEl = document.getElementById('cooldownMin');
    const vEl = document.getElementById('cooldownVal');
    if (mEl) mEl.value = m;
    if (vEl) vEl.textContent = t;
}
// 분 직접 입력 시
function syncCooldownFromMin() {
    const t   = _getCooldownTotal();
    const vEl = document.getElementById('cooldownVal');
    if (vEl) vEl.textContent = t;
}
// +/- 버튼 (분 단위)
function adjustCooldown(delta) {
    const t = Math.max(60, _getCooldownTotal() + delta);
    updateCooldownLabel(t);
}
// 프리셋 버튼
function setCooldown(sec) {
    updateCooldownLabel(sec);
}

function saveCooldownConfig() {
    const cd = _getCooldownTotal();
    fetch('/api/notifications/config', {
        method:  'POST',
        headers: {'Content-Type': 'application/json'},
        body:    JSON.stringify({ cooldown_seconds: cd })
    })
    .then(r => r.json())
    .then(d => {
        if (d.success) {
            const el = document.getElementById('cooldownSaveMsg');
            if (el) { el.classList.remove('d-none'); setTimeout(() => el.classList.add('d-none'), 2500); }
        } else {
            showAlert('쿨다운 저장 실패: ' + (d.error || d.message), 'danger');
        }
    })
    .catch(e => showAlert('쿨다운 저장 오류: ' + e.message, 'danger'));
}

// ── Stage 8.8: 서버 재시작 버튼 ─────────────────────────────
function confirmRestart() {
    if (!confirm('서버를 재시작하시겠습니까?\n\n현재 관수 중이면 즉시 중단됩니다.\n확인 후 약 15초 뒤 자동 새로고침됩니다.')) return;
    const btn = document.querySelector('#system-pane .btn-danger');
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>재시작 중...'; }
    fetch('/api/system/restart', { method: 'POST' })
        .then(() => {
            const body = document.getElementById('serverInfoBody');
            if (!body) { setTimeout(() => location.reload(), 15000); return; }
            let sec = 15;
            body.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-danger mb-3" style="width:3rem;height:3rem;"></div><p class="fs-5 fw-bold text-danger">서버 재시작 중...</p><p class="text-muted"><span id="restartCountdown">15</span>초 후 자동 새로고침</p></div>';
            const iv = setInterval(() => { sec--; const el = document.getElementById('restartCountdown'); if (el) el.textContent = sec; if (sec <= 0) { clearInterval(iv); location.reload(); } }, 1000);
        })
        .catch(() => { const body = document.getElementById('serverInfoBody'); if (!body) { setTimeout(() => location.reload(), 15000); return; } let sec = 15; body.innerHTML = '<div class="text-center py-3"><div class="spinner-border text-danger mb-3"></div><p class="text-danger">재시작 중...</p><p><span id="restartCountdown">15</span>초 후 새로고침</p></div>'; const iv = setInterval(() => { sec--; const el = document.getElementById('restartCountdown'); if (el) el.textContent = sec; if (sec <= 0) { clearInterval(iv); location.reload(); } }, 1000); });
}

function loadServerInfo() {
    const body = document.getElementById('serverInfoBody');
    if (!body) return;
    // /api/status + /api/irrigation/status 병렬 호출
    Promise.all([
        fetch('/api/status').then(r => r.json()),
        fetch('/api/irrigation/status').then(r => r.json())
    ]).then(([sys, irr]) => {
        const ts  = sys.timestamp || '--';
        const mon = sys.monitoring_active
            ? '<span class="badge bg-success px-2">✅ 활성</span>'
            : '<span class="badge bg-danger px-2">⛔ 비활성</span>';
        const mode = irr.data ? irr.data.mode || '--' : '--';
        const irrigating = irr.data ? (irr.data.is_irrigating ? '💧 관수 중' : '대기 중') : '--';
        body.innerHTML =
            '<table class="table table-sm mb-0">' +
            '<tr><th>마지막 업데이트</th><td>' + ts + '</td></tr>' +
            '<tr><th>모니터링</th><td>' + mon + '</td></tr>' +
            '<tr><th>관수 모드</th><td>' + mode + '</td></tr>' +
            '<tr><th>관수 상태</th><td>' + irrigating + '</td></tr>' +
            '</table>';
    }).catch(() => { body.innerHTML = '<p class="text-danger text-center">서버 응답 없음</p>'; });
}
document.addEventListener('DOMContentLoaded', function() {
    const t = document.getElementById('system-tab');
    if (t) t.addEventListener('shown.bs.tab', loadServerInfo);
});
// ── /Stage 8.8 ───────────────────────────────────────────────
