import sys, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
S=sys.argv[1]; HERO=sys.argv[2]
def capa(i): return Image.open(f'{S}/p{i}.png').convert('RGB')
def coeffs(src,dst):
    A=[];B=[]
    for (x,y),(u,v) in zip(dst,src):
        A+=[[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]];B+=[u,v]
    return np.linalg.lstsq(np.array(A,float),np.array(B,float),rcond=None)[0]
def livro(img,w,tilt=0.10,esp=0.06,lado='d'):
    """capa com leve perspectiva + lombada + borda de páginas; retorna RGBA"""
    h=int(w*img.height/img.width); img=img.resize((w,h))
    e=int(w*esp); W=w+e; H=h+int(h*tilt)
    out=Image.new('RGBA',(W+40,H+40),(0,0,0,0))
    t=int(h*tilt/2)
    if lado=='d':
        dst=[(e,0),(W,t),(W,h-t+int(h*tilt)//2),(e,h)]
    else:
        dst=[(0,t),(w,0),(w,h),(0,h-t+int(h*tilt)//2)]
    dst=[(x+20,y+20) for x,y in dst]
    src=[(0,0),(w,0),(w,h),(0,h)]
    c=coeffs(src,dst)
    capa_t=img.convert('RGBA').transform(out.size,Image.PERSPECTIVE,tuple(c),Image.BICUBIC)
    d=ImageDraw.Draw(out)
    # lombada (lado esquerdo) e páginas (direita) simples
    if lado=='d':
        d.polygon([(20,20+4),(e+20,20),(e+20,h+20),(20,h+20-4)],fill=(25,20,18,255))
        d.polygon([(W+20,t+20),(W+20+6,t+26),(W+26,h-t+int(h*tilt)//2+14),(W+20,h-t+int(h*tilt)//2+20)],fill=(235,228,215,255))
    out.alpha_composite(capa_t)
    # sombra
    sh=Image.new('RGBA',out.size,(0,0,0,0)); ImageDraw.Draw(sh).rectangle([30,40,out.width-10,out.height-5],fill=(0,0,0,170))
    sh=sh.filter(ImageFilter.GaussianBlur(18))
    base=Image.new('RGBA',(out.width+40,out.height+40),(0,0,0,0))
    base.alpha_composite(sh,(25,25)); base.alpha_composite(out,(0,0))
    return base
def fundo(N):
    bg=Image.open(HERO).convert('RGB').resize((N,N))
    bg=bg.filter(ImageFilter.GaussianBlur(14)); bg=ImageEnhance.Brightness(bg).enhance(0.35)
    bg=bg.convert('RGBA')
    sol=Image.new('RGBA',(N,N),(0,0,0,0)); ImageDraw.Draw(sol).ellipse([N*0.14,N*0.10,N*0.86,N*0.82],fill=(196,30,38,235))
    sol=sol.filter(ImageFilter.GaussianBlur(6)); bg.alpha_composite(sol)
    vin=Image.new('L',(N,N),0); ImageDraw.Draw(vin).ellipse([-N*0.2,-N*0.2,N*1.2,N*1.2],fill=255)
    vin=vin.filter(ImageFilter.GaussianBlur(N//6))
    escuro=Image.new('RGBA',(N,N),(10,9,8,255)); bg=Image.composite(bg,escuro,vin)
    return bg
F='/System/Library/Fonts/Supplemental/Georgia Bold.ttf'
def selo(N,txt1,txt2,x,y,r):
    s=Image.new('RGBA',(N,N),(0,0,0,0)); d=ImageDraw.Draw(s)
    d.ellipse([x-r,y-r,x+r,y+r],fill=(10,9,8,255),outline=(201,164,92,255),width=5)
    f1=ImageFont.truetype(F,int(r*0.62)); f2=ImageFont.truetype(F,int(r*0.24))
    d.text((x,y-r*0.12),txt1,font=f1,fill=(201,164,92,255),anchor='mm')
    d.text((x,y+r*0.42),txt2,font=f2,fill=(239,230,216,255),anchor='mm')
    return s
N=1080
# OPÇÃO A: 3 volumes em leque no centro + 4 bônus em fileira na frente
A=fundo(N)
for i,(dx,dy,ang) in enumerate([(-190,40,8),(190,40,-8),(0,0,0)]):
    idx=[1,3,2][i]
    b=livro(capa(idx),330,lado='d').rotate(ang,resample=Image.BICUBIC,expand=True)
    A.alpha_composite(b,(int(N/2-b.width/2+dx),int(60+dy)))
for k,i in enumerate([4,5,6,7]):
    b=livro(capa(i),165,tilt=0.06).rotate([6,2,-2,-6][k],resample=Image.BICUBIC,expand=True)
    A.alpha_composite(b,(int(40+k*250),int(N-b.height-20)))
fx=ImageDraw.Draw(A); fb=ImageFont.truetype(F,40)
fx.rounded_rectangle([N/2-150,N-372,N/2+150,N-318],radius=27,fill=(215,38,46,255)); fx.text((N/2,N-345),'+ 4 BÔNUS',font=fb,fill='white',anchor='mm')
A.alpha_composite(selo(N,'365','RECEITAS',N-150,170,105))
A.convert('RGB').save(f'{S}/opcaoA.jpg',quality=88)
# OPÇÃO B: livro principal grande à esquerda + pilha de bônus à direita
B=fundo(N)
pil=[4,5,6,7]
for k,i in enumerate(pil):
    b=livro(capa(i),240,tilt=0.05).rotate(-4+k*3,resample=Image.BICUBIC,expand=True)
    B.alpha_composite(b,(int(560+k*55),int(150+k*150)))
b=livro(capa(1),470,tilt=0.12).rotate(4,resample=Image.BICUBIC,expand=True)
B.alpha_composite(b,(40,110))
#B.alpha_composite(selo(N,'365','RECEITAS',430,170,95))
d=ImageDraw.Draw(B); d.rounded_rectangle([600,N-110,1040,N-50],radius=30,fill=(215,38,46,255)); d.text((820,N-80),'+ 4 LIVROS BÔNUS',font=ImageFont.truetype(F,34),fill='white',anchor='mm')
B.convert('RGB').save(f'{S}/opcaoB.jpg',quality=88)
