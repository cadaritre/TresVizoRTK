"use strict";
(() => {
  let pending=false;
  async function run(body) {
    if(pending)return;
    pending=true;
    try { const result=await api('/api/gnss/control','POST',body);text('device-control-message',`Operación ${result.job_id} en curso…`); }
    catch(error){text('device-control-message',error.message);}
    finally{pending=false;}
  }
  $('device-query').addEventListener('click',()=>run({action:'query'}));
  $('device-rover').addEventListener('click',()=>run({action:'rover'}));
  $('device-rate').addEventListener('click',()=>run({action:'telemetry',hz:Number($('device-hz').value)}));
  $('device-base-apply').addEventListener('click',async()=>{
    if(!preparedBase){text('device-base-message','Prepara y revisa el plan de base primero.');return;}
    try{const r=await api('/api/base/apply','POST',preparedBase.request);text('device-base-message',`Operación ${r.job_id} enviada. Revisa el estado del GPS; aceptar el modo no valida coordenadas ni precisión.`);}
    catch(error){text('device-base-message',error.message);}
  });
  // --- Perfiles NTRIP -----------------------------------------------------
  // El formulario guarda un perfil; conectar es una acción aparte sobre la
  // lista. Antes había que reescribir el caster entero en cada arranque.
  let ntripBusy=false;
  function ntripMessage(value){text('ntrip-profile-message',value);}
  function renderProfiles(data){
    const list=$('ntrip-profile-list');
    if(!list)return;
    list.textContent='';
    const saved=Array.isArray(data.profiles)?data.profiles:[];
    text('ntrip-profile-count',`${saved.length} de ${data.profiles_max||5} perfiles`);
    if(!saved.length){
      const empty=document.createElement('li');
      empty.className='hint';
      empty.textContent='Ningún perfil guardado. Añade uno abajo para que el equipo se reconecte solo.';
      list.append(empty);
      return;
    }
    for(const profile of saved){
      const row=document.createElement('li');
      const name=document.createElement('span');
      const selected=data.selected===profile.name;
      name.textContent=`${profile.name} · ${profile.host}:${profile.port}/${profile.mountpoint}${selected?' · activo':''}`;
      const actions=document.createElement('span');
      actions.className='row-actions';
      const connect=document.createElement('button');
      connect.type='button';connect.className='button secondary';connect.textContent='Conectar';
      connect.addEventListener('click',()=>profileAction({action:'connect',name:profile.name}));
      const edit=document.createElement('button');
      edit.type='button';edit.className='button secondary';edit.textContent='Editar';
      edit.addEventListener('click',()=>{
        $('ntrip-profile-name').value=profile.name;
        $('device-host').value=profile.host;
        $('device-port').value=profile.port;
        $('device-mount').value=profile.mountpoint;
        $('device-user').value=profile.username||'';
        $('device-password').value='';
        $('ntrip-profile-editor').open=true;
      });
      const remove=document.createElement('button');
      remove.type='button';remove.className='button secondary';remove.textContent='Borrar';
      remove.addEventListener('click',()=>profileAction({action:'delete',name:profile.name}));
      actions.append(connect,edit,remove);
      row.append(name,actions);
      list.append(row);
    }
  }
  async function profileAction(body){
    if(ntripBusy)return;
    ntripBusy=true;
    try{renderProfiles(await api('/api/ntrip/profiles','POST',body));ntripMessage('');}
    catch(error){ntripMessage(error.message);}
    finally{ntripBusy=false;}
  }
  async function loadProfiles(){
    try{renderProfiles(await api('/api/ntrip/profiles'));}catch(error){ntripMessage(error.message);}
  }
  $('device-ntrip-form').addEventListener('submit',async(event)=>{
    event.preventDefault();
    await profileAction({
      action:'save',
      name:$('ntrip-profile-name').value,
      host:$('device-host').value,
      port:Number($('device-port').value),
      mountpoint:$('device-mount').value,
      username:$('device-user').value,
      password:$('device-password').value,
    });
    $('device-password').value='';
  });
  $('ntrip-select-none').addEventListener('click',()=>profileAction({action:'select',name:null}));
  $('device-ntrip-stop').addEventListener('click',async()=>{
    try{await api('/api/ntrip/input','POST',{action:'stop'});}catch(error){text('device-ntrip-state',error.message);}
  });
  // Lista de puntos de montaje que publica el caster.
  $('ntrip-mount-browse').addEventListener('click',async()=>{
    const list=$('ntrip-mount-list');
    list.textContent='';
    text('ntrip-mount-hint','Consultando al caster…');
    try{
      await api('/api/ntrip/sourcetable','POST',{host:$('device-host').value,port:Number($('device-port').value)});
      let data=null;
      for(let i=0;i<20;++i){
        await new Promise(resolve=>setTimeout(resolve,700));
        data=await api('/api/ntrip/sourcetable');
        if(data.state!=='loading')break;
      }
      if(!data||data.state==='loading'){text('ntrip-mount-hint','El caster no respondió a tiempo.');return;}
      if(data.state==='waiting_network'){text('ntrip-mount-hint','El equipo no tiene red. Conéctalo a un hotspot en Configuración.');return;}
      if(data.state==='failed'){text('ntrip-mount-hint','No se pudo conectar con el caster.');return;}
      const mounts=Array.isArray(data.mountpoints)?data.mountpoints:[];
      text('ntrip-mount-hint',mounts.length?`${mounts.length} puntos publicados${data.truncated?', lista recortada':''}.`:'El caster no publicó puntos de montaje.');
      for(const mount of mounts){
        const row=document.createElement('li');
        const label=document.createElement('span');
        label.textContent=`${mount.mountpoint} · ${mount.format||'formato desconocido'}${mount.requires_gga?' · exige GGA':''}`;
        const use=document.createElement('button');
        use.type='button';use.className='button secondary';use.textContent='Usar';
        use.addEventListener('click',()=>{$('device-mount').value=mount.mountpoint;});
        row.append(label,use);
        list.append(row);
      }
    }catch(error){text('ntrip-mount-hint',error.message);}
  });

  // --- Mensajes RTCM de salida --------------------------------------------
  // Juego por defecto para triple banda: coordenadas de estación, descriptor de
  // antena y MSM7 de las cuatro constelaciones principales. MSM7 lleva
  // resolución extendida y Doppler; con MSM4 se pierde parte de lo que aporta
  // la tercera frecuencia.
  const rtcmCatalog=[
    {id:'RTCM1005',label:'1005 · Coordenadas de la estación',fixed:true,def:true},
    {id:'RTCM1033',label:'1033 · Descriptor de antena y receptor',fixed:true,def:true},
    {id:'RTCM1077',label:'1077 · GPS MSM7',def:true},
    {id:'RTCM1087',label:'1087 · GLONASS MSM7',def:true},
    {id:'RTCM1097',label:'1097 · Galileo MSM7',def:true},
    {id:'RTCM1127',label:'1127 · BeiDou MSM7',def:true},
    {id:'RTCM1117',label:'1117 · QZSS MSM7',def:false},
    {id:'RTCM1074',label:'1074 · GPS MSM4 (compatibilidad)',def:false},
    {id:'RTCM1084',label:'1084 · GLONASS MSM4 (compatibilidad)',def:false},
    {id:'RTCM1094',label:'1094 · Galileo MSM4 (compatibilidad)',def:false},
  ];
  function buildRtcmGrid(){
    const grid=$('rtcm-message-grid');
    if(!grid)return;
    grid.textContent='';
    for(const entry of rtcmCatalog){
      const label=document.createElement('label');
      label.className='checkbox-label';
      const box=document.createElement('input');
      box.type='checkbox';box.value=entry.id;box.checked=entry.def;
      box.dataset.fixed=entry.fixed?'1':'';
      label.append(box,document.createTextNode(' '+entry.label));
      grid.append(label);
    }
  }
  function applyRtcmDefaults(){
    for(const box of document.querySelectorAll('#rtcm-message-grid input'))
      box.checked=!!rtcmCatalog.find(e=>e.id===box.value&&e.def);
  }
  $('rtcm-defaults')?.addEventListener('click',applyRtcmDefaults);
  $('rtcm-output-form')?.addEventListener('submit',async(event)=>{
    event.preventDefault();
    const rate=Number($('rtcm-observation-rate').value)||1;
    const messages=[];
    for(const box of document.querySelectorAll('#rtcm-message-grid input')){
      if(!box.checked)continue;
      // Estación y descriptor van a 1 Hz: no son observaciones.
      messages.push({name:box.value,hz:box.dataset.fixed?1:rate});
    }
    if(!messages.length){text('rtcm-output-message','Selecciona al menos un mensaje.');return;}
    if(messages.length>8){text('rtcm-output-message','El receptor admite ocho mensajes como máximo. Quita alguno.');return;}
    try{
      const r=await api('/api/gnss/control','POST',{action:'rtcm_base',messages});
      text('rtcm-output-message',`Operación ${r.job_id} enviada al receptor.`);
    }catch(error){text('rtcm-output-message',error.message);}
  });

  // --- Publicación NTRIP y caster local ------------------------------------
  $('ntrip-server-form')?.addEventListener('submit',async(event)=>{
    event.preventDefault();
    try{
      const r=await api('/api/ntrip/server','POST',{action:'start',host:$('ntrip-output-host').value,
        port:Number($('ntrip-output-port').value),mountpoint:$('ntrip-output-mount').value,
        password:$('ntrip-output-pass').value});
      $('ntrip-output-pass').value='';
      text('ntrip-server-state',r.ntrip_server?r.ntrip_server.state:'enviado');
    }catch(error){text('ntrip-server-state',error.message);}
  });
  $('ntrip-server-stop')?.addEventListener('click',async()=>{
    try{await api('/api/ntrip/server','POST',{action:'stop'});text('ntrip-server-state','detenido');}
    catch(error){text('ntrip-server-state',error.message);}
  });
  $('caster-form')?.addEventListener('submit',async(event)=>{
    event.preventDefault();
    try{
      const r=await api('/api/ntrip/caster','POST',{action:'start',port:Number($('caster-port').value),
        mountpoint:$('caster-mount').value,password:$('caster-pass').value});
      $('caster-pass').value='';
      const c=r.local_caster||{};
      text('caster-state',`${c.state||'enviado'} · rovers deben apuntar a ${c.ap_address||'192.168.4.1'}:${$('caster-port').value}/${$('caster-mount').value}`);
    }catch(error){text('caster-state',error.message);}
  });
  $('caster-stop')?.addEventListener('click',async()=>{
    try{await api('/api/ntrip/caster','POST',{action:'stop'});text('caster-state','detenido');}
    catch(error){text('caster-state',error.message);}
  });
  // --- Atajos de inicialización de base ------------------------------------
  function setBaseMethod(method){
    const select=$('base-method');
    if(!select)return;
    select.value=method;
    select.dispatchEvent(new Event('change',{bubbles:true}));
    // Un solo boton de accion visible a la vez: con coordenada conocida se
    // estaciona; promediando, la accion es iniciar el promedio.
    const known=method==='known';
    $('base-use-current')?.classList.toggle('active',known);
    $('base-use-average')?.classList.toggle('active',!known);
    const bar=$('base-station-bar');
    if(bar)bar.hidden=!known;
  }
  $('base-use-current')?.addEventListener('click',()=>{
    const solution=(window.latestStatusSnapshot||{}).solution;
    if(!solution||!Number.isFinite(solution.latitude_deg)||!Number.isFinite(solution.longitude_deg)){
      text('base-result','No hay una posición vigente del receptor. Espera a que entregue solución.');
      return;
    }
    setBaseMethod('known');
    $('base-lat').value=solution.latitude_deg.toFixed(9);
    $('base-lon').value=solution.longitude_deg.toFixed(9);
    // La altura que entrega GGA es MSL del receptor; el plan pide elipsoidal.
    // Se reconstruye sumando la ondulación solo si el receptor la informó.
    const separation=solution.geoid_separation_m;
    if(Number.isFinite(solution.height_m)&&Number.isFinite(separation)){
      $('base-height').value=(solution.height_m+separation).toFixed(4);
      text('base-result',`Coordenada copiada con solución ${solution.fix||'desconocida'}. Altura elipsoidal reconstruida sumando la ondulación informada (${separation.toFixed(3)} m). Revisa datum y altura de antena antes de preparar.`);
    } else {
      $('base-height').value='';
      text('base-result',`Coordenada copiada con solución ${solution.fix||'desconocida'}. El receptor no informó ondulación del geoide, así que la altura elipsoidal hay que introducirla a mano: la de GGA es MSL y no sirve tal cual.`);
    }
  });
  $('base-use-average')?.addEventListener('click',()=>{
    setBaseMethod('average');
    $('base-seconds')?.focus();
    text('base-result','Promedio seleccionado. Indica el tiempo en segundos y prepara el plan; promediar una solución autónoma reduce el ruido, no el sesgo absoluto.');
  });

  // --- Interruptor de Bluetooth --------------------------------------------
  let bleEnabled=null;
  function renderBle(data){
    bleEnabled=!!data.enabled;
    const button=$('ble-toggle');
    if(button)button.textContent=bleEnabled?'Apagar Bluetooth':'Encender Bluetooth';
  }
  async function loadBle(){
    try{renderBle(await api('/api/ble'));}
    catch(error){const b=$('ble-toggle');if(b)b.textContent=error.message;}
  }
  $('ble-toggle')?.addEventListener('click',async()=>{
    if(bleEnabled===null)return;
    const button=$('ble-toggle');
    button.disabled=true;
    try{renderBle(await api('/api/ble','POST',{enabled:!bleEnabled}));}
    catch(error){text('ble-state',error.message);}
    finally{button.disabled=false;}
  });

  // --- Promedio en el sitio --------------------------------------------------
  let averageTimer=null;
  function renderAverage(d){
    const labels={idle:'Sin promediar',averaging:'Promediando',applied:'Promedio aplicado a la base',
                  cancelled:'Cancelado',failed:'Falló'};
    const running=d.state==='averaging'||d.state==='applying';
    // Barra de progreso y coordenada en formación: promediar a ciegas durante
    // un minuto sin ver nada es lo que hacía sentir el proceso interminable.
    const box=$('base-average-progress');
    if(box)box.hidden=d.state==='idle';
    const pct=d.seconds_requested?Math.min(100,Math.round(100*(d.seconds_elapsed||0)/d.seconds_requested)):0;
    const fill=$('base-average-fill');
    if(fill)fill.style.width=`${pct}%`;
    text('base-average-count',running
      ? `${pct}% · ${d.seconds_elapsed||0} de ${d.seconds_requested} s · ${d.samples||0} épocas usadas`
      : `${d.samples||0} épocas usadas`);
    const n=(v,unit,digits)=>Number.isFinite(v)?`${v.toFixed(digits)}${unit}`:'—';
    text('base-average-lat',n(d.latitude_deg,'°',9));
    text('base-average-lon',n(d.longitude_deg,'°',9));
    text('base-average-height',n(d.height_to_set_m,' m',4));
    const parts=[labels[d.state]||d.state];
    if(running)parts.push(`solo con solución ${d.required_quality}`);
    if(d.reason)parts.push(d.reason);
    if(d.geoid_separation_known===false)parts.push('El receptor no informa ondulación del geoide: la altura elipsoidal resultante no es fiable.');
    text('base-average-state',parts.join(' · '));
    if(running){
      clearTimeout(averageTimer);
      averageTimer=setTimeout(pollAverage,1000);
    }
  }
  async function pollAverage(){
    try{renderAverage(await api('/api/base/survey'));}
    catch(error){text('base-average-state',error.message);}
  }
  $('base-average-start')?.addEventListener('click',async()=>{
    // Realimentación inmediata: el usuario pulsa y ve que algo arrancó, sin
    // esperar al primer sondeo. Antes no pasaba nada visible y parecía muerto.
    const box=$('base-average-progress');
    if(box)box.hidden=false;
    const fill=$('base-average-fill');
    if(fill)fill.style.width='0%';
    text('base-average-count','Iniciando…');
    text('base-average-state','Pidiendo el promedio al equipo…');
    try{
      renderAverage(await api('/api/base/survey','POST',{
        action:'start',
        seconds:Number($('base-seconds').value),
        quality:$('base-quality').value,
        station_id:Number($('base-id').value),
        antenna_vertical_m:Number($('base-antenna-avg').value||0),
      }));
    }catch(error){text('base-average-state',error.message);}
  });
  $('base-average-cancel')?.addEventListener('click',async()=>{
    clearTimeout(averageTimer);
    try{renderAverage(await api('/api/base/survey','POST',{action:'cancel'}));}
    catch(error){text('base-average-state',error.message);}
  });

  // --- Papel del receptor --------------------------------------------------
  // Salir de modo base estaba enterrado en el panel de control UART; aquí es lo
  // primero que se ve al entrar a Base / rover.
  const roleNames={base:'Base',rover:'Rover',unknown:'Sin confirmar'};
  window.renderReceiverRole=(status)=>{
    const role=status?.receiver_role||'unknown';
    if(!$('role-state'))return;
    text('role-state',roleNames[role]||'Sin confirmar');
    text('role-detail',
      role==='base'?'Emite correcciones desde una coordenada fija. No consume correcciones.'
      :role==='rover'?'Recibe correcciones para corregir su propia posición.'
      :'Consulta al receptor para saber en qué modo está.');
    const button=$('role-use-rover');
    if(button)button.disabled=role==='rover';
  };
  $('role-use-rover')?.addEventListener('click',()=>{
    text('role-detail','Cambiando a rover…');
    run({action:'rover'});
  });
  // Consultar el modo al abrir la pestaña: tener que pulsar un botón para saber
  // en qué modo está el equipo no es informar, es delegar el trabajo.
  let roleAsked=false;
  document.querySelectorAll('[data-page="base"]').forEach((el)=>{
    el.addEventListener('click',()=>{
      if(roleAsked)return;
      roleAsked=true;
      run({action:'query'});
    });
  });
  if(location.hash==='#base')setTimeout(()=>{roleAsked=true;run({action:'query'});},1200);

  buildRtcmGrid();
  loadProfiles();
  loadBle();
  $('sd-profile').addEventListener('click',()=>run({action:'raw_profile'}));
  for(const action of ['start','stop'])$('sd-'+action).addEventListener('click',async()=>{
    try{await api('/api/recording/'+action,'POST',{});text('sd-message','Solicitud aceptada; espera el estado de cierre.');}
    catch(error){text('sd-message',error.message);}
  });
  async function downloadSession(session){
    const chunks=[];let offset=0,size=1;
    while(offset<size){
      const r=await api('/api/recording/read','POST',{session_id:session,offset});
      size=r.size;if(size>64*1024*1024+1024 || r.next_offset<=offset && offset<size)throw new Error('Tamaño/progreso de descarga inválido');
      chunks.push(Uint8Array.from(atob(r.data),c=>c.charCodeAt(0)));offset=r.next_offset;
    }
    const url=URL.createObjectURL(new Blob(chunks));const link=document.createElement('a');link.href=url;link.download=session+'.bin';link.click();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  async function poll(){
    try{
      const c=await api('/api/gnss/control');
      text('device-control-state',`${c.state} · ${c.mode || 'modo sin consultar'}`);
      text('device-version',c.version || 'Sin consultar');
      text('device-control-error',c.error || '');
      if(c.job_id && c.state!=='running')text('device-control-message',c.state==='confirmed'?'Operación confirmada por el GPS.':'Operación terminada: revisa el estado y sus verificaciones pendientes.');
      if(latestStatus?.memory){const m=latestStatus.memory;text('device-memory',`RAM interna libre: ${kib(m.internal_free_bytes)} · bloque mayor: ${kib(m.internal_largest_block_bytes)} · PSRAM libre: ${kib(m.psram_free_bytes)} / ${kib(m.psram_total_bytes)} · prueba: ${m.psram_test}`);}
      const sd=await api('/api/recording');
      text('sd-state',`${sd.state} · ${sd.bytes} bytes · ${sd.dropped_bytes} bytes perdidos`);
      $('sd-profile').disabled=$('sd-start').disabled=!sd.available || sd.active || sd.state==='closing';
      $('sd-stop').disabled=!sd.active;
      if(sd.available && location.hash==='#recording'){
        const catalog=await api('/api/recording/sessions');
        $('sd-sessions').replaceChildren(...catalog.sessions.map(row=>{
          const item=document.createElement('p');item.textContent=`${row.session_id} · ${row.state} · ${row.bytes} bytes `;
          if(!sd.active && sd.state!=='closing'){
            const button=document.createElement('button');button.className='button secondary';button.textContent='Descargar original';
            button.addEventListener('click',async()=>{button.disabled=true;try{await downloadSession(row.session_id);}catch(error){text('sd-message',error.message);}finally{button.disabled=false;}});item.append(button);
          }return item;
        }));
      }
      const n=await api('/api/ntrip/input');
      // waiting_network sin red configurada no es un problema pasajero: decirlo.
      text('device-ntrip-state',n.network_configured===false
        ? 'Sin red Wi-Fi configurada. Añade tu hotspot de 2.4 GHz en Configuración; NTRIP no puede salir sin internet.'
        : `${n.state} · ${n.frames_forwarded} tramas enviadas · ${n.frames_dropped} descartadas · ${n.error || ''}`);
    }catch(error){text('device-control-state','Sin respuesta del instrumento');}
    setTimeout(poll,2000);
  }
  poll();
})();
