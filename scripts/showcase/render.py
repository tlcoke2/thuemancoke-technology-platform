"""Render the AI-assisted, illustrated TCL showcase. No private or clinical data.
Public-site captures supplied by the owner-authorised browser workflow.
Requires Pillow and ffmpeg; output is a silent, captioned 34-second H.264 film.
"""
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
import math, subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'frontend/public/media/showcase';OUT.mkdir(parents=True,exist_ok=True)
W,H,FPS,DURATION=1280,720,20,34
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
fonts={}
def font(n,b=False):
 k=(n,b)
 if k not in fonts:fonts[k]=ImageFont.truetype(BOLD if b else FONT,n)
 return fonts[k]
CYAN='#38d9ef';WHITE='#f3f8ff';MUTED='#a7bed1';BG='#071522'
base=Image.new('RGB',(W,H));p=base.load()
for y in range(H):
 for x in range(W):
  v=max(0,1-math.hypot((x-1080)/1100,(y-200)/850));p[x,y]=(7+int(v*5),17+int(v*25),29+int(v*35))
def text(d,xy,s,n=24,fill=WHITE,b=False):d.text(xy,s,font=font(n,b),fill=fill)
def panel(d,box,fill='#102b40',outline='#204459',r=18):d.rounded_rectangle(box,r,fill=fill,outline=outline,width=1)
def ease(v):v=max(0,min(1,v));return 1-(1-v)**3
sources={}
for name in ['healthy','gordon']:
 capture=Path(__file__).parent/(name+'-source.jpg')
 im=Image.open(capture if capture.exists() else OUT/(name+'-website.webp')).convert('RGB')
 im=im.crop((0,0,min(1330,im.width),min(840,im.height)))
 sources[name]=im
 im.thumbnail((960,610));im.save(OUT/(name+'-website.webp'),quality=78,method=6)
logo=Image.open(ROOT/'frontend/public/images/thueman-coke-logo.png').convert('RGB')
logo=ImageOps.fit(logo,(530,354),method=Image.Resampling.LANCZOS)
def frame(t):
 im=base.copy();d=ImageDraw.Draw(im)
 for x in range(-80,1400,80):
  xx=x+int(t*6)%80;d.line((xx,120,xx,H),fill='#0d283a')
 for y in range(120,720,80):d.line((0,y,W,y),fill='#0d283a')
 d.line((64,93,1216,93),fill='#254151',width=1)
 text(d,(64,43),'THUEMAN COKE LIMITED',20,b=True)
 text(d,(910,45),'SOFTWARE  /  WEBSITES',16,fill=CYAN)
 idx=0 if t<4 else 1 if t<10 else 2 if t<16 else 3 if t<22 else 4 if t<28 else 5
 starts=[0,4,10,16,22,28];local=t-starts[idx];a=ease(local/.7);dy=int((1-a)*22)
 if idx==0:
  text(d,(64,180+dy),'Ideas into',64,b=True);text(d,(64,259+dy),'working technology.',59,fill=CYAN,b=True)
  text(d,(66,365+dy),'Software. Websites. Connected business.',26)
  text(d,(66,418+dy),'Built around the way you work.',25,fill=MUTED)
  im.paste(logo,(715,165));d=ImageDraw.Draw(im)
 elif idx==1:
  text(d,(64,136+dy),'Plan. Build. Test. Launch.',47,b=True)
  text(d,(66,204+dy),'An illustrated view of our engineering process.',24,fill=MUTED)
  labels=['Discover','Design','Build','Verify']
  for j,label in enumerate(labels):
   x=64+j*291;active=local>(j*.85)
   panel(d,(x,294,x+263,438),fill='#0f3146' if active else '#102334',outline=CYAN if active else '#254151')
   text(d,(x+22,313),f'0{j+1}',19,fill=CYAN);text(d,(x+22,360),label,30,b=True)
   if j<3:d.line((x+266,364,x+286,364),fill=CYAN,width=2)
  text(d,(64,488),'Requirements  >  Architecture  >  Code  >  Validation',24)
  d.rounded_rectangle((64,550,1216,559),4,fill='#1b3a4e')
  d.rounded_rectangle((64,550,64+int(1152*min(local/5,1)),559),4,fill=CYAN)
 elif idx==2:
  text(d,(64,145+dy),'TEC EPR',64,b=True)
  text(d,(64,232+dy),'Clinic workflows.',42,fill=CYAN,b=True)
  text(d,(64,289+dy),'Connected delivery.',42,fill=CYAN,b=True)
  text(d,(66,382),'From application development',25)
  text(d,(66,421),'to installation and licensing.',25,fill=MUTED)
  labels=['Patients','Appointments','Billing','Laboratory','Installation','Licensing']
  for j,label in enumerate(labels):
   x=730+(j%2)*235;y=170+(j//2)*127
   panel(d,(x,y,x+215,y+105),fill='#103448' if local>.35*j else '#102334')
   text(d,(x+18,y+19),f'0{j+1}',16,fill=CYAN);text(d,(x+18,y+55),label,21,b=True)
  text(d,(730,575),'WORKFLOW ILLUSTRATION',15,fill=MUTED)
 elif idx in [3,4]:
  healthy=idx==3;name='healthy' if healthy else 'gordon'
  text(d,(64,135+dy),'Websites that work for your business.',40,b=True)
  text(d,(64,201+dy),'Healthcare' if healthy else 'Professional services',24,fill=CYAN,b=True)
  text(d,(64,252+dy),'Healthy Concept' if healthy else 'Gordon & Co',37,b=True)
  text(d,(64,303+dy),'Medical Centre' if healthy else 'Legal Services',32,b=True)
  for j,line in enumerate(['Clear information.','Thoughtful design.','Easy next steps.']):text(d,(66,391+j*43),line,23,fill=MUTED)
  panel(d,(565,230,1216,620),fill='#eaf2f5',outline='#486678',r=14)
  for j,col in enumerate(['#fb7185','#fbbf24','#34d399']):d.ellipse((580+j*18,245,589+j*18,254),fill=col)
  text(d,(648,241),'healthyconceptmedical.com' if healthy else 'gordoncolegal.com',15,fill='#233b4a')
  pic=ImageOps.fit(sources[name],(627,342),method=Image.Resampling.LANCZOS,centering=(.5,.24))
  # Gentle screen movement; genuine public website capture, never a fake browser UI.
  im.paste(pic,(577,270));d=ImageDraw.Draw(im)
  text(d,(578,637),'LIVE WEBSITE EXAMPLE',15,fill=MUTED)
 else:
  text(d,(64,151+dy),'Your next chapter.',58,b=True)
  text(d,(64,229+dy),'Let’s build it.',70,fill=CYAN,b=True)
  text(d,(66,348),'Custom software  /  Websites  /  Client portals',28)
  text(d,(66,401),'UK  •  Europe  •  USA  •  Caribbean',24,fill=MUTED)
  panel(d,(64,489,815,565),fill='#39d9ef',outline=CYAN)
  text(d,(89,512),'www.thuemancokelimited.com',31,fill='#071522',b=True)
  text(d,(67,593),'Start your project with Thueman Coke Limited.',22)
 # Persistent captions and honest production label.
 d.rectangle((0,674,W,H),fill='#06111c')
 text(d,(64,689),'AI-assisted motion graphics • Illustrated build sequence • Public website examples',14,fill=MUTED)
 for j in range(6):
  x=1080+j*23;d.ellipse((x,692,x+8,700),fill=CYAN if idx==j else '#2c4557')
 # Fade in/out of each scene, preserving legibility during the hold.
 duration=[4,6,6,6,6,6][idx]
 alpha=min(1,local/.3,(duration-local)/.3)
 if alpha<1:im=Image.blend(base,im,max(0,alpha))
 return im
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'tcl-build-showcase.mp4')]
p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for i in range(FPS*DURATION):p.stdin.write(frame(i/FPS).tobytes())
p.stdin.close();assert p.wait()==0
frame(29.6).save(OUT/'tcl-build-showcase-poster.webp',quality=83,method=6)
# Review storyboard without changing the film.
board=Image.new('RGB',(960,540))
for j,t in enumerate([2,7,13,19,25,31]):board.paste(frame(t).resize((320,270)),((j%3)*320,(j//3)*270))
board.save(OUT/'storyboard.jpg',quality=90)
print('Rendered',OUT/'tcl-build-showcase.mp4',(OUT/'tcl-build-showcase.mp4').stat().st_size,'bytes')
