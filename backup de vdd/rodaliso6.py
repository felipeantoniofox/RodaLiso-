import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser
import os
import subprocess
import shutil


# --- BANCO DE DADOS (Escala 1 a 1000) ---
CPUS = {
    "Intel Core i7-950": 150,
    "Intel Core i3-4130": 150,
    "Intel Core i5-4590": 280,
    "Intel Core i5-9400F": 450,
    "AMD Ryzen 5 5500U": 520,
    "AMD Ryzen 5 5600X": 720,
    "Intel Core i9-14900K": 980
}

GPUS = {
    "Intel HD Graphics 4000": 50,
    "AMD Radeon Vega 7 (Integrated)": 110,
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

PRESETS_EMPURRAO = {
    "GTA V - Preset Potato Mode (Ultra Low)": {
        "arquivo_alvo": "settings.xml",
        "descricao": "Reduz sombras para 512x512, zera distância de renderização de pedestres/veículos e desativa oclusão de ambiente.",
        "conteudo": """<?xml version="1.0" encoding="UTF-8"?>
<Settings>
  <graphics>
    <ShadowQuality value="0" />
    <TextureQuality value="0" />
    <ReflectionQuality value="0" />
    <WaterQuality value="0" />
    <ShaderQuality value="0" />
    <Shadow_Distance value="0.000000" />
    <PedDistance value="0.000000" />
    <VehicleDistance value="0.000000" />
    <Shadow_SoftShadows value="0" />
  </graphics>
</Settings>"""
    },
    "Cyberpunk 2077 - Potato Preset 720p": {
        "arquivo_alvo": "UserSettings.json",
        "descricao": "Desativa iluminação volumétrica, sombras em cascata, densidade de multidão no mínimo e reduz escala interna.",
        "conteudo": """{
  "gamedb": {
    "RayTracing": false,
    "CrowdDensity": 0,
    "VolumetricFog": 0,
    "CascadedShadows": 0,
    "ScreenSpaceReflections": 0,
    "SubsurfaceScattering": 0
  }
}"""
    },
    "Red Dead Redemption 2 - Ultra Low Boost": {
        "arquivo_alvo": "system.xml",
        "descricao": "Força sombras em resolução mínima, desativa física complexa de neve/lama e reduz reflexos ao patamar mais baixo.",
        "conteudo": """<?xml version="1.0" encoding="UTF-8"?>
<optics>
  <quality value="kSettingLevel_UltraLow" />
  <shadowQuality value="0" />
  <waterQuality value="0" />
  <reflectionQuality value="0" />
  <volumetricsQuality value="0" />
</optics>"""
    },
    "CS 2 - Config Potato FPS": {
        "arquivo_alvo": "video.txt",
        "descricao": "Configura o jogo abaixo do painel do menu: desativa iluminação global, sombras dinâmicas e reduz detalhes de partículas.",
        "conteudo": """"VideoConfig"
{
	"setting.gpu_mem_level"		"0"
	"setting.gpu_other_level"		"0"
	"setting.cpu_level"		"0"
	"setting.csm_quality"		"0"
	"setting.mat_antialias"		"0"
}"""
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
                lbl_imagem_jogo.config(image="", text="🖼️ [Imagem do Jogo]", fg="gray")
        else:
            lbl_imagem_jogo.config(image="", text="🖼️ [Capa não encontrada]", fg="gray")

def verificar_compatibilidade():
    cpu_escolhida = combo_cpu.get()
    gpu_escolhida = combo_gpu.get()
    ram_escolhida = combo_ram.get()
    jogo_escolhido = combo_jogos.get()

    if not all([cpu_escolhida, gpu_escolhida, ram_escolhida, jogo_escolhido]):
        lbl_resultado.config(text="⚠️ Selecione todos os campos!", fg="orange")
        return

    pontos_cpu = CPUS[cpu_escolhida]
    pontos_gpu = GPUS[gpu_escolhida]
    ram_pc_mb = converter_ram_para_mb(ram_escolhida)
    
    req_cpu = JOGOS[jogo_escolhido]["cpu"]
    req_gpu = JOGOS[jogo_escolhido]["gpu"]
    req_ram_mb = converter_ram_para_mb(JOGOS[jogo_escolhido]["ram"])

    if pontos_cpu >= req_cpu and pontos_gpu >= req_gpu and ram_pc_mb >= req_ram_mb:
        lbl_resultado.config(text=f"🟢 RODA LISO!\nScore Hardware: {pontos_cpu + pontos_gpu}/2000", fg="green")
    elif ram_pc_mb < req_ram_mb:
        lbl_resultado.config(text=f"🔴 MEMÓRIA INSUFICIENTE\nRequisito: {JOGOS[jogo_escolhido]['ram']}\nVocê tem: {ram_escolhida}", fg="red")
    else:
        gargalo = "GPU" if pontos_gpu < req_gpu else "CPU"
        diff = req_gpu - pontos_gpu if gargalo == "GPU" else req_cpu - pontos_cpu
        lbl_resultado.config(text=f"🟡 GARGALO DETECTADO ({gargalo})\nFaltam {diff} pts de performance.", fg="#d4a017")

# --- LÓGICA DA ABA 2 (TUTORIAIS CLEAN) ---
def selecionar_tutorial(event=None):
    tut_nome = combo_tutoriais.get()
    if tut_nome in TUTORIAIS:
        dados = TUTORIAIS[tut_nome]
        lbl_tut_titulo.config(text=tut_nome)
        lbl_tut_desc.config(text=dados["desc"], fg="#333333")
        btn_abrir_tut.config(state="normal", command=lambda: abrir_video(dados["url"]))

# --- LÓGICA DA ABA 3 (CORREÇÃO CLEAN) ---
def atualizar_descricao_fix(event=None):
    fix_selecionado = combo_fixes.get()
    if fix_selecionado in FIXES:
        dados = FIXES[fix_selecionado]
        lbl_fix_alvo.config(text=f"Arquivo Alvo: {dados['arquivo_alvo']}", fg="#007bff")
        lbl_desc_fix.config(text=dados["descricao"], fg="#333333")
        txt_preview_fix.config(state="normal")
        txt_preview_fix.delete("1.0", tk.END)
        txt_preview_fix.insert(tk.END, dados["conteudo"])
        txt_preview_fix.config(state="disabled")

def aplicar_correcao_arquivo():
    fix_selecionado = combo_fixes.get()
    if not fix_selecionado or fix_selecionado not in FIXES:
        lbl_resultado_fix.config(text="⚠️ Selecione uma correção!", fg="orange")
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

            lbl_resultado_fix.config(text=f"🟢 SUCESSO!\n'{os.path.basename(caminho_destino)}' aplicado com backup.", fg="green")
        except Exception as e:
            lbl_resultado_fix.config(text=f"🔴 ERRO AO GRAVAR: {e}", fg="red")

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
        lbl_amd_output.config(text="⚠️ Insira valores numéricos válidos!", fg="red")

# --- LÓGICA DA ABA 5 (EMPURRÃOZINHO) ---
def atualizar_descricao_empurrao(event=None):
    preset_selecionado = combo_empurrao.get()
    if preset_selecionado in PRESETS_EMPURRAO:
        dados = PRESETS_EMPURRAO[preset_selecionado]
        lbl_empurrao_alvo.config(text=f"Arquivo Alvo: {dados['arquivo_alvo']}", fg="#007bff")
        lbl_desc_empurrao.config(text=dados["descricao"], fg="#333333")
        txt_preview_empurrao.config(state="normal")
        txt_preview_empurrao.delete("1.0", tk.END)
        txt_preview_empurrao.insert(tk.END, dados["conteudo"])
        txt_preview_empurrao.config(state="disabled")

def aplicar_preset_empurrao():
    preset_selecionado = combo_empurrao.get()
    if not preset_selecionado or preset_selecionado not in PRESETS_EMPURRAO:
        lbl_resultado_empurrao.config(text="⚠️ Selecione um preset!", fg="orange")
        return

    dados_preset = PRESETS_EMPURRAO[preset_selecionado]
    nome_arquivo = dados_preset["arquivo_alvo"]

    caminho_destino = filedialog.asksaveasfilename(
        title=f"Selecione o arquivo {nome_arquivo} do seu jogo para aplicar o preset",
        initialfile=nome_arquivo,
        filetypes=[("Arquivos de Configuração", "*.xml *.ini *.json *.txt *.cfg"), ("Todos os Arquivos", "*.*")]
    )

    if caminho_destino:
        try:
            # Faz backup do arquivo original caso ele já exista no local escolhido
            if os.path.exists(caminho_destino):
                caminho_backup = caminho_destino + ".bak"
                shutil.copyfile(caminho_destino, caminho_backup)
                msg_backup = f"Backup criado: {os.path.basename(caminho_backup)}"
            else:
                msg_backup = "Arquivo criado direto (sem backup prévio)"

            # Grava o novo preset ultra-baixo
            with open(caminho_destino, "w", encoding="utf-8") as f:
                f.write(dados_preset["conteudo"])

            lbl_resultado_empurrao.config(
                text=f"🟢 PRESET APLICADO COM SUCESSO!\n{msg_backup}", 
                fg="green"
            )
        except Exception as e:
            lbl_resultado_empurrao.config(text=f"🔴 ERRO AO GRAVAR PRESET: {e}", fg="red")


# --- UI SETUP ---
root = tk.Tk()
root.title("Roda Liso v2.0 - Performance Hub")
root.geometry("740x600")
root.configure(bg="#f8f9fa")

style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", bg="#f8f9fa", borderwidth=0)
style.configure("TNotebook.Tab", padding=[12, 6], font=("Arial", 9, "bold"))
style.configure("TFrame", bg="#f8f9fa")

nb = ttk.Notebook(root)
nb.pack(pady=10, padx=10, expand=True, fill="both")

f1 = ttk.Frame(nb)
f2 = ttk.Frame(nb)
f3 = ttk.Frame(nb)
f4 = ttk.Frame(nb)
f5 = ttk.Frame(nb)

nb.add(f1, text="Diagnóstico")
nb.add(f2, text="Tutoriais")
nb.add(f3, text="Correção de Problemas")
nb.add(f4, text="Performance AMD")
nb.add(f5, text="Empurrãozinho")

# ==========================================
# --- ABA 1: DIAGNÓSTICO (LAYOUT CLEAN) ---
# ==========================================
frame_aba1 = tk.Frame(f1, bg="#f8f9fa", padx=15, pady=10)
frame_aba1.pack(fill="both", expand=True)

col_esq1 = tk.Frame(frame_aba1, bg="#f8f9fa")
col_esq1.pack(side="left", fill="both", expand=True)

tk.Label(col_esq1, text="CONFIGURAÇÃO DO SEU PC", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))

tk.Label(col_esq1, text="Processador:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_cpu = ttk.Combobox(col_esq1, values=list(CPUS.keys()), width=32, state="readonly")
combo_cpu.pack(anchor="w", pady=(0, 8))

tk.Label(col_esq1, text="Placa de Vídeo:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_gpu = ttk.Combobox(col_esq1, values=list(GPUS.keys()), width=32, state="readonly")
combo_gpu.pack(anchor="w", pady=(0, 8))

tk.Label(col_esq1, text="Memória RAM:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_ram = ttk.Combobox(col_esq1, values=RAMS, width=32, state="readonly")
combo_ram.pack(anchor="w", pady=(0, 15))

tk.Label(col_esq1, text="JOGO DESEJADO", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))
combo_jogos = ttk.Combobox(col_esq1, values=list(JOGOS.keys()), width=32, state="readonly")
combo_jogos.pack(anchor="w", pady=(0, 15))
combo_jogos.bind("<<ComboboxSelected>>", atualizar_jogo_selecionado)

btn_exec = tk.Button(col_esq1, text="VERIFICAR COMPATIBILIDADE", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=verificar_compatibilidade, relief="flat", padx=15, pady=8, cursor="hand2")
btn_exec.pack(anchor="w", pady=5)

lbl_resultado = tk.Label(col_esq1, text="", font=("Arial", 10, "bold"), bg="#f8f9fa", justify="left")
lbl_resultado.pack(anchor="w", pady=10)

col_dir1 = tk.Frame(frame_aba1, bg="#ffffff", highlightbackground="#e9ecef", highlightthickness=1, padx=15, pady=15)
col_dir1.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_dir1, text="VISUALIZAÇÃO DO TÍTULO", font=("Arial", 9, "bold"), fg="#6c757d", bg="#ffffff").pack(pady=(0, 10))
lbl_imagem_jogo = tk.Label(col_dir1, text="Selecione um jogo ao lado", font=("Arial", 9, "italic"), bg="#e9ecef", width=25, height=12)
lbl_imagem_jogo.pack(expand=True, fill="both")

# ==========================================
# --- ABA 2: TUTORIAIS (LAYOUT CLEAN) ---
# ==========================================
frame_aba2 = tk.Frame(f2, bg="#f8f9fa", padx=15, pady=10)
frame_aba2.pack(fill="both", expand=True)

col_esq2 = tk.Frame(frame_aba2, bg="#f8f9fa")
col_esq2.pack(side="left", fill="both", expand=True)

tk.Label(col_esq2, text="CENTRAL DE CONHECIMENTO", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))

tk.Label(col_esq2, text="Selecione o Tópico:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_tutoriais = ttk.Combobox(col_esq2, values=list(TUTORIAIS.keys()), width=32, state="readonly")
combo_tutoriais.pack(anchor="w", pady=(0, 15))
combo_tutoriais.bind("<<ComboboxSelected>>", selecionar_tutorial)

col_dir2 = tk.Frame(frame_aba2, bg="#ffffff", highlightbackground="#e9ecef", highlightthickness=1, padx=15, pady=15)
col_dir2.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_dir2, text="DETALHES DO TUTORIAL", font=("Arial", 9, "bold"), fg="#6c757d", bg="#ffffff").pack(pady=(0, 10))

lbl_tut_titulo = tk.Label(col_dir2, text="Selecione um guia ao lado", font=("Arial", 10, "bold"), bg="#ffffff", fg="#333333", wraplength=220, justify="center")
lbl_tut_titulo.pack(pady=(15, 10))

lbl_tut_desc = tk.Label(col_dir2, text="Escolha uma opção no menu para exibir as instruções e o link correspondente.", font=("Arial", 9, "italic"), fg="#6c757d", bg="#ffffff", wraplength=220, justify="center")
lbl_tut_desc.pack(expand=True, pady=10)

btn_abrir_tut = tk.Button(col_dir2, text="📺 ASSISTIR TUTORIAL", bg="#007bff", fg="white", font=("Arial", 9, "bold"), relief="flat", padx=15, pady=8, cursor="hand2", state="disabled")
btn_abrir_tut.pack(pady=10)

# ==========================================
# --- ABA 3: CORREÇÃO (LAYOUT CLEAN) ---
# ==========================================
frame_aba3 = tk.Frame(f3, bg="#f8f9fa", padx=15, pady=10)
frame_aba3.pack(fill="both", expand=True)

col_esq3 = tk.Frame(frame_aba3, bg="#f8f9fa")
col_esq3.pack(side="left", fill="both", expand=True)

tk.Label(col_esq3, text="CORREÇÃO E FIXES DE JOGOS", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))

tk.Label(col_esq3, text="Selecione a Correção:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_fixes = ttk.Combobox(col_esq3, values=list(FIXES.keys()), width=32, state="readonly")
combo_fixes.pack(anchor="w", pady=(0, 8))
combo_fixes.bind("<<ComboboxSelected>>", atualizar_descricao_fix)

lbl_fix_alvo = tk.Label(col_esq3, text="Arquivo Alvo: -", font=("Arial", 8, "bold"), fg="#6c757d", bg="#f8f9fa")
lbl_fix_alvo.pack(anchor="w", pady=(0, 15))

btn_fix = tk.Button(col_esq3, text="APLICAR CORREÇÃO", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=aplicar_correcao_arquivo, relief="flat", padx=15, pady=8, cursor="hand2")
btn_fix.pack(anchor="w", pady=5)

lbl_resultado_fix = tk.Label(col_esq3, text="", font=("Arial", 9, "bold"), bg="#f8f9fa", justify="left")
lbl_resultado_fix.pack(anchor="w", pady=10)

col_dir3 = tk.Frame(frame_aba3, bg="#ffffff", highlightbackground="#e9ecef", highlightthickness=1, padx=15, pady=15)
col_dir3.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_dir3, text="DETALHES DA OTIMIZAÇÃO", font=("Arial", 9, "bold"), fg="#6c757d", bg="#ffffff").pack(pady=(0, 10))

lbl_desc_fix = tk.Label(col_dir3, text="Selecione uma correção para ver a descrição e os parâmetros aplicados.", font=("Arial", 9, "italic"), fg="#6c757d", bg="#ffffff", wraplength=220, justify="left")
lbl_desc_fix.pack(anchor="w", pady=(0, 10))

tk.Label(col_dir3, text="CONTEÚDO DO ARQUIVO:", font=("Arial", 8, "bold"), fg="#6c757d", bg="#ffffff").pack(anchor="w", pady=(5, 2))
txt_preview_fix = tk.Text(col_dir3, height=8, width=25, font=("Consolas", 8), bg="#f8f9fa", fg="#333333", relief="solid", bd=1)
txt_preview_fix.pack(fill="both", expand=True)
txt_preview_fix.config(state="disabled")

# ==========================================
# --- ABA 4: PERFORMANCE AMD ---
# ==========================================
frame_top_amd = tk.Frame(f4, bg="#00a88f", pady=6)
frame_top_amd.pack(fill="x")

lbl_apu_header = tk.Label(frame_top_amd, text="APU: AMD Ryzen Series (Custom Tuning)", font=("Arial", 10, "bold"), fg="white", bg="#00a88f")
lbl_apu_header.pack()

f4_content = tk.Frame(f4, bg="#f8f9fa", padx=20, pady=10)
f4_content.pack(fill="both", expand=True)

f_temp = tk.Frame(f4_content, bg="#f8f9fa")
f_temp.pack(anchor="w", pady=4)
tk.Label(f_temp, text="Adaptive Temp Limit: ", font=("Arial", 9, "bold"), bg="#f8f9fa").pack(side="left")
sp_temp = tk.Spinbox(f_temp, from_=60, to=105, width=5)
sp_temp.delete(0, "end"); sp_temp.insert(0, "98")
sp_temp.pack(side="left")
tk.Label(f_temp, text=" °C", font=("Arial", 9), bg="#f8f9fa").pack(side="left")

f_tdp = tk.Frame(f4_content, bg="#f8f9fa")
f_tdp.pack(anchor="w", pady=4)
var_tdp_check = tk.BooleanVar(value=True)
chk_tdp = tk.Checkbutton(f_tdp, text="Adaptive Max TDP: ", variable=var_tdp_check, font=("Arial", 9, "bold"), bg="#f8f9fa")
chk_tdp.pack(side="left")
sp_tdp = tk.Spinbox(f_tdp, from_=10, to=65, width=5)
sp_tdp.delete(0, "end"); sp_tdp.insert(0, "38")
sp_tdp.pack(side="left")
tk.Label(f_tdp, text=" W", font=("Arial", 9), bg="#f8f9fa").pack(side="left")

f_igpu = tk.Frame(f4_content, bg="#f8f9fa")
f_igpu.pack(anchor="w", pady=4)
tk.Label(f_igpu, text="iGPU Clock Offset: ", font=("Arial", 9, "bold"), bg="#f8f9fa").pack(side="left")
sp_igpu = tk.Spinbox(f_igpu, from_=0, to=1500, increment=25, width=6)
sp_igpu.delete(0, "end"); sp_igpu.insert(0, "800")
sp_igpu.pack(side="left")
tk.Label(f_igpu, text=" + MHz", font=("Arial", 9), bg="#f8f9fa").pack(side="left")

lbl_warning = tk.Label(
    f4_content, text="Aviso: O overclock pode causar instabilidade. Requer privilégios de Administrador e processadores desbloqueados.", 
    font=("Arial", 8), fg="#cc0000", bg="#f8f9fa", justify="left", wraplength=600
)
lbl_warning.pack(pady=10, anchor="w")

btn_apply_amd = tk.Button(f4_content, text="APLICAR PERFIL AMD", bg="#00a88f", fg="white", font=("Arial", 9, "bold"), command=aplicar_tuning_amd, relief="flat", padx=15, pady=6, cursor="hand2")
btn_apply_amd.pack(anchor="w", pady=5)

lbl_amd_output = tk.Label(f4_content, text="Output: Clique em APLICAR para gerar os argumentos", font=("Consolas", 8), fg="gray", bg="#f8f9fa", wraplength=600, justify="left")
lbl_amd_output.pack(anchor="w", pady=5)

# ==========================================
# --- ABA 5: EMPURRÃOZINHO (PRESETS EXTRA-BAIXOS) ---
# ==========================================
frame_aba5 = tk.Frame(f5, bg="#f8f9fa", padx=15, pady=10)
frame_aba5.pack(fill="both", expand=True)

col_esq5 = tk.Frame(frame_aba5, bg="#f8f9fa")
col_esq5.pack(side="left", fill="both", expand=True)

tk.Label(col_esq5, text="PRESETS GRAFICOS ULTRA-BAIXOS", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))

tk.Label(col_esq5, text="Selecione o Jogo / Preset:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_empurrao = ttk.Combobox(col_esq5, values=list(PRESETS_EMPURRAO.keys()), width=32, state="readonly")
combo_empurrao.pack(anchor="w", pady=(0, 8))
combo_empurrao.bind("<<ComboboxSelected>>", atualizar_descricao_empurrao)

lbl_empurrao_alvo = tk.Label(col_esq5, text="Arquivo Alvo: -", font=("Arial", 8, "bold"), fg="#6c757d", bg="#f8f9fa")
lbl_empurrao_alvo.pack(anchor="w", pady=(0, 15))

btn_empurrao = tk.Button(col_esq5, text="APLICAR PRESET EXTRA-BAIXO", bg="#dc3545", fg="white", font=("Arial", 9, "bold"), command=aplicar_preset_empurrao, relief="flat", padx=15, pady=8, cursor="hand2")
btn_empurrao.pack(anchor="w", pady=5)

lbl_resultado_empurrao = tk.Label(col_esq5, text="", font=("Arial", 9, "bold"), bg="#f8f9fa", justify="left")
lbl_resultado_empurrao.pack(anchor="w", pady=10)

col_dir5 = tk.Frame(frame_aba5, bg="#ffffff", highlightbackground="#e9ecef", highlightthickness=1, padx=15, pady=15)
col_dir5.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_dir5, text="DETALHES DO PRESET", font=("Arial", 9, "bold"), fg="#6c757d", bg="#ffffff").pack(pady=(0, 10))

lbl_desc_empurrao = tk.Label(col_dir5, text="Selecione um preset ao lado para ver detalhes e o arquivo alvo.", font=("Arial", 9, "italic"), fg="#6c757d", bg="#ffffff", wraplength=220, justify="left")
lbl_desc_empurrao.pack(anchor="w", pady=(0, 10))

tk.Label(col_dir5, text="PREVIEW DA CONFIGURAÇÃO:", font=("Arial", 8, "bold"), fg="#6c757d", bg="#ffffff").pack(anchor="w", pady=(5, 2))
txt_preview_empurrao = tk.Text(col_dir5, height=8, width=25, font=("Consolas", 8), bg="#f8f9fa", fg="#333333", relief="solid", bd=1)
txt_preview_empurrao.pack(fill="both", expand=True)
txt_preview_empurrao.config(state="disabled")

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
    combo_empurrao.current(0)
    atualizar_descricao_empurrao()

root.mainloop()