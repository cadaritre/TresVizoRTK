"""Cierre geométrico de conexiones: búsqueda A* con obstáculos reales de KiCad."""
from pathlib import Path
import pcbnew as k,json,math,heapq,collections,time,sys
B=Path(__file__).resolve().parents[1]/'rev-a';b=k.LoadBoard(str(B/'power-board.kicad_pcb'));j=json.loads((B/'review/drc.json').read_text());netname='GND' if len(sys.argv)>1 and sys.argv[1]=='gnd' else 'USB_PATH_EN';step=.05
layers=[k.F_Cu,k.In2_Cu,k.B_Cu]
def mm(x):return k.FromMM(x)
def vec(x,y):return k.VECTOR2I(mm(x),mm(y))
# The two same-net stitching vias overlapped; retain the one touching both escape stubs.
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA) and abs(k.ToMM(t.GetPosition().x)-18.8758)<.001 and abs(k.ToMM(t.GetPosition().y)-17.0008)<.001:b.RemoveNative(t)
items=list(b.GetTracks())+[p for f in b.GetFootprints() for p in f.Pads()]
shapes={};buckets=collections.defaultdict(list)
for o in items:
 if o.GetNetname()==netname:continue
 for li,ly in enumerate(layers):
  if not o.IsOnLayer(ly):continue
  sh=o.GetEffectiveShape(ly) if isinstance(o,k.PAD) else o.GetEffectiveShape()
  bb=sh.BBox();minx=math.floor(k.ToMM(bb.GetLeft())-.5);maxx=math.floor(k.ToMM(bb.GetRight())+.5);miny=math.floor(k.ToMM(bb.GetTop())-.5);maxy=math.floor(k.ToMM(bb.GetBottom())+.5)
  for xx in range(minx,maxx+1):
   for yy in range(miny,maxy+1):buckets[(li,xx,yy)].append(sh)
cache={};vcache={}
def clear(x,y,l,rad=.232):
 key=(x,y,l)
 if rad==.232 and key in cache:return cache[key]
 px=x*step;py=y*step
 ok=.5<px<44.5 and .5<py<39.5
 if ok:
  p=vec(px,py)
  for sh in buckets.get((l,math.floor(px),math.floor(py)),[]):
   if sh.Collide(p,mm(rad)):ok=False;break
 if rad==.232:cache[key]=ok
 return ok
def viaclear(x,y):
 if (x,y) not in vcache:vcache[(x,y)]=all(clear(x,y,l,.365) for l in range(3))
 return vcache[(x,y)]
start=(round(8.8/step),round(11.1/step),0);goal=(round(14.9107/step),round(23.4146/step),1)
if netname=='GND':start=(round(15.775/step),round(7/step),2);goal=(round(14.2081/step),round(8.2933/step),2)
def heuristic(n):return math.hypot(n[0]-goal[0],n[1]-goal[1])
q=[(heuristic(start),0,start)];dist={start:0};prev={};finished=False;count=0;t0=time.time()
while q:
 _,cost,n=heapq.heappop(q)
 if cost!=dist[n]:continue
 if n==goal:finished=True;break
 count+=1;x,y,l=n
 if count%100000==0:print('Expanded',count,'elapsed',round(time.time()-t0),flush=True)
 neighbors=[]
 for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
  nn=(x+dx,y+dy,l)
  if not clear(*nn):continue
  if dx and dy and not(clear(x+dx,y,l) and clear(x,y+dy,l)):continue
  neighbors.append((nn,math.sqrt(2) if dx and dy else 1))
 if viaclear(x,y):
  for ll in range(3):
   if ll!=l:neighbors.append(((x,y,ll),40))
 for nn,weight in neighbors:
  d=cost+weight
  if d<dist.get(nn,1e99):dist[nn]=d;prev[nn]=n;heapq.heappush(q,(d+heuristic(nn),d,nn))
 if count>800000:break
assert finished,('No route',count)
path=[goal]
while path[-1]!=start:path.append(prev[path[-1]])
path.reverse();ni=next(n for n in b.GetNetsByNetcode().values() if n.GetNetname()==netname)
# Compress collinear steps; retain all layer changes and diagonals.
points=[path[0]];direction=None
for i in range(1,len(path)):
 d=tuple(path[i][j]-path[i-1][j] for j in range(3))
 if direction is not None and d!=direction:points.append(path[i-1])
 direction=d
points.append(path[-1]);seen=set()
for a,c in zip(points,points[1:]):
 if a[2]!=c[2]:
  if (a[0],a[1]) in seen:continue
  seen.add((a[0],a[1]));v=k.PCB_VIA(b);v.SetPosition(vec(a[0]*step,a[1]*step));v.SetWidth(mm(.45));v.SetDrill(mm(.2));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(ni);v.SetFrontTentingMode(k.TENTING_MODE_TENTED);v.SetBackTentingMode(k.TENTING_MODE_TENTED);b.Add(v)
 elif a!=c:
  tr=k.PCB_TRACK(b);tr.SetStart(vec(a[0]*step,a[1]*step));tr.SetEnd(vec(c[0]*step,c[1]*step));tr.SetWidth(mm(.18));tr.SetLayer(layers[a[2]]);tr.SetNet(ni);b.Add(tr)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(B/'power-board.kicad_pcb'),b)
print('Routed',netname,'nodes',count,'segments',len(points)-1,'vias',len(seen),'seconds',round(time.time()-t0,2))
