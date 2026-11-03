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
FONTE_ICONE = "Segoe UI Emoji"   # ícones ficam num rótulo próprio, com a fonte própria deles
# Ajuste fino do alinhamento vertical (em pixels; positivo = desce, negativo = sobe).
# Se no seu Windows algum ícone ainda parecer 1-2 px acima/abaixo do texto, mexa só nestes valores.
ICONE_DESLOC_Y = 0
PONTO_DESLOC_Y = 1

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

_estado = {"tema": "noturno", "raiz": None, "botao": None, "pontos": []}


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
    e.layout("Plano.TNotebook.Tab", [])  # sem abas nativas: a barra_de_abas() faz o papel delas
    e.configure("Plano.TNotebook", background=pal["fundo"], borderwidth=0, tabmargins=(0, 0, 0, 0))
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
        args = ["-background", pal["campo"], "-foreground", pal["texto"],
                "-selectbackground", pal["destaque"], "-selectforeground", "#ffffff"]
        fonte = getattr(cb, "_fonte_lista", None)  # combos "grandes" também aumentam a lista que abre
        if fonte:
            args += ["-font", fonte]
        cb.tk.call(f"{pop}.f.l", "configure", *args)
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
        if nome == "noturno":
            botao.definir("\u2600", "Modo claro")
        else:
            botao.definir("\U0001F319", "Modo noturno")
    for cv, item in _estado["pontos"]:
        try:
            cv.itemconfigure(item, fill=pal["destaque"])
        except tk.TclError:
            pass


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


def _icone_limpo(icone: str) -> str:
    return (icone or "").replace("\ufe0f", "")  # seletor de emoji: o Tk não o usa e ele só atrapalha a largura


def _rotulo_icone(master, icone, tam, bg, fg, extra_y=0):
    """Rótulo só do ícone, com fonte de emoji própria: assim o ícone nunca desloca a linha do texto."""
    pady = (max(0, 2 * extra_y), max(0, -2 * extra_y))
    lbl = tk.Label(master, text=_icone_limpo(icone), font=(FONTE_ICONE, tam), bg=bg, fg=fg, bd=0,
                   padx=0, pady=0, highlightthickness=0)
    lbl.pack(side="left", pady=pady)
    return lbl


class BotaoIcone(tk.Frame):
    """Botão com ícone + texto alinhados ao centro (ícone e texto são rótulos separados)."""

    def __init__(self, master, comando, bg="#1a1a1a", fg="#ffffff", tam=9, padx=14, pady=6):
        super().__init__(master, bg=bg, cursor="hand2")
        self._comando = comando
        miolo = tk.Frame(self, bg=bg, cursor="hand2")
        miolo.pack(padx=padx, pady=pady)
        self._icone = _rotulo_icone(miolo, "", tam + 1, bg, fg, ICONE_DESLOC_Y)
        self._texto = tk.Label(miolo, text="", font=(FONTE, tam, "bold"), bg=bg, fg=fg, bd=0, padx=0, pady=0,
                               highlightthickness=0, cursor="hand2")
        self._texto.pack(side="left", padx=(8, 0))
        for w in (self, miolo, self._icone, self._texto):
            w.bind("<Button-1>", lambda e: self._comando())
            w.configure(cursor="hand2")

    def definir(self, icone, texto):
        self._icone.configure(text=_icone_limpo(icone))
        self._texto.configure(text=texto)


def barra_de_abas(raiz, nb, icones):
    """Troca as abas nativas por uma barra que preenche TODA a largura, com um ícone depois do nome.
    A navegação continua sendo do Notebook (nb.select), então nada muda no funcionamento.

    Cada aba é um 'ícone + texto' em rótulos separados, centralizados na mesma linha. Se a janela ficar
    estreita (ex.: metade da tela), as abas quebram em 2 ou mais linhas em vez de ficarem cortadas."""
    nb.configure(style="Plano.TNotebook")
    _estilo_ttk(raiz, TEMAS[_estado["tema"]])

    GAP, PADX, PADY = 1, 14, 9
    barra = tk.Frame(raiz, bg="#222222")
    barra.pack(side="top", fill="x", padx=10, pady=(8, 0), before=nb)
    try:
        nb.pack_configure(pady=(0, 10))
    except tk.TclError:
        pass

    itens = []     # (aba, celula, partes que mudam de cor, sublinha)
    celulas = []
    for aba in nb.tabs():
        nome = nb.tab(aba, "text")
        celula = tk.Frame(barra, bg="#121212", cursor="hand2")
        miolo = tk.Frame(celula, bg="#121212", cursor="hand2")
        miolo.pack(side="top", fill="both", expand=True)
        conteudo = tk.Frame(miolo, bg="#121212", cursor="hand2")
        conteudo.pack(expand=True, padx=PADX, pady=PADY)      # expand sem fill = centralizado
        txt = tk.Label(conteudo, text=nome, font=(FONTE, 10, "bold"), fg="#aaaaaa", bg="#121212", bd=0,
                       padx=0, pady=0, highlightthickness=0, cursor="hand2")
        txt.pack(side="left")
        ico = None
        if icones.get(nome):
            ico = _rotulo_icone(conteudo, icones[nome], 11, "#121212", "#aaaaaa", ICONE_DESLOC_Y)
            ico.pack_configure(padx=(7, 0))
            ico.configure(cursor="hand2")
        sublinha = tk.Frame(celula, bg="#121212", height=3)
        sublinha.pack(fill="x", side="bottom")
        partes = [celula, miolo, conteudo, txt] + ([ico] if ico else [])
        itens.append((aba, celula, partes, [txt] + ([ico] if ico else []), sublinha))
        celulas.append(celula)

        def clicar(_e, a=aba):
            nb.select(a)

        def sobre(_e=None, c=celula):
            marcar(hover=c)

        def fora(_e=None, c=celula):
            def checar():
                try:
                    x, y = c.winfo_pointerxy()
                    w = c.winfo_containing(x, y)
                except (tk.TclError, KeyError):
                    w = None
                if w is None or not (str(w) == str(c) or str(w).startswith(str(c) + ".")):
                    marcar(hover=None)
            c.after_idle(checar)

        for w in partes + [sublinha]:
            w.bind("<Button-1>", clicar)
            w.bind("<Enter>", sobre)
            w.bind("<Leave>", fora)

    def marcar(*_, hover=None):
        atual = nb.select()
        for aba, celula, partes, textos, sublinha in itens:
            ativo = aba == atual
            sobre_ela = celula is hover and not ativo
            bg = "#1a1a1a" if (ativo or sobre_ela) else "#121212"
            fg = "#38b6ff" if ativo else ("#e0e0e0" if sobre_ela else "#aaaaaa")
            for p in partes:
                p.config(bg=bg)
            for t in textos:
                t.config(fg=fg)
            sublinha.config(bg="#38b6ff" if ativo else "#121212")
        reaplicar(barra)

    # ---- distribuição das abas (1 linha se couber; senão, linhas equilibradas) ----
    ultimo = {}

    def distribuir(_e=None):
        W = barra.winfo_width()
        if W < 50 or not celulas:
            return
        nat = [c.winfo_reqwidth() for c in celulas]
        h = max(c.winfo_reqheight() for c in celulas)

        def quebrar(limite):
            linhas, atual, soma = [], [], 0
            for i, w in enumerate(nat):
                extra = GAP if atual else 0
                if atual and soma + extra + w > limite:
                    linhas.append(atual)
                    atual, soma, extra = [], 0, 0
                atual.append(i)
                soma += extra + w
            if atual:
                linhas.append(atual)
            return linhas

        linhas = quebrar(W)
        if len(linhas) > 1:  # equilibra: o menor limite que ainda cabe no mesmo número de linhas
            for limite in range(max(nat), W + 1, 4):
                cand = quebrar(limite)
                if len(cand) <= len(linhas):
                    linhas = cand
                    break
        chave = (W, h, tuple(map(tuple, linhas)), tuple(nat))
        if ultimo.get("chave") == chave:
            return
        ultimo["chave"] = chave
        barra.configure(height=len(linhas) * h + (len(linhas) - 1) * GAP)
        for r, idx in enumerate(linhas):
            livre = max(0, W - sum(nat[i] for i in idx) - GAP * (len(idx) - 1))
            base, resto = divmod(livre, len(idx))
            x = 0
            for k, i in enumerate(idx):
                w = nat[i] + base + (1 if k < resto else 0)
                celulas[i].place(x=x, y=r * (h + GAP), width=w, height=h)
                x += w + GAP

    barra.update_idletasks()
    barra.configure(height=max(c.winfo_reqheight() for c in celulas))
    barra.bind("<Configure>", distribuir, add="+")
    nb.bind("<<NotebookTabChanged>>", lambda e: marcar(), add="+")
    marcar()
    distribuir()
    return barra


def _ponto(master, bg="#121212", diametro=10):
    """Bolinha do cabeçalho desenhada num Canvas: fica exatamente no centro da faixa, sem depender de fonte."""
    cv = tk.Canvas(master, width=diametro + 4, height=28, bg=bg, highlightthickness=0, bd=0)
    item = cv.create_oval(0, 0, diametro, diametro, fill="#38b6ff", outline="")

    def centralizar(e=None):
        h = cv.winfo_height()
        x0 = 2
        y0 = (h - diametro) / 2 + PONTO_DESLOC_Y
        cv.coords(item, x0, y0, x0 + diametro, y0 + diametro)

    cv.bind("<Configure>", centralizar)
    _estado["pontos"].append((cv, item))
    return cv


def instalar(raiz, antes_de=None, titulo="RODA LISO", subtitulo="Performance Hub", icones_abas=None):
    """Cria o cabeçalho (com o botão de tema) e aplica o tema salvo.
    Chame depois de criar a interface; `antes_de` = widget que o cabeçalho deve preceder."""
    _estado["raiz"] = raiz
    _estado["tema"] = carregar_preferencia()

    cab = tk.Frame(raiz, bg="#121212", highlightbackground="#222222", highlightthickness=1)
    opcoes = {"side": "top", "fill": "x", "padx": 10, "pady": (10, 0)}
    if antes_de is not None:
        opcoes["before"] = antes_de
    cab.pack(**opcoes)

    _ponto(cab).pack(side="left", fill="y", padx=(14, 4), pady=8)
    tk.Label(cab, text=titulo, font=(FONTE, 13, "bold"), fg="#ffffff", bg="#121212", bd=0, pady=0).pack(side="left")
    tk.Label(cab, text=subtitulo, font=(FONTE, 9), fg="#aaaaaa", bg="#121212", bd=0, pady=0).pack(side="left", padx=(10, 0), pady=(3, 0))

    botao = BotaoIcone(cab, comando=lambda: alternar(raiz))
    botao.pack(side="right", padx=12, pady=8)
    _estado["botao"] = botao

    aplicar(raiz)
    if icones_abas is not None and antes_de is not None:
        barra_de_abas(raiz, antes_de, icones_abas)
    raiz.after(2000, lambda: _varredura(raiz))


class TextoJustificado(tk.Frame):
    """Texto justificado (como no Word): toda linha, menos a última de cada parágrafo, é esticada de uma
    ponta à outra do quadro. O Label do Tk não justifica, então cada palavra é um rótulo posicionado.
    Parágrafos são separados por uma linha em branco ("\\n\\n") no texto."""

    def __init__(self, master, texto, fonte, fg="#aaaaaa", bg="#121212", largura_min=220):
        super().__init__(master, bg=bg, width=largura_min, height=20)
        self._fonte = fonte
        self._medidor = tkfont.Font(root=self, font=fonte)
        self._fg, self._bg = fg, bg
        self._paragrafos = [p.split() for p in texto.split("\n\n") if p.strip()]
        self._rotulos = []
        self._ultima_largura = 0
        self._agendado = None
        self.bind("<Configure>", self._ao_redimensionar)

    def _ao_redimensionar(self, e):
        if e.width == self._ultima_largura or e.width < 60:
            return
        self._ultima_largura = e.width
        if self._agendado:
            self.after_cancel(self._agendado)
        self._agendado = self.after(15, self._montar)

    def _rotulo(self, i):
        while len(self._rotulos) <= i:
            self._rotulos.append(tk.Label(self, font=self._fonte, fg=self._fg, bg=self._bg, bd=0, padx=0, pady=0,
                                          highlightthickness=0))
        return self._rotulos[i]

    def _montar(self):
        self._agendado = None
        W = self._ultima_largura
        m = self._medidor
        alt = m.metrics("linespace")
        espaco = m.measure(" ")
        y, usados = 0, 0
        for n_par, palavras in enumerate(self._paragrafos):
            if n_par:
                y += alt                                   # linha em branco entre parágrafos
            larguras = [m.measure(p) for p in palavras]
            linhas, atual, soma = [], [], 0
            for p, w in zip(palavras, larguras):
                extra = espaco if atual else 0
                if atual and soma + extra + w > W:
                    linhas.append(atual)
                    atual, soma, extra = [], 0, 0
                atual.append((p, w))
                soma += extra + w
            if atual:
                linhas.append(atual)
            for k, linha in enumerate(linhas):
                ultima = k == len(linhas) - 1
                folga = W - sum(w for _, w in linha)
                gap = espaco if (ultima or len(linha) == 1) else folga / (len(linha) - 1)
                x = 0.0
                for p, w in linha:
                    lbl = self._rotulo(usados)
                    lbl.configure(text=p)
                    lbl.place(x=int(round(x)), y=y)
                    usados += 1
                    x += w + gap
                y += alt
        for lbl in self._rotulos[usados:]:
            lbl.place_forget()
        self.configure(height=max(y, alt))
        reaplicar(self)  # já pinta com o tema atual (sem esperar a varredura de 2 s)
