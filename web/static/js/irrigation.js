/* irrigation.js – 스마트 관수 시스템 관수 제어 페이지 v1.0 */
'use strict';
const state={mode:'manual',isIrrigating:false,currentZone:null,zones:{},history:[],progressTimer:null,progressTotal:0,progressElapsed:0,irrigationDuration:300};
const socket=io();
socket.on('connect',()=>{console.log('✅ 서버 연결됨');setConnUI(true);refreshStatus();loadHistory();});
socket.on('disconnect',()=>{console.log('❌ 서버 연결 끊김');setConnUI(false);});
socket.on('sensor_update',()=>{});
socket.on('irrigation_update',(data)=>{if(data.is_irrigating!==undefined)state.isIrrigating=data.is_irrigating;if(data.current_zone!==undefined)state.currentZone=data.current_zone;if(data.mode!==undefined){state.mode=data.mode;applyModeUI(data.mode);}applyIrrigationUI();});
document.addEventListener('DOMContentLoaded',()=>{console.log('🚀 관수 제어 페이지 초기화');buildZoneCards();initMoistureChart();refreshStatus();loadHistory();initDateDefaults();loadIrrigationConfig();setInterval(refreshStatus,30000);setInterval(loadHistory,60000);});
function loadIrrigationConfig(){fetch('/api/irrigation/config').then(r=>r.json()).then(d=>{if(d.success&&d.config&&d.config.irrigation_duration){state.irrigationDuration=d.config.irrigation_duration;const el=document.getElementById('global-duration');if(el)el.value=Math.round(d.config.irrigation_duration/60);}}).catch(()=>{});}
function buildZoneCards(){const c=document.getElementById('zone-cards-container');if(!c)return;c.innerHTML='';for(let z=1;z<=12;z++){state.zones[z]={moisture:null,temperature:null,ec:null,threshold:40.0,status:'offline'};const col=document.createElement('div');col.className='col-6 col-md-4 col-lg-3 col-xl-2';col.innerHTML=zoneCardHTML(z);c.appendChild(col);}for(let z=1;z<=12;z++)initGauge(z);}
function zoneCardHTML(z){return`<div class="card zone-card" id="zone-card-${z}"><div class="card-header d-flex justify-content-between align-items-center"><span class="fw-bold">구역 ${z}</span><span class="z-badge z-offline" id="zone-badge-${z}">오프라인</span></div><div class="card-body p-2 text-center"><div class="gauge-wrap" id="gauge-wrap-${z}"><canvas id="gauge-canvas-${z}" width="86" height="86"></canvas><div class="gauge-center"><span class="val" id="zone-moisture-${z}">—</span><span class="unit">%</span></div></div><div class="sensor-row"><span><i class="bi bi-thermometer" style="color:#ff9800;"></i><b id="zone-temp-${z}">—</b>℃</span><span><i class="bi bi-lightning" style="color:#667eea;"></i><b id="zone-ec-${z}">—</b>µS</span></div><div class="threshold-row justify-content-center">임계:<span class="val" id="zone-thr-${z}">40%</span><a href="/settings?tab=auto-control" title="자동 관수 설정에서 변경" style="color:#999;font-size:0.65rem;"><i class="bi bi-pencil"></i></a></div><button class="btn btn-outline-primary btn-irrigate w-100" id="btn-irrigate-${z}" onclick="manualIrrigate(${z})"><i class="bi bi-droplet-fill me-1"></i>관수</button></div></div>`;}
const gaugeCtx={};
function initGauge(z){const canvas=document.getElementById(`gauge-canvas-${z}`);if(!canvas)return;gaugeCtx[z]=canvas.getContext('2d');drawGauge(z,0,'#bdbdbd');}
function drawGauge(z,pct,color){const ctx=gaugeCtx[z];if(!ctx)return;const W=86,R=32,cx=W/2,cy=W/2,startA=-Math.PI*0.75,fullA=Math.PI*1.5;ctx.clearRect(0,0,W,W);ctx.beginPath();ctx.arc(cx,cy,R,startA,startA+fullA);ctx.lineWidth=7;ctx.strokeStyle='#e0e0e0';ctx.lineCap='round';ctx.stroke();if(pct>0){ctx.beginPath();ctx.arc(cx,cy,R,startA,startA+(pct/100)*fullA);ctx.lineWidth=7;ctx.strokeStyle=color;ctx.lineCap='round';ctx.stroke();}}
function moistureColor(p){if(p===null||p===undefined)return'#bdbdbd';if(p<20)return'#f44336';if(p<35)return'#ff9800';if(p<60)return'#4caf50';return'#2196f3';}
let moistureChart=null;
function initMoistureChart(){const canvas=document.getElementById('moisture-chart');if(!canvas)return;moistureChart=new Chart(canvas.getContext('2d'),{type:'bar',data:{labels:Array.from({length:12},(_,i)=>`구역${i+1}`),datasets:[{label:'토양 수분 (%)',data:new Array(12).fill(0),backgroundColor:new Array(12).fill('rgba(102,126,234,0.5)'),borderColor:new Array(12).fill('#667eea'),borderWidth:1,borderRadius:4}]},options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>` ${ctx.parsed.y.toFixed(1)} %`}}},scales:{x:{ticks:{font:{size:10}},grid:{color:'#f0f0f0'}},y:{min:0,max:100,ticks:{callback:v=>v+'%',font:{size:10}},grid:{color:'#f0f0f0'}}}}});}
function updateMoistureChart(){if(!moistureChart)return;const data=[],bg=[],bd=[];for(let z=1;z<=12;z++){const m=state.zones[z]?.moisture;data.push(m!==null&&m!==undefined?m:0);const c=moistureColor(m);bg.push(hexToRgba(c,0.5));bd.push(c);}moistureChart.data.datasets[0].data=data;moistureChart.data.datasets[0].backgroundColor=bg;moistureChart.data.datasets[0].borderColor=bd;moistureChart.update('none');}
function hexToRgba(hex,a){if(hex.startsWith('rgba')||hex.startsWith('rgb'))return hex;const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);return`rgba(${r},${g},${b},${a})`;}
async function apiGet(url){const res=await fetch(url);return res.json();}
async function apiPost(url,body){const res=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return res.json();}
async function refreshStatus(){try{const res=await apiGet('/api/irrigation/status');if(!res.success)return;const d=res.data;state.mode=d.mode||'manual';state.isIrrigating=!!d.is_irrigating;state.currentZone=d.current_zone||null;applyModeUI(state.mode);if(state.isIrrigating&&!state.progressTimer&&d.irr_total>0){const elapsed=d.irr_elapsed||0;const total=d.irr_total;const remaining=Math.max(0,total-elapsed);state.progressTotal=total;state.progressElapsed=elapsed;const fill=document.getElementById('prog-fill');if(fill)fill.style.width=Math.min(100,(elapsed/total)*100)+'%';const lbl=document.getElementById('prog-time-lbl');if(lbl)lbl.textContent=remaining>0?remaining+'초 남음':'완료';if(remaining>0){state.progressTimer=setInterval(()=>{state.progressElapsed++;const pct=Math.min(100,(state.progressElapsed/state.progressTotal)*100);if(fill)fill.style.width=pct+'%';const rem=state.progressTotal-state.progressElapsed;if(lbl)lbl.textContent=rem>0?rem+'초 남음':'완료';if(state.progressElapsed>=state.progressTotal){stopProgress();setTimeout(refreshStatus,2000);}},1000);}}if(d.zone_thresholds)Object.entries(d.zone_thresholds).forEach(([z,t])=>{const zi=parseInt(z);if(state.zones[zi])state.zones[zi].threshold=t;setText(`zone-thr-${zi}`,t+'%');});if(d.last_sensor_data&&Object.keys(d.last_sensor_data).length>0)updateZoneSensors(d.last_sensor_data);applyIrrigationUI();if(d.is_irrigating&&typeof d.irr_elapsed==="number"&&!state.progressTimer){const total=d.irr_total||300;startProgress(total);state.progressElapsed=d.irr_elapsed;}/* Fix H – patch_v4g */const today=new Date().toLocaleDateString('ko-KR');const cnt=(d.recent_history||[]).filter(h=>h.start_time&&new Date(h.start_time).toLocaleDateString('ko-KR')===today).length;setText('today-count-disp',cnt+' 회');setText('last-update-disp','갱신: '+new Date().toLocaleTimeString('ko-KR'));setConnUI(true);}catch(e){console.error('상태 조회 실패:',e);setConnUI(false);}}
function updateZoneSensors(sensorData){Object.entries(sensorData).forEach(([zStr,sData])=>{const z=parseInt(zStr);if(!state.zones[z])return;if(sData.error){state.zones[z].status='offline';renderZoneCard(z);return;}state.zones[z].moisture=sData.moisture!==undefined?+sData.moisture:null;state.zones[z].temperature=sData.temperature!==undefined?+sData.temperature:null;state.zones[z].ec=sData.ec!==undefined?+sData.ec:null;const m=state.zones[z].moisture;const thr=state.zones[z].threshold||40;state.zones[z].status=(state.isIrrigating&&state.currentZone===z)?'irrigating':m===null?'offline':m<thr?'dry':'ok';renderZoneCard(z);});updateMoistureChart();}
function renderZoneCard(z){const zn=state.zones[z];const m=zn.moisture;const color=moistureColor(m);drawGauge(z,m!==null?m:0,color);setText(`zone-moisture-${z}`,m!==null?m.toFixed(1):'—');setText(`zone-temp-${z}`,zn.temperature!==null?zn.temperature.toFixed(1):'—');setText(`zone-ec-${z}`,zn.ec!==null?Math.round(zn.ec):'—');setText(`zone-thr-${z}`,zn.threshold+'%');const badge=document.getElementById(`zone-badge-${z}`);if(badge){const map={irrigating:['관수중','z-irrigating'],dry:['건조','z-dry'],ok:['적정','z-ok'],offline:['오프라인','z-offline']};const[txt,cls]=map[zn.status]||['—','z-offline'];badge.textContent=txt;badge.className='z-badge '+cls;}const card=document.getElementById(`zone-card-${z}`);if(card){card.classList.remove('irrigating','dry');if(zn.status==='irrigating')card.classList.add('irrigating');if(zn.status==='dry')card.classList.add('dry');}const btn=document.getElementById(`btn-irrigate-${z}`);if(btn)btn.disabled=state.isIrrigating;}
function applyModeUI(mode){if(mode==='schedule')mode='auto';const bannerBg={manual:{bg:'#fff8e1',border:'#ffe082',iconColor:'#f57f17',iconCls:'bi-hand-index',textColor:'#e65100',label:'수동 모드'},auto:{bg:'#e8f5e9',border:'#a5d6a7',iconColor:'#2e7d32',iconCls:'bi-robot',textColor:'#1b5e20',label:'자동 모드'},schedule:{bg:'#e3f2fd',border:'#90caf9',iconColor:'#1565c0',iconCls:'bi-calendar-check',textColor:'#0d47a1',label:'스케줄 모드'}};const cfg=bannerBg[mode]||bannerBg.manual;const banner=document.getElementById('mode-banner');if(banner){banner.style.background=cfg.bg;banner.style.borderColor=cfg.border;}const icon=document.getElementById('mode-icon');if(icon){icon.className='bi '+cfg.iconCls+' fs-4';icon.style.color=cfg.iconColor;}const text=document.getElementById('mode-text');if(text){text.textContent=cfg.label;text.style.color=cfg.textColor;}const styles={manual:{on:'btn-warning',off:'btn-outline-warning'},auto:{on:'btn-success',off:'btn-outline-success'},schedule:{on:'btn-info',off:'btn-outline-info'}};Object.entries(styles).forEach(([m,s])=>{const btn=document.getElementById(`btn-${m}`);if(!btn)return;btn.classList.remove(s.on,s.off);btn.classList.add(m===mode?s.on:s.off);});}
function applyIrrigationUI(){const badge=document.getElementById('irr-status-badge');const panel=document.getElementById('progress-panel');if(state.isIrrigating&&state.currentZone){if(badge){badge.textContent=`구역 ${state.currentZone} 관수 중`;badge.className='badge bg-primary';}if(panel)panel.classList.remove('d-none');setText('current-zone-disp',`구역 ${state.currentZone}`);setText('prog-zone-lbl',`구역 ${state.currentZone}`);}else{if(badge){badge.textContent='대기 중';badge.className='badge bg-secondary';}if(panel)panel.classList.add('d-none');setText('current-zone-disp','—');stopProgress();}for(let z=1;z<=12;z++){const btn=document.getElementById(`btn-irrigate-${z}`);if(btn)btn.disabled=state.isIrrigating;}}
function startProgress(duration){stopProgress();state.progressTotal=duration;state.progressElapsed=0;const fill=document.getElementById('prog-fill');const lbl=document.getElementById('prog-time-lbl');state.progressTimer=setInterval(()=>{state.progressElapsed++;const pct=Math.min(100,(state.progressElapsed/state.progressTotal)*100);if(fill)fill.style.width=pct+'%';const rem=state.progressTotal-state.progressElapsed;if(lbl)lbl.textContent=rem>0?`${rem}초 남음`:'완료';if(state.progressElapsed>=state.progressTotal){stopProgress();setTimeout(refreshStatus,2000);}},1000);}
function stopProgress(){if(state.progressTimer){clearInterval(state.progressTimer);state.progressTimer=null;}const fill=document.getElementById('prog-fill');if(fill)fill.style.width='0%';}
async function setMode(mode){try{const res=await apiPost('/api/irrigation/mode',{mode});if(res.success){state.mode=mode;applyModeUI(mode);showToast(res.message||`모드 변경: ${mode}`);}else{showToast(res.error||'모드 변경 실패');}}catch(e){showToast('서버 오류: '+e.message);}}
async function manualIrrigate(zoneId){const durInput=document.getElementById('global-duration');const durMin=durInput?parseInt(durInput.value)||Math.round(state.irrigationDuration/60):Math.round(state.irrigationDuration/60);if(isNaN(durMin)||durMin<1||durMin>60){showToast('관수 시간은 1~60분 사이로 입력하세요.');return;}const dur=durMin*60;try{const res=await apiPost('/api/irrigation/start',{zone_id:zoneId,duration:dur});if(res.success){state.isIrrigating=true;state.currentZone=zoneId;applyIrrigationUI();startProgress(dur);if(state.zones[zoneId]){state.zones[zoneId].status='irrigating';renderZoneCard(zoneId);}showToast(res.message||`구역 ${zoneId} 관수 시작`);document.getElementById('zones-tab')?.click();}else{showToast(res.error||'관수 시작 실패');}}catch(e){showToast('서버 오류: '+e.message);}}
async function emergencyStop(){try{const res=await apiPost('/api/irrigation/stop',{});if(res.success){state.isIrrigating=false;state.currentZone=null;applyIrrigationUI();stopProgress();showToast('긴급 정지 완료');await refreshStatus();}else{showToast(res.error||'정지 실패');}}catch(e){showToast('서버 오류: '+e.message);}}
async function readAllSensors(){showToast('센서 데이터 수집 중...');try{const res=await apiPost('/api/irrigation/sensors/read',{});if(res.success&&res.data){updateZoneSensors(res.data);showToast('센서 데이터 갱신 완료');}else{showToast(res.error||'센서 읽기 실패 (센서 미연결?)');}}catch(e){showToast('서버 오류: '+e.message);}}
function openThresholdModal(zoneId){const t=state.zones[zoneId]?.threshold||40;document.getElementById('modal-zone-id').value=zoneId;document.getElementById('modal-zone-label').textContent=`구역 ${zoneId}`;const slider=document.getElementById('modal-slider');slider.value=t;document.getElementById('modal-val').textContent=t+'%';new bootstrap.Modal(document.getElementById('thresholdModal')).show();}
async function saveThreshold(){const zoneId=parseInt(document.getElementById('modal-zone-id').value);const threshold=parseFloat(document.getElementById('modal-slider').value);try{const res=await apiPost('/api/irrigation/threshold',{zone_id:zoneId,threshold});if(res.success){state.zones[zoneId].threshold=threshold;setText(`zone-thr-${zoneId}`,threshold+'%');bootstrap.Modal.getInstance(document.getElementById('thresholdModal')).hide();showToast(`구역 ${zoneId} 임계값 ${threshold}% 저장`);}else{showToast(res.error||'임계값 저장 실패');}}catch(e){showToast('서버 오류: '+e.message);}}
async function loadHistory(){try{const res=await apiGet('/api/irrigation/history');if(!res.success||!res.data)return;const tbody=document.getElementById('history-tbody');if(!tbody)return;if(!res.data.length){tbody.innerHTML='<tr><td colspan="5" class="text-center text-muted py-4">이력 없음</td></tr>';return;}tbody.innerHTML=res.data.map(h=>{const dt=h.start_time?new Date(h.start_time):null;const time=dt?dt.toLocaleString('ko-KR',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}):'—';const trigger=h.trigger==='auto'?'<span class="badge bg-success">자동</span>':h.trigger==='manual'?'<span class="badge bg-warning text-dark">수동</span>':`<span class="badge bg-secondary">${h.trigger||'—'}</span>`;const result=h.success===false?'<span class="text-danger"><i class="bi bi-x-circle"></i> 실패</span>':'<span class="text-success"><i class="bi bi-check-circle"></i> 완료</span>';return`<tr><td class="ps-3 text-muted">${time}</td><td class="fw-bold">구역 ${h.zone_id||'—'}</td><td>${h.duration||'—'} 초</td><td>${trigger}</td><td>${result}</td></tr>`;}).join('');state.history=res.data;}catch(e){console.error('이력 로드 실패:',e);}}
function setConnUI(connected){const dot=document.getElementById('conn-dot');const text=document.getElementById('conn-text');if(dot)dot.className='conn-dot '+(connected?'conn-on':'conn-off');if(text)text.textContent=connected?'서버 연결됨':'연결 끊김';}
function setText(id,val){const el=document.getElementById(id);if(el)el.textContent=val;}
let toastTimer=null;
function showToast(msg){const existing=document.querySelector('.irr-toast');if(existing)existing.remove();if(toastTimer)clearTimeout(toastTimer);const div=document.createElement('div');div.className='irr-toast';div.textContent=msg;document.body.appendChild(div);toastTimer=setTimeout(()=>div.remove(),3500);}

// ────────────────────────────────────────────────────
// 날짜 필터 기본값 초기화 (오늘 기준 30일 ~ 오늘)
// ────────────────────────────────────────────────────
function initDateDefaults(){
  const toEl=document.getElementById('hist-to');
  const fromEl=document.getElementById('hist-from');
  if(!toEl||!fromEl)return;
  const today=new Date();
  const yyyy=today.getFullYear();
  const mm=String(today.getMonth()+1).padStart(2,'0');
  const dd=String(today.getDate()).padStart(2,'0');
  toEl.value=`${yyyy}-${mm}-${dd}`;
  const past=new Date(today);past.setDate(today.getDate()-30);
  const py=past.getFullYear(),pm=String(past.getMonth()+1).padStart(2,'0'),pd=String(past.getDate()).padStart(2,'0');
  fromEl.value=`${py}-${pm}-${pd}`;
}

// ────────────────────────────────────────────────────
// 관수 이력 CSV 다운로드
// ────────────────────────────────────────────────────
function downloadIrrigationCSV(){
  const fromEl=document.getElementById('hist-from');
  const toEl=document.getElementById('hist-to');
  const from=fromEl?fromEl.value:'';
  const to=toEl?toEl.value:'';

  let url='/api/download/irrigation-history';
  const params=[];
  if(from)params.push(`from=${encodeURIComponent(from)}`);
  if(to)params.push(`to=${encodeURIComponent(to)}`);
  if(params.length)url+='?'+params.join('&');

  // 파일 없음 사전 체크 후 다운로드
  fetch('/api/download/files')
    .then(r=>r.json())
    .then(d=>{
      if(!d.success||!d.data.irrigation_csv){
        showToast('⚠️ 저장된 관수 이력 CSV 파일이 없습니다.\n(자동 관수가 한 번도 실행되지 않았을 수 있습니다)');
        return;
      }
      showToast(`📥 CSV 다운로드 중... (${d.data.irrigation_csv.rows}건)`);
      const a=document.createElement('a');
      a.href=url;
      a.download='';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    })
    .catch(()=>{
      // 체크 실패해도 그냥 다운로드 시도
      const a=document.createElement('a');
      a.href=url;
      a.download='';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    });
}
