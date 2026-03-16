#!/usr/bin/env python3
"""
WebP Converter — macOS e Windows
- Conversão em lote para WebP com compressão iterativa
- Área de crop salva individualmente por foto
- Posicionamento interativo com grade de terços
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, io, threading, platform
from PIL import Image, ImageTk, ImageDraw, ImageOps

# ─── Sistema operacional ────────────────────────────────────────────────────────
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

# ─── Paleta de cores ────────────────────────────────────────────────────────────
BG      = "#0F0F11"
BG2     = "#1A1A1F"
BG3     = "#242429"
ACCENT  = "#7C6BFF"
ACCENT2 = "#A896FF"
SUCCESS = "#4ADE80"
WARNING = "#FACC15"
DANGER  = "#F87171"
TEXT    = "#F0EFF8"
TEXT2   = "#9896A8"
BORDER  = "#2E2E38"

# Cores explícitas para botões — resolve o problema de texto branco em fundo branco
BTN_DARK_BG = "#2E2E3A"
BTN_DARK_FG = "#F0EFF8"
BTN_LITE_BG = "#7C6BFF"
BTN_LITE_FG = "#FFFFFF"

if IS_MAC:
    F_TITLE = ("SF Pro Display", 22, "bold")
    F_LABEL = ("SF Pro Text", 11)
    F_SMALL = ("SF Pro Text", 10)
    F_MONO  = ("SF Mono", 10)
else:
    F_TITLE = ("Segoe UI", 20, "bold")
    F_LABEL = ("Segoe UI", 10)
    F_SMALL = ("Segoe UI", 10)
    F_MONO  = ("Consolas", 10)


# ─── Canvas de preview com crop interativo ──────────────────────────────────────

class CropCanvas(tk.Canvas):

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG3, highlightthickness=0, **kw)
        self._img    = None
        self._photo  = None
        self._crop_w = None
        self._crop_h = None
        self._ox     = 0.5
        self._oy     = 0.5
        self._drag   = None
        self._cbs    = []

        self.bind("<ButtonPress-1>",   self._press)
        self.bind("<B1-Motion>",       self._drag_move)
        self.bind("<ButtonRelease-1>", self._release)
        self.bind("<Configure>",       lambda e: self._render())

    # Pública
    def load_image(self, pil_img, ox=0.5, oy=0.5):
        self._img = pil_img
        self._ox  = ox
        self._oy  = oy
        self._render()

    def set_crop_size(self, w, h):
        self._crop_w = w
        self._crop_h = h
        self._render()

    def get_offset(self):
        return self._ox, self._oy

    def on_change(self, fn):
        self._cbs.append(fn)

    def clear(self):
        self._img = None
        self._render()

    # Drag
    def _press(self, e):
        self._drag = (e.x, e.y, self._ox, self._oy)

    def _drag_move(self, e):
        if not self._drag or not self._img:
            return
        sx, sy, ox0, oy0 = self._drag
        cw = self.winfo_width()
        ch = self.winfo_height()
        iw, ih = self._img.size
        scale  = min(cw / iw, ch / ih)
        dw, dh = iw * scale, ih * scale

        if self._crop_w and self._crop_h:
            ca = self._crop_w / self._crop_h
            ia = iw / ih
            if ca > ia:
                cdw, cdh = dw, dw / ca
            else:
                cdh, cdw = dh, dh * ca
            dx = (e.x - sx) / max(dw - cdw, 1)
            dy = (e.y - sy) / max(dh - cdh, 1)
        else:
            dx = dy = 0

        self._ox = max(0.0, min(1.0, ox0 + dx))
        self._oy = max(0.0, min(1.0, oy0 + dy))
        self._render()
        for fn in self._cbs:
            fn(self._ox, self._oy)

    def _release(self, e):
        self._drag = None

    # Render
    def _render(self):
        self.delete("all")
        cw = max(self.winfo_width(),  1)
        ch = max(self.winfo_height(), 1)

        if not self._img:
            self._placeholder(cw, ch)
            return

        iw, ih = self._img.size
        scale   = min(cw / iw, ch / ih)
        dw, dh  = int(iw * scale), int(ih * scale)
        px, py  = (cw - dw) // 2, (ch - dh) // 2

        thumb = self._img.resize((dw, dh), Image.LANCZOS)
        base  = Image.new("RGB", (cw, ch), (26, 26, 31))
        base.paste(thumb, (px, py))

        if self._crop_w and self._crop_h:
            ca = self._crop_w / self._crop_h
            ia = iw / ih
            if ca > ia:
                cdw, cdh = dw, int(dw / ca)
            else:
                cdh, cdw = dh, int(dh * ca)

            mox = dw - cdw
            moy = dh - cdh
            cx  = px + int(self._ox * mox)
            cy  = py + int(self._oy * moy)

            ov   = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
            draw = ImageDraw.Draw(ov)
            draw.rectangle([0, 0, cw, ch], fill=(0, 0, 0, 150))
            draw.rectangle([cx, cy, cx+cdw, cy+cdh], fill=(0, 0, 0, 0))
            draw.rectangle([cx, cy, cx+cdw, cy+cdh], outline=(124, 107, 255, 255), width=2)

            for i in range(1, 3):
                x = cx + i * cdw // 3
                y = cy + i * cdh // 3
                draw.line([(x, cy), (x, cy+cdh)], fill=(124, 107, 255, 70), width=1)
                draw.line([(cx, y), (cx+cdw, y)], fill=(124, 107, 255, 70), width=1)

            sz = 14
            c  = (168, 150, 255, 255)
            for bx, by, dx2, dy2 in [
                (cx, cy, 1, 1), (cx+cdw, cy, -1, 1),
                (cx, cy+cdh, 1, -1), (cx+cdw, cy+cdh, -1, -1)
            ]:
                draw.line([(bx, by), (bx+sz*dx2, by)], fill=c, width=3)
                draw.line([(bx, by), (bx, by+sz*dy2)], fill=c, width=3)

            base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")

        self._photo = ImageTk.PhotoImage(base)
        self.create_image(0, 0, anchor="nw", image=self._photo)

    def _placeholder(self, cw, ch):
        self.create_rectangle(0, 0, cw, ch, fill=BG3, outline="")
        self.create_text(cw//2, ch//2 - 20, text="📂",
                         font=(F_SMALL[0], 34), fill=BORDER, anchor="center")
        self.create_text(cw//2, ch//2 + 22,
                         text="Adicione fotos e ajuste o enquadramento de cada uma",
                         font=F_SMALL, fill=TEXT2, anchor="center")


# ─── Janela principal ───────────────────────────────────────────────────────────

class WebPConverter(tk.Tk):

    PRESETS = [
        ("Quadrado 1080",  1080, 1080),
        ("Story 9:16",     1080, 1920),
        ("Paisagem 16:9",  1920, 1080),
        ("Banner 4:1",     1200,  300),
        ("Personalizado",     0,    0),
    ]

    def __init__(self):
        super().__init__()
        self.title("WebP Converter")
        self.configure(bg=BG)
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.images       = []
        self.pil_cache    = {}
        self.crop_offsets = {}   # ← offset salvo por foto
        self.current_idx  = 0
        self.converting   = False

        self._apply_theme()
        self._build_ui()
        self._refresh_state()

    def _apply_theme(self):
        opts = {
            "*Background":                BG2,
            "*Foreground":                TEXT,
            "*Button.Background":         BTN_DARK_BG,
            "*Button.Foreground":         BTN_DARK_FG,
            "*Button.activeBackground":   ACCENT,
            "*Button.activeForeground":   "#FFFFFF",
            "*Button.disabledForeground": TEXT2,
            "*Entry.Background":          BG3,
            "*Entry.Foreground":          TEXT,
            "*Entry.disabledBackground":  BG3,
            "*Entry.disabledForeground":  TEXT2,
            "*Entry.insertBackground":    TEXT,
            "*Listbox.Background":        BG3,
            "*Listbox.Foreground":        TEXT,
            "*Listbox.selectBackground":  ACCENT,
            "*Listbox.selectForeground":  "#FFFFFF",
            "*Radiobutton.Background":    BG2,
            "*Radiobutton.Foreground":    TEXT,
            "*Radiobutton.activeBackground": BG2,
            "*Radiobutton.activeForeground": ACCENT2,
            "*Scale.Background":          BG2,
            "*Scale.Foreground":          TEXT,
            "*Scale.troughColor":         BG3,
            "*Label.Background":          BG2,
            "*Label.Foreground":          TEXT,
        }
        for k, v in opts.items():
            self.option_add(k, v)

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Accent.Horizontal.TProgressbar",
                        troughcolor=BG3, background=ACCENT,
                        borderwidth=0, thickness=5)

    # ── UI ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        sidebar = tk.Frame(self, bg=BG2, width=310)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        main = tk.Frame(self, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self._build_sidebar(sidebar)
        self._build_main(main)

    def _build_sidebar(self, p):
        PAD = {"padx": 20}

        hdr = tk.Frame(p, bg=BG2)
        hdr.pack(fill="x", pady=(24, 0), **PAD)
        tk.Label(hdr, text="WebP",       font=(F_TITLE[0], 22, "bold"),
                 bg=BG2, fg=ACCENT2).pack(side="left")
        tk.Label(hdr, text=" Converter", font=(F_TITLE[0], 22),
                 bg=BG2, fg=TEXT).pack(side="left")
        tk.Label(p, text="Converta e otimize suas fotos",
                 font=F_SMALL, bg=BG2, fg=TEXT2).pack(anchor="w", **PAD, pady=(2, 18))
        self._sep(p)

        # Arquivos
        self._section(p, "ARQUIVOS")
        br = tk.Frame(p, bg=BG2)
        br.pack(fill="x", **PAD, pady=(0, 6))
        self._btn(br, "＋ Adicionar fotos", self._add_files,
                  primary=True).pack(side="left", fill="x", expand=True)
        tk.Frame(br, bg=BG2, width=8).pack(side="left")
        self._btn(br, "✕ Limpar", self._clear_files).pack(side="left")

        lbf = tk.Frame(p, bg=BG3)
        lbf.pack(fill="x", **PAD, pady=(0, 4))
        sb = tk.Scrollbar(lbf, bg=BG3, troughcolor=BG3, relief="flat", bd=0, width=10)
        sb.pack(side="right", fill="y")
        self.listbox = tk.Listbox(lbf, bg=BG3, fg=TEXT,
                                  selectbackground=ACCENT, selectforeground="#fff",
                                  relief="flat", bd=0, font=F_SMALL, height=5,
                                  activestyle="none", highlightthickness=0,
                                  yscrollcommand=sb.set)
        self.listbox.pack(fill="x", padx=8, pady=6)
        sb.configure(command=self.listbox.yview)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        self.count_lbl = tk.Label(p, text="Nenhuma foto adicionada",
                                  font=F_SMALL, bg=BG2, fg=TEXT2)
        self.count_lbl.pack(anchor="w", **PAD, pady=(0, 2))
        self.crop_info_lbl = tk.Label(p, text="", font=F_SMALL, bg=BG2, fg=ACCENT2)
        self.crop_info_lbl.pack(anchor="w", **PAD, pady=(0, 14))
        self._sep(p)

        # Tamanho
        self._section(p, "TAMANHO DE SAÍDA (px)")
        grid = tk.Frame(p, bg=BG2)
        grid.pack(fill="x", **PAD, pady=(0, 10))
        self.preset_var = tk.StringVar(value=self.PRESETS[0][0])
        for i, (name, _, __) in enumerate(self.PRESETS):
            tk.Radiobutton(grid, text=name, variable=self.preset_var, value=name,
                           bg=BG2, fg=TEXT, selectcolor=BG3,
                           activebackground=BG2, activeforeground=ACCENT2,
                           font=F_SMALL, command=self._on_preset,
                           highlightthickness=0, bd=0
                           ).grid(row=i//2, column=i%2, sticky="w", padx=4, pady=2)

        dim = tk.Frame(p, bg=BG2)
        dim.pack(fill="x", **PAD, pady=(0, 14))
        tk.Label(dim, text="Largura:", font=F_SMALL, bg=BG2, fg=TEXT2).grid(row=0, column=0, sticky="w")
        self.w_var = tk.StringVar(value="1080")
        self.w_entry = self._entry(dim, self.w_var, width=7)
        self.w_entry.grid(row=0, column=1, padx=(6,16))
        tk.Label(dim, text="Altura:", font=F_SMALL, bg=BG2, fg=TEXT2).grid(row=0, column=2, sticky="w")
        self.h_var = tk.StringVar(value="1080")
        self.h_entry = self._entry(dim, self.h_var, width=7)
        self.h_entry.grid(row=0, column=3, padx=(6,0))
        self.w_var.trace_add("write", lambda *_: self._on_dim_change())
        self.h_var.trace_add("write", lambda *_: self._on_dim_change())
        self._sep(p)

        # Qualidade
        self._section(p, "QUALIDADE / TAMANHO MÁXIMO")
        qf = tk.Frame(p, bg=BG2)
        qf.pack(fill="x", **PAD, pady=(0, 14))
        tk.Label(qf, text="Tamanho máximo (KB):", font=F_SMALL, bg=BG2, fg=TEXT2).pack(anchor="w")
        sr = tk.Frame(qf, bg=BG2)
        sr.pack(fill="x", pady=(4,0))
        self.kb_var = tk.IntVar(value=100)
        tk.Scale(sr, from_=10, to=500, variable=self.kb_var, orient="horizontal",
                 bg=BG2, fg=TEXT, troughcolor=BG3, activebackground=ACCENT,
                 highlightthickness=0, bd=0, sliderrelief="flat", showvalue=False,
                 command=self._on_kb_change).pack(side="left", fill="x", expand=True)
        self.kb_lbl = tk.Label(sr, text="100 KB", font=F_MONO, bg=BG2, fg=ACCENT2, width=7)
        self.kb_lbl.pack(side="left")
        self._sep(p)

        # Pasta
        self._section(p, "PASTA DE SAÍDA")
        of = tk.Frame(p, bg=BG2)
        of.pack(fill="x", **PAD, pady=(0, 16))
        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop", "WebP"))
        self._entry(of, self.out_var).pack(side="left", fill="x", expand=True)
        self._btn(of, "...", self._choose_out).pack(side="left", padx=(6,0))

        tk.Frame(p, bg=BG2).pack(fill="y", expand=True)
        self.convert_btn = tk.Button(
            p, text="⚡  Converter tudo",
            font=(F_LABEL[0], 13, "bold"),
            bg=BTN_LITE_BG, fg=BTN_LITE_FG, relief="flat", bd=0,
            activebackground=ACCENT2, activeforeground="#fff",
            cursor="hand2", command=self._convert_all, pady=14,
            highlightthickness=0
        )
        self.convert_btn.pack(fill="x", padx=20, pady=(0, 24))

    def _build_main(self, p):
        bar = tk.Frame(p, bg=BG, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        nav = tk.Frame(bar, bg=BG)
        nav.pack(side="right", padx=12, pady=8)
        self._btn(nav, "◀", self._prev, width=3).pack(side="left", padx=2)
        self.idx_lbl = tk.Label(nav, text="0 / 0", font=F_SMALL, bg=BG, fg=TEXT2, width=9)
        self.idx_lbl.pack(side="left", padx=4)
        self._btn(nav, "▶", self._next, width=3).pack(side="left", padx=2)

        tk.Label(bar, text="Arraste a foto para ajustar o enquadramento",
                 font=F_SMALL, bg=BG, fg=TEXT2).pack(side="left", padx=20)
        self.offset_lbl = tk.Label(bar, text="", font=F_MONO, bg=BG, fg=ACCENT2)
        self.offset_lbl.pack(side="right", padx=12)

        self.canvas = CropCanvas(p)
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.canvas.on_change(self._on_offset_change)

        foot = tk.Frame(p, bg=BG)
        foot.pack(fill="x", padx=16, pady=(0, 14))
        self.prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(foot, variable=self.prog_var, maximum=100,
                        style="Accent.Horizontal.TProgressbar"
                        ).pack(fill="x", pady=(0, 4))
        self.status_lbl = tk.Label(foot, text="Pronto", font=F_SMALL, bg=BG, fg=TEXT2)
        self.status_lbl.pack(anchor="w")

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _sep(self, p):
        tk.Frame(p, bg=BORDER, height=1).pack(fill="x", padx=20)

    def _section(self, p, title):
        tk.Label(p, text=title, font=(F_SMALL[0], 9, "bold"),
                 bg=BG2, fg=TEXT2).pack(anchor="w", padx=20, pady=(12, 6))

    def _btn(self, parent, text, cmd, primary=False, width=None):
        kw = dict(text=text, command=cmd, font=F_SMALL, relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2", highlightthickness=0)
        if primary:
            kw.update(bg=BTN_LITE_BG, fg=BTN_LITE_FG,
                      activebackground=ACCENT2, activeforeground="#fff")
        else:
            kw.update(bg=BTN_DARK_BG, fg=BTN_DARK_FG,
                      activebackground=ACCENT, activeforeground="#fff")
        if width:
            kw["width"] = width
        return tk.Button(parent, **kw)

    def _entry(self, parent, var, width=None):
        kw = dict(textvariable=var, bg=BG3, fg=TEXT, insertbackground=TEXT,
                  relief="flat", bd=0, font=F_SMALL,
                  disabledbackground=BG3, disabledforeground=TEXT2)
        if width:
            kw["width"] = width
        e = tk.Entry(parent, **kw)
        e.configure(highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        return e

    # ── Arquivos ─────────────────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Selecionar fotos",
            filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp *.tiff *.heic *.webp"),
                       ("Todos", "*.*")]
        )
        first_new = len(self.images)
        for p in paths:
            if p not in self.images:
                self.images.append(p)
                self.listbox.insert("end", os.path.basename(p))
        self._refresh_state()
        if paths:
            self.current_idx = first_new
            self._load_preview()

    def _clear_files(self):
        self.images.clear()
        self.pil_cache.clear()
        self.crop_offsets.clear()
        self.listbox.delete(0, "end")
        self.current_idx = 0
        self.canvas.clear()
        self._refresh_state()

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            self._save_offset()
            self.current_idx = sel[0]
            self._load_preview()

    def _prev(self):
        if self.images:
            self._save_offset()
            self.current_idx = (self.current_idx - 1) % len(self.images)
            self._load_preview()

    def _next(self):
        if self.images:
            self._save_offset()
            self.current_idx = (self.current_idx + 1) % len(self.images)
            self._load_preview()

    def _save_offset(self):
        """Persiste o offset do canvas na foto atual antes de trocar."""
        if self.images:
            path = self.images[self.current_idx]
            self.crop_offsets[path] = self.canvas.get_offset()
            self._update_listbox_marks()

    def _update_listbox_marks(self):
        """Mostra ✓ na listbox para fotos que já foram ajustadas."""
        cur_sel = self.current_idx
        for i, path in enumerate(self.images):
            name = os.path.basename(path)
            if path in self.crop_offsets:
                ox, oy = self.crop_offsets[path]
                mark = " ✓" if (abs(ox - 0.5) > 0.02 or abs(oy - 0.5) > 0.02) else ""
            else:
                mark = ""
            self.listbox.delete(i)
            self.listbox.insert(i, name + mark)
        self.listbox.selection_clear(0, "end")
        if self.images:
            self.listbox.selection_set(cur_sel)

    # ── Preview ──────────────────────────────────────────────────────────────────

    def _load_preview(self):
        if not self.images:
            return
        path = self.images[self.current_idx]
        if path not in self.pil_cache:
            try:
                img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
                self.pil_cache[path] = img
            except Exception as e:
                self._status(f"Erro ao abrir: {e}", DANGER)
                return
        ox, oy = self.crop_offsets.get(path, (0.5, 0.5))
        self.canvas.load_image(self.pil_cache[path], ox, oy)
        self._update_canvas_crop()
        self._refresh_state()

    def _on_offset_change(self, ox, oy):
        # Salva em tempo real enquanto o usuário arrasta
        if self.images:
            self.crop_offsets[self.images[self.current_idx]] = (ox, oy)

        names_x = ["Esq.", "Centro", "Dir."]
        names_y = ["Topo", "Centro", "Base"]
        nx = 0 if ox < 0.33 else (2 if ox > 0.66 else 1)
        ny = 0 if oy < 0.33 else (2 if oy > 0.66 else 1)
        self.offset_lbl.configure(
            text=f"{names_x[nx]} / {names_y[ny]}  ({int(ox*100)}%, {int(oy*100)}%)"
        )

    def _on_preset(self):
        name = self.preset_var.get()
        for n, w, h in self.PRESETS:
            if n == name:
                if w and h:
                    self.w_var.set(str(w)); self.h_var.set(str(h))
                state = "disabled" if n != "Personalizado" else "normal"
                self.w_entry.configure(state=state)
                self.h_entry.configure(state=state)
                break
        self._update_canvas_crop()

    def _on_dim_change(self):
        self.preset_var.set("Personalizado")
        self._update_canvas_crop()

    def _update_canvas_crop(self):
        try:
            self.canvas.set_crop_size(int(self.w_var.get()), int(self.h_var.get()))
        except ValueError:
            pass

    def _on_kb_change(self, val):
        self.kb_lbl.configure(text=f"{int(float(val))} KB")

    def _choose_out(self):
        d = filedialog.askdirectory(title="Escolher pasta de saída")
        if d:
            self.out_var.set(d)

    def _refresh_state(self):
        n = len(self.images)
        self.count_lbl.configure(
            text=f"{n} foto{'s' if n!=1 else ''} adicionada{'s' if n!=1 else ''}"
            if n else "Nenhuma foto adicionada"
        )
        self.idx_lbl.configure(
            text=f"{self.current_idx+1 if n else 0} / {n}"
        )
        adjusted = sum(
            1 for p, (ox, oy) in self.crop_offsets.items()
            if abs(ox-0.5) > 0.02 or abs(oy-0.5) > 0.02
        )
        if n > 1:
            remaining = n - len(self.crop_offsets)
            if adjusted > 0:
                self.crop_info_lbl.configure(
                    text=f"✓ {adjusted}/{n} fotos com enquadramento ajustado"
                )
            else:
                self.crop_info_lbl.configure(
                    text=f"Ajuste o enquadramento de cada foto antes de converter"
                )
        elif n == 1:
            self.crop_info_lbl.configure(text="")
        else:
            self.crop_info_lbl.configure(text="")

        self._update_listbox_marks()

    # ── Conversão ────────────────────────────────────────────────────────────────

    def _convert_all(self):
        if not self.images:
            messagebox.showwarning("Atenção", "Adicione pelo menos uma foto.")
            return
        if self.converting:
            return
        self._save_offset()  # salva foto atual antes de converter

        try:
            out_w  = int(self.w_var.get())
            out_h  = int(self.h_var.get())
            max_kb = self.kb_var.get()
        except ValueError:
            messagebox.showerror("Erro", "Dimensões inválidas.")
            return

        out_dir = self.out_var.get()
        os.makedirs(out_dir, exist_ok=True)

        # Snapshot dos offsets — cada foto usa seu próprio
        offsets = {p: self.crop_offsets.get(p, (0.5, 0.5)) for p in self.images}

        self.converting = True
        self.convert_btn.configure(state="disabled", text="Convertendo...")
        self.prog_var.set(0)

        threading.Thread(
            target=self._worker,
            args=(list(self.images), out_w, out_h, max_kb, out_dir, offsets),
            daemon=True
        ).start()

    def _worker(self, images, out_w, out_h, max_kb, out_dir, offsets):
        total   = len(images)
        results = []
        for i, path in enumerate(images):
            self.after(0, self._status,
                       f"Convertendo {i+1}/{total}: {os.path.basename(path)}", TEXT2)
            try:
                img     = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
                ox, oy  = offsets[path]
                cropped = self._smart_crop(img, out_w, out_h, ox, oy)
                data, q = self._compress(cropped, max_kb)
                stem    = os.path.splitext(os.path.basename(path))[0]
                with open(os.path.join(out_dir, stem + ".webp"), "wb") as f:
                    f.write(data)
                results.append((stem, len(data)/1024, q, True))
            except Exception as e:
                results.append((os.path.basename(path), 0, 0, False))
            self.after(0, self.prog_var.set, (i+1)/total*100)
        self.after(0, self._done, results, out_dir)

    def _smart_crop(self, img, out_w, out_h, ox, oy):
        iw, ih  = img.size
        t_ratio = out_w / out_h
        i_ratio = iw / ih
        if t_ratio > i_ratio:
            cw, ch = iw, int(iw / t_ratio)
        else:
            ch, cw = ih, int(ih * t_ratio)
        x0 = int(ox * max(iw - cw, 0))
        y0 = int(oy * max(ih - ch, 0))
        return img.crop((x0, y0, x0+cw, y0+ch)).resize((out_w, out_h), Image.LANCZOS)

    def _compress(self, img, max_kb):
        max_b = max_kb * 1024
        for q in range(92, 9, -5):
            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=q, method=6)
            if buf.tell() <= max_b:
                return buf.getvalue(), q
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=10, method=6)
        return buf.getvalue(), 10

    def _done(self, results, out_dir):
        self.converting = False
        self.convert_btn.configure(state="normal", text="⚡  Converter tudo")
        ok, failed = [r for r in results if r[3]], [r for r in results if not r[3]]
        avg_kb = sum(r[1] for r in ok) / len(ok) if ok else 0

        self._status(
            f"✓ {len(ok)} foto(s) convertida(s)  ·  Média: {avg_kb:.1f} KB"
            + (f"  ·  ✕ {len(failed)} erro(s)" if failed else ""),
            SUCCESS if not failed else WARNING
        )
        self.prog_var.set(100)

        msg = f"{len(ok)} foto(s) convertida(s) com sucesso!\nTamanho médio: {avg_kb:.1f} KB\nSalvas em: {out_dir}"
        if failed:
            msg += f"\n\n{len(failed)} arquivo(s) com erro."

        if messagebox.askyesno("Concluído", msg + "\n\nAbrir pasta de saída?"):
            if IS_WIN:
                import subprocess; subprocess.Popen(["explorer", out_dir])
            elif IS_MAC:
                import subprocess; subprocess.Popen(["open", out_dir])
            else:
                import subprocess; subprocess.Popen(["xdg-open", out_dir])

    def _status(self, msg, color=TEXT2):
        self.status_lbl.configure(text=msg, fg=color)


# ─── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = WebPConverter()
    app.mainloop()
