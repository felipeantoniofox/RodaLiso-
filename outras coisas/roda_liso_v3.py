
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

# --- NOVO BANCO DE DADOS (PRESETS_EMPURRAO) ---
PRESETS_EMPURRAO = {
    "The Witcher 3 2015": {
        "arquivo_alvo": "user.settings", # O arquivo alvo real do jogo
        "descricao_geral": "Ajuste de gráficos do jogo conforme pastas selecionadas.",
        "pasta_backup": "presets/the witcher 3 2015/original antes das modificações",
        "niveis": {
            "Nível 1 - Mais Baixo (Máx. FPS)": {"arquivo": "presets/the witcher 3 2015/Mais Baixo/user.settings", "img": "presets/the witcher 3 2015/Mais Baixo/preview.png"},
            "Nível 2 - Baixo": {"arquivo": "presets/the witcher 3 2015/baixo/user.settings", "img": "presets/the witcher 3 2015/baixo/preview.png"},
            "Nível 3 - Normal": {"arquivo": "presets/the witcher 3 2015/normal/user.settings", "img": "presets/the witcher 3 2015/normal/preview.png"},
            "Nível 4 - Alto": {"arquivo": "presets/the witcher 3 2015/alto/user.settings", "img": "presets/the witcher 3 2015/alto/preview.png"},
            "Nível 5 - Muito Alto": {"arquivo": "presets/the witcher 3 2015/muito alto/user.settings", "img": "presets/the witcher 3 2015/muito alto/preview.png"},
            "Nível 6 - Ultra (Empurrãozinho)": {"arquivo": "presets/the witcher 3 2015/ultra/user.settings", "img": "presets/the witcher 3 2015/ultra/preview.png"}
        }
    },
    # Você pode adicionar mais jogos aqui no mesmo formato
    # "GTA V": {
    #     ...
    # }
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
                img_zoom_atual = img_original # Guarda imagem grande para o zoom
                
                # Reduz imagem para caber no painel lateral (ajuste o fator de subsample conforme necessário)
                # O fator 3 divide largura e altura por 3.
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
        lbl_zoom_overlay.lift() # Traz para frente de tudo

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

    extensao = os.path.splitext(dados_jogo["arquivo_alvo"])[1]

    caminho_original_usuario = filedialog.askopenfilename(
        title=f"Selecione o arquivo ({dados_jogo['arquivo_alvo']}) do seu jogo",
        initialfile=dados_jogo["arquivo_alvo"],
        filetypes=[(f"Arquivo {extensao}", f"*{extensao}"), ("Todos os Arquivos", "*.*")]
    )

    if caminho_original_usuario:
        try:
            # Cria a pasta de backup (original antes das modificações) se não existir
            if not os.path.exists(pasta_backup):
                os.makedirs(pasta_backup)

            caminho_backup = os.path.join(pasta_backup, dados_jogo["arquivo_alvo"] + ".bak")
            
            # Salva o arquivo original SOMENTE se a pasta backup estiver vazia (preserva a primeira config pura)
            if not os.path.exists(caminho_backup):
                shutil.copyfile(caminho_original_usuario, caminho_backup)
            
            # Aplica o novo patch (sobrescreve o original do usuário com o nosso preset)
            shutil.copyfile(caminho_preset_fisico, caminho_original_usuario)
            
            caminho_arquivo_modificado_atual = caminho_original_usuario
            pasta_backup_atual = pasta_backup
            btn_reverter.config(state="normal")
            
            lbl_resultado_empurrao.config(
                text=f"🟢 {nivel} APLICADO!\nBackup seguro na pasta original.", 
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
                # Restaura o backup por cima do arquivo modificado
                shutil.copyfile(caminho_backup, caminho_arquivo_modificado_atual)
                lbl_resultado_empurrao.config(text="🔄 CONFIGURAÇÕES ORIGINAIS RESTAURADAS!", fg="#28a745")
                btn_reverter.config(state="disabled")
            except Exception as e:
                lbl_resultado_empurrao.config(text=f"🔴 ERRO AO REVERTER: {e}", fg="#dc3545")
    else:
        lbl_resultado_empurrao.config(text="🔴 ERRO: Arquivo de backup não encontrado.", fg="#dc3545")

# --- UI SETUP ---
root = tk.Tk()
root.title("Roda Liso v2.0 - Performance Hub")
root.geometry("800x650") # Aumentei um pouco a altura geral para caber a imagem
root.configure(bg="#000000")

# --- OVERLAY PARA O ZOOM (Oculto por padrão) ---
# Fica no topo da hierarquia, acima das abas.
lbl_zoom_overlay = tk.Label(root, bg="#1a1a1a", cursor="X_cursor")
# Clicar na imagem em zoom a faz desaparecer (des-desenhar)
lbl_zoom_overlay.bind("<Button-1>", lambda e: lbl_zoom_overlay.place_forget())

style = ttk.Style()
style.theme_use("clam")

# Estilo Dark para Notebook e Abas
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
# --- ABA 1: DIAGNÓSTICO ---
# ==========================================
frame_aba1 = tk.Frame(f1, bg="#000000", padx=15, pady=10)
frame_aba1.pack(fill="both", expand=True)

col_esq1 = tk.Frame(frame_aba1, bg="#000000")
col_esq1.pack(side="left", fill="both", expand=True)

tk.Label(col_esq1, text="CONFIGURAÇÃO DO SEU PC", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))

tk.Label(col_esq1, text="Processador:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
combo_cpu = ttk.Combobox(col_esq1, values=list(CPUS.keys()), width=32, state="readonly")
combo_cpu.pack(anchor="w", pady=(0, 8))

tk.Label(col_esq1, text="Placa de Vídeo:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
combo_gpu = ttk.Combobox(col_esq1, values=list(GPUS.keys()), width=32, state="readonly")
combo_gpu.pack(anchor="w", pady=(0, 8))

tk.Label(col_esq1, text="Memória RAM:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
combo_ram = ttk.Combobox(col_esq1, values=RAMS, width=32, state="readonly")
combo_ram.pack(anchor="w", pady=(0, 15))

tk.Label(col_esq1, text="JOGO DESEJADO", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))
combo_jogos = ttk.Combobox(col_esq1, values=list(JOGOS.keys()), width=32, state="readonly")
combo_jogos.pack(anchor="w", pady=(0, 15))
combo_jogos.bind("<<ComboboxSelected>>", atualizar_jogo_selecionado)

btn_exec = tk.Button(col_esq1, text="VERIFICAR COMPATIBILIDADE", bg="#28a745", fg="white", font=("Arial", 9, "bold"), command=verificar_compatibilidade, relief="flat", padx=15, pady=8, cursor="hand2")
btn_exec.pack(anchor="w", pady=5)

lbl_resultado = tk.Label(col_esq1, text="", font=("Arial", 10, "bold"), bg="#000000", justify="left")
lbl_resultado.pack(anchor="w", pady=10)

col_dir1 = tk.Frame(frame_aba1, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
col_dir1.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_dir1, text="VISUALIZAÇÃO DO TÍTULO", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))
lbl_imagem_jogo = tk.Label(col_dir1, text="Selecione um jogo ao lado", font=("Arial", 9, "italic"), bg="#1a1a1a", fg="#aaaaaa", width=25, height=12)
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

lbl_tut_titulo = tk.Label(col_dir2, text="Selecione um guia ao lado", font=("Arial", 10, "bold"), bg="#121212", fg="#ffffff", wraplength=220, justify="center")
lbl_tut_titulo.pack(pady=(15, 10))

lbl_tut_desc = tk.Label(col_dir2, text="Escolha uma opção no menu para exibir as instruções e o link correspondente.", font=("Arial", 9, "italic"), fg="#aaaaaa", bg="#121212", wraplength=220, justify="center")
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

lbl_desc_fix = tk.Label(col_dir3, text="Selecione uma correção para ver a descrição e os parâmetros aplicados.", font=("Arial", 9, "italic"), fg="#aaaaaa", bg="#121212", wraplength=220, justify="left")
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
    font=("Arial", 8), fg="#ff6b6b", bg="#000000", justify="left", wraplength=600
)
lbl_warning.pack(pady=10, anchor="w")

btn_apply_amd = tk.Button(f4_content, text="APLICAR PERFIL AMD", bg="#00a88f", fg="white", font=("Arial", 9, "bold"), command=aplicar_tuning_amd, relief="flat", padx=15, pady=6, cursor="hand2")
btn_apply_amd.pack(anchor="w", pady=5)

lbl_amd_output = tk.Label(f4_content, text="Output: Clique em APLICAR para gerar os argumentos", font=("Consolas", 8), fg="#aaaaaa", bg="#000000", wraplength=600, justify="left")
lbl_amd_output.pack(anchor="w", pady=5)

# ==========================================
# --- ABA 5: EMPURRÃOZINHO ---
# ==========================================
frame_aba5 = tk.Frame(f5, bg="#000000", padx=15, pady=10)
frame_aba5.pack(fill="both", expand=True)

col_esq5 = tk.Frame(frame_aba5, bg="#000000")
col_esq5.pack(side="left", fill="both", expand=True)

tk.Label(col_esq5, text="PRESETS GRAFICOS ULTRA-BAIXOS", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#000000").pack(anchor="w", pady=(0, 5))

# --- COMBOBOX DO JOGO ---
tk.Label(col_esq5, text="Selecione o Jogo:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
combo_jogo_empurrao = ttk.Combobox(col_esq5, values=list(PRESETS_EMPURRAO.keys()), width=32, state="readonly")
combo_jogo_empurrao.pack(anchor="w", pady=(0, 8))
combo_jogo_empurrao.bind("<<ComboboxSelected>>", atualizar_niveis_empurrao)

# --- COMBOBOX DO NÍVEL ---
tk.Label(col_esq5, text="Selecione o Nível do Patch:", font=("Arial", 9), fg="#ffffff", bg="#000000").pack(anchor="w")
combo_nivel_empurrao = ttk.Combobox(col_esq5, width=32, state="readonly")
combo_nivel_empurrao.pack(anchor="w", pady=(0, 8))
combo_nivel_empurrao.bind("<<ComboboxSelected>>", atualizar_preview_empurrao)

lbl_empurrao_alvo = tk.Label(col_esq5, text="Arquivo Alvo: -", font=("Arial", 8, "bold"), fg="#38b6ff", bg="#000000")
lbl_empurrao_alvo.pack(anchor="w", pady=(0, 15))

# --- BOTÕES APLICAR E REVERTER ---
frame_botoes = tk.Frame(col_esq5, bg="#000000")
frame_botoes.pack(anchor="w", pady=5)

btn_empurrao = tk.Button(frame_botoes, text="APLICAR PRESET", bg="#dc3545", fg="white", font=("Arial", 9, "bold"), command=aplicar_preset_empurrao, relief="flat", padx=15, pady=8, cursor="hand2")
btn_empurrao.pack(side="left", padx=(0, 10))

btn_reverter = tk.Button(frame_botoes, text="🔄 REVERTER", bg="#6c757d", fg="white", font=("Arial", 9, "bold"), command=reverter_preset_empurrao, relief="flat", padx=15, pady=8, cursor="hand2", state="disabled")
btn_reverter.pack(side="left")

lbl_resultado_empurrao = tk.Label(col_esq5, text="", font=("Arial", 9, "bold"), bg="#000000", justify="left")
lbl_resultado_empurrao.pack(anchor="w", pady=10)

col_dir5 = tk.Frame(frame_aba5, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=15, pady=15)
col_dir5.pack(side="right", fill="both", expand=True, padx=(15, 0))

tk.Label(col_dir5, text="DETALHES DO JOGO", font=("Arial", 9, "bold"), fg="#aaaaaa", bg="#121212").pack(pady=(0, 10))

lbl_desc_empurrao = tk.Label(col_dir5, text="-", font=("Arial", 9, "italic"), fg="#aaaaaa", bg="#121212", wraplength=220, justify="left")
lbl_desc_empurrao.pack(anchor="w", pady=(0, 10))

# --- NOVO: PREVIEW DE IMAGEM ---
tk.Label(col_dir5, text="PREVIEW GRÁFICO (Clique para Zoom):", font=("Arial", 8, "bold"), fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(5, 2))

lbl_img_preview = tk.Label(col_dir5, text="Aguardando seleção...", bg="#1a1a1a", fg="#888888", width=35, height=8)
lbl_img_preview.pack(fill="x", pady=(0, 10))
lbl_img_preview.bind("<Button-1>", abrir_zoom) # Conecta o clique à função de zoom

# --- PREVIEW DE CÓDIGO ---
tk.Label(col_dir5, text="PREVIEW DO ARQUIVO:", font=("Arial", 8, "bold"), fg="#aaaaaa", bg="#121212").pack(anchor="w", pady=(5, 2))
txt_preview_empurrao = tk.Text(col_dir5, height=6, width=25, font=("Consolas", 8), bg="#1a1a1a", fg="#e0e0e0", insertbackground="white", relief="solid", bd=1)
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
    combo_jogo_empurrao.current(0)
    atualizar_niveis_empurrao()

if __name__ == '__main__':
    # root.mainloop() # Comentado para rodar no ambiente de execução
    pass
