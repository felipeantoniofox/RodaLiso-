import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
import os
import sys
import subprocess
import shutil
import threading
import ctypes

# --- NITIDEZ EM TELAS COM ESCALA (125%, 150%...) ---
# Sem isso o Windows desenha a janela em 96 DPI e AMPLIA a imagem pronta (fica borrada).
# Declarando o programa "ciente de DPI", o Windows deixa o Tk desenhar direto na resolução nativa.
# Precisa rodar ANTES de criar a janela (tk.Tk()).
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)      # Windows 8.1+
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()       # Windows Vista/7/8
    except Exception:
        pass

ESCALA_UI = 1.0  # fator da escala do Windows (1.25 = 125%); calculado quando a janela é criada


def _px(valor):
    """Converte um tamanho em pixels 'de projeto' (96 DPI) para pixels reais da tela."""
    return int(round(valor * ESCALA_UI))


def _forma_arredondada(canvas, x1, y1, x2, y2, raio, **opcoes):
    """Desenha um retângulo arredondado suave em um Canvas do Tk."""
    raio = max(2, min(raio, (x2 - x1) / 2, (y2 - y1) / 2))
    pontos = [
        x1 + raio, y1, x2 - raio, y1,
        x2, y1, x2, y1 + raio,
        x2, y2 - raio, x2, y2,
        x2 - raio, y2, x1 + raio, y2,
        x1, y2, x1, y2 - raio,
        x1, y1 + raio, x1, y1,
    ]
    return canvas.create_polygon(pontos, smooth=True, splinesteps=32, **opcoes)


def _clarear_cor(cor, fator=0.12):
    try:
        r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
        r, g, b = (min(255, int(c + (255 - c) * fator)) for c in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"
    except (TypeError, ValueError):
        return cor


class PainelArredondado(tk.Frame):
    """Superfície com cantos arredondados que aceita widgets em `conteudo`."""

    _TOKENS = {
        "#000000": "fundo", "#121212": "painel", "#1a1a1a": "campo", "#222222": "borda",
        "#38b6ff": "destaque", "#28a745": "ok", "#dc3545": "perigo", "#ff9800": "aviso",
    }

    def __init__(self, master, papel="painel", borda="#222222", raio=14, padding=18, altura=None):
        try:
            fundo_pai = master.cget("bg")
        except tk.TclError:
            fundo_pai = "#000000"
        super().__init__(master, bg=fundo_pai, bd=0, highlightthickness=0)
        self._papel = papel
        self._cor_superficie = "#121212" if papel == "painel" else "#1a1a1a"
        self._token_borda = self._TOKENS.get(borda.lower()) if isinstance(borda, str) else None
        self._cor_borda = borda
        self._raio = _px(raio)
        self._padding = _px(padding)
        self._canvas = tk.Canvas(self, bg=fundo_pai, bd=0, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True)
        self.conteudo = tk.Frame(self._canvas, bg=self._cor_superficie, bd=0, highlightthickness=0)
        self._janela = self._canvas.create_window(
            self._padding, self._padding, anchor="nw", window=self.conteudo
        )
        if altura is not None:
            self.configure(height=_px(altura))
            self.pack_propagate(False)
            self.grid_propagate(False)
        self._canvas.bind("<Configure>", self._redesenhar)
        if altura is None:
            self.conteudo.bind("<Configure>", self._ajustar_altura_ao_conteudo, add="+")

    def _ajustar_altura_ao_conteudo(self, _evento=None):
        try:
            altura_pedida = self.conteudo.winfo_reqheight() + 2 * self._padding
            if altura_pedida > 1 and self._canvas.winfo_reqheight() != altura_pedida:
                self._canvas.configure(height=altura_pedida)
        except tk.TclError:
            pass

    def _redesenhar(self, _evento=None):
        largura = self._canvas.winfo_width()
        altura = self._canvas.winfo_height()
        if largura < 4 or altura < 4:
            return
        self._canvas.delete("superficie")
        _forma_arredondada(
            self._canvas, 1, 1, largura - 1, altura - 1, self._raio,
            fill=self._cor_superficie, outline=self._cor_borda, width=1, tags="superficie"
        )
        self._canvas.tag_lower("superficie")
        interno_l = max(1, largura - 2 * self._padding)
        interno_a = max(1, altura - 2 * self._padding)
        self._canvas.coords(self._janela, self._padding, self._padding)
        self._canvas.itemconfigure(self._janela, width=interno_l, height=interno_a)

    def definir_borda(self, cor):
        self._token_borda = self._TOKENS.get(cor.lower()) if isinstance(cor, str) else None
        self._cor_borda = cor
        self._redesenhar()

    def _aplicar_paleta(self, pal):
        self._cor_superficie = pal.get(self._papel, self._cor_superficie)
        if self._token_borda:
            self._cor_borda = pal[self._token_borda]
        try:
            fundo_pai = self.master.cget("bg")
            self.configure(bg=fundo_pai)
            self._canvas.configure(bg=fundo_pai)
        except tk.TclError:
            pass
        self.conteudo.configure(bg=self._cor_superficie)
        self._redesenhar()


class ComboModerno(tk.Canvas):
    """Seletor arredondado com popup escuro, hover e destaque de foco."""

    def __init__(self, master, valores, fonte=("Segoe UI", 10), altura=44):
        try:
            fundo_pai = master.cget("bg")
        except tk.TclError:
            fundo_pai = "#121212"
        super().__init__(
            master, height=_px(altura), bg=fundo_pai, bd=0, highlightthickness=0,
            cursor="hand2", takefocus=1
        )
        self._valores = list(valores)
        self._valor = ""
        self._fonte = fonte
        self._popup = None
        self._sobre = False
        self._foco = False
        self._cores = {
            "campo": "#1f2630", "borda": "#2a313c", "texto": "#e6edf3",
            "suave": "#8b949e", "destaque": "#4cc2ff", "painel": "#161b22",
        }
        self.bind("<Configure>", self._desenhar)
        self.bind("<Button-1>", self._alternar_popup)
        self.bind("<Enter>", lambda _e: self._mudar_sobre(True))
        self.bind("<Leave>", lambda _e: self._mudar_sobre(False))
        self.bind("<FocusIn>", lambda _e: self._mudar_foco(True))
        self.bind("<FocusOut>", lambda _e: self._mudar_foco(False))
        self.bind("<Return>", self._alternar_popup)
        self.bind("<space>", self._alternar_popup)
        self.bind("<Escape>", lambda _e: self._fechar_popup())
        self.bind("<Down>", lambda _e: self._mover(1))
        self.bind("<Up>", lambda _e: self._mover(-1))

    def _mudar_sobre(self, ativo):
        self._sobre = ativo
        self._desenhar()

    def _mudar_foco(self, ativo):
        self._foco = ativo
        self._desenhar()

    def _desenhar(self, _evento=None):
        largura, altura = self.winfo_width(), self.winfo_height()
        if largura < 4 or altura < 4:
            return
        self.delete("all")
        cor_borda = self._cores["destaque"] if (self._foco or self._popup) else self._cores["borda"]
        cor_campo = _clarear_cor(self._cores["campo"], 0.045) if self._sobre else self._cores["campo"]
        _forma_arredondada(
            self, 1, 1, largura - 1, altura - 1, _px(10),
            fill=cor_campo, outline=cor_borda, width=2 if (self._foco or self._popup) else 1
        )
        texto = self._valor or "Selecione uma opção"
        self.create_text(
            _px(14), altura / 2, text=texto, anchor="w", font=self._fonte,
            fill=self._cores["texto"] if self._valor else self._cores["suave"]
        )
        x = largura - _px(17)
        y = altura / 2
        self.create_line(x - _px(4), y - _px(2), x, y + _px(2), fill=self._cores["suave"], width=2)
        self.create_line(x, y + _px(2), x + _px(4), y - _px(2), fill=self._cores["suave"], width=2)

    def _alternar_popup(self, _evento=None):
        self.focus_set()
        if self._popup and self._popup.winfo_exists():
            self._fechar_popup()
        else:
            self._abrir_popup()
        return "break"

    def _abrir_popup(self):
        if not self._valores:
            return
        topo = tk.Toplevel(self)
        self._popup = topo
        topo.withdraw()
        topo.overrideredirect(True)
        topo.transient(self.winfo_toplevel())
        transparente = "#010203"
        topo.configure(bg=transparente)
        try:
            topo.wm_attributes("-transparentcolor", transparente)
        except tk.TclError:
            transparente = self._cores["painel"]
            topo.configure(bg=transparente)
        largura = max(self.winfo_width(), _px(220))
        linhas = min(8, len(self._valores))
        altura_linha = _px(36)
        margem = _px(6)
        altura = linhas * altura_linha + margem * 2
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + _px(4)
        if y + altura > self.winfo_screenheight() - _px(12):
            y = self.winfo_rooty() - altura - _px(4)
        topo.geometry(f"{largura}x{altura}+{x}+{y}")

        caixa = tk.Canvas(
            topo, width=largura, height=altura, bg=transparente, bd=0,
            highlightthickness=0, cursor="hand2", takefocus=1
        )
        caixa.pack(fill="both", expand=True)
        atual = self._valores.index(self._valor) if self._valor in self._valores else 0
        estado = {
            "ativo": atual,
            "inicio": max(0, min(atual - linhas // 2, len(self._valores) - linhas)),
        }

        def manter_visivel():
            if estado["ativo"] < estado["inicio"]:
                estado["inicio"] = estado["ativo"]
            elif estado["ativo"] >= estado["inicio"] + linhas:
                estado["inicio"] = estado["ativo"] - linhas + 1

        def desenhar_opcoes():
            caixa.delete("all")
            _forma_arredondada(
                caixa, 1, 1, largura - 1, altura - 1, _px(11),
                fill=self._cores["painel"], outline=self._cores["borda"], width=1
            )
            fim = min(len(self._valores), estado["inicio"] + linhas)
            for posicao, indice in enumerate(range(estado["inicio"], fim)):
                y1 = margem + posicao * altura_linha
                y2 = y1 + altura_linha
                if indice == estado["ativo"]:
                    _forma_arredondada(
                        caixa, margem, y1 + _px(2), largura - margem, y2 - _px(2), _px(8),
                        fill=_clarear_cor(self._cores["campo"], 0.08), outline=""
                    )
                    caixa.create_rectangle(
                        margem, y1 + _px(10), margem + _px(3), y2 - _px(10),
                        fill=self._cores["destaque"], outline=""
                    )
                caixa.create_text(
                    margem + _px(14), (y1 + y2) / 2, text=self._valores[indice],
                    anchor="w", font=self._fonte, fill=self._cores["texto"]
                )
                if self._valores[indice] == self._valor:
                    caixa.create_text(
                        largura - margem - _px(12), (y1 + y2) / 2, text="\u2713",
                        anchor="e", font=("Segoe UI", 10, "bold"), fill=self._cores["destaque"]
                    )

        def indice_do_mouse(evento):
            posicao = int((evento.y - margem) // altura_linha)
            if 0 <= posicao < linhas:
                indice = estado["inicio"] + posicao
                if indice < len(self._valores):
                    return indice
            return None

        def escolher(_evento=None):
            indice = estado["ativo"]
            if _evento is not None and getattr(_evento, "num", None) == 1:
                indice_apontado = indice_do_mouse(_evento)
                if indice_apontado is not None:
                    indice = indice_apontado
            if 0 <= indice < len(self._valores):
                self.set(self._valores[indice])
                self._fechar_popup()
                self.event_generate("<<ComboboxSelected>>")
            return "break"

        def acompanhar_mouse(evento):
            indice = indice_do_mouse(evento)
            if indice is not None and indice != estado["ativo"]:
                estado["ativo"] = indice
                desenhar_opcoes()

        def mover_popup(passo):
            estado["ativo"] = max(0, min(len(self._valores) - 1, estado["ativo"] + passo))
            manter_visivel()
            desenhar_opcoes()
            return "break"

        def rolar(evento):
            passo = -1 if evento.delta > 0 else 1
            limite = max(0, len(self._valores) - linhas)
            estado["inicio"] = max(0, min(limite, estado["inicio"] + passo))
            estado["ativo"] = max(
                estado["inicio"], min(estado["ativo"], estado["inicio"] + linhas - 1)
            )
            desenhar_opcoes()
            return "break"

        desenhar_opcoes()
        caixa.bind("<Motion>", acompanhar_mouse)
        caixa.bind("<ButtonRelease-1>", escolher)
        caixa.bind("<Return>", escolher)
        caixa.bind("<Up>", lambda _e: mover_popup(-1))
        caixa.bind("<Down>", lambda _e: mover_popup(1))
        caixa.bind("<MouseWheel>", rolar)
        caixa.bind("<Escape>", lambda _e: self._fechar_popup())
        topo.bind("<FocusOut>", lambda _e: topo.after(80, self._fechar_se_perdeu_foco))
        topo.deiconify()
        topo.lift()
        caixa.focus_set()
        self._desenhar()

    def _fechar_se_perdeu_foco(self):
        if self._popup and self._popup.winfo_exists():
            foco = self._popup.focus_get()
            if foco is None:
                self._fechar_popup()

    def _fechar_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        self._desenhar()

    def _mover(self, passo):
        if not self._valores:
            return "break"
        atual = self._valores.index(self._valor) if self._valor in self._valores else -1
        self.set(self._valores[(atual + passo) % len(self._valores)])
        self.event_generate("<<ComboboxSelected>>")
        return "break"

    def get(self):
        return self._valor

    def set(self, valor):
        self._valor = str(valor)
        self._desenhar()

    def current(self, indice=None):
        if indice is None:
            return self._valores.index(self._valor) if self._valor in self._valores else -1
        if 0 <= indice < len(self._valores):
            self.set(self._valores[indice])

    def configurar_valores(self, valores):
        self._valores = list(valores)
        if self._valor not in self._valores:
            self.set("")

    def _aplicar_paleta(self, pal):
        self._cores.update({k: pal[k] for k in self._cores if k in pal})
        try:
            self.configure(bg=self.master.cget("bg"))
        except tk.TclError:
            pass
        self._desenhar()


class BotaoModerno(tk.Canvas):
    """Botão primário arredondado com estados de hover e clique."""

    def __init__(self, master, texto, comando, fonte=("Segoe UI", 10, "bold"), altura=46):
        try:
            fundo_pai = master.cget("bg")
        except tk.TclError:
            fundo_pai = "#121212"
        super().__init__(master, height=_px(altura), bg=fundo_pai, bd=0, highlightthickness=0, cursor="hand2")
        self._texto = texto
        self._comando = comando
        self._fonte = fonte
        self._cor = "#2f81f7"
        self._sobre = False
        self._pressionado = False
        self.bind("<Configure>", self._desenhar)
        self.bind("<Enter>", lambda _e: self._estado(sobre=True))
        self.bind("<Leave>", lambda _e: self._estado(sobre=False, pressionado=False))
        self.bind("<ButtonPress-1>", lambda _e: self._estado(pressionado=True))
        self.bind("<ButtonRelease-1>", self._clicar)

    def _estado(self, sobre=None, pressionado=None):
        if sobre is not None:
            self._sobre = sobre
        if pressionado is not None:
            self._pressionado = pressionado
        self._desenhar()

    def _clicar(self, evento):
        estava_pressionado = self._pressionado
        self._pressionado = False
        self._desenhar()
        if estava_pressionado and 0 <= evento.x <= self.winfo_width() and 0 <= evento.y <= self.winfo_height():
            self._comando()

    def _desenhar(self, _evento=None):
        largura, altura = self.winfo_width(), self.winfo_height()
        if largura < 4 or altura < 4:
            return
        self.delete("all")
        cor = _clarear_cor(self._cor, 0.12 if self._sobre else 0.0)
        if self._pressionado:
            cor = self._cor
        _forma_arredondada(self, 1, 1, largura - 1, altura - 1, _px(10), fill=cor, outline=cor)
        self.create_text(largura / 2, altura / 2, text=self._texto, font=self._fonte, fill="#ffffff")

    def _aplicar_paleta(self, pal):
        self._cor = pal.get("azul", self._cor)
        try:
            self.configure(bg=self.master.cget("bg"))
        except tk.TclError:
            pass
        self._desenhar()


def _cabecalho_aba(master, titulo, subtitulo):
    cabecalho = tk.Frame(master, bg="#000000")
    cabecalho.pack(fill="x", pady=(0, _px(16)))
    tk.Label(
        cabecalho, text=titulo, font=(tema.FONTE, 20, "bold"),
        fg="#ffffff", bg="#000000", anchor="w"
    ).pack(fill="x")
    tk.Label(
        cabecalho, text=subtitulo, font=(tema.FONTE, 10),
        fg="#aaaaaa", bg="#000000", anchor="w", justify="left"
    ).pack(fill="x", pady=(_px(4), 0))
    return cabecalho


def _titulo_card(master, titulo, subtitulo=None):
    tk.Label(
        master, text=titulo, font=(tema.FONTE, 13, "bold"),
        fg="#ffffff", bg="#121212", anchor="w", justify="left"
    ).pack(fill="x")
    if subtitulo:
        tk.Label(
            master, text=subtitulo, font=(tema.FONTE, 9),
            fg="#aaaaaa", bg="#121212", anchor="w", justify="left",
            wraplength=_px(420)
        ).pack(fill="x", pady=(_px(4), _px(16)))


def _botao_acao(master, texto, comando=None, cor="#2f81f7", state="normal"):
    return tk.Button(
        master, text=texto, command=comando, state=state,
        bg=cor, activebackground=_clarear_cor(cor, 0.1), fg="white",
        activeforeground="white", disabledforeground="#7d8590",
        font=(tema.FONTE, 10, "bold"), relief="flat", bd=0,
        padx=_px(16), pady=_px(10), cursor="hand2"
    )

# Importação condicional do monitoramento da IA
try:
    from monitor import iniciar_monitoramento_tempo_real
except ImportError:
    def iniciar_monitoramento_tempo_real(limite_fps, segundos_consecutivos=10, delay_inicio_jogo=120):
        print(f"[Placeholder] Thread de monitoramento da IA iniciada buscando {limite_fps} FPS em segundo plano.")

# Importação condicional do filtro de nitidez (ReShade/CAS)
try:
    from nitidez import (NIVEIS_NITIDEZ, aplicar_nitidez, remover_nitidez,
                         localizar_pasta_exe, salvar_pasta_manual, status_nitidez,
                         reshade_precisa_instalar, instalar_reshade)
except ImportError:
    def reshade_precisa_instalar(*args, **kwargs): return False
    def instalar_reshade(*args, **kwargs): return False, "Módulo nitidez.py não encontrado na pasta do projeto."
    NIVEIS_NITIDEZ = {"Baixa (Suave)": 0.3, "Média (Padrão)": 0.5, "Alta (Nítida)": 0.7, "Máxima (Agressiva)": 0.9}
    def aplicar_nitidez(*args, **kwargs): return False, "Módulo nitidez.py não encontrado na pasta do projeto."
    def remover_nitidez(*args, **kwargs): return False, "Módulo nitidez.py não encontrado na pasta do projeto."
    def localizar_pasta_exe(*args, **kwargs): return None
    def salvar_pasta_manual(*args, **kwargs): return None
    def status_nitidez(*args, **kwargs): return "Desligado"

# --- BANCO DE DADOS (Escala 1 a 1000) ---
CPUS = {
    "Intel Core i7-950": 150,
    "Intel Core i3-4130": 150,
    "Intel Core i5-4590": 280,
    "Intel Core i5-9400F": 450,
    "AMD Ryzen 5 5500U": 520,
    "AMD Ryzen 5 5600X": 720,
    "AMD Ryzen 5 7535HS": 780,
    "Intel Core i9-14900K": 980
}

GPUS = {
    "Intel HD Graphics 4000": 50,
    "AMD Radeon Vega 7 (Integrated)": 110,
    "AMD Radeon 660M (Integrated)": 140,
    "NVIDIA GTX 750 Ti": 65,
    "NVIDIA GTX 950": 88,
    "NVIDIA GTX 960": 95,
    "NVIDIA GTX 1050 Ti": 102,
    "NVIDIA GTX 1060 6GB": 160,
    "NVIDIA RTX 3060": 680,
    "AMD Radeon RX 7900 XT": 890,
    "NVIDIA RTX 4090": 1161,
    "NVIDIA RTX 5090": 1522
}

RAMS = ["256 MB", "512 MB", "1 GB", "2 GB", "4 GB", "8 GB", "16 GB", "32 GB", "64 GB"]

JOGOS = {
    "CS 2": {"cpu": 200, "gpu": 150, "ram": "4 GB", "capa": "capas/cs2.png"},
    "GTA V": {"cpu": 400, "gpu": 350, "ram": "8 GB", "capa": "capas/gtav.png"},
    "Red Dead Redemption 2": {"cpu": 600, "gpu": 550, "ram": "12 GB", "capa": "capas/rdr2.png"},
    "Cyberpunk 2077": {"cpu": 800, "gpu": 850, "ram": "16 GB", "capa": "capas/cyberpunk.png"},
    "MW2 2009": {"cpu": 100, "gpu": 45, "ram": "1 GB", "capa": "capas/mw2.png"},
    "Black Ops 2": {"cpu": 110, "gpu": 50, "ram": "2 GB", "capa": "capas/bo2.png"},
    "MW3 2011": {"cpu": 100, "gpu": 50, "ram": "2 GB", "capa": "capas/mw3.png"}
}

TUTORIAIS = {
    "Limpeza de Sistema e Debloat": {
        "desc": "Remova aplicativos desnecessários em segundo plano do Windows 10/11 para liberar memória RAM e ciclos de CPU.",
        "url": "https://www.youtube.com/results?search_query=debloat+windows+10+11"
    },
    "Undervolt e Gestão Térmica": {
        "desc": "Aprenda a reduzir as temperaturas da GPU mantendo ou aumentando o desempenho com curvas de tensão otimizadas.",
        "url": "https://www.youtube.com/results?search_query=tutorial+undervolt+gpu+ptbr"
    },
    "Gestão Térmica Processadores Ryzen": {
        "desc": "Ajuste limites de consumo (PPT/TDC/EDC) e curva de fans para diminuir o aquecimento dos processadores AMD.",
        "url": "https://www.youtube.com/watch?v=frsiS3g0-Mk"
    },
    "Overclock Seguro em Placa de Vídeo": {
        "desc": "Aumente os clocks de memória e núcleo via MSI Afterburner mantendo a estabilidade em jogos pesados.",
        "url": "https://www.youtube.com/watch?v=BUMwelj3SaY"
    },
    "Conversão DirectX para Vulkan (DXVK)": {
        "desc": "Guia para traduzir chamadas DirectX 9/10/11 para Vulkan, eliminando engasgos (stuttering) em jogos antigos.",
        "url": "https://github.com/doitsujin/DXVK"
    },
    "Otimização de Drivers Legacy": {
        "desc": "Como realizar a instalação limpa de drivers descontinuados para GPUs antigas usando DDU.",
        "url": "https://www.youtube.com/results?search_query=como+instalar+drivers+antigos+corretamente"
    }
}

FIXES = {
    "Assassin's Creed 4 Black Flag 2013 - Resolução de Crash": {
        "arquivo_alvo": "GFXSettings.AC4BFSP.xml",
        "descricao": "Diminui a probabilidade de o jogo fechar sozinho em cenas aleatórias.",
        "conteudo": "-ignoreDifferentVideoCard\n-DX11\n-unlimitedcputails\n-strMemLim 4096\n-BFM\n-frameLimit 0"
    },
    "CS 2 - Autoexec de Alto Desempenho": {
        "arquivo_alvo": "autoexec.cfg",
        "descricao": "Otimiza a taxa de quadros (FPS), reduz o input lag e desativa efeitos visuais pesados.",
        "conteudo": "fps_max 0\ncl_forcepreload 1\nr_drawtracers_firstperson 0\nengine_low_latency_sleep_after_client_tick true\n"
    },
    "Cyberpunk 2077 - Stutter Fix": {
        "arquivo_alvo": "engine_config.ini",
        "descricao": "Melhora o carregamento assíncrono de arquivos para evitar quedas bruscas de FPS na cidade.",
        "conteudo": "[Streaming]\nAsyncEngineLoading = true\nDisableAsyncLoading = false\n"
    },
    "Geral - Fix de DXVK para Placas Antigas": {
        "arquivo_alvo": "dxvk.conf",
        "descricao": "Força a compilação de shaders em segundo plano para jogos convertidos de DirectX para Vulkan.",
        "conteudo": "dxvk.enableAsync = true\ndxvk.numCompilerThreads = 0\n"
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_HOME = os.path.expanduser("~") 
LOCAL_APP_DATA = os.environ.get('LOCALAPPDATA', '') 

PRESETS_EMPURRAO = {
    "The Witcher 3 2015": {
        "arquivo_alvo": "user.settings", 
        "descricao_geral": "Ajuste de gráficos do jogo conforme pastas selecionadas.",
        "pasta_backup": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "original antes das modificações"),
        "caminhos_comuns": [
            os.path.join(USER_HOME, "Documents", "The Witcher 3", "user.settings"),
            os.path.join(USER_HOME, "OneDrive", "Documentos", "The Witcher 3", "user.settings"),
            os.path.join(USER_HOME, "Documentos", "The Witcher 3", "user.settings")
        ],
        "niveis": {
            "Nível 1 - Mais Baixo (Máx. FPS)": {
                "arquivo": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "Mais Baixo", "user.settings"), 
                "img": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "Mais Baixo", "preview.png")
            },
            "Nível 2 - Baixo": {
                "arquivo": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "baixo", "user.settings"), 
                "img": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "baixo", "preview.png")
            },
            "Nível 3 - Normal": {
                "arquivo": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "normal", "user.settings"), 
                "img": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "normal", "preview.png")
            },
            "Nível 4 - Alto": {
                "arquivo": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "alto", "user.settings"), 
                "img": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "alto", "preview.png")
            },
            "Nível 5 - Muito Alto": {
                "arquivo": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "muito alto", "user.settings"), 
                "img": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "muito alto", "preview.png")
            },
            "Nível 6 - Ultra (Empurrãozinho)": {
                "arquivo": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "ultra", "user.settings"), 
                "img": os.path.join(BASE_DIR, "presets", "The Witcher 3 2015", "ultra", "preview.png")
            }
        }
    },
    "Cyberpunk 2077": {
        "arquivo_alvo": "UserSettings.json",
        "descricao_geral": "Desativa opções pesadas do motor gráfico.",
        "pasta_backup": os.path.join(BASE_DIR, "presets", "cyberpunk", "original antes das modificações"),
        "caminhos_comuns": [
            os.path.join(LOCAL_APP_DATA, "CD Projekt Red", "Cyberpunk 2077", "UserSettings.json")
        ],
        "niveis": {} 
    }
}

# --- AUTO-DETECÇÃO DE HARDWARE ---
def auto_detectar_hardware():
    cpu_encontrada, gpu_encontrada, ram_encontrada = "", "", ""
    try:
        cmd_cpu = 'powershell "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"'
        out_cpu = subprocess.check_output(cmd_cpu, shell=True, text=True, encoding="utf-8", errors="ignore").strip()
        for c in CPUS.keys():
            modelo = c.replace("Intel ", "").replace("Core ", "").replace("AMD ", "").replace("Ryzen ", "")
            if modelo.lower() in out_cpu.lower():
                cpu_encontrada = c
                break

        cmd_gpu = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
        out_gpu = subprocess.check_output(cmd_gpu, shell=True, text=True, encoding="utf-8", errors="ignore").strip()
        for g in GPUS.keys():
            modelo = g.replace("NVIDIA ", "").replace("AMD ", "").replace("Intel ", "")
            if modelo.lower() in out_gpu.lower():
                gpu_encontrada = g
                break

        cmd_ram = 'powershell "(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum"'
        out_ram = subprocess.check_output(cmd_ram, shell=True, text=True, encoding="utf-8", errors="ignore").strip()
        if out_ram.isdigit():
            gb = round(int(out_ram) / (1024**3))
            ram_encontrada = f"{gb} GB"
    except Exception:
        pass

    return cpu_encontrada, gpu_encontrada, ram_encontrada

# --- FUNÇÕES AUXILIARES ---
def converter_ram_para_mb(ram_str):
    partes = ram_str.strip().split()
    valor = int(partes[0])
    unidade = partes[1].upper()
    return valor * 1024 if unidade == "GB" else valor

def abrir_video(url):
    webbrowser.open(url)

# --- LÓGICA DA ABA 1 (DIAGNÓSTICO) ---
def _mostrar_resultado_diagnostico(titulo: str, detalhe: str, cor: str):
    """Atualiza o cartão de resultado da tela de diagnóstico."""
    lbl_resultado_status.config(text=titulo, fg=cor)
    lbl_resultado.config(text=detalhe, fg="#e0e0e0")
    if hasattr(frame_resultado_diag, "definir_borda"):
        frame_resultado_diag.definir_borda(cor)
    else:
        frame_resultado_diag.config(highlightbackground=cor)


def atualizar_jogo_selecionado(event=None):
    jogo = combo_jogos.get()
    if jogo in JOGOS:
        dados = JOGOS[jogo]
        caminho_capa = dados["capa"]
        if not os.path.isabs(caminho_capa):
            caminho_capa = os.path.join(BASE_DIR, caminho_capa)

        lbl_jogo_nome.config(text=jogo)
        lbl_jogo_requisitos.config(
            text=(f"Referência cadastrada\n"
                  f"CPU: {dados['cpu']} pts   GPU: {dados['gpu']} pts\n"
                  f"Memória: {dados['ram']}")
        )

        if os.path.exists(caminho_capa):
            try:
                img = tk.PhotoImage(file=caminho_capa)
                fator = max(1, (img.width() + _px(139)) // _px(140),
                            (img.height() + _px(159)) // _px(160))
                if fator > 1:
                    img = img.subsample(fator, fator)
                lbl_imagem_jogo.config(image=img, text="")
                lbl_imagem_jogo.image = img
            except Exception:
                lbl_imagem_jogo.config(image="", text="Capa indisponível", fg="#888888")
                lbl_imagem_jogo.image = None
        else:
            lbl_imagem_jogo.config(image="", text="Capa não disponível\npara este título", fg="#888888")
            lbl_imagem_jogo.image = None

        _mostrar_resultado_diagnostico(
            "Pronto para analisar",
            "Confira os componentes e inicie a comparação. Nenhuma configuração do PC será alterada.",
            "#38b6ff",
        )

def verificar_compatibilidade():
    cpu_escolhida = combo_cpu.get()
    gpu_escolhida = combo_gpu.get()
    ram_escolhida = combo_ram.get()
    jogo_escolhido = combo_jogos.get()

    if not all([cpu_escolhida, gpu_escolhida, ram_escolhida, jogo_escolhido]):
        _mostrar_resultado_diagnostico(
            "Complete os campos",
            "Selecione processador, placa de vídeo, memória e jogo antes de analisar.",
            "#ff9800",
        )
        return

    pontos_cpu = CPUS[cpu_escolhida]
    pontos_gpu = GPUS[gpu_escolhida]
    ram_pc_mb = converter_ram_para_mb(ram_escolhida)
    
    req_cpu = JOGOS[jogo_escolhido]["cpu"]
    req_gpu = JOGOS[jogo_escolhido]["gpu"]
    req_ram_mb = converter_ram_para_mb(JOGOS[jogo_escolhido]["ram"])

    if pontos_cpu >= req_cpu and pontos_gpu >= req_gpu and ram_pc_mb >= req_ram_mb:
        _mostrar_resultado_diagnostico(
            "Compatível com o perfil",
            (f"CPU e GPU somam {pontos_cpu + pontos_gpu} pontos e a memória atende aos "
             f"{JOGOS[jogo_escolhido]['ram']} cadastrados. Esta é uma estimativa, não um benchmark."),
            "#28a745",
        )
    elif ram_pc_mb < req_ram_mb:
        _mostrar_resultado_diagnostico(
            "Memória abaixo do requisito",
            f"O perfil pede {JOGOS[jogo_escolhido]['ram']}, mas a seleção atual possui {ram_escolhida}.",
            "#dc3545",
        )
    else:
        gargalo = "GPU" if pontos_gpu < req_gpu else "CPU"
        diff = req_gpu - pontos_gpu if gargalo == "GPU" else req_cpu - pontos_cpu
        _mostrar_resultado_diagnostico(
            f"Limite identificado na {gargalo}",
            f"A pontuação está {diff} pontos abaixo da referência cadastrada para {jogo_escolhido}.",
            "#ff9800",
        )

# --- LÓGICA DA ABA 2 (TUTORIAIS CLEAN) ---
def selecionar_tutorial(event=None):
    tut_nome = combo_tutoriais.get()
    if tut_nome in TUTORIAIS:
        dados = TUTORIAIS[tut_nome]
        lbl_tut_titulo.config(text=tut_nome)
        lbl_tut_desc.config(text=dados["desc"], fg="#e0e0e0")
        btn_abrir_tut.config(state="normal", command=lambda: abrir_video(dados["url"]))

# --- LÓGICA DA ABA 3 (CORREÇÃO CLEAN) ---
def atualizar_descricao_fix(event=None):
    fix_selecionado = combo_fixes.get()
    if fix_selecionado in FIXES:
        dados = FIXES[fix_selecionado]
        lbl_fix_alvo.config(text=f"Arquivo Alvo: {dados['arquivo_alvo']}", fg="#38b6ff")
        lbl_desc_fix.config(text=dados["descricao"], fg="#e0e0e0")
        txt_preview_fix.config(state="normal")
        txt_preview_fix.delete("1.0", tk.END)
        txt_preview_fix.insert(tk.END, dados["conteudo"])
        txt_preview_fix.config(state="disabled")

def aplicar_correcao_arquivo():
    fix_selecionado = combo_fixes.get()
    if not fix_selecionado or fix_selecionado not in FIXES:
        lbl_resultado_fix.config(text="⚠️ Selecione uma correção!", fg="#ffc107")
        return

    dados_fix = FIXES[fix_selecionado]
    nome_arquivo = dados_fix["arquivo_alvo"]

    caminho_destino = filedialog.asksaveasfilename(
        title=f"Selecione a pasta do jogo para salvar {nome_arquivo}",
        initialfile=nome_arquivo,
        filetypes=[("Arquivos de Configuração", "*.txt *.cfg *.ini *.conf *.xml"), ("Todos os Arquivos", "*.*")]
    )

    if caminho_destino:
        try:
            if os.path.exists(caminho_destino):
                shutil.copyfile(caminho_destino, caminho_destino + ".bak")

            with open(caminho_destino, "w", encoding="utf-8") as f:
                f.write(dados_fix["conteudo"])

            lbl_resultado_fix.config(text=f"🟢 SUCESSO!\n'{os.path.basename(caminho_destino)}' aplicado com backup.", fg="#28a745")
        except Exception as e:
            lbl_resultado_fix.config(text=f"🔴 ERRO AO GRAVAR: {e}", fg="#dc3545")

# --- LÓGICA DA ABA 4 (PERFORMANCE AMD) ---
def aplicar_tuning_amd():
    try:
        temp_limit = int(sp_temp.get())
        tdp_watts = int(sp_tdp.get())
        igpu_offset = int(sp_igpu.get())
        usar_tdp = var_tdp_check.get()

        tdp_mw = tdp_watts * 1000 if usar_tdp else 35000

        cmd_args = (
            f"Output: --tctl-temp={temp_limit} --apu-skin-temp={temp_limit} "
            f"--stapm-limit={tdp_mw} --fast-limit={tdp_mw} --slow-limit={tdp_mw} "
            f"--vrm-current=74000 --gfx-clk={1000 + igpu_offset}"
        )
        lbl_amd_output.config(text=cmd_args, fg="#28a745")
    except ValueError:
        lbl_amd_output.config(text="⚠️ Insira valores numéricos válidos!", fg="#dc3545")

# --- LÓGICA DA ABA 5 (EMPURRÃOZINHO) ---
img_thumbnail_atual = None
img_zoom_atual = None
caminho_arquivo_modificado_atual = None
pasta_backup_atual = None

def atualizar_niveis_empurrao(event=None):
    jogo_selecionado = combo_jogo_empurrao.get()
    if jogo_selecionado in PRESETS_EMPURRAO:
        dados_jogo = PRESETS_EMPURRAO[jogo_selecionado]
        lbl_empurrao_alvo.config(text=f"Arquivo Alvo: {dados_jogo['arquivo_alvo']}", fg="#38b6ff")
        lbl_desc_empurrao.config(text=dados_jogo["descricao_geral"], fg="#e0e0e0")
        
        niveis_disponiveis = list(dados_jogo["niveis"].keys())
        if hasattr(combo_nivel_empurrao, "configurar_valores"):
            combo_nivel_empurrao.configurar_valores(niveis_disponiveis)
        else:
            combo_nivel_empurrao.config(values=niveis_disponiveis)
        if niveis_disponiveis:
            combo_nivel_empurrao.current(0)
            atualizar_preview_empurrao()

def atualizar_preview_empurrao(event=None):
    global img_thumbnail_atual, img_zoom_atual
    jogo = combo_jogo_empurrao.get()
    nivel = combo_nivel_empurrao.get()
    
    if jogo in PRESETS_EMPURRAO and nivel in PRESETS_EMPURRAO[jogo]["niveis"]:
        dados_nivel = PRESETS_EMPURRAO[jogo]["niveis"][nivel]
        
        # 1. Carrega o preview do texto
        txt_preview_empurrao.config(state="normal")
        txt_preview_empurrao.delete("1.0", tk.END)
        if os.path.exists(dados_nivel["arquivo"]):
            with open(dados_nivel["arquivo"], "r", encoding="utf-8") as f:
                txt_preview_empurrao.insert(tk.END, f.read())
        else:
            txt_preview_empurrao.insert(tk.END, f"⚠️ Arquivo não encontrado no sistema:\n{dados_nivel['arquivo']}")
        txt_preview_empurrao.config(state="disabled")

        # 2. Carrega a Imagem
        caminho_img = dados_nivel["img"]
        if os.path.exists(caminho_img):
            try:
                img_original = tk.PhotoImage(file=caminho_img)
                img_zoom_atual = img_original 
                img_thumbnail_atual = img_original.subsample(3, 3) 
                lbl_img_preview.config(image=img_thumbnail_atual, text="", cursor="hand2")
            except Exception as e:
                lbl_img_preview.config(image="", text=f"🖼️ Erro na imagem:\n{e}", cursor="arrow")
                img_zoom_atual = None
        else:
            lbl_img_preview.config(image="", text="🖼️ Preview Ausente\n(Adicione preview.png na pasta)", cursor="arrow")
            img_zoom_atual = None

def abrir_zoom(event):
    if img_zoom_atual:
        lbl_zoom_overlay.config(image=img_zoom_atual)
        lbl_zoom_overlay.place(relx=0.5, rely=0.5, relwidth=1, relheight=1, anchor="center")
        lbl_zoom_overlay.lift()

def aplicar_preset_empurrao():
    global caminho_arquivo_modificado_atual, pasta_backup_atual
    jogo = combo_jogo_empurrao.get()
    nivel = combo_nivel_empurrao.get()
    
    if not jogo or not nivel:
        lbl_resultado_empurrao.config(text="⚠️ Selecione um jogo e um nível!", fg="#ffc107")
        return

    dados_jogo = PRESETS_EMPURRAO[jogo]
    caminho_preset_fisico = dados_jogo["niveis"][nivel]["arquivo"]
    pasta_backup = dados_jogo["pasta_backup"]

    if not os.path.exists(caminho_preset_fisico):
        lbl_resultado_empurrao.config(text="🔴 ERRO: Arquivo do patch ausente no sistema!", fg="#dc3545")
        return

    caminho_original_usuario = None
    
    if "caminhos_comuns" in dados_jogo:
        for caminho_teste in dados_jogo["caminhos_comuns"]:
            if os.path.exists(caminho_teste):
                caminho_original_usuario = caminho_teste
                break
    
    if not caminho_original_usuario:
        extensao = os.path.splitext(dados_jogo["arquivo_alvo"])[1]
        messagebox.showinfo(
            "Auto-Detecção Falhou", 
            f"O sistema não encontrou o arquivo original do jogo automaticamente.\n\nPor favor, localize o arquivo '{dados_jogo['arquivo_alvo']}' manualmente na próxima janela."
        )
        caminho_original_usuario = filedialog.askopenfilename(
            title=f"Selecione o arquivo ({dados_jogo['arquivo_alvo']}) do seu jogo",
            initialfile=dados_jogo["arquivo_alvo"],
            filetypes=[(f"Arquivo {extensao}", f"*{extensao}"), ("Todos os Arquivos", "*.*")]
        )

    if caminho_original_usuario:
        try:
            if not os.path.exists(pasta_backup):
                os.makedirs(pasta_backup)

            caminho_backup = os.path.join(pasta_backup, dados_jogo["arquivo_alvo"] + ".bak")
            
            if not os.path.exists(caminho_backup):
                shutil.copyfile(caminho_original_usuario, caminho_backup)
            
            shutil.copyfile(caminho_preset_fisico, caminho_original_usuario)
            
            caminho_arquivo_modificado_atual = caminho_original_usuario
            pasta_backup_atual = pasta_backup
            btn_reverter.config(state="normal")
            
            lbl_resultado_empurrao.config(
                text=f"🟢 {nivel} APLICADO!\nModificado em: {os.path.basename(os.path.dirname(caminho_original_usuario))}", 
                fg="#28a745"
            )
        except Exception as e:
            lbl_resultado_empurrao.config(text=f"🔴 ERRO: {e}", fg="#dc3545")

def reverter_preset_empurrao():
    if not caminho_arquivo_modificado_atual or not pasta_backup_atual:
        lbl_resultado_empurrao.config(text="⚠️ Nenhum arquivo modificado recentemente para reverter.", fg="#ffc107")
        return

    nome_arquivo = os.path.basename(caminho_arquivo_modificado_atual)
    caminho_backup = os.path.join(pasta_backup_atual, nome_arquivo + ".bak")
    
    if os.path.exists(caminho_backup):
        if messagebox.askyesno("Reverter Modificação", "Deseja restaurar o arquivo original da pasta de backup?"):
            try:
                shutil.copyfile(caminho_backup, caminho_arquivo_modificado_atual)
                lbl_resultado_empurrao.config(text="🔄 CONFIGURAÇÕES ORIGINAIS RESTAURADAS!", fg="#28a745")
                btn_reverter.config(state="disabled")
            except Exception as e:
                lbl_resultado_empurrao.config(text=f"🔴 ERRO AO REVERTER: {e}", fg="#dc3545")
    else:
        lbl_resultado_empurrao.config(text="🔴 ERRO: Arquivo de backup não encontrado.", fg="#dc3545")

# --- LÓGICA DA ABA 6 (AGENTE DE IA) ---
thread_monitor = None

def executar_monitoramento_ia_thread(fps_alvo: float):
    iniciar_monitoramento_tempo_real(limite_fps=fps_alvo, segundos_consecutivos=10, delay_inicio_jogo=120)

def ativar_agente_ia():
    global thread_monitor
    jogo_selecionado = combo_jogos_ia.get()
    fps_alvo_str = combo_fps_ia.get()
    fps_alvo = float(fps_alvo_str) if fps_alvo_str else 30.0

    usar_fsr = var_fsr.get()
    nitidez_fsr = combo_nitidez_fsr.get()

    if not jogo_selecionado:
        lbl_status_ia.config(text="⚠️ Selecione um jogo para monitorar!", fg="#ffc107")
        return

    os.environ["RODALISO_MONITOR_ATIVO"] = "True"
    os.environ["RODALISO_FPS_ALVO"] = str(fps_alvo)
    os.environ["USAR_FSR_1"] = str(usar_fsr)
    os.environ["FSR_SHARPNESS"] = nitidez_fsr

    if thread_monitor is not None and thread_monitor.is_alive():
        lbl_status_ia.config(text=f"▶️ Agente retomado: Monitorando {jogo_selecionado} a {fps_alvo} FPS", fg="#28a745")
        return

    lbl_status_ia.config(text=f"🟢 Agente Ativo: Monitorando {jogo_selecionado} a {fps_alvo} FPS em segundo plano", fg="#28a745")

    thread_monitor = threading.Thread(
        target=executar_monitoramento_ia_thread,
        args=(fps_alvo,),
        daemon=True
    )
    thread_monitor.start()

def pausar_agente_ia():
    if thread_monitor is None or not thread_monitor.is_alive():
        lbl_status_ia.config(text="ℹ️ O agente ainda não foi ativado.", fg="#aaaaaa")
        return
    os.environ["RODALISO_MONITOR_ATIVO"] = "False"
    lbl_status_ia.config(text="⏸️ Agente Pausado: nenhuma medição ou sugestão será feita até você clicar em ATIVAR AGENTE.", fg="#ffc107")

def _mostrar_status_ia(texto: str, cor: str):
    lbl_status_ia.config(text=texto, fg=cor, wraplength=_px(300), justify="left")

def aplicar_nitidez_ia():
    jogo_selecionado = combo_jogos_ia.get()
    if not jogo_selecionado:
        _mostrar_status_ia("⚠️ Selecione um jogo para aplicar a nitidez!", "#ffc107")
        return
    if localizar_pasta_exe(jogo_selecionado) is None:
        pasta = filedialog.askdirectory(title=f"Selecione a pasta onde fica o executável de {jogo_selecionado}")
        if not pasta:
            return
        salvar_pasta_manual(jogo_selecionado, pasta)
    nivel = combo_nitidez_fsr.get()

    if reshade_precisa_instalar(jogo_selecionado):
        if not messagebox.askyesno(
                "Instalar ReShade",
                "O ReShade (que roda o filtro de nitidez) ainda não está na pasta do jogo.\n\n"
                "O Roda Liso pode baixar e instalar sozinho agora (ReShade oficial + efeito CAS).\n"
                "Só são ADICIONADOS arquivos na pasta do jogo; nada do jogo é apagado.\n\n"
                "Instalar e aplicar a nitidez?"):
            return
        _mostrar_status_ia("⏳ Preparando a instalação do ReShade...", "#38b6ff")

        def _tarefa():
            def _progresso(texto):
                root.after(0, _mostrar_status_ia, "⏳ " + texto, "#38b6ff")
            ok, msg = instalar_reshade(jogo_selecionado, progresso=_progresso)
            if ok:
                ok, msg2 = aplicar_nitidez(jogo_selecionado, nivel)
                msg = msg + " " + msg2
            root.after(0, _mostrar_status_ia, ("✨ " if ok else "🔴 ") + msg, "#28a745" if ok else "#dc3545")

        threading.Thread(target=_tarefa, daemon=True).start()
        return

    sucesso, mensagem = aplicar_nitidez(jogo_selecionado, nivel)
    _mostrar_status_ia(("✨ " if sucesso else "🔴 ") + mensagem, "#28a745" if sucesso else "#dc3545")

def remover_nitidez_ia():
    jogo_selecionado = combo_jogos_ia.get()
    if not jogo_selecionado:
        _mostrar_status_ia("⚠️ Selecione um jogo para remover a nitidez!", "#ffc107")
        return
    sucesso, mensagem = remover_nitidez(jogo_selecionado)
    _mostrar_status_ia(("🔄 " if sucesso else "ℹ️ ") + mensagem, "#28a745" if sucesso else "#ffc107")

def reverter_agente_ia():
    jogo_selecionado = combo_jogos_ia.get()
    if not jogo_selecionado or jogo_selecionado not in PRESETS_EMPURRAO:
        lbl_status_ia.config(text="⚠️ Selecione um jogo válido para reverter.", fg="#ffc107")
        return
        
    dados_jogo = PRESETS_EMPURRAO[jogo_selecionado]
    pasta_backup_jogo = os.path.join(BASE_DIR, "Rodaliso_Backups", jogo_selecionado)
    arquivo_alvo = dados_jogo.get("arquivo_alvo")
    caminho_backup = os.path.join(pasta_backup_jogo, f"{arquivo_alvo}.bak")
    
    if not os.path.exists(caminho_backup):
        lbl_status_ia.config(text="🔴 Nenhum backup original encontrado na pasta central. A IA ainda não realizou alterações.", fg="#dc3545")
        return

    caminho_original_usuario = None
    for caminho_teste in dados_jogo.get("caminhos_comuns", []):
        if os.path.exists(caminho_teste) or os.path.exists(os.path.dirname(caminho_teste)):
            caminho_original_usuario = caminho_teste
            break
                
    if caminho_original_usuario:
        titulo = "Restaurar Configuração Original"
        texto = f"O Agente de IA detectou o backup seguro para {jogo_selecionado}.\nDeseja remover as otimizações dinâmicas e restaurar os arquivos originais?"
        resposta = ctypes.windll.user32.MessageBoxW(0, texto, titulo, 4 | 32 | 4096)
        
        if resposta == 6:
            try:
                shutil.copyfile(caminho_backup, caminho_original_usuario)
                lbl_status_ia.config(text=f"🔄 As configurações originais de {jogo_selecionado} foram restauradas com sucesso!", fg="#28a745")
            except Exception as e:
                lbl_status_ia.config(text=f"🔴 ERRO AO REVERTER: {e}", fg="#dc3545")
    else:
        lbl_status_ia.config(text="🔴 Não foi possível localizar a pasta de configurações do jogo no sistema operacional.", fg="#dc3545")


# --- UI SETUP ---
if __name__ == '__main__':
    root = tk.Tk()
    root.title("Roda Liso - Performance Hub")
    # Tamanho inicial nunca maior que a tela; tamanho mínimo pequeno o bastante para encaixar em METADE da tela
    # (Win+←/→). As abas e o Otimizador de SO se reorganizam sozinhos quando a janela fica estreita.
    ESCALA_UI = max(1.0, root.winfo_fpixels("1i") / 96.0)   # 125% -> 1.25 (o Tk já escala as fontes sozinho)
    _sw, _sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{min(_px(1100), _sw - 40)}x{min(_px(760), _sh - 100)}")
    root.minsize(min(_px(640), _sw // 2), min(_px(520), _sh // 2))
    root.configure(bg="#000000")

    lbl_zoom_overlay = tk.Label(root, bg="#1a1a1a", cursor="X_cursor")
    lbl_zoom_overlay.bind("<Button-1>", lambda e: lbl_zoom_overlay.place_forget())

    style = ttk.Style()
    style.theme_use("clam")

    style.configure("TNotebook", background="#000000", borderwidth=0)
    style.configure(
        "TNotebook.Tab", 
        background="#1a1a1a", 
        foreground="#aaaaaa", 
        padding=[12, 6], 
        font=("Arial", 9, "bold"),
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab", 
        background=[("selected", "#000000")], 
        foreground=[("selected", "#38b6ff")]
    )
    style.configure("TFrame", background="#000000")

    nb = ttk.Notebook(root)
    nb.pack(pady=10, padx=10, expand=True, fill="both")

    # Cabeçalho + botão de modo noturno/claro (o tema é aplicado ao final, depois de criar todas as abas)
    import tema

    f1 = ttk.Frame(nb)
    f2 = ttk.Frame(nb)
    f3 = ttk.Frame(nb)
    f4 = ttk.Frame(nb)
    f5 = ttk.Frame(nb)
    f6 = ttk.Frame(nb)
    f7 = ttk.Frame(nb) # Nova aba criada aqui

    nb.add(f1, text="Diagnóstico")
    nb.add(f2, text="Tutoriais")
    nb.add(f3, text="Correção de Problemas")
    nb.add(f4, text="Performance AMD")
    nb.add(f5, text="Empurrãozinho")
    nb.add(f6, text="Agente de IA")
    nb.add(f7, text="Otimizador de SO") # Adicionado ao painel

    # ==========================================
    # --- ABA 1: DIAGNÓSTICO ---
    # ==========================================
    # Fontes das abas Diagnóstico e Empurrãozinho: +35% sobre as originais (9 -> 12, 8 -> 11, 10 -> 14)
    F_TIT = ("Arial", 12, "bold")
    F_TXT = ("Arial", 12)
    F_ITA = ("Arial", 12, "italic")
    F_PEQ = ("Arial", 11, "bold")
    F_RES = ("Arial", 14, "bold")
    F_MONO = ("Consolas", 11)
    F_COMBO = (tema.FONTE, 12)

    def combo_grande(master, **kw):
        """Combobox com fonte maior (o texto E a lista que abre)."""
        cb = ttk.Combobox(master, font=F_COMBO, state="readonly", **kw)
        cb._fonte_lista = F_COMBO
        return cb

    # A primeira tela segue uma composição Fluent: título claro, dois cartões e uma ação principal.
    D_FONTE = tema.FONTE
    D_TITULO = (D_FONTE, 20, "bold")
    D_SUBTITULO = (D_FONTE, 10)
    D_CARD_TITULO = (D_FONTE, 13, "bold")
    D_LABEL = (D_FONTE, 10, "bold")
    D_CORPO = (D_FONTE, 10)
    D_PEQUENO = (D_FONTE, 9)

    frame_aba1 = tk.Frame(f1, bg="#000000", padx=24, pady=18)
    frame_aba1.pack(fill="both", expand=True)

    cabecalho_diag = tk.Frame(frame_aba1, bg="#000000")
    cabecalho_diag.pack(fill="x", pady=(0, 16))
    tk.Label(
        cabecalho_diag, text="Diagnóstico do PC", font=D_TITULO,
        fg="#ffffff", bg="#000000", anchor="w"
    ).pack(anchor="w")
    tk.Label(
        cabecalho_diag,
        text="Compare seu hardware com o perfil cadastrado de cada jogo em poucos segundos.",
        font=D_SUBTITULO, fg="#aaaaaa", bg="#000000", anchor="w", justify="left"
    ).pack(anchor="w", pady=(4, 0))

    conteudo_diag = tk.Frame(frame_aba1, bg="#000000")
    conteudo_diag.pack(fill="both", expand=True)
    conteudo_diag.grid_columnconfigure(0, weight=5, uniform="diagnostico")
    conteudo_diag.grid_columnconfigure(1, weight=6, uniform="diagnostico")
    conteudo_diag.grid_rowconfigure(0, weight=1)

    card_pc_shell = PainelArredondado(conteudo_diag, papel="painel", raio=16, padding=22)
    card_pc_shell.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
    card_pc = card_pc_shell.conteudo

    topo_pc = tk.Frame(card_pc, bg="#121212")
    topo_pc.pack(fill="x", pady=(0, 18))
    tk.Label(
        topo_pc, text="Configuração do computador", font=D_CARD_TITULO,
        fg="#ffffff", bg="#121212", anchor="w"
    ).pack(anchor="w")
    tk.Label(
        topo_pc, text="Os dados detectados podem ser ajustados manualmente.", font=D_PEQUENO,
        fg="#aaaaaa", bg="#121212", anchor="w", justify="left"
    ).pack(anchor="w", pady=(4, 0))

    def campo_diagnostico(master, texto, valores):
        grupo = tk.Frame(master, bg="#121212")
        grupo.pack(fill="x", pady=(0, 14))
        tk.Label(
            grupo, text=texto, font=D_LABEL, fg="#e0e0e0", bg="#121212", anchor="w"
        ).pack(anchor="w", pady=(0, 6))
        combo = ComboModerno(grupo, valores=valores, fonte=(D_FONTE, 10))
        combo.pack(fill="x")
        return combo

    combo_cpu = campo_diagnostico(card_pc, "Processador", list(CPUS.keys()))
    combo_gpu = campo_diagnostico(card_pc, "Placa de vídeo", list(GPUS.keys()))
    combo_ram = campo_diagnostico(card_pc, "Memória RAM", RAMS)

    dica_pc_shell = PainelArredondado(
        card_pc, papel="campo", borda="#222222", raio=10, padding=10, altura=44
    )
    dica_pc_shell.pack(fill="x", side="bottom", pady=(4, 0))
    dica_pc = dica_pc_shell.conteudo
    tk.Label(
        dica_pc, text="Detecção local", font=D_PEQUENO, fg="#38b6ff", bg="#1a1a1a"
    ).pack(side="left")
    tk.Label(
        dica_pc, text="  Você mantém o controle dos valores.", font=D_PEQUENO,
        fg="#aaaaaa", bg="#1a1a1a"
    ).pack(side="left")

    card_jogo_shell = PainelArredondado(conteudo_diag, papel="painel", raio=16, padding=22)
    card_jogo_shell.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
    card_jogo = card_jogo_shell.conteudo

    tk.Label(
        card_jogo, text="Jogo e compatibilidade", font=D_CARD_TITULO,
        fg="#ffffff", bg="#121212", anchor="w"
    ).pack(anchor="w")
    tk.Label(
        card_jogo, text="Escolha um título para consultar a referência cadastrada.",
        font=D_PEQUENO, fg="#aaaaaa", bg="#121212", anchor="w", justify="left"
    ).pack(anchor="w", pady=(4, 14))

    combo_jogos = ComboModerno(card_jogo, valores=list(JOGOS.keys()), fonte=(D_FONTE, 10))
    combo_jogos.pack(fill="x", pady=(0, 14))
    combo_jogos.bind("<<ComboboxSelected>>", atualizar_jogo_selecionado)

    resumo_jogo_shell = PainelArredondado(
        card_jogo, papel="campo", borda="#222222", raio=12, padding=14, altura=156
    )
    resumo_jogo_shell.pack(fill="x", pady=(0, 14))
    resumo_jogo = resumo_jogo_shell.conteudo
    lbl_imagem_jogo = tk.Label(
        resumo_jogo, text="Selecione um jogo", font=D_PEQUENO,
        bg="#121212", fg="#aaaaaa", width=18, height=8, justify="center"
    )
    lbl_imagem_jogo.pack(side="left", fill="y")

    dados_jogo_diag = tk.Frame(resumo_jogo, bg="#1a1a1a")
    dados_jogo_diag.pack(side="left", fill="both", expand=True, padx=(16, 0))
    lbl_jogo_nome = tk.Label(
        dados_jogo_diag, text="Nenhum jogo selecionado", font=(D_FONTE, 12, "bold"),
        fg="#ffffff", bg="#1a1a1a", anchor="w", justify="left", wraplength=_px(250)
    )
    lbl_jogo_nome.pack(anchor="w")
    lbl_jogo_requisitos = tk.Label(
        dados_jogo_diag, text="A referência aparecerá aqui.", font=D_PEQUENO,
        fg="#aaaaaa", bg="#1a1a1a", anchor="w", justify="left"
    )
    lbl_jogo_requisitos.pack(anchor="w", pady=(8, 0))

    btn_exec = BotaoModerno(
        card_jogo, texto="Analisar compatibilidade", comando=verificar_compatibilidade,
        fonte=(D_FONTE, 10, "bold"), altura=46
    )
    btn_exec.pack(fill="x", pady=(0, 14))

    frame_resultado_diag = PainelArredondado(
        card_jogo, papel="campo", borda="#38b6ff", raio=12, padding=14
    )
    frame_resultado_diag.pack(fill="both", expand=True)
    frame_resultado_conteudo = frame_resultado_diag.conteudo
    lbl_resultado_status = tk.Label(
        frame_resultado_conteudo, text="Pronto para analisar", font=D_LABEL,
        fg="#38b6ff", bg="#1a1a1a", anchor="w", justify="left"
    )
    lbl_resultado_status.pack(anchor="w")
    lbl_resultado = tk.Label(
        frame_resultado_conteudo,
        text="Confira os componentes e inicie a comparação. Nenhuma configuração do PC será alterada.",
        font=D_PEQUENO, fg="#e0e0e0", bg="#1a1a1a", anchor="w", justify="left",
        wraplength=_px(390)
    )
    lbl_resultado.pack(anchor="w", pady=(5, 0), fill="x")

    # ==========================================
    # --- ABA 2: TUTORIAIS ---
    # ==========================================
    frame_aba2 = tk.Frame(f2, bg="#000000", padx=_px(26), pady=_px(22))
    frame_aba2.pack(fill="both", expand=True)

    _cabecalho_aba(
        frame_aba2, "Tutoriais",
        "Guias rápidos para configurar jogos, drivers e recursos do Roda Liso."
    )
    corpo2 = tk.Frame(frame_aba2, bg="#000000")
    corpo2.pack(fill="both", expand=True)

    painel_esq2 = PainelArredondado(corpo2, raio=14, padding=20)
    painel_esq2.pack(side="left", fill="both", expand=True, padx=(0, _px(8)))
    col_esq2 = painel_esq2.conteudo
    _titulo_card(
        col_esq2, "Central de conhecimento",
        "Escolha um assunto para ver um resumo antes de abrir o conteúdo completo."
    )
    tk.Label(
        col_esq2, text="Tópico", font=D_LABEL, fg="#ffffff", bg="#121212"
    ).pack(anchor="w", pady=(0, _px(6)))
    combo_tutoriais = ComboModerno(col_esq2, list(TUTORIAIS.keys()), fonte=D_CORPO)
    combo_tutoriais.pack(fill="x", pady=(0, _px(18)))
    combo_tutoriais.bind("<<ComboboxSelected>>", selecionar_tutorial)
    tk.Label(
        col_esq2,
        text="Os tutoriais são abertos no navegador e não alteram nenhuma configuração automaticamente.",
        font=D_PEQUENO, fg="#aaaaaa", bg="#121212", justify="left", anchor="w",
        wraplength=_px(390)
    ).pack(fill="x", anchor="w")

    painel_dir2 = PainelArredondado(corpo2, raio=14, padding=20)
    painel_dir2.pack(side="right", fill="both", expand=True, padx=(_px(8), 0))
    col_dir2 = painel_dir2.conteudo
    _titulo_card(col_dir2, "Detalhes do tutorial", "Uma visão rápida do conteúdo selecionado.")
    lbl_tut_titulo = tk.Label(
        col_dir2, text="Selecione um guia ao lado", font=D_CARD_TITULO,
        bg="#121212", fg="#ffffff", wraplength=_px(420), justify="left", anchor="w"
    )
    lbl_tut_titulo.pack(fill="x", pady=(_px(18), _px(8)))
    lbl_tut_desc = tk.Label(
        col_dir2,
        text="Escolha uma opção no menu para exibir as instruções e o link correspondente.",
        font=D_CORPO, fg="#aaaaaa", bg="#121212", wraplength=_px(420),
        justify="left", anchor="nw"
    )
    lbl_tut_desc.pack(fill="both", expand=True, pady=(0, _px(18)))
    btn_abrir_tut = _botao_acao(col_dir2, "ASSISTIR TUTORIAL", state="disabled")
    btn_abrir_tut.pack(fill="x")

    # ==========================================
    # --- ABA 3: CORREÇÃO ---
    # ==========================================
    frame_aba3 = tk.Frame(f3, bg="#000000", padx=_px(26), pady=_px(22))
    frame_aba3.pack(fill="both", expand=True)

    _cabecalho_aba(
        frame_aba3, "Correção de Problemas",
        "Aplique arquivos de configuração conhecidos com cópia de segurança automática."
    )
    corpo3 = tk.Frame(frame_aba3, bg="#000000")
    corpo3.pack(fill="both", expand=True)

    painel_esq3 = PainelArredondado(corpo3, raio=14, padding=20)
    painel_esq3.pack(side="left", fill="both", expand=True, padx=(0, _px(8)))
    col_esq3 = painel_esq3.conteudo
    _titulo_card(
        col_esq3, "Escolha uma correção",
        "Confira o arquivo de destino e revise o conteúdo antes de salvar."
    )
    tk.Label(col_esq3, text="Correção", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    combo_fixes = ComboModerno(col_esq3, list(FIXES.keys()), fonte=D_CORPO)
    combo_fixes.pack(fill="x", pady=(0, _px(10)))
    combo_fixes.bind("<<ComboboxSelected>>", atualizar_descricao_fix)

    lbl_fix_alvo = tk.Label(col_esq3, text="Arquivo alvo: nenhum", font=D_PEQUENO, fg="#38b6ff", bg="#121212")
    lbl_fix_alvo.pack(anchor="w", pady=(0, _px(18)))

    btn_fix = _botao_acao(col_esq3, "APLICAR CORREÇÃO", aplicar_correcao_arquivo)
    btn_fix.pack(fill="x")

    lbl_resultado_fix = tk.Label(
        col_esq3, text="", font=D_LABEL, bg="#121212", justify="left",
        anchor="w", wraplength=_px(410)
    )
    lbl_resultado_fix.pack(fill="x", anchor="w", pady=(_px(14), 0))

    painel_dir3 = PainelArredondado(corpo3, raio=14, padding=20)
    painel_dir3.pack(side="right", fill="both", expand=True, padx=(_px(8), 0))
    col_dir3 = painel_dir3.conteudo
    _titulo_card(col_dir3, "Detalhes da otimização", "Descrição e prévia do arquivo que será criado.")
    lbl_desc_fix = tk.Label(
        col_dir3, text="Selecione uma correção para ver a descrição e os parâmetros aplicados.",
        font=D_CORPO, fg="#aaaaaa", bg="#121212", wraplength=_px(420),
        justify="left", anchor="w"
    )
    lbl_desc_fix.pack(fill="x", anchor="w", pady=(0, _px(14)))
    tk.Label(col_dir3, text="Conteúdo do arquivo", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    txt_preview_fix = tk.Text(
        col_dir3, height=8, width=25, font=("Consolas", 9), bg="#1a1a1a",
        fg="#e0e0e0", insertbackground="white", relief="flat", bd=0,
        padx=_px(12), pady=_px(10), selectbackground="#2f81f7"
    )
    txt_preview_fix.pack(fill="both", expand=True)
    txt_preview_fix.config(state="disabled")

    # ==========================================
    # --- ABA 4: PERFORMANCE AMD ---
    # ==========================================
    f4_content = tk.Frame(f4, bg="#000000", padx=_px(26), pady=_px(22))
    f4_content.pack(fill="both", expand=True)

    _cabecalho_aba(
        f4_content, "Performance AMD",
        "Monte um perfil personalizado para APUs Ryzen e revise os argumentos antes de aplicar."
    )
    corpo4 = tk.Frame(f4_content, bg="#000000")
    corpo4.pack(fill="both", expand=True)

    painel_config4 = PainelArredondado(corpo4, raio=14, padding=20)
    painel_config4.pack(side="left", fill="both", expand=True, padx=(0, _px(8)))
    config4 = painel_config4.conteudo
    _titulo_card(config4, "Perfil da APU", "AMD Ryzen Series · ajuste personalizado")

    f_temp = tk.Frame(config4, bg="#121212")
    f_temp.pack(fill="x", pady=(_px(6), _px(12)))
    tk.Label(f_temp, text="Limite de temperatura", font=D_LABEL, fg="#ffffff", bg="#121212").pack(side="left")
    sp_temp = tk.Spinbox(
        f_temp, from_=60, to=105, width=7, font=D_CORPO, justify="center",
        bg="#1a1a1a", fg="#ffffff", insertbackground="white", relief="flat", bd=0
    )
    sp_temp.delete(0, "end"); sp_temp.insert(0, "98")
    sp_temp.pack(side="right", ipady=_px(7))
    tk.Label(f_temp, text="°C", font=D_PEQUENO, fg="#aaaaaa", bg="#121212").pack(side="right", padx=(0, _px(8)))

    f_tdp = tk.Frame(config4, bg="#121212")
    f_tdp.pack(fill="x", pady=_px(12))
    var_tdp_check = tk.BooleanVar(value=True)
    chk_tdp = tk.Checkbutton(
        f_tdp, text="Limite máximo de TDP", variable=var_tdp_check,
        font=D_LABEL, bg="#121212", fg="#ffffff", selectcolor="#1a1a1a",
        activebackground="#121212", activeforeground="#ffffff", bd=0
    )
    chk_tdp.pack(side="left")
    sp_tdp = tk.Spinbox(
        f_tdp, from_=10, to=65, width=7, font=D_CORPO, justify="center",
        bg="#1a1a1a", fg="#ffffff", insertbackground="white", relief="flat", bd=0
    )
    sp_tdp.delete(0, "end"); sp_tdp.insert(0, "38")
    sp_tdp.pack(side="right", ipady=_px(7))
    tk.Label(f_tdp, text="W", font=D_PEQUENO, fg="#aaaaaa", bg="#121212").pack(side="right", padx=(0, _px(8)))

    f_igpu = tk.Frame(config4, bg="#121212")
    f_igpu.pack(fill="x", pady=_px(12))
    tk.Label(f_igpu, text="Offset de clock da iGPU", font=D_LABEL, fg="#ffffff", bg="#121212").pack(side="left")
    sp_igpu = tk.Spinbox(
        f_igpu, from_=0, to=1500, increment=25, width=7, font=D_CORPO, justify="center",
        bg="#1a1a1a", fg="#ffffff", insertbackground="white", relief="flat", bd=0
    )
    sp_igpu.delete(0, "end"); sp_igpu.insert(0, "800")
    sp_igpu.pack(side="right", ipady=_px(7))
    tk.Label(f_igpu, text="+ MHz", font=D_PEQUENO, fg="#aaaaaa", bg="#121212").pack(side="right", padx=(0, _px(8)))

    lbl_warning = tk.Label(
        config4, text="Atenção: overclock pode causar instabilidade. Use somente em processadores compatíveis e com privilégios de administrador.",
        font=D_PEQUENO, fg="#ff9800", bg="#121212", justify="left", anchor="w", wraplength=_px(410)
    )
    lbl_warning.pack(fill="x", pady=(_px(18), 0), anchor="w")

    painel_saida4 = PainelArredondado(corpo4, raio=14, padding=20)
    painel_saida4.pack(side="right", fill="both", expand=True, padx=(_px(8), 0))
    saida4 = painel_saida4.conteudo
    _titulo_card(saida4, "Comando gerado", "Revise os parâmetros calculados pelo perfil.")
    lbl_amd_output = tk.Label(
        saida4, text="Clique em gerar perfil para visualizar os argumentos.",
        font=("Consolas", 9), fg="#aaaaaa", bg="#1a1a1a", wraplength=_px(310),
        justify="left", anchor="nw", padx=_px(14), pady=_px(14)
    )
    lbl_amd_output.pack(fill="both", expand=True, pady=(0, _px(16)))

    btn_apply_amd = _botao_acao(saida4, "GERAR PERFIL AMD", aplicar_tuning_amd)
    btn_apply_amd.pack(fill="x")

    # ==========================================
    # --- ABA 5: EMPURRÃOZINHO ---
    # ==========================================
    frame_aba5 = tk.Frame(f5, bg="#000000", padx=_px(26), pady=_px(22))
    frame_aba5.pack(fill="both", expand=True)

    _cabecalho_aba(
        frame_aba5, "Empurrãozinho",
        "Presets gráficos ultraleves para extrair desempenho de máquinas mais modestas."
    )
    corpo5 = tk.Frame(frame_aba5, bg="#000000")
    corpo5.pack(fill="both", expand=True)

    painel_esq5 = PainelArredondado(corpo5, raio=14, padding=20)
    painel_esq5.pack(side="left", fill="both", expand=True, padx=(0, _px(8)))
    col_esq5 = painel_esq5.conteudo
    bloco5 = tk.Frame(col_esq5, bg="#121212")
    bloco5.pack(fill="both", expand=True)
    _titulo_card(bloco5, "Configuração do preset", "Selecione o jogo e a intensidade do ajuste.")

    tk.Label(bloco5, text="Jogo", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    combo_jogo_empurrao = ComboModerno(bloco5, list(PRESETS_EMPURRAO.keys()), fonte=D_CORPO)
    combo_jogo_empurrao.pack(fill="x", pady=(0, _px(12)))
    combo_jogo_empurrao.bind("<<ComboboxSelected>>", atualizar_niveis_empurrao)

    tk.Label(bloco5, text="Nível do patch", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    combo_nivel_empurrao = ComboModerno(bloco5, [], fonte=D_CORPO)
    combo_nivel_empurrao.pack(fill="x", pady=(0, _px(10)))
    combo_nivel_empurrao.bind("<<ComboboxSelected>>", atualizar_preview_empurrao)

    lbl_empurrao_alvo = tk.Label(bloco5, text="Arquivo alvo: nenhum", font=D_PEQUENO, fg="#38b6ff", bg="#121212")
    lbl_empurrao_alvo.pack(anchor="w", pady=(0, _px(16)))

    frame_botoes = tk.Frame(bloco5, bg="#121212")
    frame_botoes.pack(fill="x", pady=5)
    frame_botoes.grid_columnconfigure(0, weight=1, uniform="preset")
    frame_botoes.grid_columnconfigure(1, weight=1, uniform="preset")

    btn_empurrao = _botao_acao(frame_botoes, "APLICAR PRESET", aplicar_preset_empurrao)
    btn_empurrao.grid(row=0, column=0, sticky="ew", padx=(0, 5))

    btn_reverter = _botao_acao(frame_botoes, "REVERTER", reverter_preset_empurrao, cor="#4b5563", state="disabled")
    btn_reverter.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    lbl_resultado_empurrao = tk.Label(
        bloco5, text="", font=D_LABEL, bg="#121212", justify="left",
        anchor="w", wraplength=_px(390)
    )
    lbl_resultado_empurrao.pack(fill="x", anchor="w", pady=(_px(12), 0))

    painel_dir5 = PainelArredondado(corpo5, raio=14, padding=20)
    painel_dir5.pack(side="right", fill="both", expand=True, padx=(_px(8), 0))
    col_dir5 = painel_dir5.conteudo
    _titulo_card(col_dir5, "Detalhes do jogo", "Prévia visual e conteúdo do arquivo selecionado.")

    lbl_desc_empurrao = tk.Label(
        col_dir5, text="Selecione um jogo para ver os detalhes.", font=D_CORPO,
        fg="#aaaaaa", bg="#121212", wraplength=_px(420), justify="left", anchor="w"
    )
    lbl_desc_empurrao.pack(fill="x", anchor="w", pady=(0, _px(10)))

    tk.Label(col_dir5, text="Prévia gráfica · clique para ampliar", font=D_PEQUENO, fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(0, _px(5)))
    lbl_img_preview = tk.Label(col_dir5, text="Aguardando seleção...", font=D_CORPO, bg="#1a1a1a", fg="#888888", height=6)
    lbl_img_preview.pack(fill="x", pady=(0, _px(10)))
    lbl_img_preview.bind("<Button-1>", abrir_zoom)

    tk.Label(col_dir5, text="Prévia do arquivo", font=D_PEQUENO, fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(0, _px(5)))
    txt_preview_empurrao = tk.Text(
        col_dir5, height=5, width=25, font=("Consolas", 9), bg="#1a1a1a",
        fg="#e0e0e0", insertbackground="white", relief="flat", bd=0,
        padx=_px(10), pady=_px(8), selectbackground="#2f81f7"
    )
    txt_preview_empurrao.pack(fill="both", expand=True)
    txt_preview_empurrao.config(state="disabled")

    # ==========================================
    # --- ABA 6: AGENTE DE IA ---
    # ==========================================
    frame_aba6 = tk.Frame(f6, bg="#000000", padx=_px(26), pady=_px(22))
    frame_aba6.pack(fill="both", expand=True)

    _cabecalho_aba(
        frame_aba6, "Agente de IA",
        "Defina uma meta de FPS e acompanhe sugestões de desempenho de forma controlada."
    )
    corpo6 = tk.Frame(frame_aba6, bg="#000000")
    corpo6.pack(fill="both", expand=True)

    painel_esq6 = PainelArredondado(corpo6, raio=14, padding=20)
    painel_esq6.pack(side="left", fill="both", expand=True, padx=(0, _px(8)))
    col_esq6 = painel_esq6.conteudo
    bloco6 = tk.Frame(col_esq6, bg="#121212")
    bloco6.pack(fill="both", expand=True)
    _titulo_card(bloco6, "Configuração do agente", "Escolha o jogo, a meta e o nível de nitidez.")

    campo_jogo6 = tk.Frame(bloco6, bg="#121212")
    campo_jogo6.pack(fill="x")
    campo_fps6 = tk.Frame(bloco6, bg="#121212")
    campo_fps6.pack(fill="x")
    tk.Label(campo_jogo6, text="Jogo instalado", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    combo_jogos_ia = ComboModerno(campo_jogo6, list(PRESETS_EMPURRAO.keys()), fonte=D_CORPO, altura=42)
    combo_jogos_ia.pack(fill="x", pady=(0, _px(12)))

    tk.Label(campo_fps6, text="Meta de FPS", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    combo_fps_ia = ComboModerno(campo_fps6, ["24", "30", "40", "60", "90", "120"], fonte=D_CORPO, altura=42)
    combo_fps_ia.set("30")
    combo_fps_ia.pack(fill="x", pady=(0, _px(12)))

    var_fsr = tk.BooleanVar(value=True)
    chk_fsr = tk.Checkbutton(
        bloco6, 
        text="Aplicar filtro de nitidez na próxima inicialização do jogo",
        variable=var_fsr, 
        font=D_LABEL,
        bg="#121212",
        fg="#38b6ff", 
        selectcolor="#1a1a1a", 
        activebackground="#121212",
        activeforeground="#ffffff",
        wraplength=_px(420), justify="left", anchor="w", bd=0
    )
    chk_fsr.pack(fill="x", pady=(0, _px(8)))
    bloco6.bind("<Configure>", lambda e: chk_fsr.configure(wraplength=max(200, e.width - 30)))

    tk.Label(bloco6, text="Nível do filtro de nitidez", font=D_LABEL, fg="#ffffff", bg="#121212").pack(anchor="w", pady=(0, _px(6)))
    combo_nitidez_fsr = ComboModerno(
        bloco6, ["Baixa (Suave)", "Média (Padrão)", "Alta (Nítida)", "Máxima (Agressiva)"],
        fonte=D_CORPO, altura=42
    )
    combo_nitidez_fsr.set("Média (Padrão)")
    combo_nitidez_fsr.pack(fill="x", pady=(0, _px(8)))

    frame_botoes_nitidez = tk.Frame(bloco6, bg="#121212")
    frame_botoes_nitidez.pack(fill="x", pady=(0, _px(14)))
    frame_botoes_nitidez.grid_columnconfigure(0, weight=1, uniform="nitidez")
    frame_botoes_nitidez.grid_columnconfigure(1, weight=1, uniform="nitidez")
    _botao_acao(frame_botoes_nitidez, "APLICAR NITIDEZ", aplicar_nitidez_ia).grid(row=0, column=0, sticky="ew", padx=(0, 5))
    _botao_acao(frame_botoes_nitidez, "REMOVER NITIDEZ", remover_nitidez_ia, cor="#4b5563").grid(row=0, column=1, sticky="ew", padx=(5, 0))

    # O status fica FORA do bloco: textos longos dele não podem alargar as colunas acima
    lbl_status_ia = tk.Label(
        bloco6, text="Status: aguardando inicialização", font=D_PEQUENO,
        fg="#aaaaaa", bg="#121212", justify="left", anchor="w", wraplength=_px(420)
    )

    frame_botoes_ia = tk.Frame(bloco6, bg="#121212")
    frame_botoes_ia.pack(fill="x", pady=5)

    btn_ativar_ia = _botao_acao(frame_botoes_ia, "ATIVAR AGENTE", ativar_agente_ia)
    btn_ativar_ia.pack(side="left", fill="x", expand=True, padx=(0, 10))

    btn_pausar_ia = _botao_acao(frame_botoes_ia, "PAUSAR", pausar_agente_ia, cor="#4b5563")
    btn_pausar_ia.pack(side="left", fill="x", expand=True, padx=(0, 10))

    btn_reverter_ia = _botao_acao(frame_botoes_ia, "REVERTER", reverter_agente_ia, cor="#4b5563")
    btn_reverter_ia.pack(side="left", fill="x", expand=True)

    lbl_status_ia.pack(fill="x", anchor="w", pady=(_px(10), 0))

    painel_dir6 = PainelArredondado(corpo6, raio=14, padding=20)
    painel_dir6.pack(side="right", fill="both", expand=True, padx=(_px(8), 0))
    col_dir6 = painel_dir6.conteudo
    _titulo_card(col_dir6, "Como o agente funciona", "Controle, segurança e reversibilidade em primeiro lugar.")

    lbl_info_ia = tema.TextoJustificado(
        col_dir6,
        texto="O Agente Roda Liso preserva os arquivos originais e mantém você no controle.\n\n"
              "PAUSAR suspende medições e sugestões; ATIVAR AGENTE retoma o acompanhamento.\n\n"
              "A meta de FPS é cruzada com as configurações atuais para evitar reduções agressivas desnecessárias.\n\n"
              "O filtro usa o ReShade com efeito CAS e precisa estar instalado na pasta do jogo.",
        fonte=(tema.FONTE, 10), fg="#aaaaaa", bg="#121212"
    )
    lbl_info_ia.pack(fill="both", expand=True, pady=(_px(8), 0))

    # ==========================================
    # --- ABA 7: OTIMIZADOR DE SO (painel embutido, reversível) ---
    # ==========================================
    frame_aba7 = tk.Frame(f7, bg="#000000", padx=_px(26), pady=_px(22))
    frame_aba7.pack(fill="both", expand=True)
    _cabecalho_aba(
        frame_aba7, "Otimizador de SO",
        "Ajustes reversíveis do Windows, organizados por impacto e nível de risco."
    )
    try:
        from otimizador_so import PainelOtimizadorSO
        PainelOtimizadorSO(frame_aba7, painel_cls=PainelArredondado).pack(fill="both", expand=True)
    except Exception as erro_so:
        tk.Label(frame_aba7, text=f"Não foi possível carregar o Otimizador de SO:\n{erro_so}", fg="#dc3545",
                 bg="#000000", font=("Arial", 10), justify="left").pack(padx=20, pady=20, anchor="w")

    # --- EXECUTA A DETECÇÃO AUTOMÁTICA AO INICIAR ---
    cpu_autodetect, gpu_autodetect, ram_autodetect = auto_detectar_hardware()

    if cpu_autodetect:
        combo_cpu.set(cpu_autodetect)
    elif CPUS:
        combo_cpu.current(0)

    if gpu_autodetect:
        combo_gpu.set(gpu_autodetect)
    elif GPUS:
        combo_gpu.current(0)

    if ram_autodetect and ram_autodetect in RAMS:
        combo_ram.set(ram_autodetect)
    else:
        combo_ram.set("8 GB")

    if JOGOS:
        combo_jogos.current(0)
        atualizar_jogo_selecionado()

    if TUTORIAIS:
        combo_tutoriais.current(0)
        selecionar_tutorial()

    if FIXES:
        combo_fixes.current(0)
        atualizar_descricao_fix()

    if PRESETS_EMPURRAO:
        combo_jogo_empurrao.current(0)
        atualizar_niveis_empurrao()
        combo_jogos_ia.current(0)

    # tema salvo (noturno por padrão) + barra de abas em largura total, com um ícone depois do nome de cada aba
    ICONES_ABAS = {
        "Diagnóstico": "🩺", "Tutoriais": "📖", "Correção de Problemas": "🔧", "Performance AMD": "⚡",
        "Empurrãozinho": "🚀", "Agente de IA": "🤖", "Otimizador de SO": "⚙️",
    }
    tema.instalar(root, antes_de=nb, icones_abas=ICONES_ABAS)
    root.mainloop()
