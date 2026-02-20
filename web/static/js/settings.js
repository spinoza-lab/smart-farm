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
    
    // 저장된 폰트 크기 불러오기
    const savedFontSize = localStorage.getItem('fontSize') || 'normal';
    setFontSize(savedFontSize);
    
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
// 폰트 크기 조절
// ========================================
const fontSizes = ['xs', 'small', 'normal', 'medium', 'large', 'xl', 'xxl'];
let currentFontIndex = 2;

function setFontSize(size) {
    document.body.classList.remove('font-xs', 'font-small', 'font-medium', 'font-large', 'font-xl', 'font-xxl');
    
    if (size === 'xs') {
        document.body.classList.add('font-xs');
        currentFontIndex = 0;
    } else if (size === 'small') {
        document.body.classList.add('font-small');
        currentFontIndex = 1;
    } else if (size === 'normal') {
        currentFontIndex = 2;
    } else if (size === 'medium') {
        document.body.classList.add('font-medium');
        currentFontIndex = 3;
    } else if (size === 'large') {
        document.body.classList.add('font-large');
        currentFontIndex = 4;
    } else if (size === 'xl') {
        document.body.classList.add('font-xl');
        currentFontIndex = 5;
    } else if (size === 'xxl') {
        document.body.classList.add('font-xxl');
        currentFontIndex = 6;
    }
    
    localStorage.setItem('fontSize', size);
    console.log('폰트 크기:', size, `(${currentFontIndex + 1}/7)`);
}

function increaseFontSize() {
    currentFontIndex = Math.min(currentFontIndex + 1, fontSizes.length - 1);
    setFontSize(fontSizes[currentFontIndex]);
}

function decreaseFontSize() {
    currentFontIndex = Math.max(currentFontIndex - 1, 0);
    setFontSize(fontSizes[currentFontIndex]);
}

function resetFontSize() {
    setFontSize('normal');
}

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
