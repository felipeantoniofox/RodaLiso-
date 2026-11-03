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
def atualizar_jogo_selecionado(event=None):
    jogo = combo_jogos.get()
    if jogo in JOGOS:
        caminho_capa = JOGOS[jogo]["capa"]
        if os.path.exists(caminho_capa):
            try:
                img = tk.PhotoImage(file=caminho_capa)
                lbl_imagem_jogo.config(image=img, text="")
                lbl_imagem_jogo.image = img
            except Exception:
                lbl_imagem_jogo.config(image="", text="🖼️ [Imagem do Jogo]", fg="#888888")
        else:
            lbl_imagem_jogo.config(image="", text="🖼️ [Capa não encontrada]", fg="#888888")

def verificar_compatibilidade():
    cpu_escolhida = combo_cpu.get()
    gpu_escolhida = combo_gpu.get()
    ram_escolhida = combo_ram.get()
    jogo_escolhido = combo_jogos.get()

    if not all([cpu_escolhida, gpu_escolhida, ram_escolhida, jogo_escolhido]):
        lbl_resultado.config(text="⚠️ Selecione todos os campos!", fg="#ffc107")
        return

    pontos_cpu = CPUS[cpu_escolhida]
    pontos_gpu = GPUS[gpu_escolhida]
    ram_pc_mb = converter_ram_para_mb(ram_escolhida)
    
    req_cpu = JOGOS[jogo_escolhido]["cpu"]
    req_gpu = JOGOS[jogo_escolhido]["gpu"]
    req_ram_mb = converter_ram_para_mb(JOGOS[jogo_escolhido]["ram"])

    if pontos_cpu >= req_cpu and pontos_gpu >= req_gpu and ram_pc_mb >= req_ram_mb:
        lbl_resultado.config(text=f"🟢 RODA LISO!\nScore Hardware: {pontos_cpu + pontos_gpu}/2000", fg="#28a745")
    elif ram_pc_mb < req_ram_mb:
        lbl_resultado.config(text=f"🔴 MEMÓRIA INSUFICIENTE\nRequisito: {JOGOS[jogo_escolhido]['ram']}\nVocê tem: {ram_escolhida}", fg="#dc3545")
    else:
        gargalo = "GPU" if pontos_gpu < req_gpu else "CPU"
        diff = req_gpu - pontos_gpu if gargalo == "GPU" else req_cpu - pontos_cpu
        lbl_resultado.config(text=f"🟡 GARGALO DETECTADO ({gargalo})\nFaltam {diff} pts de performance.", fg="#ffc107")

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

    frame_aba1 = tk.Frame(f1, bg="#000000", padx=15, pady=10)
    frame_aba1.pack(fill="both", expand=True)

    col_esq1 = tk.Frame(frame_aba1, bg="#000000")
    col_esq1.pack(side="left", fill="both", expand=True)

    # Bloco com a largura do controle mais largo: as listas e o botão VERIFICAR esticam até a mesma largura
    bloco1 = tk.Frame(col_esq1, bg="#000000")
    bloco1.pack(anchor="w")

    tk.Label(bloco1, text="CONFIGURAÇÃO DO SEU PC", font=F_TIT, fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))

    tk.Label(bloco1, text="Processador:", font=F_TXT, fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_cpu = combo_grande(bloco1, values=list(CPUS.keys()), width=32)
    combo_cpu.pack(fill="x", pady=(0, 8))

    tk.Label(bloco1, text="Placa de Vídeo:", font=F_TXT, fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_gpu = combo_grande(bloco1, values=list(GPUS.keys()), width=32)
    combo_gpu.pack(fill="x", pady=(0, 8))

    tk.Label(bloco1, text="Memória RAM:", font=F_TXT, fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_ram = combo_grande(bloco1, values=RAMS, width=32)
    combo_ram.pack(fill="x", pady=(0, 15))

    tk.Label(bloco1, text="JOGO DESEJADO", font=F_TIT, fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))
    combo_jogos = combo_grande(bloco1, values=list(JOGOS.keys()), width=32)
    combo_jogos.pack(fill="x", pady=(0, 15))
    combo_jogos.bind("<<ComboboxSelected>>", atualizar_jogo_selecionado)

    btn_exec = tk.Button(bloco1, text="VERIFICAR COMPATIBILIDADE", bg="#28a745", fg="white", font=F_TIT, command=verificar_compatibilidade, relief="flat", padx=15, pady=8, cursor="hand2")
    btn_exec.pack(fill="x", pady=5)

    # O resultado fica FORA do bloco: textos longos dele não podem alargar as listas e o botão
    lbl_resultado = tk.Label(col_esq1, text="", font=F_RES, bg="#000000", justify="left")
    lbl_resultado.pack(anchor="w", pady=10)

    col_dir1 = tk.Frame(frame_aba1, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
    col_dir1.pack(side="right", fill="both", expand=True, padx=(15, 0))

    tk.Label(col_dir1, text="VISUALIZAÇÃO DO TÍTULO", font=F_TIT, fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))
    lbl_imagem_jogo = tk.Label(col_dir1, text="Selecione um jogo ao lado", font=F_ITA, bg="#1a1a1a", fg="#aaaaaa", width=18, height=12)
    lbl_imagem_jogo.pack(expand=True, fill="both")

    # ==========================================
    # --- ABA 2: TUTORIAIS ---
    # ==========================================
    frame_aba2 = tk.Frame(f2, bg="#000000", padx=15, pady=10)
    frame_aba2.pack(fill="both", expand=True)

    col_esq2 = tk.Frame(frame_aba2, bg="#000000")
    col_esq2.pack(side="left", fill="both", expand=True)

    tk.Label(col_esq2, text="CENTRAL DE CONHECIMENTO", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))

    tk.Label(col_esq2, text="Selecione o Tópico:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_tutoriais = ttk.Combobox(col_esq2, values=list(TUTORIAIS.keys()), width=32, state="readonly")
    combo_tutoriais.pack(anchor="w", pady=(0, 15))
    combo_tutoriais.bind("<<ComboboxSelected>>", selecionar_tutorial)

    col_dir2 = tk.Frame(frame_aba2, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
    col_dir2.pack(side="right", fill="both", expand=True, padx=(15, 0))

    tk.Label(col_dir2, text="DETALHES DO TUTORIAL", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))

    lbl_tut_titulo = tk.Label(col_dir2, text="Selecione um guia ao lado", font=("Arial", 10, "bold"), bg="#121212", fg="#ffffff", wraplength=_px(220), justify="center")
    lbl_tut_titulo.pack(pady=(15, 10))

    lbl_tut_desc = tk.Label(col_dir2, text="Escolha uma opção no menu para exibir as instruções e o link correspondente.", font=("Arial", 9, "italic"), fg="#aaaaaa", bg="#121212", wraplength=_px(220), justify="center")
    lbl_tut_desc.pack(expand=True, pady=10)

    btn_abrir_tut = tk.Button(col_dir2, text="📺 ASSISTIR TUTORIAL", bg="#007bff", fg="white", font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", state="disabled")
    btn_abrir_tut.pack(pady=10)

    # ==========================================
    # --- ABA 3: CORREÇÃO ---
    # ==========================================
    frame_aba3 = tk.Frame(f3, bg="#000000", padx=15, pady=10)
    frame_aba3.pack(fill="both", expand=True)

    col_esq3 = tk.Frame(frame_aba3, bg="#000000")
    col_esq3.pack(side="left", fill="both", expand=True)

    tk.Label(col_esq3, text="CORREÇÃO E FIXES DE JOGOS", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))

    tk.Label(col_esq3, text="Selecione a Correção:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_fixes = ttk.Combobox(col_esq3, values=list(FIXES.keys()), width=32, state="readonly")
    combo_fixes.pack(anchor="w", pady=(0, 8))
    combo_fixes.bind("<<ComboboxSelected>>", atualizar_descricao_fix)

    lbl_fix_alvo = tk.Label(col_esq3, text="Arquivo Alvo: -", font=("Arial", 8, "bold"), fg="#38b6ff", bg="#000000")
    lbl_fix_alvo.pack(anchor="w", pady=(0, 15))

    btn_fix = tk.Button(col_esq3, text="APLICAR CORREÇÃO", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=aplicar_correcao_arquivo, relief="flat", padx=15, pady=8, cursor="hand2")
    btn_fix.pack(anchor="w", pady=5)

    lbl_resultado_fix = tk.Label(col_esq3, text="", font=("Arial", 9, "bold"), bg="#000000", justify="left")
    lbl_resultado_fix.pack(anchor="w", pady=10)

    col_dir3 = tk.Frame(frame_aba3, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
    col_dir3.pack(side="right", fill="both", expand=True, padx=(15, 0))

    tk.Label(col_dir3, text="DETALHES DA OTIMIZAÇÃO", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))

    lbl_desc_fix = tk.Label(col_dir3, text="Selecione uma correção para ver a descrição e os parâmetros aplicados.", font=("Arial", 9, "italic"), fg="#aaaaaa", bg="#121212", wraplength=_px(220), justify="left")
    lbl_desc_fix.pack(anchor="w", pady=(0, 10))

    tk.Label(col_dir3, text="CONTEÚDO DO ARQUIVO:", font=("Arial", 8, "bold"), fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(5, 2))
    txt_preview_fix = tk.Text(col_dir3, height=8, width=25, font=("Consolas", 8), bg="#1a1a1a", fg="#e0e0e0", insertbackground="white", relief="solid", bd=1)
    txt_preview_fix.pack(fill="both", expand=True)
    txt_preview_fix.config(state="disabled")

    # ==========================================
    # --- ABA 4: PERFORMANCE AMD ---
    # ==========================================
    frame_top_amd = tk.Frame(f4, bg="#00a88f", pady=6)
    frame_top_amd.pack(fill="x")

    lbl_apu_header = tk.Label(frame_top_amd, text="APU: AMD Ryzen Series (Custom Tuning)", font=("Arial", 10, "bold"), fg="white", bg="#00a88f")
    lbl_apu_header.pack()

    f4_content = tk.Frame(f4, bg="#000000", padx=20, pady=10)
    f4_content.pack(fill="both", expand=True)

    f_temp = tk.Frame(f4_content, bg="#000000")
    f_temp.pack(anchor="w", pady=4)
    tk.Label(f_temp, text="Adaptive Temp Limit: ", font=("Arial", 9, "bold"), fg="#ffffff", bg="#000000").pack(side="left")
    sp_temp = tk.Spinbox(f_temp, from_=60, to=105, width=5, bg="#1a1a1a", fg="#ffffff", insertbackground="white")
    sp_temp.delete(0, "end"); sp_temp.insert(0, "98")
    sp_temp.pack(side="left")
    tk.Label(f_temp, text=" °C", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(side="left")

    f_tdp = tk.Frame(f4_content, bg="#000000")
    f_tdp.pack(anchor="w", pady=4)
    var_tdp_check = tk.BooleanVar(value=True)
    chk_tdp = tk.Checkbutton(f_tdp, text="Adaptive Max TDP: ", variable=var_tdp_check, font=("Arial", 9, "bold"), bg="#000000", fg="#ffffff", selectcolor="#1a1a1a", activebackground="#000000", activeforeground="#ffffff")
    chk_tdp.pack(side="left")
    sp_tdp = tk.Spinbox(f_tdp, from_=10, to=65, width=5, bg="#1a1a1a", fg="#ffffff", insertbackground="white")
    sp_tdp.delete(0, "end"); sp_tdp.insert(0, "38")
    sp_tdp.pack(side="left")
    tk.Label(f_tdp, text=" W", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(side="left")

    f_igpu = tk.Frame(f4_content, bg="#000000")
    f_igpu.pack(anchor="w", pady=4)
    tk.Label(f_igpu, text="iGPU Clock Offset: ", font=("Arial", 9, "bold"), fg="#ffffff", bg="#000000").pack(side="left")
    sp_igpu = tk.Spinbox(f_igpu, from_=0, to=1500, increment=25, width=6, bg="#1a1a1a", fg="#ffffff", insertbackground="white")
    sp_igpu.delete(0, "end"); sp_igpu.insert(0, "800")
    sp_igpu.pack(side="left")
    tk.Label(f_igpu, text=" + MHz", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(side="left")

    lbl_warning = tk.Label(
        f4_content, text="Aviso: O overclock pode causar instabilidade. Requer privilégios de Administrador e processadores desbloqueados.", 
        font=("Arial", 8), fg="#ff6b6b", bg="#000000", justify="left", wraplength=_px(480)
    )
    lbl_warning.pack(pady=10, anchor="w")

    btn_apply_amd = tk.Button(f4_content, text="APLICAR PERFIL AMD", bg="#00a88f", fg="white", font=("Arial", 9, "bold"), command=aplicar_tuning_amd, relief="flat", padx=15, pady=6, cursor="hand2")
    btn_apply_amd.pack(anchor="w", pady=5)

    lbl_amd_output = tk.Label(f4_content, text="Output: Clique em APLICAR para gerar os argumentos", font=("Consolas", 8), fg="#aaaaaa", bg="#000000", wraplength=_px(480), justify="left")
    lbl_amd_output.pack(anchor="w", pady=5)

    # ==========================================
    # --- ABA 5: EMPURRÃOZINHO ---
    # ==========================================
    frame_aba5 = tk.Frame(f5, bg="#000000", padx=15, pady=10)
    frame_aba5.pack(fill="both", expand=True)

    col_esq5 = tk.Frame(frame_aba5, bg="#000000")
    col_esq5.pack(side="left", fill="both", expand=True)

    # Bloco com a largura do controle mais largo: as duas listas e a fileira de botões ficam do mesmo tamanho
    bloco5 = tk.Frame(col_esq5, bg="#000000")
    bloco5.pack(anchor="w")

    tk.Label(bloco5, text="PRESETS GRAFICOS ULTRA-BAIXOS", font=F_TIT, fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))

    tk.Label(bloco5, text="Selecione o Jogo:", font=F_TXT, fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_jogo_empurrao = combo_grande(bloco5, values=list(PRESETS_EMPURRAO.keys()), width=32)
    combo_jogo_empurrao.pack(fill="x", pady=(0, 8))
    combo_jogo_empurrao.bind("<<ComboboxSelected>>", atualizar_niveis_empurrao)

    tk.Label(bloco5, text="Selecione o Nível do Patch:", font=F_TXT, fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_nivel_empurrao = combo_grande(bloco5, width=32)
    combo_nivel_empurrao.pack(fill="x", pady=(0, 8))
    combo_nivel_empurrao.bind("<<ComboboxSelected>>", atualizar_preview_empurrao)

    lbl_empurrao_alvo = tk.Label(bloco5, text="Arquivo Alvo: -", font=F_PEQ, fg="#38b6ff", bg="#000000")
    lbl_empurrao_alvo.pack(anchor="w", pady=(0, 15))

    frame_botoes = tk.Frame(bloco5, bg="#000000")
    frame_botoes.pack(fill="x", pady=5)
    frame_botoes.grid_columnconfigure(0, weight=1, uniform="preset")
    frame_botoes.grid_columnconfigure(1, weight=1, uniform="preset")

    btn_empurrao = tk.Button(frame_botoes, text="APLICAR PRESET", bg="#dc3545", fg="white", font=F_TIT, command=aplicar_preset_empurrao, relief="flat", padx=15, pady=8, cursor="hand2")
    btn_empurrao.grid(row=0, column=0, sticky="ew", padx=(0, 5))

    btn_reverter = tk.Button(frame_botoes, text="🔄 REVERTER", bg="#6c757d", fg="white", font=F_TIT, command=reverter_preset_empurrao, relief="flat", padx=15, pady=8, cursor="hand2", state="disabled")
    btn_reverter.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    # O resultado fica FORA do bloco: textos longos dele não podem alargar as listas e os botões
    lbl_resultado_empurrao = tk.Label(col_esq5, text="", font=F_TIT, bg="#000000", justify="left")
    lbl_resultado_empurrao.pack(anchor="w", pady=10)

    col_dir5 = tk.Frame(frame_aba5, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
    col_dir5.pack(side="right", fill="both", expand=True, padx=(15, 0))

    tk.Label(col_dir5, text="DETALHES DO JOGO", font=F_TIT, fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))

    lbl_desc_empurrao = tk.Label(col_dir5, text="-", font=F_ITA, fg="#aaaaaa", bg="#121212", wraplength=_px(300), justify="left")
    lbl_desc_empurrao.pack(anchor="w", pady=(0, 10))

    tk.Label(col_dir5, text="PREVIEW GRÁFICO (Clique para Zoom):", font=F_PEQ, fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(5, 2))
    lbl_img_preview = tk.Label(col_dir5, text="Aguardando seleção...", font=F_TXT, bg="#1a1a1a", fg="#888888", width=26, height=8)
    lbl_img_preview.pack(fill="x", pady=(0, 10))
    lbl_img_preview.bind("<Button-1>", abrir_zoom)

    tk.Label(col_dir5, text="PREVIEW DO ARQUIVO:", font=F_PEQ, fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(5, 2))
    txt_preview_empurrao = tk.Text(col_dir5, height=6, width=25, font=F_MONO, bg="#1a1a1a", fg="#e0e0e0", insertbackground="white", relief="solid", bd=1)
    txt_preview_empurrao.pack(fill="both", expand=True)
    txt_preview_empurrao.config(state="disabled")

    # ==========================================
    # --- ABA 6: AGENTE DE IA ---
    # ==========================================
    frame_aba6 = tk.Frame(f6, bg="#000000", padx=15, pady=10)
    frame_aba6.pack(fill="both", expand=True)

    col_esq6 = tk.Frame(frame_aba6, bg="#000000")
    col_esq6.pack(side="left", fill="both", expand=True)

    # Bloco com a largura do controle mais largo (a fileira ATIVAR/PAUSAR/REVERTER): listas suspensas e botões
    # de nitidez esticam até a mesma largura, com as bordas esquerda e direita alinhadas.
    bloco6 = tk.Frame(col_esq6, bg="#000000")
    bloco6.pack(anchor="w")

    tk.Label(bloco6, text="CONFIGURAÇÃO DO AGENTE INTELIGENTE", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 15))

    tk.Label(bloco6, text="Selecione o Jogo (Instalado):", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_jogos_ia = ttk.Combobox(bloco6, values=list(PRESETS_EMPURRAO.keys()), width=32, state="readonly")
    combo_jogos_ia.pack(fill="x", pady=(0, 15))

    tk.Label(bloco6, text="Taxa de FPS Desejada (Meta):", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_fps_ia = ttk.Combobox(bloco6, values=["24", "30", "40", "60", "90", "120"], width=32, state="readonly")
    combo_fps_ia.set("30")
    combo_fps_ia.pack(fill="x", pady=(0, 15))

    var_fsr = tk.BooleanVar(value=True)
    chk_fsr = tk.Checkbutton(
        bloco6, 
        text="Aplicar filtro de nitidez (Tipo FSR) na próxima vez que o título for reiniciado", 
        variable=var_fsr, 
        font=("Arial", 9, "bold"), 
        bg="#000000", 
        fg="#38b6ff", 
        selectcolor="#1a1a1a", 
        activebackground="#000000", 
        activeforeground="#ffffff",
        wraplength=_px(300), justify="left", anchor="w"
    )
    chk_fsr.pack(fill="x", pady=(0, 5))
    bloco6.bind("<Configure>", lambda e: chk_fsr.configure(wraplength=max(200, e.width - 30)))

    tk.Label(bloco6, text="Nível do filtro de nitidez (estilo FSR):", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
    combo_nitidez_fsr = ttk.Combobox(bloco6, values=["Baixa (Suave)", "Média (Padrão)", "Alta (Nítida)", "Máxima (Agressiva)"], width=32, state="readonly")
    combo_nitidez_fsr.set("Média (Padrão)")
    combo_nitidez_fsr.pack(fill="x", pady=(0, 6))

    frame_botoes_nitidez = tk.Frame(bloco6, bg="#000000")
    frame_botoes_nitidez.pack(fill="x", pady=(0, 20))
    frame_botoes_nitidez.grid_columnconfigure(0, weight=1, uniform="nitidez")
    frame_botoes_nitidez.grid_columnconfigure(1, weight=1, uniform="nitidez")
    tk.Button(frame_botoes_nitidez, text="APLICAR NITIDEZ", bg="#38b6ff", fg="white", font=("Arial", 9, "bold"), command=aplicar_nitidez_ia, relief="flat", padx=12, pady=5, cursor="hand2").grid(row=0, column=0, sticky="ew", padx=(0, 5))
    tk.Button(frame_botoes_nitidez, text="REMOVER NITIDEZ", bg="#6c757d", fg="white", font=("Arial", 9, "bold"), command=remover_nitidez_ia, relief="flat", padx=12, pady=5, cursor="hand2").grid(row=0, column=1, sticky="ew", padx=(5, 0))

    # O status fica FORA do bloco: textos longos dele não podem alargar as colunas acima
    lbl_status_ia = tk.Label(col_esq6, text="Status: Aguardando inicialização...", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000", justify="left")

    frame_botoes_ia = tk.Frame(bloco6, bg="#000000")
    frame_botoes_ia.pack(fill="x", pady=5)

    btn_ativar_ia = tk.Button(frame_botoes_ia, text="ATIVAR AGENTE", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=ativar_agente_ia, relief="flat", padx=15, pady=8, cursor="hand2")
    btn_ativar_ia.pack(side="left", fill="x", expand=True, padx=(0, 10))

    btn_pausar_ia = tk.Button(frame_botoes_ia, text="PAUSAR", bg="#ff9800", fg="white", font=("Arial", 9, "bold"), command=pausar_agente_ia, relief="flat", padx=15, pady=8, cursor="hand2")
    btn_pausar_ia.pack(side="left", fill="x", expand=True, padx=(0, 10))

    btn_reverter_ia = tk.Button(frame_botoes_ia, text="REVERTER", bg="#dc3545", fg="white", font=("Arial", 9, "bold"), command=reverter_agente_ia, relief="flat", padx=15, pady=8, cursor="hand2")
    btn_reverter_ia.pack(side="left", fill="x", expand=True)

    lbl_status_ia.pack(anchor="w", pady=15)

    col_dir6 = tk.Frame(frame_aba6, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
    col_dir6.pack(side="right", fill="both", expand=True, padx=(15, 0))

    tk.Label(col_dir6, text="PAINEL DE INFORMAÇÕES", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))

    lbl_info_ia = tema.TextoJustificado(
        col_dir6,
        texto="O Agente Roda Liso atua em conformidade estrita com a segurança dos arquivos.\n\n"
              "1. O botão PAUSAR suspende as medições e as sugestões. Clique em ATIVAR AGENTE para retomar.\n\n"
              "2. A IA não aplica rebaixamentos agressivos desnecessários. O motor LangGraph cruza sua meta de FPS com as configurações atuais.\n\n"
              "3. O filtro de nitidez usa o ReShade (efeito CAS, da família do FSR). Ele precisa estar instalado na pasta do jogo; veja a mensagem ao clicar em APLICAR NITIDEZ.",
        fonte=("Segoe UI", 9, "italic"), fg="#aaaaaa", bg="#121212"
    )
    lbl_info_ia.pack(fill="x", pady=10)

    # ==========================================
    # --- ABA 7: OTIMIZADOR DE SO (painel embutido, reversível) ---
    # ==========================================
    try:
        from otimizador_so import PainelOtimizadorSO
        PainelOtimizadorSO(f7).pack(fill="both", expand=True, padx=10, pady=10)
    except Exception as erro_so:
        tk.Label(f7, text=f"Não foi possível carregar o Otimizador de SO:\n{erro_so}", fg="#dc3545",
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