import tkinter as tk
from tkinter import ttk, filedialog
import webbrowser
import os

# --- BANCO DE DADOS (Escala 1 a 10000) ---
CPUS = {
    "Intel Core i7-950": 150,
    "Intel Core i3-4130": 150,
    "Intel Core i5-9400F": 450,
    "AMD Ryzen 5 5600X": 720,
    "Intel Core i9-14900K": 980
}

GPUS = {
    "Intel HD Graphics 4000": 50,
    "NVIDIA GTX 750": 60,
    "NVIDIA GTX 750 Ti": 65,
    "NVIDIA GTX 760": 85,
    "NVIDIA GTX 770": 98,
    "NVIDIA GTX 780": 120,
    "NVIDIA GTX 780TI": 150,
    "NVIDIA GTX 950": 88,
    "NVIDIA GTX 960": 95,
    "NVIDIA GTX 970": 150,
    "NVIDIA GTX 980": 160,
    "NVIDIA GTX 980TI": 210,
    "NVIDIA GTX 1030": 55,
    "NVIDIA GTX 1050": 90,
    "NVIDIA GTX 1050 Ti": 102,
    "NVIDIA GTX 1060 3GB": 150,
    "NVIDIA GTX 1060 6GB": 160,
    "NVIDIA GTX 1070": 215,
    "NVIDIA GTX 1070Ti": 240,
    "NVIDIA GTX 1080": 247,
    "NVIDIA GTX 1080Ti": 330,
    "NVIDIA RTX 3060": 680,
    "AMD Radeon RX 7900 XT": 890,
    "NVIDIA RTX 4090": 1161,
    "NVIDIA RTX 5090": 1522
}

RAMS = ["256 MB", "512 MB", "1 GB", "2 GB", "4 GB", "8 GB", "16 GB", "32 GB", "64 GB"]

JOGOS = {
    "CS 2": {"cpu": 200, "gpu": 150, "ram": "4 GB"},
    "GTA V": {"cpu": 400, "gpu": 350, "ram": "8 GB"},
    "Red Dead Redemption 2": {"cpu": 600, "gpu": 550, "ram": "12 GB"},
    "Cyberpunk 2077": {"cpu": 800, "gpu": 850, "ram": "16 GB"},
    "MW2 2009": {"cpu": 100, "gpu": 45, "ram": "1 GB"},
    "Black Ops 2": {"cpu": 110, "gpu": 50, "ram": "2 GB"},
    "MW3 2011": {"cpu": 100, "gpu": 50, "ram": "2 GB"}
}

# --- BANCO DE FIXES / ARQUIVOS DE CONFIGURAÇÃO ---
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

# --- FUNÇÃO AUXILIAR DE MEMÓRIA ---
def converter_ram_para_mb(ram_str):
    partes = ram_str.strip().split()
    valor = int(partes[0])
    unidade = partes[1].upper()
    if unidade == "GB":
        return valor * 1024
    return valor

# --- LÓGICA DE COMPARAÇÃO ---
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
        lbl_resultado.config(text=f"🟢 RODA LISO!\nScore do Hardware: {pontos_cpu + pontos_gpu}/2000", fg="green")
    elif ram_pc_mb < req_ram_mb:
        lbl_resultado.config(text=f"🔴 MEMÓRIA INSUFICIENTE\nRequisito: {JOGOS[jogo_escolhido]['ram']} | Você tem: {ram_escolhida}", fg="red")
    else:
        gargalo = "GPU" if pontos_gpu < req_gpu else "CPU"
        diff = req_gpu - pontos_gpu if gargalo == "GPU" else req_cpu - pontos_cpu
        lbl_resultado.config(text=f"🟡 GARGALO DETECTADO ({gargalo})\nFaltam {diff} pontos de performance.", fg="#d4a017")

# --- LÓGICA DE CORREÇÃO DE ARQUIVOS ---
def atualizar_descricao_fix(event):
    fix_selecionado = combo_fixes.get()
    if fix_selecionado in FIXES:
        lbl_desc_fix.config(text=FIXES[fix_selecionado]["descricao"], fg="black")

def aplicar_correcao_arquivo():
    fix_selecionado = combo_fixes.get()
    
    if not fix_selecionado or fix_selecionado not in FIXES:
        lbl_resultado_fix.config(text="⚠️ Selecione uma correção da lista!", fg="orange")
        return

    dados_fix = FIXES[fix_selecionado]
    nome_arquivo = dados_fix["arquivo_alvo"]

    # Abre a caixa para o usuário selecionar onde está o arquivo original ou salvar a correção
    caminho_destino = filedialog.asksaveasfilename(
        title=f"Selecione a pasta do jogo para salvar/substituir o {nome_arquivo}",
        initialfile=nome_arquivo,
        filetypes=[("Arquivos de Configuração", "*.txt *.cfg *.ini *.conf"), ("Todos os Arquivos", "*.*")]
    )

    if caminho_destino:
        try:
            # Se já existir um arquivo no local, cria um backup (.bak) de segurança
            if os.path.exists(caminho_destino):
                caminho_backup = caminho_destino + ".bak"
                os.replace(caminho_destino, caminho_backup)

            # Grava o conteúdo corrigido
            with open(caminho_destino, "w", encoding="utf-8") as f:
                f.write(dados_fix["conteudo"])

            lbl_resultado_fix.config(
                text=f"🟢 SUCESSO!\nArquivo '{os.path.basename(caminho_destino)}' aplicado com sucesso.", 
                fg="green"
            )
        except Exception as e:
            lbl_resultado_fix.config(text=f"🔴 ERRO AO GRAVAR ARQUIVO: {e}", fg="red")

def abrir_video(url):
    webbrowser.open(url)

# --- UI SETUP ---
root = tk.Tk()
root.title("Roda Liso v2.0 - Performance Hub")
root.geometry("650x520")

style = ttk.Style()
style.configure("TNotebook.Tab", padding=[15, 5])

nb = ttk.Notebook(root)
nb.pack(pady=10, expand=True, fill="both")

f1 = ttk.Frame(nb)
f2 = ttk.Frame(nb)
f3 = ttk.Frame(nb)

nb.add(f1, text="Diagnóstico de Hardware")
nb.add(f2, text="Tutoriais de Otimização")
nb.add(f3, text="Correção de Problemas")

# --- CONTEÚDO ABA 1 ---
tk.Label(f1, text="ENGINE DE COMPARAÇÃO (SCALED 1-1000)", font=("Consolas", 10, "bold"), fg="gray").pack(pady=5)

tk.Label(f1, text="Processador:", font=("Arial", 10)).pack()
combo_cpu = ttk.Combobox(f1, values=list(CPUS.keys()), width=50, state="readonly")
combo_cpu.pack(pady=5)

tk.Label(f1, text="Placa de Vídeo:", font=("Arial", 10)).pack()
combo_gpu = ttk.Combobox(f1, values=list(GPUS.keys()), width=50, state="readonly")
combo_gpu.pack(pady=5)

tk.Label(f1, text="Memória RAM:", font=("Arial", 10)).pack()
combo_ram = ttk.Combobox(f1, values=RAMS, width=50, state="readonly")
combo_ram.pack(pady=5)

ttk.Separator(f1, orient='horizontal').pack(fill='x', pady=15, padx=20)

tk.Label(f1, text="Selecione o Software/Jogo:", font=("Arial", 10, "bold")).pack()
combo_jogos = ttk.Combobox(f1, values=list(JOGOS.keys()), width=50, state="readonly")
combo_jogos.pack(pady=5)

btn = tk.Button(f1, text="EXECUTAR MATCHMAKING", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=verificar_compatibilidade, padx=20)
btn.pack(pady=20)

lbl_resultado = tk.Label(f1, text="", font=("Arial", 11, "bold"), justify="center")
lbl_resultado.pack()

# --- CONTEÚDO ABA 2 ---
tk.Label(f2, text="CENTRAL DE CONHECIMENTO (ODS 4)", font=("Arial", 14, "bold")).pack(pady=20)

btns_links = [
    ("Limpeza de Sistema e Debloat", "https://www.youtube.com/results?search_query=debloat+windows+10+11"),
    ("Undervolt e Gestão Térmica", "https://www.youtube.com/results?search_query=tutorial+undervolt+gpu+ptbr"),
    ("Como diminuir á temperatura dos processadores Ryzen sem gastar dinheiro", "https://www.youtube.com/watch?v=frsiS3g0-Mk"),
    ("Como fazer Overclock em qualquer Placa de Video", "https://www.youtube.com/watch?v=BUMwelj3SaY"),
    ("Como converter jogos de DirectX para Vulkan", "https://github.com/doitsujin/DXVK"),
    ("Como fazer overclock em Intel de 1° á 7° Geração", "https://www.youtube.com/watch?v=nj60vV5Hu2A"),
    ("Otimização de Drivers Legacy", "https://www.youtube.com/results?search_query=como+instalar+drivers+antigos+corretamente")
]

for txt, url in btns_links:
    b = tk.Button(f2, text=f"📺 {txt}", width=45, command=lambda u=url: abrir_video(u), pady=8)
    b.pack(pady=5)

# --- CONTEÚDO ABA 3 ---
tk.Label(f3, text="CORREÇÃO E FIXES DE JOGOS", font=("Arial", 14, "bold")).pack(pady=15)

tk.Label(f3, text="Selecione o problema / arquivo de correção:", font=("Arial", 10)).pack()
combo_fixes = ttk.Combobox(f3, values=list(FIXES.keys()), width=55, state="readonly")
combo_fixes.pack(pady=5)
combo_fixes.bind("<<ComboboxSelected>>", atualizar_descricao_fix)

lbl_desc_fix = tk.Label(f3, text="Selecione um fix acima para ler a descrição.", font=("Arial", 9, "italic"), fg="gray", wraplength=500, justify="center")
lbl_desc_fix.pack(pady=15)

ttk.Separator(f3, orient='horizontal').pack(fill='x', pady=10, padx=20)

btn_fix = tk.Button(f3, text="SELECIONAR ARQUIVO E APLICAR CORREÇÃO", bg="#28a745", fg="white", font=("Arial", 10, "bold"), command=aplicar_correcao_arquivo, padx=15, pady=8)
btn_fix.pack(pady=15)

lbl_resultado_fix = tk.Label(f3, text="", font=("Arial", 10, "bold"), justify="center")
lbl_resultado_fix.pack(pady=10)

root.mainloop()