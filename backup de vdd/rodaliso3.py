import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser
import os
import subprocess

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

# Dicionário de jogos associado ao caminho da imagem de capa
JOGOS = {
    "CS 2": {"cpu": 200, "gpu": 150, "ram": "4 GB", "capa": "capas/cs2.png"},
    "GTA V": {"cpu": 400, "gpu": 350, "ram": "8 GB", "capa": "capas/gtav.png"},
    "Red Dead Redemption 2": {"cpu": 600, "gpu": 550, "ram": "12 GB", "capa": "capas/rdr2.png"},
    "Cyberpunk 2077": {"cpu": 800, "gpu": 850, "ram": "16 GB", "capa": "capas/cyberpunk.png"},
    "MW2 2009": {"cpu": 100, "gpu": 45, "ram": "1 GB", "capa": "capas/mw2.png"},
    "Black Ops 2": {"cpu": 110, "gpu": 50, "ram": "2 GB", "capa": "capas/bo2.png"},
    "MW3 2011": {"cpu": 100, "gpu": 50, "ram": "2 GB", "capa": "capas/mw3.png"}
}

FIXES = {
    "GTA V - Fix de Stuttering e VRAM (commandline.txt)": {
        "arquivo_alvo": "commandline.txt",
        "descricao": "Corrige travamentos de textura e alocação incorreta de memória VRAM em GPUs antigas/intermediárias.",
        "conteudo": "-ignoreDifferentVideoCard\n-DX11\n-unlimitedcputails\n-strMemLim 4096\n-BFM\n-frameLimit 0"
    },
    "CS 2 - Autoexec de Alto Desempenho (autoexec.cfg)": {
        "arquivo_alvo": "autoexec.cfg",
        "descricao": "Otimiza a taxa de quadros (FPS), reduz o input lag e desativa efeitos visuais pesados.",
        "conteudo": "fps_max 0\ncl_forcepreload 1\nr_drawtracers_firstperson 0\nengine_low_latency_sleep_after_client_tick true\n"
    },
    "Cyberpunk 2077 - Stutter Fix (engine_config.ini)": {
        "arquivo_alvo": "engine_config.ini",
        "descricao": "Melhora o carregamento assíncrono de arquivos para evitar quedas bruscas de FPS na cidade.",
        "conteudo": "[Streaming]\nAsyncEngineLoading = true\nDisableAsyncLoading = false\n"
    },
    "Geral - Fix de DXVK para Placas Antigas (dxvk.conf)": {
        "arquivo_alvo": "dxvk.conf",
        "descricao": "Força a compilação de shaders em segundo plano para jogos convertidos de DirectX para Vulkan.",
        "conteudo": "dxvk.enableAsync = true\ndxvk.numCompilerThreads = 0\n"
    }
}

# --- AUTO-DETECÇÃO DE HARDWARE DO WINDOWS ---
def auto_detectar_hardware():
    cpu_encontrada, gpu_encontrada, ram_encontrada = "", "", ""
    try:
        # Detecta CPU
        cmd_cpu = 'powershell "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name"'
        out_cpu = subprocess.check_output(cmd_cpu, shell=True, text=True, encoding="utf-8", errors="ignore").strip()
        for c in CPUS.keys():
            # Procura por correspondência parcial (ex: "i5-4590" ou "5600X")
            modelo = c.replace("Intel ", "").replace("Core ", "").replace("AMD ", "").replace("Ryzen ", "")
            if modelo.lower() in out_cpu.lower():
                cpu_encontrada = c
                break

        # Detecta GPU
        cmd_gpu = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
        out_gpu = subprocess.check_output(cmd_gpu, shell=True, text=True, encoding="utf-8", errors="ignore").strip()
        for g in GPUS.keys():
            modelo = g.replace("NVIDIA ", "").replace("AMD ", "").replace("Intel ", "")
            if modelo.lower() in out_gpu.lower():
                gpu_encontrada = g
                break

        # Detecta RAM
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

# --- LÓGICA DA ABA 1 (DIAGNÓSTICO & CAPA DO JOGO) ---
def atualizar_jogo_selecionado(event=None):
    jogo = combo_jogos.get()
    if jogo in JOGOS:
        caminho_capa = JOGOS[jogo]["capa"]
        if os.path.exists(caminho_capa):
            try:
                img = tk.PhotoImage(file=caminho_capa)
                lbl_imagem_jogo.config(image=img, text="")
                lbl_imagem_jogo.image = img  # Mantém referência da imagem na memória
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

# --- LÓGICA DA ABA 3 (CORREÇÃO DE PROBLEMAS) ---
def atualizar_descricao_fix(event):
    fix_selecionado = combo_fixes.get()
    if fix_selecionado in FIXES:
        lbl_desc_fix.config(text=FIXES[fix_selecionado]["descricao"], fg="#333333")

def aplicar_correcao_arquivo():
    fix_selecionado = combo_fixes.get()
    if not fix_selecionado or fix_selecionado not in FIXES:
        lbl_resultado_fix.config(text="⚠️ Selecione uma correção da lista!", fg="orange")
        return

    dados_fix = FIXES[fix_selecionado]
    nome_arquivo = dados_fix["arquivo_alvo"]

    caminho_destino = filedialog.asksaveasfilename(
        title=f"Selecione a pasta do jogo para salvar {nome_arquivo}",
        initialfile=nome_arquivo,
        filetypes=[("Arquivos de Configuração", "*.txt *.cfg *.ini *.conf"), ("Todos os Arquivos", "*.*")]
    )

    if caminho_destino:
        try:
            if os.path.exists(caminho_destino):
                os.replace(caminho_destino, caminho_destino + ".bak")

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

def abrir_video(url):
    webbrowser.open(url)

# --- UI SETUP (VISUAL CLEAN) ---
root = tk.Tk()
root.title("Roda Liso v2.0 - Performance Hub")
root.geometry("720x580")
root.configure(bg="#f8f9fa")

style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", bg="#f8f9fa", borderwidth=0)
style.configure("TNotebook.Tab", padding=[15, 6], font=("Arial", 9, "bold"))
style.configure("TFrame", bg="#f8f9fa")

nb = ttk.Notebook(root)
nb.pack(pady=10, padx=10, expand=True, fill="both")

f1 = ttk.Frame(nb)
f2 = ttk.Frame(nb)
f3 = ttk.Frame(nb)
f4 = ttk.Frame(nb)

nb.add(f1, text="Diagnóstico")
nb.add(f2, text="Tutoriais")
nb.add(f3, text="Correção de Problemas")
nb.add(f4, text="Performance AMD")

# --- CONTEÚDO ABA 1 (DIAGNÓSTICO LAYOUT CLEAN) ---
frame_aba1 = tk.Frame(f1, bg="#f8f9fa", padx=15, pady=10)
frame_aba1.pack(fill="both", expand=True)

# Coluna Esquerda: Formulario
col_esquerda = tk.Frame(frame_aba1, bg="#f8f9fa")
col_esquerda.pack(side="left", fill="both", expand=True)

tk.Label(col_esquerda, text="CONFIGURAÇÃO DO SEU PC", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))

tk.Label(col_esquerda, text="Processador:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_cpu = ttk.Combobox(col_esquerda, values=list(CPUS.keys()), width=32, state="readonly")
combo_cpu.pack(anchor="w", pady=(0, 8))

tk.Label(col_esquerda, text="Placa de Vídeo:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_gpu = ttk.Combobox(col_esquerda, values=list(GPUS.keys()), width=32, state="readonly")
combo_gpu.pack(anchor="w", pady=(0, 8))

tk.Label(col_esquerda, text="Memória RAM:", font=("Arial", 9), bg="#f8f9fa").pack(anchor="w")
combo_ram = ttk.Combobox(col_esquerda, values=RAMS, width=32, state="readonly")
combo_ram.pack(anchor="w", pady=(0, 15))

tk.Label(col_esquerda, text="JOGO DESEJADO", font=("Arial", 9, "bold"), fg="#6c757d", bg="#f8f9fa").pack(anchor="w", pady=(0, 5))
combo_jogos = ttk.Combobox(col_esquerda, values=list(JOGOS.keys()), width=32, state="readonly")
combo_jogos.pack(anchor="w", pady=(0, 15))
combo_jogos.bind("<<ComboboxSelected>>", atualizar_jogo_selecionado)

btn_exec = tk.Button(
    col_esquerda, text="VERIFICAR COMPATIBILIDADE", bg="#28a745", fg="white", 
    font=("Arial", 9, "bold"), command=verificar_compatibilidade, relief="flat", padx=15, pady=8, cursor="hand2"
)
btn_exec.pack(anchor="w", pady=5)

lbl_resultado = tk.Label(col_esquerda, text="", font=("Arial", 10, "bold"), bg="#f8f9fa", justify="left")
lbl_resultado.pack(anchor="w", pady=10)

# Coluna Direita: Capa do Jogo (Card Clean)
col_direita = tk.Frame(frame_aba1, bg="#ffffff", highlightbackground="#e9ecef", highlightthickness=1, padx=15, pady=15)
col_direita.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_direita, text="VISUALIZAÇÃO DO TÍTULO", font=("Arial", 9, "bold"), fg="#6c757d", bg="#ffffff").pack(pady=(0, 10))

lbl_imagem_jogo = tk.Label(col_direita, text="Selecione um jogo ao lado", font=("Arial", 9, "italic"), bg="#e9ecef", width=25, height=12)
lbl_imagem_jogo.pack(expand=True, fill="both")

# --- CONTEÚDO ABA 2 (TUTORIAIS CLEAN) ---
tk.Label(f2, text="CENTRAL DE CONHECIMENTO", font=("Arial", 12, "bold"), bg="#f8f9fa").pack(pady=15)

btns_links = [
    ("Limpeza de Sistema e Debloat", "https://www.youtube.com/results?search_query=debloat+windows+10+11"),
    ("Undervolt e Gestão Térmica", "https://www.youtube.com/results?search_query=tutorial+undervolt+gpu+ptbr"),
    ("Diminuir Temperatura de Processadores Ryzen", "https://www.youtube.com/watch?v=frsiS3g0-Mk"),
    ("Overclock em Qualquer Placa de Vídeo", "https://www.youtube.com/watch?v=BUMwelj3SaY"),
    ("Como Converter Jogos DirectX para Vulkan (DXVK)", "https://github.com/doitsujin/DXVK"),
    ("Otimização de Drivers Legacy", "https://www.youtube.com/results?search_query=como+instalar+drivers+antigos+corretamente")
]

for txt, url in btns_links:
    b = tk.Button(f2, text=f"📺  {txt}", width=50, command=lambda u=url: abrir_video(u), bg="#ffffff", relief="solid", bd=1, pady=6, cursor="hand2")
    b.pack(pady=4)

# --- CONTEÚDO ABA 3 (CORREÇÃO CLEAN) ---
tk.Label(f3, text="CORREÇÃO E FIXES DE JOGOS", font=("Arial", 12, "bold"), bg="#f8f9fa").pack(pady=15)

combo_fixes = ttk.Combobox(f3, values=list(FIXES.keys()), width=55, state="readonly")
combo_fixes.pack(pady=5)
combo_fixes.bind("<<ComboboxSelected>>", atualizar_descricao_fix)

lbl_desc_fix = tk.Label(f3, text="Selecione um fix acima para ver a descrição.", font=("Arial", 9, "italic"), fg="#6c757d", bg="#f8f9fa", wraplength=500, justify="center")
lbl_desc_fix.pack(pady=15)

btn_fix = tk.Button(f3, text="SELECIONAR ARQUIVO E APLICAR CORREÇÃO", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=aplicar_correcao_arquivo, relief="flat", padx=15, pady=8, cursor="hand2")
btn_fix.pack(pady=10)

lbl_resultado_fix = tk.Label(f3, text="", font=("Arial", 9, "bold"), bg="#f8f9fa", justify="center")
lbl_resultado_fix.pack(pady=10)

# --- CONTEÚDO ABA 4 (PERFORMANCE AMD) ---
frame_top_amd = tk.Frame(f4, bg="#00a88f", pady=6)
frame_top_amd.pack(fill="x")

lbl_apu_header = tk.Label(frame_top_amd, text="APU: AMD Ryzen Series (Custom Tuning)", font=("Arial", 10, "bold"), fg="white", bg="#00a88f")
lbl_apu_header.pack()

f4_content = tk.Frame(f4, bg="#f8f9fa", padx=20, pady=10)
f4_content.pack(fill="both", expand=True)

# Controles
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

root.mainloop()