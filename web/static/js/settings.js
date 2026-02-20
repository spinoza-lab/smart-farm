// ========================================
// 설정 페이지 JavaScript
// ========================================

let currentValues = {
    tank1: null,
    tank2: null
};

// ========================================
// 페이지 로드 시 초기화
// ========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('설정 페이지 로드됨');
    
    // 캘리브레이션 설정 로드
    loadCalibration();
    
    // 호스건 상태 로드
    loadHoseGunStatus();
    
    // 5초마다 현재 센서 값 갱신
    updateCurrentValues();
    setInterval(updateCurrentValues, 5000);
    
    // 저장된 폰트 크기 불러오기
    const savedFontSize = localStorage.getItem('fontSize') || 'normal';
    setFontSize(savedFontSize);
    updateFontIndicator();
});

// ========================================
// 폰트 크기 조절
// ========================================
// 폰트 크기 단계 (6단계)
const fontSizes = ['xs', 'small', 'normal', 'medium', 'large', 'xl', 'xxl'];
let currentFontIndex = 2; // 기본값: normal (3/7)

function setFontSize(size) {
    document.body.classList.remove('font-xs', 'font-small', 'font-medium', 'font-large', 'font-xl', 'font-xxl');
    
    if (size === 'xs') {
        document.body.classList.add('font-xs');
        currentFontIndex = 0;
    } else if (size === 'small') {
        document.body.classList.add('font-small');
        currentFontIndex = 1;
    } else if (size === 'normal') {
        // 기본 크기 (클래스 없음)
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
    updateFontIndicator();
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

function updateFontIndicator() {
    const indicator = document.getElementById('fontSizeIndicator');
    if (indicator) {
        indicator.textContent = `${currentFontIndex + 1}/7`;
    }
}



function setFontSizeBySlider(value) {
    const sizes = ['xs', 'small', 'normal', 'large', 'xl', 'xxl'];
    const size = sizes[parseInt(value) - 1];
    setFontSize(size);
}

function updateFontSlider(size) {
    const sizes = ['xs', 'small', 'normal', 'large', 'xl', 'xxl'];
    const index = sizes.indexOf(size);
    const slider = document.getElementById('fontSlider');
    if (slider && index !== -1) {
        slider.value = index + 1;
    }
}

// ========================================
// 숫자 입력 조절 (+/- 버튼)
// ========================================
function adjustValue(inputId, delta) {
    const input = document.getElementById(inputId);
    let value = parseFloat(input.value) || 0;
    value = Math.round((value + delta) * 10) / 10; // 소수점 1자리
    value = Math.max(0, Math.min(5, value)); // 0~5 범위
    input.value = value.toFixed(1);
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
                
                const unit = data.sensor_type === 'voltage' ? ' V' : ' mA';
                
                document.getElementById('tank1CurrentValue').textContent = 
                    currentValues.tank1.toFixed(2) + unit;
                document.getElementById('tank2CurrentValue').textContent = 
                    currentValues.tank2.toFixed(2) + unit;
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
                // 센서 타입
                document.getElementById('sensorType').value = data.sensor_type || 'voltage';
                
                // 물탱크 캘리브레이션
                if (data.tank1_water) {
                    document.getElementById('tank1Empty').value = 
                        parseFloat(data.tank1_water.empty_value || 0.5).toFixed(1);
                    document.getElementById('tank1Full').value = 
                        parseFloat(data.tank1_water.full_value || 4.5).toFixed(1);
                }
                
                // 양액탱크 캘리브레이션
                if (data.tank2_nutrient) {
                    document.getElementById('tank2Empty').value = 
                        parseFloat(data.tank2_nutrient.empty_value || 0.5).toFixed(1);
                    document.getElementById('tank2Full').value = 
                        parseFloat(data.tank2_nutrient.full_value || 4.5).toFixed(1);
                }
                
                console.log('캘리브레이션 설정 로드 완료');
            }
        })
        .catch(error => {
            console.error('캘리브레이션 로드 실패:', error);
            showAlert('캘리브레이션 설정을 불러오는데 실패했습니다.', 'danger');
        });
}

// ========================================
// 현재 값을 공탱크로 설정
// ========================================
function setCurrentAsEmpty(tank) {
    const value = tank === 1 ? currentValues.tank1 : currentValues.tank2;
    const inputId = tank === 1 ? 'tank1Empty' : 'tank2Empty';
    
    if (value === null) {
        showAlert('현재 센서 값을 가져올 수 없습니다.', 'warning');
        return;
    }
    
    document.getElementById(inputId).value = value.toFixed(1);
    showAlert(`Tank ${tank} 공탱크 값을 ${value.toFixed(1)}로 설정했습니다.`, 'success');
}

// ========================================
// 현재 값을 만수로 설정
// ========================================
function setCurrentAsFull(tank) {
    const value = tank === 1 ? currentValues.tank1 : currentValues.tank2;
    const inputId = tank === 1 ? 'tank1Full' : 'tank2Full';
    
    if (value === null) {
        showAlert('현재 센서 값을 가져올 수 없습니다.', 'warning');
        return;
    }
    
    document.getElementById(inputId).value = value.toFixed(1);
    showAlert(`Tank ${tank} 만수 값을 ${value.toFixed(1)}로 설정했습니다.`, 'success');
}

// ========================================
// 센서 타입 저장
// ========================================
function saveSensorType() {
    const sensorType = document.getElementById('sensorType').value;
    
    fetch('/api/calibration', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            sensor_type: sensorType,
            update_type_only: true
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('센서 타입이 저장되었습니다.', 'success');
            updateCurrentValues(); // 센서 값 갱신
        } else {
            showAlert('센서 타입 저장 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(error => {
        console.error('센서 타입 저장 오류:', error);
        showAlert('센서 타입 저장 중 오류가 발생했습니다.', 'danger');
    });
}

// ========================================
// 캘리브레이션 저장
// ========================================
function saveCalibration() {
    // 입력값 검증
    const tank1Empty = parseFloat(document.getElementById('tank1Empty').value);
    const tank1Full = parseFloat(document.getElementById('tank1Full').value);
    const tank2Empty = parseFloat(document.getElementById('tank2Empty').value);
    const tank2Full = parseFloat(document.getElementById('tank2Full').value);
    
    if (tank1Empty >= tank1Full) {
        showAlert('물탱크: 공탱크 값이 만수 값보다 작아야 합니다.', 'danger');
        return;
    }
    
    if (tank2Empty >= tank2Full) {
        showAlert('양액탱크: 공탱크 값이 만수 값보다 작아야 합니다.', 'danger');
        return;
    }
    
    const sensorType = document.getElementById('sensorType').value;
    
    const calibrationData = {
        sensor_type: sensorType,
        tank1_water: {
            empty_value: tank1Empty,
            full_value: tank1Full
        },
        tank2_nutrient: {
            empty_value: tank2Empty,
            full_value: tank2Full
        }
    };
    
    fetch('/api/calibration', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(calibrationData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('캘리브레이션 설정이 저장되었습니다!', 'success');
            loadCalibration(); // 설정 다시 로드
        } else {
            showAlert('저장 실패: ' + (data.error || '알 수 없는 오류'), 'danger');
        }
    })
    .catch(error => {
        console.error('저장 오류:', error);
        showAlert('저장 중 오류가 발생했습니다.', 'danger');
    });
}

// ========================================
// 호스건 상태 로드
// ========================================
function loadHoseGunStatus() {
    fetch('/api/hose-gun/status')
        .then(response => response.json())
        .then(data => {
            updateHoseGunUI(data.active);
        })
        .catch(error => {
            console.error('호스건 상태 로드 실패:', error);
        });
}

// ========================================
// 호스건 활성화
// ========================================
function activateHoseGun() {
    if (confirm('호스건을 시작하시겠습니까?\n\n물탱크와 양액탱크가 자동으로 차단됩니다.')) {
        fetch('/api/hose-gun/activate', {
            method: 'POST'
        })
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

// ========================================
// 호스건 비활성화
// ========================================
function deactivateHoseGun() {
    fetch('/api/hose-gun/deactivate', {
        method: 'POST'
    })
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

// ========================================
// 호스건 UI 업데이트
// ========================================
function updateHoseGunUI(isActive) {
    const statusBadge = document.getElementById('hoseGunStatus');
    
    if (isActive) {
        statusBadge.textContent = 'ON';
        statusBadge.className = 'badge bg-success';
    } else {
        statusBadge.textContent = 'OFF';
        statusBadge.className = 'badge bg-secondary';
    }
}

// ========================================
// 알림 표시
// ========================================
function showAlert(message, type = 'info') {
    // 기존 알림 제거
    const existingAlert = document.querySelector('.floating-alert');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    // 새 알림 생성
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
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (alertDiv.parentElement) {
            alertDiv.remove();
        }
    }, 3000);
}
