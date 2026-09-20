"""Modelo eléctrico Rev A. Señales externas por nombre; sin GPIO ESP inventados."""
from pathlib import Path
from collections import defaultdict
import json
BASE=Path(__file__).resolve().parents[1]/'rev-a'
parts=[]; models={}; refs=defaultdict(int)
def model(name,pins,fp,mpn,ds=''):
    models[name]=dict(pins={str(n):[label,typ] for n,label,typ in pins},footprint=fp,mpn=mpn,datasheet=ds)
def part(kind,section,nets,value=None,ref=None,at=None,side='F',dnp=False,reason=''):
    m=models[kind]; prefix='U'
    if kind in ['R','C','L','SW','LED','D','F','J2','J16','FPC','USB','TP','SJ','NFET','PFET','FET_PWR']:
        prefix={'J2':'J','J16':'J','FPC':'J','USB':'J','NFET':'Q','PFET':'Q','FET_PWR':'Q','SJ':'JP'}.get(kind,kind)
    if not ref: refs[prefix]+=1;ref=prefix+str(refs[prefix])
    else: refs[prefix]=max(refs[prefix],int(''.join(c for c in ref if c.isdigit()) or '0'))
    p=dict(reference=ref,model=kind,section=section,pins={str(k):v for k,v in nets.items()},value=value or m['mpn'],footprint=m['footprint'],mpn=m['mpn'],datasheet=m['datasheet'],placement=at,side=side,dnp=dnp,reason=reason)
    assert set(p['pins'])==set(m['pins']),(ref,kind,set(m['pins'])-set(p['pins']))
    parts.append(p);return ref
SOT5='Package_TO_SOT_SMD:SOT-23-5';SOT6='Package_TO_SOT_SMD:SOT-23-6'
def ti(p):return 'https://www.ti.com/lit/ds/symlink/'+p+'.pdf'
def ic(n,names,fp,mpn,ds):model(n,[(i+1,a,b) for i,(a,b) in enumerate(names)],fp,mpn,ds)
def pins(seq):return [(x,'passive') for x in seq.split()]
for n in ['R','C','L','SW','LED','D','F','SJ']:
    fp={'R':'Resistor_SMD:R_0603_1608Metric','C':'Capacitor_SMD:C_0603_1608Metric','L':'Inductor_SMD:L_Coilcraft_XAL4020-XXX','SW':'Button_Switch_SMD:SW_SPST_TL3305A','LED':'LED_SMD:LED_0603_1608Metric','D':'Diode_SMD:D_SOD-323','F':'Fuse:Fuse_1206_3216Metric','SJ':'Jumper:SolderJumper-2_P1.3mm_Open_Pad1.0x1.5mm'}[n]
    ic(n,pins('1 2'),fp,{'SW':'TL3305AF160QG','L':'XAL4020-102MEC','LED':'LTST-C190KGKT','D':'BAT54WS-7-F','F':'0466002.NRHF','SJ':'OPEN'}.get(n,'')) if False else None
    model(n,[(1,'K' if n in ['LED','D'] else '1','passive'),(2,'A' if n in ['LED','D'] else '2','passive')],fp,{'SW':'TL3305AF160QG','L':'XAL4020-102MEC','LED':'LTST-C190KGKT','D':'BAT54WS-7-F','F':'0466002.NRHF','SJ':'OPEN'}.get(n,''))
model('TP',[(1,'TP','passive')],'TestPoint:TestPoint_Pad_D1.0mm','TestPoint')
model('NFET',[(1,'G','input'),(2,'S','passive'),(3,'D','passive')],'Package_TO_SOT_SMD:SOT-23','AO3400A','https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf')
model('FET_PWR',[(1,'D','passive'),(2,'D','passive'),(3,'D','passive'),(4,'S','passive'),(5,'S','passive'),(6,'G','input'),(7,'S_EP','passive'),(8,'D_EP','passive')],'Power:CSD13202Q2','CSD13202Q2',ti('csd13202q2'))
ic('LDO', [('IN','power_in'),('GND','power_in'),('EN','input'),('NC','no_connect'),('OUT','power_out')],SOT5,'TLV75530PDBVR',ti('tlv755p'))
ic('BQ24074', [('TS','passive'),('BAT','passive'),('BAT','passive'),('CE_N','input'),('EN2','input'),('EN1','input'),('PGOOD_N','open_collector'),('GND','power_in'),('CHG_N','open_collector'),('OUT','power_out'),('OUT','passive'),('ILIM','passive'),('IN','power_in'),('TMR','passive'),('ITERM','passive'),('ISET','passive'),('EP','power_in')],'Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.68x1.68mm','BQ24074RGTR',ti('bq24074'))
ic('BQ29700', [('NC','no_connect'),('COUT','output'),('DOUT','output'),('VSS','power_in'),('BAT','power_in'),('V_MINUS','passive')],'Package_SON:WSON-6_1.5x1.5mm_P0.5mm','BQ29700DSER',ti('bq2970'))
ic('BOOST', [('FB','passive'),('EN','input'),('VIN','power_in'),('GND','power_in'),('SW','passive'),('VOUT','power_out')],'Package_TO_SOT_SMD:SOT-563','TPS61023DRLR',ti('tps61023'))
ic('LTC2954', [('VIN','power_in'),('PB_N','input'),('ONT','passive'),('GND','power_in'),('INT_N','open_collector'),('EN','open_collector'),('PDT','passive'),('KILL','input')],'Package_TO_SOT_SMD:TSOT-23-8','LTC2954ITS8-1#TRMPBF','https://www.analog.com/media/en/technical-documentation/data-sheets/2954fb.pdf')
ic('SUPERVISOR', [('RESET_N','open_collector'),('GND','power_in'),('MR_N','input'),('CT','passive'),('SENSE','passive'),('VDD','power_in')],SOT6,'TPS3808G01DBVR',ti('tps3808'))
ic('MAX17048', [('CTG','power_in'),('CELL','passive'),('VDD','power_in'),('GND','power_in'),('ALERT_N','open_collector'),('QSTRT','input'),('SCL','input'),('SDA','bidirectional'),('EP','power_in')],'Package_DFN_QFN:TDFN-8-1EP_2x2mm_P0.5mm_EP0.8x1.2mm','MAX17048G+T10','https://www.analog.com/media/en/technical-documentation/data-sheets/MAX17048-MAX17049.pdf')
ic('GAUGE_SWITCH', [('SEL1','input'),('SH','passive'),('D1','passive'),('SEL2','input'),('S2','passive'),('D2','passive'),('GND','power_in'),('D3','passive'),('S3','passive'),('SEL3','input'),('D4','passive'),('S4','passive'),('SEL4','input'),('VDD','power_in')],'Package_SO:TSSOP-14_4.4x5mm_P0.65mm','TMUX1511PWR',ti('tmux1511'))
ic('CC', [('CC1','bidirectional'),('CC2','bidirectional'),('PORT','input'),('VBUS_DET','passive'),('ADDR','passive'),('OUT3','open_collector'),('OUT1','open_collector'),('OUT2','open_collector'),('ID','open_collector'),('GND','power_in'),('EN_N','input'),('VDD','power_in')],'Package_DFN_QFN:Texas_X2QFN-12_1.6x1.6mm_P0.4mm','TUSB320LAIRWBR',ti('tusb320lai'))
model('USB_LIMIT', [('A1','ON','input'),('A2','FLT_N','open_collector'),('B1','VIN','power_in'),('B2','VOUT','power_out'),('C1','GND','power_in'),('C2','ILIM','passive')],'Power:TPS22950_YBH','TPS22950YBHR',ti('tps22950'))
ic('USB_SWITCH', [('OE','input'),('HSD+','bidirectional'),('D+','bidirectional'),('GND','power_in'),('D-','bidirectional'),('HSD-','bidirectional'),('NC','no_connect'),('VCC','power_in')],'Package_DFN_QFN:Texas_UQFN-8_1.5x1.5mm_P0.5mm','TS3USB31ERSER',ti('ts3usb31e'))
ic('USB_ESD',pins('IO1 GND IO2 IO2 VBUS IO1'),SOT6,'USBLC6-2SC6','https://www.st.com/resource/en/datasheet/usblc6-2.pdf')
for name,mpn,inputs in [('AND','SN74LVC1G08DBVR',True),('OR','SN74LVC1G32DBVR',True),('NAND','SN74LVC1G00DBVR',True),('NOT','SN74LVC1G04DBVR',False),('BUF','SN74LVC1G17DBVR',False)]:
    ic(name,[(('A' if inputs else 'NC'),('input' if inputs else 'no_connect')),('B' if inputs else 'A','input'),('GND','power_in'),('Y','output'),('VCC','power_in')],SOT5,mpn,ti(mpn.split('DBV')[0].lower()))
model('USB', [(p,p,'passive') for p in ['A1','A4','A5','A6','A7','A8','A9','A12','B1','B4','B5','B6','B7','B8','B9','B12','SH']],'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12','TYPE-C-31-M-12','https://www.lcsc.com/datasheet/C165948.pdf')
model('J2',[(1,'1','passive'),(2,'2','passive')],'Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal','S2B-PH-SM4-TB(LF)(SN)','https://www.jst-mfg.com/product/pdf/eng/ePH.pdf')
model('J_NTC',[(1,'NTC','passive'),(2,'GND','passive')],'Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal','SM02B-SRSS-TB(LF)(SN)','https://www.jst-mfg.com/product/pdf/eng/eSH.pdf')
model('J16',[(i,str(i),'passive') for i in range(1,15)],'Connector_JST:JST_SH_SM14B-SRSS-TB_1x14-1MP_P1.00mm_Horizontal','SM14B-SRSS-TB(LF)(SN)','https://www.jst-mfg.com/product/pdf/eng/eSH.pdf')
model('FPC',[(i,str(i),'passive') for i in range(1,9)],'Connector_FFC-FPC:Hirose_FH12-8S-0.5SH_1x08-1MP_P0.50mm_Horizontal','FH12-8S-0.5SH(55)','https://www.hirose.com/product/series/FH12')
model('CC_ESD',[(1,'IO','passive'),(2,'GND','passive')],'Diode_SMD:D_SOD-882','PESD5V0S1UL,315','https://assets.nexperia.com/documents/data-sheet/PESD5V0S1UL.pdf')
def two(kind,val,a,b,sec,**kw):return part(kind,sec,{1:b,2:a} if kind in ['LED','D'] else {1:a,2:b},val,**kw)
def r(val,a,b,sec,**kw):return two('R',val,a,b,sec,**kw)
def c(val,a,b,sec,**kw):return two('C',val,a,b,sec,**kw)
def logic(kind,a,b,out,sec,vcc='AON_3V0',**kw):return part(kind,sec,{1:a if kind in ['AND','OR','NAND'] else None,2:b if kind in ['AND','OR','NAND'] else a,3:'GND',4:out,5:vcc},**kw)
def dec(net,sec):return c('100n',net,'GND',sec)
def sup(name,sense,power,sec,ct=None,mr=None,at=None):
    u=part('SUPERVISOR',sec,{1:name,2:'GND',3:mr or power,4:ct,5:sense,6:power},at=at);r('10k' if name=='USB_VALID_AON' else '47k' if name in ['SYS_OK','TINY_OK'] else '100k',power,name,sec);dec(power,sec);return u
# 01. USB-C, límite de corriente y detección CC.
s='01_usb_power'
part('USB',s,{p:('USB_VBUS' if p in ['A4','A9','B4','B9'] else 'GND' if p in ['A1','A12','B1','B12','SH'] else 'USB_CC1' if p=='A5' else 'USB_CC2' if p=='B5' else 'HOST_USB_P' if p in ['A6','B6'] else 'HOST_USB_N' if p in ['A7','B7'] else None) for p in models['USB']['pins']},ref='J1',at=[20,3.2,180])
for line in ['USB_CC1','USB_CC2']:
    part('CC_ESD',s,{1:line,2:'GND'})
# Fuses don't replace semiconductor overvoltage protection.
two('F','1.5A fast fuse','USB_VBUS','USB_FUSED',s,ref='F1')
c('100n','USB_FUSED','GND',s)
r('3.3k','USB_VBUS','GND',s,reason='Descarga de VBUS; carga continua USB contabilizada')
part('LDO',s,{1:'USB_FUSED',2:'GND',3:'USB_FUSED',4:None,5:'USB_3V3'},value='TLV75533PDBVR')
c('1u','USB_FUSED','GND',s);c('1u','USB_3V3','GND',s)
part('CC',s,{1:'USB_CC1',2:'USB_CC2',3:'GND',4:'CC_VBUS_DET',5:None,6:None,7:'CC_HIGH_N',8:None,9:None,10:'GND',11:'GND',12:'USB_3V3'})
r('887k','USB_VBUS','CC_VBUS_DET',s);r('47k','USB_3V3','CC_HIGH_N',s);dec('USB_3V3',s)
logic('NOT','CC_HIGH_N',None,'CC_HIGH',s,'USB_3V3')
logic('NOT','USB_SUSPEND',None,'USB_AWAKE',s,'USB_3V3');r('100k','USB_SUSPEND','GND',s)
logic('OR','CC_HIGH','USB_AWAKE','USB_PATH_EN',s,'USB_3V3')
part('USB_LIMIT',s,{'A1':'USB_PATH_EN','A2':'USB_FAULT_N','B1':'USB_FUSED','B2':'USB_INPUT_PROTECTED','C1':'GND','C2':'USB_ILIM'})
r('19.1k','USB_ILIM','GND',s);r('1.21k','USB_ILIM','ILIM_FAST_RETURN',s)
part('NFET',s,{1:'CC_HIGH',2:'GND',3:'ILIM_FAST_RETURN'});r('100k','CC_HIGH','GND',s)
r('47k','USB_3V3','USB_FAULT_N',s)
# 02. Battery protection independent of unspecified pack PCB.
s='02_battery_charger'
part('J2',s,{1:'CELL_P',2:'CELL_N'},ref='J2',at=[5,30,90],reason='Conector de nuestra PCB; no asumir polaridad del cable comercial')
part('BQ29700',s,{1:None,2:'BAT_CHG_GATE',3:'BAT_DSG_GATE',4:'CELL_N',5:'PROT_BAT',6:'PROT_VMINUS'})
r('330','CELL_P','PROT_BAT',s);c('100n','PROT_BAT','CELL_N',s);r('2.2k','GND','PROT_VMINUS',s)
part('FET_PWR',s,{1:'BAT_FET_MID',2:'BAT_FET_MID',3:'BAT_FET_MID',4:'CELL_N',5:'CELL_N',6:'BAT_DSG_GATE',7:'CELL_N',8:'BAT_FET_MID'})
part('FET_PWR',s,{1:'BAT_FET_MID',2:'BAT_FET_MID',3:'BAT_FET_MID',4:'BAT_SHUNT_N',5:'BAT_SHUNT_N',6:'BAT_CHG_GATE',7:'BAT_SHUNT_N',8:'BAT_FET_MID'})
r('10m 1% 0.5W','BAT_SHUNT_N','GND',s)
two('F','2A fast fuse','CELL_P','PACK_P',s,ref='F2')
part('BQ24074',s,{1:'BAT_NTC',2:'PACK_P',3:'PACK_P',4:'GND',5:'USB_3V3',6:'GND',7:'USB_PGOOD_N',8:'GND',9:'CHG_N',10:'SYSTEM_POWER',11:'SYSTEM_POWER',12:'BQ_ILIM',13:'USB_INPUT_PROTECTED',14:'GND',15:None,16:'BQ_ISET',17:'GND'},at=[12,13,0])
r('1.78k','BQ_ISET','GND',s);r('1.47k','BQ_ILIM','GND',s);r('47k','AON_3V0','USB_PGOOD_N',s)
c('1u','USB_INPUT_PROTECTED','GND',s);c('10u','PACK_P','GND',s);c('22u','SYSTEM_POWER','GND',s)
part('J_NTC',s,{1:'BAT_NTC',2:'GND'},value='NTC externo 10k',ref='J3',at=[5,21,90])
# Charge LED fed after input limit, included in current budget.
r('2.2k','USB_INPUT_PROTECTED','CHG_LED_A',s);two('LED','CHARGE green','CHG_LED_A','CHG_N',s)
# 03. Core power, independent undervoltage trip, pushbutton latch.
s='03_power_control'
part('LDO',s,{1:'SYSTEM_POWER',2:'GND',3:'SYSTEM_POWER',4:None,5:'AON_3V0'})
c('1u','SYSTEM_POWER','GND',s);c('1u','AON_3V0','GND',s)
r('665k','SYSTEM_POWER','SYS_SENSE',s);r('100k','SYS_SENSE','GND',s);c('1n','SYS_SENSE','GND',s)
sup('SYS_OK','SYS_SENSE','AON_3V0',s,ct='SYS_OK_CT');r('100k','AON_3V0','SYS_OK_CT',s)
part('LTC2954',s,{1:'SYSTEM_POWER',2:'BUTTON_N',3:'PWR_ONT',4:'GND',5:'POWER_REQUEST_N',6:'LATCH_EN',7:'PWR_PDT',8:'KILL_SAFE'},at=[9,6,0])
dec('SYSTEM_POWER',s);c('47n','PWR_ONT','GND',s);c('1u timing','PWR_PDT','GND',s);c('390n timing','PWR_PDT','GND',s)
r('100k','AON_3V0','LATCH_EN',s);r('47k','TINY_3V3','POWER_REQUEST_N',s)
two('SW','POWER','BUTTON_N','GND',s,ref='SW1',at=[33,4,0])
sup('BOOT_DONE','LATCH_EN','AON_3V0',s,ct='BOOT_CT');c('1u','BOOT_CT','GND',s)
logic('NOT','BOOT_DONE',None,'BOOT_WINDOW',s)
r('100k','POWER_HOLD','GND',s)
two('SJ','PROGRAM_MODE','USB_VALID_AON','PROGRAM_HOLD',s);r('100k','PROGRAM_HOLD','GND',s)
logic('OR','BOOT_WINDOW','POWER_HOLD','KEEP_1',s)
logic('OR','KEEP_1','PROGRAM_HOLD','KEEP_ALIVE',s)
logic('AND','SYS_OK','KEEP_ALIVE','KILL_SAFE',s)
logic('AND','SYS_OK','LATCH_EN','BOOST_EN',s)
# 04. Boost rail; all peripherals switch together to avoid UART phantom supply.
s='04_5v_outputs'
part('BOOST',s,{1:'BOOST_FB',2:'BOOST_EN',3:'SYSTEM_POWER',4:'GND',5:'BOOST_SW',6:'SYSTEM_5V'},at=[23,13,0])
two('L','1uH XAL4020','SYSTEM_POWER','BOOST_SW',s,at=[23,9,0])
c('10u','SYSTEM_POWER','GND',s);c('22u','SYSTEM_5V','GND',s);c('22u','SYSTEM_5V','GND',s)
r('732k 0.1%','SYSTEM_5V','BOOST_FB',s);r('100k 0.1%','BOOST_FB','GND',s);r('100k','BOOST_EN','GND',s)
part('J2',s,{1:'SYSTEM_5V',2:'GND'},ref='J4',value='GNSS 5V',at=[35,27,270])
# 05. Native USB sensing/ESD/isolation. No external DTR/RTS.
s='05_usb_native'
part('USB_ESD',s,{1:'HOST_USB_P',2:'GND',3:'HOST_USB_N',4:'HOST_USB_N',5:'USB_VBUS',6:'HOST_USB_P'},at=[20,8,0])
# TPS3808 immediately asserts reset below threshold; 20 ms qualification only on rising.
r('101k 0.1% 10ppm','USB_VBUS','VBUS_SENSE',s);r('10k 0.1% 10ppm','VBUS_SENSE','GND',s)
sup('USB_VALID_AON','VBUS_SENSE','AON_3V0',s)
r('649k 0.1%','TINY_3V3','TINY_SENSE',s);r('100k 0.1%','TINY_SENSE','GND',s)
sup('TINY_OK','TINY_SENSE','TINY_3V3',s)
logic('NAND','USB_VALID_AON','TINY_OK','USB_DISCONNECT',s,'TINY_3V3')
r('47k','TINY_3V3','USB_DISCONNECT',s)
part('USB_SWITCH',s,{1:'USB_DISCONNECT',2:'TINY_USB_P',3:'HOST_USB_P',4:'GND',5:'HOST_USB_N',6:'TINY_USB_N',7:None,8:'TINY_3V3'},at=[25,6,0]);dec('TINY_3V3',s)
logic('BUF','USB_VALID_AON',None,'USB_VBUS_VALID',s,'TINY_3V3')
# Candidate assembly only: electrical mapping matches official Tiny-Adapter, with cable validation required.
part('FPC',s,{1:'GND',2:'SYSTEM_5V',3:'TINY_RUN',4:'TINY_BOOT',5:'GND',6:'TINY_USB_P',7:'TINY_USB_N',8:'GND'},ref='J5',at=[25,31,0],dnp=True,reason='Candidato basado en adaptador oficial. No poblar antes de comprobar revisión/cable físico; no huella aprobada de la Tiny del usuario.')
for signal in ['TINY_RUN','TINY_BOOT']:
    two('SJ',signal,signal,'GND',s)
# 06. Gauge and isolation powered from the actual external MCU domain.
s='06_gauge'
part('MAX17048',s,{1:'GND',2:'PACK_P',3:'PACK_P',4:'GND',5:'GAUGE_ALERT_N',6:'GND',7:'GAUGE_SCL',8:'GAUGE_SDA',9:'GND'})
dec('PACK_P',s)
r('549k','PACK_P','PACK_SENSE',s);r('100k','PACK_SENSE','GND',s)
sup('GAUGE_VOLTAGE_OK','PACK_SENSE','AON_3V0',s)
logic('AND','GAUGE_VOLTAGE_OK','TINY_OK','GAUGE_EN',s,'TINY_3V3')
part('GAUGE_SWITCH',s,{1:'GAUGE_EN',2:'GAUGE_SDA',3:'I2C_SDA',4:'GAUGE_EN',5:'GAUGE_SCL',6:'I2C_SCL',7:'GND',8:'BATTERY_ALERT_N',9:'GAUGE_ALERT_N',10:'GAUGE_EN',11:None,12:None,13:'GND',14:'TINY_3V3'})
dec('TINY_3V3',s)
for net in ['I2C_SDA','I2C_SCL','BATTERY_ALERT_N']:r('4.7k' if 'I2C' in net else '47k','TINY_3V3',net,s)
# 07. External signals, indicators, service points. GPIO assignment is external firmware's job.
s='07_interfaces'
aux=['GND','TINY_3V3','POWER_HOLD','POWER_REQUEST_N','I2C_SDA','I2C_SCL','BATTERY_ALERT_N','USB_VBUS_VALID','USB_SUSPEND','RGB_R','RGB_G','RGB_B','GND','USB_FAULT_LOGIC_N']
part('J16',s,{i+1:net for i,net in enumerate(aux)},ref='J6',at=[20,24,0])
logic('BUF','USB_FAULT_N',None,'USB_FAULT_LOGIC_N',s,'TINY_3V3')
for col in ['R','G','B']:
    r('100k','RGB_'+col,'GND',s);part('NFET',s,{1:'RGB_'+col,2:'GND',3:'LED_'+col+'_K'})
    r('1k','SYSTEM_5V','LED_'+col+'_SUP',s);two('LED','STATUS '+col,'LED_'+col+'_SUP','LED_'+col+'_K',s)
for net in ['GND','PACK_P','SYSTEM_POWER','SYSTEM_5V','AON_3V0','USB_VBUS','BOOST_EN','KILL_SAFE','TINY_USB_P','TINY_USB_N']:
    part('TP',s,{1:net},value=net)
# Per-IC bypass caps, unless already represented nearby. These are real BOM items.
for p in parts.copy():
    if p['model'] in ['AND','OR','NAND','NOT','BUF']:
        dec(p['pins']['5'],p['section'])
# Generic part purchasing definitions; current/power-dependent exceptions explicit.
for p in parts:
    if p['model']=='LDO' and p['value'].startswith('TLV755'):p['mpn']=p['value']
    if p['model']=='R':
        if p['value'].startswith('10m'):
            p['footprint']='Resistor_SMD:R_1206_3216Metric';p['mpn']='WSL1206R0100FEA'
        else:
            raw=p['value'].split()[0].upper();unit=next((u for u in ['M','K'] if u in raw),'R');raw=raw.replace(unit,'');a,_,b=raw.partition('.');code=a+unit+b
            p['mpn']=('RT0603BRB07' if '10ppm' in p['value'] else 'RT0603BRD07' if '0.1%' in p['value'] else 'RC0603FR-07')+code+'L'
            p['datasheet']='https://yageogroup.com/download/specsheet/'+p['mpn'];p['reason']+='; 0.1W, tolerancia '+('0.1%' if '0.1%' in p['value'] else '1%')
    if p['model']=='C':
        if p['value'].startswith('22u'):p['footprint']='Capacitor_SMD:C_1206_3216Metric';p['mpn']='GRM31CR71A226KE15L'
        elif p['value'].startswith('10u'):p['footprint']='Capacitor_SMD:C_0805_2012Metric';p['mpn']='GRM21BR71A106KE51L'
        else:
            key=p['value'].split()[0]
            p['mpn']={'100n':'CC0603KRX7R9BB104','1n':'CC0603KRX7R9BB102','47n':'CC0603KRX7R9BB473','1u':'GRM188R71C105KA12D','390n':'GCM188R71C394KA55D'}[key]
            p['datasheet']=('https://yageogroup.com/download/specsheet/'+p['mpn'] if p['mpn'].startswith('CC') else 'https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/'+p['mpn'][:-1]+'-01.pdf')
    if p['model']=='F' and p['reference']=='F1':p['mpn']='046601.5NRHF';p['value']='1.5A fast'
    if p['model']=='F':p['datasheet']='https://www.littelfuse.com/products/fuses-overcurrent-protection/fuses/surface-mount-fuses/thin-film-chip-fuses/466'
    if p['model']=='LED':
        if p['value']=='STATUS R':p['mpn']='LTST-C190KRKT'
        if p['value']=='STATUS B':p['mpn']='LTST-C190TBKT'
BASE.mkdir(parents=True,exist_ok=True)
(BASE/'circuit.json').write_text(json.dumps(dict(revision='A-prototype',models=models,components=parts),ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':print(len(parts),'components',len({p['section'] for p in parts}),'sheets')
