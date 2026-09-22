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
  $('device-ntrip-form').addEventListener('submit',async(event)=>{
    event.preventDefault();
    try{
      // Detener siempre antes de arrancar. Con una conexion anterior viva, el
      // router queda con la fuente en 'ntrip' y eso rechaza la consulta de modo
      // que hace falta para arrancar: sin esto no hay forma de corregir una
      // credencial equivocada desde el panel.
      const previous=await api('/api/ntrip/input');
      if(previous.enabled || previous.state!=='stopped'){
        text('device-ntrip-state','Cerrando la conexión anterior…');
        await api('/api/ntrip/input','POST',{action:'stop'});
        for(let i=0;i<20;++i){
          await new Promise(resolve=>setTimeout(resolve,150));
          if((await api('/api/ntrip/input')).state==='stopped')break;
        }
      }
      await api('/api/gnss/control','POST',{action:'query'});
      let modeConfirmed=false;
      for(let i=0;i<25;++i){
        await new Promise(resolve=>setTimeout(resolve,200));const control=await api('/api/gnss/control');
        if(control.state==='confirmed'){modeConfirmed=control.mode==='MODE ROVER SURVEY';break;}
        if(control.state!=='running')throw new Error(control.error||'No se confirmó el GPS');
      }
      if(!modeConfirmed)throw new Error('Configura y confirma modo rover antes de conectar');
      const r=await api('/api/ntrip/input','POST',{action:'start',host:$('device-host').value,port:Number($('device-port').value),mountpoint:$('device-mount').value,username:$('device-user').value,password:$('device-password').value});
      $('device-password').value='';text('device-ntrip-state',r.state);
    }catch(error){text('device-ntrip-state',error.message);}
  });
  $('device-ntrip-stop').addEventListener('click',async()=>{
    try{await api('/api/ntrip/input','POST',{action:'stop'});}catch(error){text('device-ntrip-state',error.message);}
  });
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
