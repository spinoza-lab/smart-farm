// 스마트 관수 시스템 - 대시보드 JavaScript

// Socket.IO 연결
const socket = io();

// 차트 객체
let waterChart = null;

// 차트 데이터
let chartData = {
    labels: [],
    tank1: [],
    tank2: []
};

// ============================================================
// Socket.IO 이벤트
// ============================================================

socket.on('connect', () => {
    console.log('✅ 서버 연결됨');
    });

socket.on('disconnect', () => {
    console.log('❌ 서버 연결 끊김');
    });

socket.on('connected', (data) => {
    // console.log('📡', data.message);  // 디버그용
});

socket.on('sensor_update', (data) => {
    // console.log('📊 센서 데이터 수신:', data);  // 디버그용
    updateSensorData(data);
    updateChart(data);
});

socket.on('new_alert', (alert) => {
    console.log('🚨 새 경고:', alert);
    addAlertToList(alert);
    updateAlertCount();
});

// ============================================================
// UI 업데이트 함수
// ============================================================


function updateSensorData(data) {
    // 디버깅: 원본 데이터 확인
    // console.log("📊 센서 데이터 수신:", data);  // 디버그용
    // console.log("📅 원본 timestamp:", data.timestamp);  // 디버그용
    
    // 마지막 업데이트 시간 (시간만 표시)
    let displayTime = data.timestamp;
    
    // 전체 날짜 시간 형식이면 시간만 추출해서 표시
    if (displayTime && displayTime.includes(' ')) {
        displayTime = displayTime.split(' ')[1];  // '2026-02-12 14:13:43' → '14:13:43'
    }
    
    document.getElementById('last-update').textContent = displayTime;
    
    // 탱크 1 수위
    const tank1Level = data.tank1_level;
    updateWaterGauge('tank1', tank1Level);
    
    // 탱크 2 수위
    const tank2Level = data.tank2_level;
    updateWaterGauge('tank2', tank2Level);
    
    // 전압 데이터
    // document.getElementById('voltage-ch0').textContent = data.voltages[0].toFixed(3) + 'V';  // 센서 전압 표시 제거됨
    // document.getElementById('voltage-ch1').textContent = data.voltages[1].toFixed(3) + 'V';  // 센서 전압 표시 제거됨
    // document.getElementById('voltage-ch2').textContent = data.voltages[2].toFixed(3) + 'V';  // 센서 전압 표시 제거됨
    // document.getElementById('voltage-ch3').textContent = data.voltages[3].toFixed(3) + 'V';  // 센서 전압 표시 제거됨
}

function updateWaterGauge(tankId, level) {
    const waterElement = document.getElementById(`${tankId}-water`);
    const percentageElement = document.getElementById(`${tankId}-percentage`);
    
    // 수위 높이 설정
    waterElement.style.height = level + '%';
    
    // 퍼센트 표시
    percentageElement.textContent = level.toFixed(1) + '%';
    
    // 색상 변경 (낮음/높음)
    waterElement.className = 'water-level';
    if (level < 20) {
        waterElement.classList.add('low');
    } else if (level > 90) {
        waterElement.classList.add('high');
    }
}

function updateChart(data) {
    // console.log("📈 [updateChart] 원본 data:", data);  // 디버그용
    // console.log("📈 [updateChart] 원본 timestamp:", data.timestamp);  // 디버그용
    
    let timestamp = data.timestamp;
    if (timestamp && typeof timestamp === 'string') {
        timestamp = timestamp.replace(' ', 'T');
    }
    
    // console.log("📈 [updateChart] 변환된 timestamp:", timestamp);  // 디버그용
    
    const now = new Date(timestamp);
    
    // console.log("📈 [updateChart] Date 객체:", now);  // 디버그용
    // console.log("📈 [updateChart] 유효한가?", !isNaN(now.getTime()));  // 디버그용
    
    const timeLabel = now.toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
    });
    
    // console.log("📈 [updateChart] timeLabel:", timeLabel);  // 디버그용

    
    // 데이터 추가
    chartData.labels.push(timeLabel);
    chartData.tank1.push(data.tank1_level);
    chartData.tank2.push(data.tank2_level);
    
    // 최근 360개만 유지 (1시간)
    if (chartData.labels.length > 360) {
        chartData.labels.shift();
        chartData.tank1.shift();
        chartData.tank2.shift();
    }
    
    // 차트 업데이트
    if (waterChart) {
        waterChart.data.labels = chartData.labels;
        waterChart.data.datasets[0].data = chartData.tank1;
        waterChart.data.datasets[1].data = chartData.tank2;
        waterChart.update();
    }
}

function addAlertToList(alert) {
    const alertList = document.getElementById('alert-list');
    
    // 첫 경고인 경우 "경고 없음" 메시지 제거
    if (alertList.children[0]?.classList.contains('text-muted')) {
        alertList.innerHTML = '';
    }
    
    // 경고 레벨에 따른 아이콘 및 클래스
    let icon, levelClass;
    switch (alert.level) {
        case 'CRITICAL':
            icon = 'fas fa-exclamation-circle text-danger';
            levelClass = 'critical';
            break;
        case 'WARNING':
            icon = 'fas fa-exclamation-triangle text-warning';
            levelClass = 'warning';
            break;
        case 'INFO':
            icon = 'fas fa-info-circle text-info';
            levelClass = 'info';
            break;
        default:
            icon = 'fas fa-bell';
            levelClass = '';
    }
    
    // 경고 아이템 생성
    const alertItem = document.createElement('div');
    alertItem.className = `alert-item ${levelClass}`;
    alertItem.innerHTML = `
        <div class="d-flex align-items-start">
            <i class="${icon} alert-icon"></i>
            <div class="flex-grow-1">
                <div class="alert-message">${alert.message}</div>
                <div class="alert-time">${alert.timestamp}</div>
            </div>
        </div>
    `;
    
    // 목록 맨 위에 추가
    alertList.insertBefore(alertItem, alertList.firstChild);
    
    // 최대 10개까지만 표시
    while (alertList.children.length > 10) {
        alertList.removeChild(alertList.lastChild);
    }
}

// ============================================================
// API 호출 함수
// ============================================================

async function loadAlerts() {
    try {
        const response = await fetch('/api/alerts?limit=10');
        const data = await response.json();
        
        if (response.ok) {
            const alertList = document.getElementById('alert-list');
            alertList.innerHTML = '';
            
            if (data.alerts.length === 0) {
                alertList.innerHTML = '<div class="text-center text-muted p-3">경고 없음</div>';
            } else {
                data.alerts.forEach(alert => addAlertToList(alert));
            }
        }
    } catch (error) {
        console.error('❌ 경고 목록 로드 실패:', error);
    }
}

async function updateAlertCount() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (response.ok) {
            document.getElementById('alert-count-24h').textContent = data.alert_count_24h || 0;
        }
    } catch (error) {
        console.error('❌ 상태 업데이트 실패:', error);
    }
}

// ============================================================
// 차트 초기화
// ============================================================

function initChart() {
    const ctx = document.getElementById('water-chart').getContext('2d');
    
    waterChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: '탱크 1',
                    data: [],
                    borderColor: '#1976d2',
                    backgroundColor: 'rgba(25, 118, 210, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: '탱크 2',
                    data: [],
                    borderColor: '#0288d1',
                    backgroundColor: 'rgba(2, 136, 209, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: '수위 (%)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '시간'
                    }
                }
            }
        }
    });
}
// ============================================================
// 이벤트 리스너
// ============================================================


// ============================================================
// 초기화
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 대시보드 초기화');
    
    // 차트 초기화
    initChart();
    
    // 경고 목록 로드
    loadAlerts();
    
    // 경고 카운트 업데이트
    updateAlertCount();
    
    // 10초마다 경고 카운트 업데이트
    setInterval(updateAlertCount, 10000);
});
