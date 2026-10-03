// Preflight del panel real: un manifiesto editado no autoriza otra placa.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const hardware='tresvizo-thingplus-s3-4m-v1';
async function attempt(board,validIdentity=true) {
  const bytes=Buffer.alloc(2048);
  if(validIdentity) bytes.write('TVZFWID1',288);
  bytes.write(board,320);
  bytes.write('TVZSIG01',bytes.length-72);
  const image=new Blob([bytes]);
  const manifest=new Blob([JSON.stringify({hardware_id:hardware,size:image.size,sha256:'a'.repeat(64)})]);
  const nodes={};let handler,starts=0;
  function $(id){return nodes[id]??= {textContent:'',addEventListener:(event,fn)=>{if(id==='update-form' && event==='submit')handler=fn;}};}
  $('update-image').files=[image];$('update-manifest').files=[manifest];
  const api=async (route)=>{
    if(route==='/api/update')return {hardware_id:hardware,signature_required:true,state:'idle',max_image_bytes:1966080};
    if(route==='/api/update/begin'){++starts;throw new Error('Fin del banco antes de escribir flash');}
    throw new Error('Ruta inesperada: '+route);
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../firmware/esp32/web/update.js'),'utf8'),{
    $,api,text:(id,value)=>{$(id).textContent=value;},window:{addEventListener(){}},setTimeout(){},Uint8Array,Blob,
  });
  await new Promise(setImmediate);
  await handler({preventDefault(){}});
  return starts;
}
(async()=>{
  assert.equal(await attempt('tresvizo-esp32s3-4m-v1'),0);
  assert.equal(await attempt(hardware,false),0);
  assert.equal(await attempt('x'.repeat(48)),0);
  assert.equal(await attempt(hardware),1);
  console.log('Panel OTA: placa correcta admitida; Tiny, identidad ausente y truncada rechazadas antes de begin.');
})().catch(error=>{console.error(error);process.exitCode=1;});
