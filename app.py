import os
import json
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageEnhance, ImageOps, ImageDraw, ImageFont

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except Exception:
    BaseTk = tk.Tk
    DND_AVAILABLE = False

APP_TITLE = "Batch Watermark Tool Pro v3"
APP_DIR = Path.home() / ".batch_watermark_tool_v3"
SETTINGS_FILE = APP_DIR / "settings.json"
PRESETS_FILE = APP_DIR / "presets.json"
BRANDS_FILE = APP_DIR / "brands.json"
PROFILES_FILE = APP_DIR / "profiles.json"
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
RATIOS = {"原始比例": None, "1:1": (1,1), "4:5": (4,5), "3:4": (3,4), "16:9": (16,9), "9:16": (9,16), "2:3": (2,3), "3:2": (3,2)}
POSITIONS = ["左上","上中","右上","左中","置中","右中","左下","下中","右下"]

class App(BaseTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1420x860")
        self.minsize(1180,720)
        self.paths=[]
        self.watermark_path=None
        self.preview_photo=None
        self.preview_box=None
        self.cancelled=False
        self.output_dir=tk.StringVar(value=str(Path.home()/"Desktop"))
        self.wm_mode=tk.StringVar(value="九宮格")
        self.wm_position=tk.StringVar(value="右下")
        self.wm_scale=tk.DoubleVar(value=18)
        self.wm_opacity=tk.DoubleVar(value=70)
        self.wm_rotation=tk.DoubleVar(value=0)
        self.margin=tk.IntVar(value=24)
        self.free_x=tk.DoubleVar(value=.85)
        self.free_y=tk.DoubleVar(value=.85)
        self.tile_gap=tk.IntVar(value=80)
        self.text_enabled=tk.BooleanVar(value=False)
        self.text_value=tk.StringVar(value="© Brand")
        self.text_size=tk.IntVar(value=48)
        self.text_opacity=tk.DoubleVar(value=70)
        self.text_color="#ffffff"
        self.text_position=tk.StringVar(value="左下")
        self.output_ratio=tk.StringVar(value="原始比例")
        self.crop_x=tk.DoubleVar(value=.5)
        self.crop_y=tk.DoubleVar(value=.5)
        self.size_mode=tk.StringVar(value="百分比")
        self.resize_percent=tk.DoubleVar(value=100)
        self.long_edge=tk.IntVar(value=2048)
        self.allow_upscale=tk.BooleanVar(value=False)
        self.output_format=tk.StringVar(value="JPG")
        self.quality=tk.IntVar(value=92)
        self.preserve_exif=tk.BooleanVar(value=True)
        self.rename_enabled=tk.BooleanVar(value=False)
        self.rename_template=tk.StringVar(value="{name}_{index}")
        self.rename_start=tk.IntVar(value=1)
        self.rename_digits=tk.IntVar(value=3)
        self.conflict_mode=tk.StringVar(value="自動加序號")
        self.status=tk.StringVar(value="就緒")
        self.presets={}
        self.brands={}
        self.profiles={}
        self.profile_vars={}
        self._style(); self._ui(); self._load_all()

    def _style(self):
        self.configure(bg="#151515")
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except:pass
        for n in ["TFrame","TLabelframe","TLabel","TCheckbutton"]:
            s.configure(n,background="#1b1b1b",foreground="#f2f2f2")
        s.configure("TLabelframe.Label",background="#1b1b1b",foreground="#f2f2f2")
        s.configure("TButton",padding=6)
        s.configure("Accent.TButton",padding=9,font=("Segoe UI",10,"bold"))

    def _ui(self):
        root=ttk.Frame(self,padding=10); root.pack(fill="both",expand=True)
        left=ttk.Frame(root,width=320); left.pack(side="left",fill="y",padx=(0,10))
        center=ttk.Frame(root); center.pack(side="left",fill="both",expand=True,padx=(0,10))
        right=ttk.Frame(root,width=380); right.pack(side="right",fill="y")

        box=ttk.LabelFrame(left,text="圖片來源",padding=10); box.pack(fill="both",expand=True,pady=(0,10))
        r=ttk.Frame(box); r.pack(fill="x")
        ttk.Button(r,text="加入圖片",command=self.add_images).pack(side="left",fill="x",expand=True,padx=(0,3))
        ttk.Button(r,text="加入資料夾",command=self.add_folder).pack(side="left",fill="x",expand=True,padx=(3,0))
        ttk.Button(box,text="移除選取",command=self.remove_selected).pack(fill="x",pady=(6,0))
        ttk.Button(box,text="清空",command=self.clear).pack(fill="x",pady=(4,8))
        self.drop=tk.Label(box,text="拖曳圖片 / 資料夾到這裡" if DND_AVAILABLE else "可使用按鈕匯入",bg="#252525",fg="#ddd",height=3)
        self.drop.pack(fill="x",pady=(0,8))
        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES); self.drop.dnd_bind("<<Drop>>",self.on_drop)
        lf=ttk.Frame(box); lf.pack(fill="both",expand=True)
        self.listbox=tk.Listbox(lf,bg="#101010",fg="#eee",selectbackground="#444",highlightthickness=0,width=34)
        sb=ttk.Scrollbar(lf,orient="vertical",command=self.listbox.yview); self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        self.listbox.bind("<<ListboxSelect>>",lambda e:self.preview())

        wb=ttk.LabelFrame(left,text="浮水印來源",padding=10); wb.pack(fill="x",pady=(0,10))
        ttk.Button(wb,text="選擇 Logo / 浮水印",command=self.choose_wm).pack(fill="x")
        self.wm_label=ttk.Label(wb,text="尚未選擇"); self.wm_label.pack(fill="x",pady=(5,0))
        ob=ttk.LabelFrame(left,text="輸出資料夾",padding=10); ob.pack(fill="x")
        ttk.Entry(ob,textvariable=self.output_dir).pack(fill="x"); ttk.Button(ob,text="選擇資料夾",command=self.choose_output).pack(fill="x",pady=(6,0))

        ttk.Label(center,text="自由位置模式：拖曳 Logo；裁切比例模式：拖曳圖片改變裁切重心。",wraplength=700).pack(fill="x",pady=(0,6))
        pv=ttk.LabelFrame(center,text="互動預覽",padding=8); pv.pack(fill="both",expand=True)
        self.canvas=tk.Canvas(pv,bg="#0d0d0d",highlightthickness=0); self.canvas.pack(fill="both",expand=True)
        self.canvas.bind("<Configure>",lambda e:self.preview()); self.canvas.bind("<Button-1>",self.drag); self.canvas.bind("<B1-Motion>",self.drag)

        bp=ttk.LabelFrame(right,text="品牌 / Preset",padding=10); bp.pack(fill="x",pady=(0,10))
        self.brand_name=tk.StringVar(); self.brand_combo=ttk.Combobox(bp,textvariable=self.brand_name,state="readonly"); self.brand_combo.pack(fill="x")
        br=ttk.Frame(bp); br.pack(fill="x",pady=(5,8)); ttk.Button(br,text="套用品牌",command=self.apply_brand).pack(side="left",fill="x",expand=True,padx=(0,3)); ttk.Button(br,text="儲存品牌",command=self.save_brand).pack(side="left",fill="x",expand=True,padx=(3,0))
        self.preset_name=tk.StringVar(); self.preset_combo=ttk.Combobox(bp,textvariable=self.preset_name,state="readonly"); self.preset_combo.pack(fill="x")
        pr=ttk.Frame(bp); pr.pack(fill="x",pady=(5,0)); ttk.Button(pr,text="套用",command=self.apply_preset).pack(side="left",fill="x",expand=True,padx=(0,3)); ttk.Button(pr,text="儲存",command=self.save_preset).pack(side="left",fill="x",expand=True,padx=3); ttk.Button(pr,text="刪除",command=self.delete_preset).pack(side="left",fill="x",expand=True,padx=(3,0))

        nb=ttk.Notebook(right); nb.pack(fill="both",expand=True)
        logo=ttk.Frame(nb,padding=10); text=ttk.Frame(nb,padding=10); crop=ttk.Frame(nb,padding=10); out=ttk.Frame(nb,padding=10); multi=ttk.Frame(nb,padding=10)
        nb.add(logo,text="Logo"); nb.add(text,text="文字"); nb.add(crop,text="裁切"); nb.add(out,text="輸出"); nb.add(multi,text="多尺寸")

        ttk.Label(logo,text="模式").pack(anchor="w"); c=ttk.Combobox(logo,values=["九宮格","自由位置","平鋪"],state="readonly",textvariable=self.wm_mode); c.pack(fill="x"); c.bind("<<ComboboxSelected>>",lambda e:self.preview())
        self.slider(logo,"大小 %",self.wm_scale,1,100); self.slider(logo,"透明度 %",self.wm_opacity,0,100); self.slider(logo,"旋轉",self.wm_rotation,-180,180)
        ttk.Label(logo,text="位置").pack(anchor="w",pady=(8,2)); pc=ttk.Combobox(logo,values=POSITIONS,state="readonly",textvariable=self.wm_position); pc.pack(fill="x"); pc.bind("<<ComboboxSelected>>",lambda e:self.preview())
        rr=ttk.Frame(logo); rr.pack(fill="x",pady=(8,0)); ttk.Label(rr,text="邊距 px").pack(side="left"); ttk.Spinbox(rr,from_=0,to=1000,textvariable=self.margin,width=8,command=self.preview).pack(side="right")
        rr=ttk.Frame(logo); rr.pack(fill="x",pady=(8,0)); ttk.Label(rr,text="平鋪間距 px").pack(side="left"); ttk.Spinbox(rr,from_=0,to=1000,textvariable=self.tile_gap,width=8,command=self.preview).pack(side="right")

        ttk.Checkbutton(text,text="啟用文字浮水印",variable=self.text_enabled,command=self.preview).pack(anchor="w"); ttk.Entry(text,textvariable=self.text_value).pack(fill="x",pady=(8,0)); self.text_value.trace_add("write",lambda *a:self.preview())
        rr=ttk.Frame(text); rr.pack(fill="x",pady=(8,0)); ttk.Label(rr,text="字體大小").pack(side="left"); ttk.Spinbox(rr,from_=10,to=500,textvariable=self.text_size,width=8,command=self.preview).pack(side="right")
        self.slider(text,"文字透明度 %",self.text_opacity,0,100); ttk.Button(text,text="選擇文字顏色",command=self.choose_text_color).pack(fill="x",pady=(8,0)); tp=ttk.Combobox(text,values=POSITIONS,state="readonly",textvariable=self.text_position); tp.pack(fill="x",pady=(8,0)); tp.bind("<<ComboboxSelected>>",lambda e:self.preview())

        rc=ttk.Combobox(crop,values=list(RATIOS.keys()),state="readonly",textvariable=self.output_ratio); rc.pack(fill="x"); rc.bind("<<ComboboxSelected>>",lambda e:self.preview()); ttk.Label(crop,text="選擇比例後可在預覽中拖曳裁切重心。",wraplength=330).pack(fill="x",pady=8); ttk.Button(crop,text="重設裁切中心",command=self.reset_crop).pack(fill="x")

        sm=ttk.Combobox(out,values=["百分比","指定長邊"],state="readonly",textvariable=self.size_mode); sm.pack(fill="x"); sm.bind("<<ComboboxSelected>>",lambda e:self.preview()); self.slider(out,"百分比 %",self.resize_percent,10,200)
        rr=ttk.Frame(out); rr.pack(fill="x",pady=(8,0)); ttk.Label(rr,text="指定長邊 px").pack(side="left"); ttk.Spinbox(rr,from_=320,to=20000,increment=100,textvariable=self.long_edge,width=9,command=self.preview).pack(side="right")
        ttk.Checkbutton(out,text="允許放大原圖",variable=self.allow_upscale,command=self.preview).pack(anchor="w",pady=(8,0)); ttk.Combobox(out,values=["JPG","JPEG","PNG"],state="readonly",textvariable=self.output_format).pack(fill="x",pady=(8,0))
        rr=ttk.Frame(out); rr.pack(fill="x",pady=(8,0)); ttk.Label(rr,text="JPG 品質").pack(side="left"); ttk.Spinbox(rr,from_=40,to=100,textvariable=self.quality,width=8).pack(side="right")
        ttk.Checkbutton(out,text="保留 EXIF",variable=self.preserve_exif).pack(anchor="w",pady=(8,0)); ttk.Combobox(out,values=["自動加序號","覆蓋","略過"],state="readonly",textvariable=self.conflict_mode).pack(fill="x",pady=(8,0)); ttk.Checkbutton(out,text="啟用重新命名",variable=self.rename_enabled).pack(anchor="w",pady=(8,0)); ttk.Entry(out,textvariable=self.rename_template).pack(fill="x",pady=(4,0)); ttk.Label(out,text="{name} {index} {date} {width} {height}").pack(anchor="w",pady=(4,0))

        ttk.Label(multi,text="一次輸出多種規格").pack(anchor="w"); self.multi_frame=ttk.Frame(multi); self.multi_frame.pack(fill="both",expand=True,pady=(8,0)); mb=ttk.Frame(multi); mb.pack(fill="x",pady=(8,0)); ttk.Button(mb,text="新增規格",command=self.add_profile).pack(side="left",fill="x",expand=True,padx=(0,3)); ttk.Button(mb,text="刪除勾選",command=self.delete_profiles).pack(side="left",fill="x",expand=True,padx=(3,0))

        act=ttk.Frame(right); act.pack(fill="x",pady=(10,0)); ttk.Button(act,text="開始導出",style="Accent.TButton",command=self.export).pack(side="left",fill="x",expand=True,padx=(0,4)); ttk.Button(act,text="取消",command=self.cancel).pack(side="left")
        self.progress=ttk.Progressbar(right,mode="determinate"); self.progress.pack(fill="x",pady=(10,4)); ttk.Label(right,textvariable=self.status,wraplength=370).pack(fill="x")

    def slider(self,parent,label,var,a,b):
        r=ttk.Frame(parent); r.pack(fill="x",pady=(5,0)); ttk.Label(r,text=label).pack(side="left"); v=ttk.Label(r,text=str(int(var.get()))); v.pack(side="right"); ttk.Scale(parent,from_=a,to=b,variable=var,command=lambda x:(v.config(text=str(int(var.get()))),self.preview())).pack(fill="x")

    def add_images(self): self._append(filedialog.askopenfilenames(filetypes=[("Images","*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff")]))
    def add_folder(self):
        d=filedialog.askdirectory();
        if d:self._append([str(p) for p in Path(d).iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED])
    def on_drop(self,e):
        items=self.tk.splitlist(e.data); arr=[]
        for x in items:
            p=Path(x)
            if p.is_dir(): arr += [str(y) for y in p.iterdir() if y.is_file() and y.suffix.lower() in SUPPORTED]
            elif p.suffix.lower() in SUPPORTED: arr.append(str(p))
        self._append(arr)
    def _append(self,items):
        existing=set(self.paths)
        for p in items:
            p=str(p)
            if p not in existing:self.paths.append(p); self.listbox.insert("end",Path(p).name); existing.add(p)
        if self.paths and not self.listbox.curselection(): self.listbox.selection_set(0)
        self.status.set(f"已載入 {len(self.paths)} 張"); self.preview()
    def remove_selected(self):
        s=list(self.listbox.curselection())
        for i in reversed(s): self.listbox.delete(i); del self.paths[i]
        if self.paths:self.listbox.selection_set(min(s[0] if s else 0,len(self.paths)-1)); self.preview()
    def clear(self): self.paths.clear(); self.listbox.delete(0,"end"); self.canvas.delete("all")
    def choose_wm(self):
        p=filedialog.askopenfilename(filetypes=[("Images","*.png *.jpg *.jpeg *.webp")]);
        if p:self.watermark_path=p; self.wm_label.config(text=Path(p).name); self.preview()
    def choose_output(self):
        d=filedialog.askdirectory();
        if d:self.output_dir.set(d)
    def choose_text_color(self):
        c=colorchooser.askcolor(color=self.text_color)
        if c and c[1]:self.text_color=c[1]; self.preview()

    def crop(self,img,ratio_name=None):
        ratio=RATIOS.get(ratio_name or self.output_ratio.get());
        if not ratio:return img
        rw,rh=ratio; target=rw/rh; w,h=img.size; cur=w/h
        if cur>target:
            nw=int(h*target); left=int((w-nw)*max(0,min(1,self.crop_x.get()))); return img.crop((left,0,left+nw,h))
        nh=int(w/target); top=int((h-nh)*max(0,min(1,self.crop_y.get()))); return img.crop((0,top,w,top+nh))
    def resize(self,img,mode=None,pct=None,edge=None):
        mode=mode or self.size_mode.get(); pct=self.resize_percent.get() if pct is None else pct; edge=self.long_edge.get() if edge is None else edge; w,h=img.size
        if mode=="指定長邊":
            cur=max(w,h); scale=edge/cur
            if scale>1 and not self.allow_upscale.get():scale=1
        else:
            scale=pct/100
            if scale>1 and not self.allow_upscale.get():scale=1
        if abs(scale-1)<.001:return img
        return img.resize((max(1,int(w*scale)),max(1,int(h*scale))),Image.Resampling.LANCZOS)
    def anchor(self,bs,osz,pos,margin=24):
        bw,bh=bs; ow,oh=osz; xs={"左":margin,"中":(bw-ow)//2,"右":bw-ow-margin}; ys={"上":margin,"中":(bh-oh)//2,"下":bh-oh-margin}
        if pos=="置中":return xs["中"],ys["中"]
        if len(pos)==2:
            a,b=pos[0],pos[1]
            return (xs[a],ys[b]) if a in "左右" else (xs[b],ys[a])
        return bw-ow-margin,bh-oh-margin
    def apply_wm(self,img):
        base=img.convert("RGBA")
        if self.watermark_path:
            wm=Image.open(self.watermark_path).convert("RGBA"); tw=max(1,int(base.width*self.wm_scale.get()/100)); sc=tw/wm.width; wm=wm.resize((tw,max(1,int(wm.height*sc))),Image.Resampling.LANCZOS)
            if abs(self.wm_rotation.get())>.01:wm=wm.rotate(self.wm_rotation.get(),expand=True,resample=Image.Resampling.BICUBIC)
            a=wm.getchannel("A"); wm.putalpha(ImageEnhance.Brightness(a).enhance(self.wm_opacity.get()/100))
            if self.wm_mode.get()=="平鋪":
                sx=wm.width+self.tile_gap.get(); sy=wm.height+self.tile_gap.get(); row=0; y=-wm.height//2
                while y<base.height:
                    x=-wm.width//2+(sx//2 if row%2 else 0)
                    while x<base.width:base.alpha_composite(wm,dest=(x,y)); x+=max(1,sx)
                    y+=max(1,sy); row+=1
            else:
                if self.wm_mode.get()=="自由位置":x=int(self.free_x.get()*base.width-wm.width/2); y=int(self.free_y.get()*base.height-wm.height/2)
                else:x,y=self.anchor(base.size,wm.size,self.wm_position.get(),self.margin.get())
                base.alpha_composite(wm,dest=(x,y))
        if self.text_enabled.get() and self.text_value.get().strip():
            lay=Image.new("RGBA",base.size,(0,0,0,0)); d=ImageDraw.Draw(lay)
            try:f=ImageFont.truetype("arial.ttf",self.text_size.get())
            except:f=ImageFont.load_default()
            h=self.text_color.lstrip("#"); rgb=tuple(int(h[i:i+2],16) for i in (0,2,4)); fill=(*rgb,int(self.text_opacity.get()*2.55)); bb=d.textbbox((0,0),self.text_value.get(),font=f); size=(bb[2]-bb[0],bb[3]-bb[1]); x,y=self.anchor(base.size,size,self.text_position.get(),self.margin.get()); d.text((x,y),self.text_value.get(),font=f,fill=fill); base=Image.alpha_composite(base,lay)
        return base
    def process(self,path,ratio=None,mode=None,pct=None,edge=None):
        with Image.open(path) as s:
            exif=s.info.get("exif"); img=ImageOps.exif_transpose(s).convert("RGBA"); img=self.crop(img,ratio); img=self.resize(img,mode,pct,edge); return self.apply_wm(img),exif

    def preview(self):
        if not self.paths:return
        try:
            idx=self.listbox.curselection()[0] if self.listbox.curselection() else 0; img,_=self.process(self.paths[idx]); cw=max(200,self.canvas.winfo_width()-20); ch=max(200,self.canvas.winfo_height()-20); p=img.copy(); p.thumbnail((cw,ch),Image.Resampling.LANCZOS); self.preview_photo=ImageTk.PhotoImage(p); self.canvas.delete("all"); cx=self.canvas.winfo_width()//2; cy=self.canvas.winfo_height()//2; self.canvas.create_image(cx,cy,image=self.preview_photo); self.preview_box=(cx-p.width//2,cy-p.height//2,cx+p.width//2,cy+p.height//2)
        except Exception as e:self.status.set(f"預覽失敗：{e}")
    def drag(self,e):
        if not self.preview_box:return
        l,t,r,b=self.preview_box
        if not(l<=e.x<=r and t<=e.y<=b):return
        nx=(e.x-l)/max(1,r-l); ny=(e.y-t)/max(1,b-t)
        if self.wm_mode.get()=="自由位置":self.free_x.set(nx); self.free_y.set(ny)
        elif RATIOS.get(self.output_ratio.get()):self.crop_x.set(nx); self.crop_y.set(ny)
        self.preview()
    def reset_crop(self):self.crop_x.set(.5); self.crop_y.set(.5); self.preview()

    def filename(self,src,i,img,fmt):
        ext=".png" if fmt=="PNG" else ".jpeg" if fmt=="JPEG" else ".jpg"
        if not self.rename_enabled.get():return Path(src).stem+ext
        idx=f"{self.rename_start.get()+i:0{self.rename_digits.get()}d}"; d={"name":Path(src).stem,"index":idx,"date":datetime.now().strftime("%Y%m%d"),"width":img.width,"height":img.height}
        try:stem=self.rename_template.get().format(**d)
        except:stem=f"{Path(src).stem}_{idx}"
        for c in '<>:"/\\|?*':stem=stem.replace(c,"_")
        return stem+ext
    def resolve(self,p):
        if not p.exists() or self.conflict_mode.get()=="覆蓋":return p
        if self.conflict_mode.get()=="略過":return None
        n=1
        while True:
            c=p.with_name(f"{p.stem}_{n}{p.suffix}")
            if not c.exists():return c
            n+=1
    def save_image(self,img,p,fmt,q,exif):
        if fmt in ("JPG","JPEG"):
            bg=Image.new("RGB",img.size,"white"); bg.paste(img,mask=img.getchannel("A")); kw={"format":"JPEG","quality":q,"optimize":True};
            if self.preserve_exif.get() and exif:kw["exif"]=exif
            bg.save(p,**kw)
        else:img.save(p,"PNG",optimize=True)

    def export(self):
        if not self.paths:messagebox.showwarning("提醒","請先加入圖片"); return
        out=Path(self.output_dir.get()); out.mkdir(parents=True,exist_ok=True); self.cancelled=False; self._sync_profiles(); active=[(n,c) for n,c in self.profiles.items() if c.get("enabled")]; total=len(self.paths)*(len(active) if active else 1); self.progress["maximum"]=max(1,total); self.progress["value"]=0; self.save_settings(); threading.Thread(target=self.worker,args=(out,active),daemon=True).start()
    def worker(self,out,active):
        done=skip=step=0; errors=[]
        for i,src in enumerate(self.paths):
            if self.cancelled:break
            profiles=active or [("Single",{"ratio":self.output_ratio.get(),"mode":self.size_mode.get(),"pct":self.resize_percent.get(),"edge":self.long_edge.get(),"format":self.output_format.get(),"quality":self.quality.get()})]
            for name,c in profiles:
                if self.cancelled:break
                try:
                    img,exif=self.process(src,c.get("ratio"),c.get("mode","指定長邊"),c.get("pct",100),c.get("edge",2048)); fmt=c.get("format","JPG"); folder=out if not active else out/name; folder.mkdir(parents=True,exist_ok=True); p=self.resolve(folder/self.filename(src,i,img,fmt));
                    if p is None:skip+=1
                    else:self.save_image(img,p,fmt,c.get("quality",92),exif); done+=1
                except Exception as e:errors.append(f"{Path(src).name}: {e}")
                step+=1; self.after(0,lambda v=step:(self.progress.configure(value=v),self.status.set(f"處理中 {v}/{int(self.progress['maximum'])}")))
        self.after(0,lambda:self.finish(done,skip,errors,out))
    def finish(self,done,skip,errors,out):
        self.status.set("已取消" if self.cancelled else f"完成：{done}"); msg=f"成功 {done}\n略過 {skip}\n錯誤 {len(errors)}\n\n{out}"; messagebox.showwarning("完成",msg+"\n\n"+"\n".join(errors[:5])) if errors else messagebox.showinfo("完成",msg)
        try:
            if os.name=="nt":os.startfile(str(out))
        except:pass
    def cancel(self):self.cancelled=True

    def default_profiles(self):return {"Instagram_4x5":{"enabled":True,"ratio":"4:5","mode":"指定長邊","edge":1350,"format":"JPG","quality":92},"Story_9x16":{"enabled":False,"ratio":"9:16","mode":"指定長邊","edge":1920,"format":"JPG","quality":92},"Square_1x1":{"enabled":False,"ratio":"1:1","mode":"指定長邊","edge":1080,"format":"JPG","quality":92}}
    def refresh_profiles(self):
        for w in self.multi_frame.winfo_children():w.destroy()
        self.profile_vars={}
        for n,c in self.profiles.items():
            v=tk.BooleanVar(value=c.get("enabled",False)); self.profile_vars[n]=v; r=ttk.Frame(self.multi_frame); r.pack(fill="x",pady=3); ttk.Checkbutton(r,text=n,variable=v,command=self._sync_profiles).pack(side="left"); ttk.Label(r,text=f"{c.get('ratio')} / {c.get('edge')}px").pack(side="right")
    def _sync_profiles(self):
        for n,v in self.profile_vars.items():self.profiles[n]["enabled"]=v.get()
        self._save_json(PROFILES_FILE,self.profiles)
    def add_profile(self):
        n=simpledialog.askstring("新增規格","名稱：",parent=self)
        if not n:return
        ratio=simpledialog.askstring("比例","4:5 / 9:16 / 1:1 / 原始比例",initialvalue="4:5",parent=self); ratio=ratio if ratio in RATIOS else "原始比例"; edge=simpledialog.askinteger("長邊","像素",initialvalue=1350,minvalue=320,maxvalue=20000,parent=self) or 1350; self.profiles[n]={"enabled":True,"ratio":ratio,"mode":"指定長邊","edge":edge,"format":"JPG","quality":92}; self._save_json(PROFILES_FILE,self.profiles); self.refresh_profiles()
    def delete_profiles(self):
        for n in [x for x,v in self.profile_vars.items() if v.get()]:self.profiles.pop(n,None)
        self._save_json(PROFILES_FILE,self.profiles); self.refresh_profiles()

    def config(self):return {"wm_mode":self.wm_mode.get(),"wm_position":self.wm_position.get(),"wm_scale":self.wm_scale.get(),"wm_opacity":self.wm_opacity.get(),"wm_rotation":self.wm_rotation.get(),"margin":self.margin.get(),"free_x":self.free_x.get(),"free_y":self.free_y.get(),"tile_gap":self.tile_gap.get(),"text_enabled":self.text_enabled.get(),"text_value":self.text_value.get(),"text_size":self.text_size.get(),"text_opacity":self.text_opacity.get(),"text_color":self.text_color,"text_position":self.text_position.get(),"output_ratio":self.output_ratio.get(),"crop_x":self.crop_x.get(),"crop_y":self.crop_y.get(),"size_mode":self.size_mode.get(),"resize_percent":self.resize_percent.get(),"long_edge":self.long_edge.get(),"allow_upscale":self.allow_upscale.get(),"output_format":self.output_format.get(),"quality":self.quality.get(),"preserve_exif":self.preserve_exif.get(),"rename_enabled":self.rename_enabled.get(),"rename_template":self.rename_template.get(),"rename_start":self.rename_start.get(),"rename_digits":self.rename_digits.get(),"conflict_mode":self.conflict_mode.get(),"output_dir":self.output_dir.get(),"watermark_path":self.watermark_path}
    def apply_cfg(self,c):
        m={"wm_mode":self.wm_mode,"wm_position":self.wm_position,"wm_scale":self.wm_scale,"wm_opacity":self.wm_opacity,"wm_rotation":self.wm_rotation,"margin":self.margin,"free_x":self.free_x,"free_y":self.free_y,"tile_gap":self.tile_gap,"text_enabled":self.text_enabled,"text_value":self.text_value,"text_size":self.text_size,"text_opacity":self.text_opacity,"text_position":self.text_position,"output_ratio":self.output_ratio,"crop_x":self.crop_x,"crop_y":self.crop_y,"size_mode":self.size_mode,"resize_percent":self.resize_percent,"long_edge":self.long_edge,"allow_upscale":self.allow_upscale,"output_format":self.output_format,"quality":self.quality,"preserve_exif":self.preserve_exif,"rename_enabled":self.rename_enabled,"rename_template":self.rename_template,"rename_start":self.rename_start,"rename_digits":self.rename_digits,"conflict_mode":self.conflict_mode,"output_dir":self.output_dir}
        for k,v in m.items():
            if k in c:v.set(c[k])
        if "text_color" in c:self.text_color=c["text_color"]
        p=c.get("watermark_path");
        if p and Path(p).exists():self.watermark_path=p; self.wm_label.config(text=Path(p).name)
        self.preview()
    def _save_json(self,p,obj):APP_DIR.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
    def _load_json(self,p,default):
        try:return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
        except:return default
    def save_settings(self):self._save_json(SETTINGS_FILE,self.config())
    def _load_all(self):
        c=self._load_json(SETTINGS_FILE,{}); self.presets=self._load_json(PRESETS_FILE,{}); self.brands=self._load_json(BRANDS_FILE,{}); self.profiles=self._load_json(PROFILES_FILE,self.default_profiles()); self.apply_cfg(c); self.refresh_presets(); self.refresh_brands(); self.refresh_profiles()
    def refresh_presets(self):self.preset_combo["values"]=list(self.presets); self.preset_name.set(next(iter(self.presets),""))
    def refresh_brands(self):self.brand_combo["values"]=list(self.brands); self.brand_name.set(next(iter(self.brands),""))
    def save_preset(self):
        n=simpledialog.askstring("Preset","名稱：",parent=self)
        if n:self.presets[n]=self.config(); self._save_json(PRESETS_FILE,self.presets); self.refresh_presets(); self.preset_name.set(n)
    def apply_preset(self):
        if self.preset_name.get() in self.presets:self.apply_cfg(self.presets[self.preset_name.get()])
    def delete_preset(self):
        n=self.preset_name.get(); self.presets.pop(n,None); self._save_json(PRESETS_FILE,self.presets); self.refresh_presets()
    def save_brand(self):
        n=simpledialog.askstring("品牌","品牌名稱：",parent=self)
        if n:self.brands[n]=self.config(); self._save_json(BRANDS_FILE,self.brands); self.refresh_brands(); self.brand_name.set(n)
    def apply_brand(self):
        if self.brand_name.get() in self.brands:self.apply_cfg(self.brands[self.brand_name.get()])

if __name__=="__main__":
    App().mainloop()
