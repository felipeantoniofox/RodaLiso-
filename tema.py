"""Roda Liso - Tema noturno/claro para Tkinter.

Como funciona (sem reescrever as 1000 linhas da interface):
  * O roda_liso.py já usa um conjunto pequeno de cores fixas (#000000, #121212, #38b6ff ...).
    Cada cor vira um "papel" (fundo, painel, texto, destaque...) e cada tema define
    qual cor real o papel usa.
  * instalar() cria o cabeçalho com o botão de alternar tema e percorre todos os widgets,
    trocando as cores. A cor original de cada widget é guardada, então alternar várias
    vezes nunca "perde" a cor de origem.
  * Se o programa mudar uma cor depois (ex.: status verde/vermelho), a varredura
    periódica reaplica o tema nela.
  * A escolha do usuário fica salva em rodaliso_tema.json.
"""
import ctypes
import json
import os
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQ_TEMA = os.path.join(BASE_DIR, "rodaliso_tema.json")
FONTE = "Segoe UI"

TEMAS = {
    "noturno": {
        "fundo": "#0e1116", "painel": "#161b22", "campo": "#1f2630", "borda": "#2a313c",
        "texto": "#e6edf3", "suave": "#8b949e", "destaque": "#4cc2ff",
        "ok": "#2ea043", "perigo": "#e5484d", "azul": "#2f81f7",
        "neutro": "#4b5563", "aviso": "#f0883e", "amd": "#00a88f",
    },
    "claro": {
        "fundo": "#f4f6fa", "painel": "#ffffff", "campo": "#eef1f6", "borda": "#d0d7de",
        "texto": "#1f2328", "suave": "#57606a", "destaque": "#0969da",
        "ok": "#1a7f37", "perigo": "#cf222e", "azul": "#0969da",
        "neutro": "#6e7781", "aviso": "#bc4c00", "amd": "#00897b",
    },
}

# cor original (do código atual) -> papel
PAPEIS = {
    "#000000": "fundo", "#121212": "painel", "#1a1a1a": "campo", "#222222": "borda",
    "#ffffff": "texto", "#e0e0e0": "texto", "#aaaaaa": "suave", "#888888": "suave",
    "#38b6ff": "destaque", "#28a745": "ok", "#dc3545": "perigo", "#007bff": "azul",
    "#6c757d": "neutro", "#ff9800": "aviso", "#00a88f": "amd",
}
PAPEIS_NEUTROS = {"fundo", "painel", "campo", "borda"}

OPCOES_BG = ("bg", "highlightbackground", "selectcolor", "activebackground",
             "troughcolor", "buttonbackground", "readonlybackground", "disabledbackground")
OPCOES_FG = ("fg", "insertbackground", "activeforeground", "disabledforeground")

_estado = {"tema": "noturno", "raiz": None, "botao": None}


# ----------------------------------------------------------------- utilidades
def _hex(w, cor):
    try:
        r, g, b = w.winfo_rgb(cor)
        return "#%02x%02x%02x" % (r >> 8, g >> 8, b >> 8)
    except tk.TclError:
        return None


def _clarear(cor_hex, f=0.14):
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (1, 3, 5))
    r, g, b = (int(c + (255 - c) * f) for c in (r, g, b))
    return "#%02x%02x%02x" % (r, g, b)


def _papel(hex_cor, bg_kind):
    if bg_kind:
        if hex_cor == "#ffffff":
            return "campo"
        if hex_cor == "#f0f0f0":
            return "fundo"
    elif hex_cor == "#000000":  # texto padrão do Tk (preto) -> texto do tema
        return "texto"
    return PAPEIS.get(hex_cor)


def _percorrer(w):
    yield w
    for filho in w.winfo_children():
        yield from _percorrer(filho)


def carregar_preferencia() -> str:
    try:
        with open(ARQ_TEMA, "r", encoding="utf-8") as f:
            t = json.load(f).get("tema")
            return t if t in TEMAS else "noturno"
    except (OSError, ValueError):
        return "noturno"


def _salvar_preferencia(nome: str):
    try:
        with open(ARQ_TEMA, "w", encoding="utf-8") as f:
            json.dump({"tema": nome}, f)
    except OSError:
        pass


# ----------------------------------------------------------------- ttk
def _estilo_ttk(raiz, pal):
    e = ttk.Style(raiz)
    e.theme_use("clam")
    e.configure(".", background=pal["fundo"], foreground=pal["texto"], fieldbackground=pal["campo"],
                bordercolor=pal["borda"], lightcolor=pal["borda"], darkcolor=pal["borda"],
                troughcolor=pal["campo"], focuscolor=pal["fundo"], font=(FONTE, 9))
    e.configure("TFrame", background=pal["fundo"])
    e.configure("TLabel", background=pal["fundo"], foreground=pal["texto"])
    e.configure("TLabelframe", background=pal["fundo"], bordercolor=pal["borda"])
    e.configure("TLabelframe.Label", background=pal["fundo"], foreground=pal["destaque"],
                font=(FONTE, 9, "bold"))
    e.configure("TCheckbutton", background=pal["fundo"], foreground=pal["texto"])
    e.map("TCheckbutton", background=[("active", pal["fundo"])], foreground=[("active", pal["destaque"])],
          indicatorcolor=[("selected", pal["destaque"]), ("!selected", pal["campo"])])
    e.configure("TButton", background=pal["painel"], foreground=pal["texto"], padding=(14, 7),
                borderwidth=1, relief="flat", font=(FONTE, 9, "bold"))
    e.map("TButton", background=[("active", pal["campo"]), ("pressed", pal["borda"])])
    e.configure("Accent.TButton", background=pal["azul"], foreground="#ffffff")
    e.map("Accent.TButton", background=[("active", _clarear(pal["azul"])), ("pressed", pal["azul"])])
    e.configure("TNotebook", background=pal["fundo"], borderwidth=0, tabmargins=(2, 6, 2, 0))
    e.configure("TNotebook.Tab", background=pal["painel"], foreground=pal["suave"],
                padding=(9, 8), font=(FONTE, 9, "bold"), borderwidth=0)
    e.map("TNotebook.Tab", background=[("selected", pal["campo"]), ("active", pal["campo"])],
          foreground=[("selected", pal["destaque"]), ("active", pal["texto"])])
    e.configure("TCombobox", fieldbackground=pal["campo"], background=pal["painel"], foreground=pal["texto"],
                arrowcolor=pal["texto"], bordercolor=pal["borda"], lightcolor=pal["campo"],
                darkcolor=pal["campo"], selectbackground=pal["campo"], selectforeground=pal["texto"])
    e.map("TCombobox", fieldbackground=[("readonly", pal["campo"])], foreground=[("readonly", pal["texto"])],
          selectbackground=[("readonly", pal["campo"])], selectforeground=[("readonly", pal["texto"])])
    e.configure("Vertical.TScrollbar", background=pal["painel"], troughcolor=pal["fundo"],
                bordercolor=pal["fundo"], arrowcolor=pal["texto"])
    raiz.option_add("*TCombobox*Listbox.background", pal["campo"])
    raiz.option_add("*TCombobox*Listbox.foreground", pal["texto"])
    raiz.option_add("*TCombobox*Listbox.selectBackground", pal["destaque"])
    raiz.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")


def _lista_do_combobox(cb, pal):
    """A lista suspensa do Combobox é criada uma vez e reaproveitada: recolore a existente."""
    try:
        pop = cb.tk.call("ttk::combobox::PopdownWindow", str(cb))
        cb.tk.call(f"{pop}.f.l", "configure", "-background", pal["campo"], "-foreground", pal["texto"],
                   "-selectbackground", pal["destaque"], "-selectforeground", "#ffffff")
    except tk.TclError:
        pass


# ----------------------------------------------------------------- widgets tk
def _trocar_fonte(w):
    if getattr(w, "_rl_fonte", False):
        return
    w._rl_fonte = True
    try:
        descricao = str(w.cget("font"))
        if not descricao.lower().startswith("arial"):
            return
        f = tkfont.Font(root=w, font=descricao).actual()
    except tk.TclError:
        return
    estilo = []
    if f["weight"] == "bold":
        estilo.append("bold")
    if f["slant"] == "italic":
        estilo.append("italic")
    try:
        w.configure(font=(FONTE, f["size"], *estilo))
    except tk.TclError:
        pass


def _aplicar_widget(w, pal):
    if not hasattr(w, "_rl_orig"):
        w._rl_orig, w._rl_ult = {}, {}
    eh_botao = isinstance(w, tk.Button)
    mudancas = {}

    # 1) fundo primeiro, para saber se o widget é "colorido" (botão verde, faixa AMD...)
    bg_colorido = False
    for op in OPCOES_BG + OPCOES_FG:
        if eh_botao and op in ("activebackground", "activeforeground"):
            continue  # o hover do botão é tratado abaixo
        try:
            atual = str(w.cget(op))
        except tk.TclError:
            continue
        if not atual:
            continue
        if w._rl_ult.get(op) == atual:
            base = w._rl_orig[op]          # ainda é a nossa cor: usa a original guardada
        else:
            base = atual                   # cor nova (definida pelo programa): vira a original
            w._rl_orig[op] = base
        h = _hex(w, base)
        bg_kind = op in OPCOES_BG
        papel = _papel(h, bg_kind) if h else None
        if op == "bg" and papel and papel not in PAPEIS_NEUTROS:
            bg_colorido = True
        if papel is None or (not bg_kind and bg_colorido):
            nova = base                    # cor desconhecida/botão colorido: mantém
        else:
            nova = pal[papel]
        if nova != atual:
            mudancas[op] = nova
        w._rl_ult[op] = nova if nova != atual else atual

    if mudancas:
        try:
            w.configure(**mudancas)
        except tk.TclError:
            pass
        for op in mudancas:                # guarda como o Tk normalizou o valor
            try:
                w._rl_ult[op] = str(w.cget(op))
            except tk.TclError:
                pass

    if eh_botao:
        try:
            w.configure(highlightthickness=0, bd=0)
            bg = str(w.cget("bg"))
            fg = str(w.cget("fg"))
            w.configure(activebackground=_clarear(_hex(w, bg) or "#444444"), activeforeground=fg)
        except tk.TclError:
            pass
    if isinstance(w, tk.Checkbutton):
        try:
            w.configure(highlightthickness=0)
        except tk.TclError:
            pass
    _trocar_fonte(w)


def _passada_widgets(raiz, pal):
    for w in _percorrer(raiz):
        if isinstance(w, ttk.Widget):
            if isinstance(w, ttk.Combobox):
                _lista_do_combobox(w, pal)
            continue
        _aplicar_widget(w, pal)


def aplicar(raiz, nome=None):
    nome = nome or _estado["tema"]
    pal = TEMAS[nome]
    _estado["tema"] = nome
    _estilo_ttk(raiz, pal)
    _passada_widgets(raiz, pal)
    _barra_de_titulo(raiz, nome == "noturno")
    botao = _estado.get("botao")
    if botao is not None:
        botao.config(text="☀️  Modo claro" if nome == "noturno" else "🌙  Modo noturno")


def reaplicar(widget):
    """Reaplica o tema só na subárvore de `widget` (use depois de recriar widgets)."""
    _passada_widgets(widget, TEMAS[_estado["tema"]])


def _barra_de_titulo(raiz, escuro):
    """Barra de título escura no Windows 10/11 (ignora silenciosamente se não suportar)."""
    try:
        hwnd = ctypes.windll.user32.GetParent(raiz.winfo_id())
        valor = ctypes.c_int(1 if escuro else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(valor), ctypes.sizeof(valor))
    except Exception:
        pass


def alternar(raiz):
    novo = "claro" if _estado["tema"] == "noturno" else "noturno"
    aplicar(raiz, novo)
    _salvar_preferencia(novo)


def _varredura(raiz):
    """Reaplica o tema em cores que o programa mudou depois (status, mensagens...)."""
    try:
        _passada_widgets(raiz, TEMAS[_estado["tema"]])
        raiz.after(2000, lambda: _varredura(raiz))
    except tk.TclError:
        pass  # janela fechada


def instalar(raiz, antes_de=None, titulo="RODA LISO", subtitulo="Performance Hub"):
    """Cria o cabeçalho (com o botão de tema) e aplica o tema salvo.
    Chame depois de criar a interface; `antes_de` = widget que o cabeçalho deve preceder."""
    _estado["raiz"] = raiz
    _estado["tema"] = carregar_preferencia()

    cab = tk.Frame(raiz, bg="#121212", highlightbackground="#222222", highlightthickness=1)
    opcoes = {"side": "top", "fill": "x", "padx": 10, "pady": (10, 0)}
    if antes_de is not None:
        opcoes["before"] = antes_de
    cab.pack(**opcoes)

    tk.Label(cab, text="●", font=("Arial", 14, "bold"), fg="#38b6ff", bg="#121212").pack(side="left", padx=(14, 6), pady=8)
    tk.Label(cab, text=titulo, font=("Arial", 13, "bold"), fg="#ffffff", bg="#121212").pack(side="left")
    tk.Label(cab, text=subtitulo, font=("Arial", 9), fg="#aaaaaa", bg="#121212").pack(side="left", padx=(10, 0), pady=(3, 0))

    botao = tk.Button(cab, text="", font=("Arial", 9, "bold"), fg="#ffffff", bg="#1a1a1a", relief="flat",
                      padx=14, pady=6, cursor="hand2", bd=0, command=lambda: alternar(raiz))
    botao.pack(side="right", padx=12, pady=8)
    _estado["botao"] = botao

    aplicar(raiz)
    raiz.after(2000, lambda: _varredura(raiz))
