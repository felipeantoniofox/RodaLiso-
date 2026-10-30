"""Filtro de nitidez estilo FSR (AMD FidelityFX CAS/RCAS) aplicado pelo Rodaliso via ReShade.

O QUE ISTO FAZ (e o que não faz)
  O FSR 1.0 tem duas etapas: ampliar a imagem (EASU) e dar nitidez (RCAS). Um programa em Python não
  consegue "injetar" a ampliação em um jogo. A etapa de NITIDEZ, porém, é um filtro de pós-processamento
  e o ReShade já sabe rodá-lo dentro do jogo. O Rodaliso então:
    0. se o ReShade não estiver na pasta do jogo, BAIXA E INSTALA sozinho (com a sua permissão);
       o efeito de nitidez (RodaLiso_CAS.fx) já vem embutido neste arquivo: não é baixado de lugar nenhum;
    1. encontra a pasta do executável do jogo;
    2. confere se o ReShade está instalado ali e copia o efeito de nitidez para a pasta de shaders;
    3. cria um preset próprio (RodaLiso_Nitidez.ini) com a intensidade do nível escolhido;
    4. aponta o ReShade.ini para esse preset (guardando o preset original para poder desfazer).

SEGURANÇA
  * Só mexe no ReShade.ini (com backup .rodaliso.bak) e no preset RodaLiso_Nitidez.ini.
  * Na instalação automática, só ADICIONA arquivos (dxgi.dll/d3d9.dll do ReShade + o efeito RodaLiso_CAS.fx).
    Se já existir um dxgi.dll/d3d9.dll de OUTRO programa (ex.: DXVK), nada é sobrescrito.
  * Jogos online com anticheat (ex.: CS 2) ficam bloqueados: ReShade neles pode causar banimento.
  * Remover o filtro devolve o ReShade.ini ao preset que estava antes.
"""
import io
import json
import os
import re
import shutil
import struct
import tempfile
import urllib.request
import zipfile

import psutil

try:
    import winreg  # só existe no Windows
except ImportError:
    winreg = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ESTADO = os.path.join(BASE_DIR, "rodaliso_nitidez.json")
NOME_PRESET = "RodaLiso_Nitidez.ini"

# Efeito do ReShade usado como filtro (AMD FidelityFX CAS: vem na coleção padrão de shaders do ReShade).
# Se no seu ReShade o efeito/parâmetro tiver outro nome (abra o menu do ReShade no jogo, tecla Home,
# e veja o nome do efeito e do controle), ajuste só estas constantes.
EFEITO_ARQUIVO = "RodaLiso_CAS.fx"   # efeito próprio, embutido neste arquivo (SHADER_CAS): não depende de download
TECNICA = "RodaLiso_CAS"
PARAM_NITIDEZ = "Sharpening"
PARAM_CONTRASTE = "Contrast"         # o efeito próprio não tem contraste: é ignorado automaticamente

PASTA_SHADERS_LOCAL = os.path.join(BASE_DIR, "shaders")  # cópia editável do efeito, ao lado do programa

# Efeito do ReShade: nitidez adaptativa ao contraste, mesmo algoritmo do AMD FidelityFX CAS (licença MIT, AMD).
SHADER_CAS = r"""// RodaLiso_CAS.fx - nitidez adaptativa ao contraste (algoritmo AMD FidelityFX CAS, licença MIT).
// Reescrito para o ReShade pelo projeto Roda Liso. Não precisa de outros arquivos.

uniform float Sharpening <
    ui_type = "slider";
    ui_label = "Nitidez";
    ui_min = 0.0; ui_max = 1.0;
> = 0.5;

texture RL_BackBufferTex : COLOR;
sampler RL_BackBuffer { Texture = RL_BackBufferTex; };

float3 RL_Load(int2 p)
{
    p = clamp(p, int2(0, 0), int2(BUFFER_WIDTH - 1, BUFFER_HEIGHT - 1));
    return tex2Dfetch(RL_BackBuffer, p).rgb;
}

void RL_VS(in uint id : SV_VertexID, out float4 position : SV_Position, out float2 texcoord : TEXCOORD)
{
    texcoord.x = (id == 2) ? 2.0 : 0.0;
    texcoord.y = (id == 1) ? 2.0 : 0.0;
    position = float4(texcoord * float2(2.0, -2.0) + float2(-1.0, 1.0), 0.0, 1.0);
}

float3 RL_PS(float4 vpos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    int2 p = int2(vpos.xy);
    //  a b c
    //  d e f
    //  g h i
    float3 a = RL_Load(p + int2(-1, -1));
    float3 b = RL_Load(p + int2( 0, -1));
    float3 c = RL_Load(p + int2( 1, -1));
    float3 d = RL_Load(p + int2(-1,  0));
    float3 e = RL_Load(p);
    float3 f = RL_Load(p + int2( 1,  0));
    float3 g = RL_Load(p + int2(-1,  1));
    float3 h = RL_Load(p + int2( 0,  1));
    float3 i = RL_Load(p + int2( 1,  1));

    // Mínimo e máximo suaves da vizinhança (cruz + cantos)
    float3 mn4 = min(min(b, d), min(e, min(f, h)));
    float3 mn  = mn4 + min(min(mn4, min(a, c)), min(g, i));
    float3 mx4 = max(max(b, d), max(e, max(f, h)));
    float3 mx  = mx4 + max(max(mx4, max(a, c)), max(g, i));

    // Quanto de nitidez cabe neste pixel sem estourar (áreas de alto contraste recebem menos)
    float3 amp = saturate(min(mn, 2.0 - mx) / max(mx, 0.0001));
    amp = sqrt(amp);

    // Filtro em cruz: 0 w 0 / w 1 w / 0 w 0
    float peak = -1.0 / lerp(8.0, 5.0, Sharpening);
    float3 w = amp * peak;
    float3 rcpW = 1.0 / (1.0 + 4.0 * w);
    return saturate(((b + d + f + h) * w + e) * rcpW);
}

technique RodaLiso_CAS
{
    pass
    {
        VertexShader = RL_VS;
        PixelShader = RL_PS;
    }
}
"""

# Intensidade (0 a 1) de cada nível mostrado na aba do agente. São valores de partida.
NIVEIS_NITIDEZ = {
    "Baixa (Suave)": 0.30,
    "Média (Padrão)": 0.50,
    "Alta (Nítida)": 0.70,
    "Máxima (Agressiva)": 0.90,
}

DLLS_RESHADE = ("dxgi.dll", "d3d9.dll", "d3d10.dll", "d3d11.dll", "d3d12.dll", "opengl32.dll")

# Instalação automática: de onde baixar e qual DLL usar em cada API gráfica.
URL_SITE_RESHADE = "https://reshade.me"
URL_INSTALADOR_PADRAO = "https://reshade.me/downloads/ReShade_Setup_6.8.0.exe"  # usado se o site mudar de layout
DLL_POR_API = {"dxgi": "dxgi.dll", "d3d9": "d3d9.dll", "opengl": "opengl32.dll"}

JOGOS = {
    "The Witcher 3 2015": {"exe": "witcher3.exe", "appids": [292030, 499450], "api": "dxgi"},
    "Cyberpunk 2077": {"exe": "cyberpunk2077.exe", "appids": [1091500], "api": "dxgi"},
    "Red Dead Redemption 2": {"exe": "rdr2.exe", "appids": [1174180], "api": "vulkan"},
    "GTA V": {"exe": "gta5.exe", "appids": [271590], "api": "dxgi",
              "aviso": "Use apenas no modo história: no GTA Online o ReShade pode causar problemas."},
    "CS 2": {"exe": "cs2.exe", "appids": [730], "api": "vulkan",
             "bloqueado": "O CS 2 é online com VAC: filtros injetados podem causar banimento. Bloqueado por segurança."},
}


# ----------------------------------------------------------------------------------------
# Estado salvo (pastas escolhidas e o que foi alterado, para poder desfazer)
# ----------------------------------------------------------------------------------------
def _ler_estado() -> dict:
    try:
        with open(ARQUIVO_ESTADO, "r", encoding="utf-8") as f:
            estado = json.load(f)
    except (OSError, ValueError):
        estado = {}
    estado.setdefault("pastas", {})
    estado.setdefault("ativos", {})
    return estado


def _gravar_estado(estado: dict):
    with open(ARQUIVO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def salvar_pasta_manual(jogo: str, pasta: str):
    """Guarda a pasta do executável escolhida pelo usuário (quando a detecção automática falha)."""
    estado = _ler_estado()
    estado["pastas"][jogo] = os.path.normpath(pasta)
    _gravar_estado(estado)


# ----------------------------------------------------------------------------------------
# Onde está o executável do jogo?
# ----------------------------------------------------------------------------------------
def _bibliotecas_steam():
    raizes = []
    if winreg:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
                raizes.append(winreg.QueryValueEx(k, "SteamPath")[0])
        except OSError:
            pass
    for var in ("PROGRAMFILES(X86)", "PROGRAMFILES"):
        base = os.environ.get(var)
        if base:
            raizes.append(os.path.join(base, "Steam"))

    bibliotecas, vistos = [], set()

    def adicionar(p):
        p = os.path.normpath(p)
        if os.path.isdir(os.path.join(p, "steamapps")) and os.path.normcase(p) not in vistos:
            vistos.add(os.path.normcase(p))
            bibliotecas.append(p)

    for r in raizes:
        adicionar(r)
        try:
            with open(os.path.join(r, "steamapps", "libraryfolders.vdf"), encoding="utf-8", errors="replace") as f:
                for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                    adicionar(m.group(1).replace("\\\\", "\\"))
        except OSError:
            pass
    return bibliotecas


def _pasta_instalacao_steam(appids):
    for lib in _bibliotecas_steam():
        for appid in appids:
            acf = os.path.join(lib, "steamapps", f"appmanifest_{appid}.acf")
            try:
                with open(acf, encoding="utf-8", errors="replace") as f:
                    m = re.search(r'"installdir"\s+"([^"]+)"', f.read())
            except OSError:
                continue
            if m:
                pasta = os.path.join(lib, "steamapps", "common", m.group(1))
                if os.path.isdir(pasta):
                    return pasta
    return None


def _achar_pasta_do_exe(pasta_instalacao, exe_nome, profundidade=4):
    """Pasta (dentro da instalação) que contém o executável. Prefere a versão DX11 à DX12."""
    achadas = []
    base = pasta_instalacao.rstrip("\\/").count(os.sep)
    for raiz, dirs, arquivos in os.walk(pasta_instalacao):
        if raiz.count(os.sep) - base >= profundidade:
            dirs[:] = []
        if any(a.lower() == exe_nome for a in arquivos):
            achadas.append(raiz)
    achadas.sort(key=lambda p: ("dx12" in p.lower(), len(p)))
    return achadas[0] if achadas else None


def _processo_do_jogo(exe_nome):
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if (proc.info["name"] or "").lower() == exe_nome and proc.info.get("exe"):
                return proc.info["exe"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


def jogo_aberto(jogo: str) -> bool:
    info = JOGOS.get(jogo)
    return bool(info and _processo_do_jogo(info["exe"]))


def localizar_pasta_exe(jogo: str):
    """Pasta do executável: 1) jogo aberto agora, 2) pasta escolhida antes, 3) biblioteca da Steam."""
    info = JOGOS.get(jogo)
    if not info:
        return None
    caminho_exe = _processo_do_jogo(info["exe"])
    if caminho_exe:
        return os.path.dirname(caminho_exe)
    salva = _ler_estado()["pastas"].get(jogo)
    if salva and os.path.isdir(salva):
        return salva
    instalacao = _pasta_instalacao_steam(info["appids"])
    return _achar_pasta_do_exe(instalacao, info["exe"]) if instalacao else None


# ----------------------------------------------------------------------------------------
# ReShade: conferir instalação e editar o ReShade.ini
# ----------------------------------------------------------------------------------------
def _ler_texto(caminho):
    with open(caminho, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read()


def _gravar_texto(caminho, texto):
    temporario = caminho + ".rodaliso.tmp"
    with open(temporario, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(texto)
    os.replace(temporario, caminho)


def _dll_e_reshade(caminho: str) -> bool:
    """True se a DLL é do ReShade (e não de outro programa que usa o mesmo nome, como o DXVK)."""
    if os.path.normcase(os.path.abspath(caminho)) in _ler_estado().get("dlls_instaladas", []):
        return True  # foi o próprio Rodaliso que instalou
    try:
        with open(caminho, "rb") as f:
            while True:
                bloco = f.read(4 * 1024 * 1024)
                if not bloco:
                    return False
                if b"ReShade" in bloco or "ReShade".encode("utf-16-le") in bloco:
                    return True
    except OSError:
        return False


def _caminho_efeito(pasta, texto_ini: str):
    """Caminho completo do CAS.fx (ou None se não existir nas pastas de shaders)."""
    candidatos = [os.path.join(pasta, "reshade-shaders", "Shaders")]
    m = re.search(r"(?im)^\s*EffectSearchPaths\s*=\s*(.+)$", texto_ini or "")
    if m:
        for parte in m.group(1).split(","):
            parte = parte.strip().replace("**", "").replace("\\", os.sep).rstrip("\\/")
            if parte:
                candidatos.append(parte if os.path.isabs(parte) else os.path.join(pasta, parte))
    for base in candidatos:
        for raiz, _, arquivos in os.walk(base):
            for a in arquivos:
                if a.lower() == EFEITO_ARQUIVO.lower():
                    return os.path.join(raiz, a)
    return None


def _nomes_parametros(caminho_efeito):
    """Lê o CAS.fx e devolve (nome_do_parametro_de_nitidez, nome_do_parametro_de_contraste).
    Assim o preset acerta mesmo que a versão do shader use nomes um pouco diferentes."""
    nitidez, contraste = PARAM_NITIDEZ, PARAM_CONTRASTE
    try:
        codigo = _ler_texto(caminho_efeito)
    except OSError:
        return nitidez, contraste
    nomes = re.findall(r"uniform\s+float\s+(\w+)", codigo)
    if nomes and nitidez not in nomes:
        nitidez = next((n for n in nomes if "sharp" in n.lower()), nitidez)
    if nomes and contraste not in nomes:
        contraste = next((n for n in nomes if "contrast" in n.lower()), None)
    return nitidez, contraste


def _pasta_shaders_do_jogo(pasta: str, texto_ini: str) -> str:
    """Pasta onde o ReShade procura efeitos: a 1ª de EffectSearchPaths do ReShade.ini, ou o padrão."""
    m = re.search(r"(?im)^\s*EffectSearchPaths\s*=\s*(.+)$", texto_ini or "")
    if m:
        primeira = m.group(1).split(",")[0].strip().replace("**", "").replace("\\", os.sep).rstrip("\\/")
        if primeira:
            return primeira if os.path.isabs(primeira) else os.path.normpath(os.path.join(pasta, primeira))
    return os.path.join(pasta, "reshade-shaders", "Shaders")


def instalar_efeito_local(pasta: str):
    """Grava o efeito RodaLiso_CAS.fx na pasta do programa (shaders/) e copia para a pasta de shaders do jogo.
    Não usa internet. Retorna o caminho do efeito dentro do jogo."""
    os.makedirs(PASTA_SHADERS_LOCAL, exist_ok=True)
    local = os.path.join(PASTA_SHADERS_LOCAL, EFEITO_ARQUIVO)
    if not os.path.isfile(local):  # se o usuário editar a cópia local, ela é respeitada
        with open(local, "w", encoding="utf-8", newline="\n") as f:
            f.write(SHADER_CAS)
    ini = os.path.join(pasta, "ReShade.ini")
    destino_dir = _pasta_shaders_do_jogo(pasta, _ler_texto(ini) if os.path.isfile(ini) else "")
    os.makedirs(destino_dir, exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(destino_dir), "Textures"), exist_ok=True)
    destino = os.path.join(destino_dir, EFEITO_ARQUIVO)
    shutil.copyfile(local, destino)
    return destino


def diagnosticar_reshade(pasta: str) -> dict:
    ini = os.path.join(pasta, "ReShade.ini")
    dlls = [d for d in DLLS_RESHADE
            if os.path.isfile(os.path.join(pasta, d)) and _dll_e_reshade(os.path.join(pasta, d))]
    texto = _ler_texto(ini) if os.path.isfile(ini) else ""
    caminho = _caminho_efeito(pasta, texto)
    # O ReShade.ini pode ainda não existir (ele é criado na 1ª vez que o jogo abre): o que vale é a DLL.
    return {"ini": ini, "dlls": dlls, "instalado": bool(dlls),
            "efeito_ok": caminho is not None, "efeito_caminho": caminho}


def _trocar_preset_path(texto: str, novo: str):
    """Troca o PresetPath da seção [GENERAL]. Retorna (novo_texto, valor_anterior ou None)."""
    eol = "\r\n" if "\r\n" in texto else "\n"
    linhas = texto.split(eol)
    secao, idx_general, original = None, None, None
    for i, linha in enumerate(linhas):
        s = linha.strip().lstrip("﻿")
        if s.startswith("[") and s.endswith("]"):
            secao = s[1:-1].upper()
            if secao == "GENERAL" and idx_general is None:
                idx_general = i
        elif secao == "GENERAL" and "=" in s and s.split("=", 1)[0].strip().lower() == "presetpath":
            original = s.split("=", 1)[1].strip()
            linhas[i] = f"PresetPath={novo}"
            return eol.join(linhas), original
    if idx_general is not None:
        linhas.insert(idx_general + 1, f"PresetPath={novo}")
    else:
        if linhas and linhas[-1] == "":
            linhas.pop()
        linhas += ["[GENERAL]", f"PresetPath={novo}", ""]
    return eol.join(linhas), None


def _conteudo_preset(intensidade: float, param_nitidez=PARAM_NITIDEZ, param_contraste=PARAM_CONTRASTE) -> str:
    tecnica = f"{TECNICA}@{EFEITO_ARQUIVO}"
    linhas = [f"PreprocessorDefinitions=", f"Techniques={tecnica}", f"TechniqueSorting={tecnica}",
              f"[{EFEITO_ARQUIVO}]"]
    if param_contraste:
        linhas.append(f"{param_contraste}=0.000000")
    linhas.append(f"{param_nitidez}={intensidade:.6f}")
    return "\n".join(linhas) + "\n"


def _ini_base() -> str:
    """ReShade.ini mínimo (usado quando o ReShade foi instalado mas o jogo ainda não gerou o arquivo)."""
    return ("[GENERAL]\n"
            "EffectSearchPaths=.\\reshade-shaders\\Shaders\\**\n"
            "TextureSearchPaths=.\\reshade-shaders\\Textures\\**\n"
            "PresetPath=.\\ReShadePreset.ini\n"
            "[OVERLAY]\n"
            "TutorialProgress=4\n")


# ----------------------------------------------------------------------------------------
# Instalação automática do ReShade
# ----------------------------------------------------------------------------------------
def _baixar(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "RodaLiso/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _exe_e_64bits(caminho_exe: str) -> bool:
    """Lê o cabeçalho PE do executável. Na dúvida, assume 64 bits (jogos modernos)."""
    try:
        with open(caminho_exe, "rb") as f:
            f.seek(0x3C)
            pe = struct.unpack("<I", f.read(4))[0]
            f.seek(pe + 4)
            maquina = struct.unpack("<H", f.read(2))[0]
        return maquina != 0x014C  # 0x014C = x86 (32 bits)
    except (OSError, struct.error):
        return True


def reshade_precisa_instalar(jogo: str, pasta_exe=None) -> bool:
    """True se dá para instalar o ReShade automaticamente neste jogo e ele ainda não está pronto."""
    info = JOGOS.get(jogo)
    if not info or info.get("bloqueado") or info.get("api") not in DLL_POR_API:
        return False
    pasta = pasta_exe or localizar_pasta_exe(jogo)
    if not pasta or not os.path.isdir(pasta):
        return False
    return not diagnosticar_reshade(pasta)["instalado"]


def instalar_reshade(jogo: str, pasta_exe=None, progresso=None):
    """Baixa e instala o ReShade + shaders (incluindo o CAS) na pasta do jogo. Retorna (sucesso, mensagem).

    `progresso` é uma função opcional que recebe textos curtos ("Baixando...") para mostrar na interface.
    """
    def avisar(texto):
        print(f"[NITIDEZ] {texto}")
        if progresso:
            progresso(texto)

    info = JOGOS.get(jogo)
    if not info:
        return False, f"Jogo '{jogo}' não suportado."
    if info.get("bloqueado"):
        return False, info["bloqueado"]
    api = info.get("api")
    if api not in DLL_POR_API:
        return False, (f"A instalação automática não cobre {jogo} (usa {api}). Instale o ReShade manualmente "
                       "em reshade.me escolhendo a API Vulkan e marcando o efeito CAS.fx.")

    pasta = pasta_exe or localizar_pasta_exe(jogo)
    if not pasta or not os.path.isdir(pasta):
        return False, f"Não encontrei a pasta do executável de {jogo}. Escolha a pasta manualmente."

    nome_dll = DLL_POR_API[api]
    destino_dll = os.path.join(pasta, nome_dll)
    if os.path.isfile(destino_dll) and not _dll_e_reshade(destino_dll):
        return False, (f"Já existe um {nome_dll} de outro programa (ex.: DXVK) em {pasta}. Para não quebrar o "
                       "jogo, o Rodaliso não sobrescreve. Remova/renomeie esse arquivo ou instale o ReShade manualmente.")

    try:
        # 1) Instalador oficial -> tira a DLL de dentro dele (o .exe do instalador é também um .zip)
        avisar("Procurando a versão mais recente do ReShade...")
        url = URL_INSTALADOR_PADRAO
        try:
            html = _baixar(URL_SITE_RESHADE, timeout=30).decode("utf-8", errors="replace")
            m = re.search(r"downloads/(ReShade_Setup_[\d.]+\.exe)", html)
            if m:
                url = f"{URL_SITE_RESHADE}/downloads/{m.group(1)}"
        except Exception:
            pass  # usa o link padrão

        dll_bytes = None
        if os.path.isfile(destino_dll) and _dll_e_reshade(destino_dll):
            avisar("ReShade já está na pasta; só faltam os shaders.")
        else:
            avisar("Baixando o ReShade (instalador oficial)...")
            dados_instalador = _baixar(url)
            bits = "64" if _exe_e_64bits(os.path.join(pasta, info["exe"])) else "32"
            with zipfile.ZipFile(io.BytesIO(dados_instalador)) as zf:
                membro = next((n for n in zf.namelist() if os.path.basename(n).lower() == f"reshade{bits}.dll"), None)
                if not membro:
                    return False, f"Não achei ReShade{bits}.dll dentro do instalador baixado ({url})."
                dll_bytes = zf.read(membro)

        # 2) Grava a DLL e o ReShade.ini (só se ainda não existir)
        avisar("Instalando na pasta do jogo...")
        if dll_bytes is not None:
            with open(destino_dll, "wb") as f:
                f.write(dll_bytes)
        ini = os.path.join(pasta, "ReShade.ini")
        if not os.path.isfile(ini):
            with open(ini, "w", encoding="utf-8", newline="") as f:
                f.write(_ini_base())

        # 3) Efeito de nitidez: vem embutido no programa (nada para baixar)
        avisar("Copiando o efeito de nitidez...")
        instalar_efeito_local(pasta)
    except PermissionError:
        return False, (f"Sem permissão para gravar em {pasta}. Feche o jogo e rode o Roda Liso como "
                       "Administrador (ou mova o jogo para uma pasta fora de Arquivos de Programas).")
    except OSError as e:
        return False, f"Falha na instalação do ReShade (internet ou arquivo em uso?): {e}"
    except zipfile.BadZipFile:
        return False, "O arquivo baixado não é válido (download incompleto?). Tente de novo."

    if not _caminho_efeito(pasta, _ler_texto(ini) if os.path.isfile(ini) else ""):
        return False, f"ReShade instalado, mas não consegui gravar o efeito {EFEITO_ARQUIVO} na pasta de shaders."

    estado = _ler_estado()
    estado["pastas"][jogo] = pasta
    marca = os.path.normcase(os.path.abspath(destino_dll))
    estado.setdefault("dlls_instaladas", [])
    if marca not in estado["dlls_instaladas"]:
        estado["dlls_instaladas"].append(marca)
    _gravar_estado(estado)
    return True, f"ReShade instalado em {pasta} ({nome_dll} + efeito {EFEITO_ARQUIVO})."


# ----------------------------------------------------------------------------------------
# API usada pela interface e pelo agente
# ----------------------------------------------------------------------------------------
def aplicar_nitidez(jogo: str, nivel: str = "Média (Padrão)", pasta_exe=None):
    """Liga o filtro de nitidez no `nivel` escolhido. Retorna (sucesso, mensagem)."""
    info = JOGOS.get(jogo)
    if not info:
        return False, f"Filtro de nitidez ainda não disponível para '{jogo}'."
    if info.get("bloqueado"):
        return False, info["bloqueado"]
    if nivel not in NIVEIS_NITIDEZ:
        return False, f"Nível de nitidez desconhecido: '{nivel}'."

    pasta = pasta_exe or localizar_pasta_exe(jogo)
    if not pasta or not os.path.isdir(pasta):
        return False, f"Não encontrei a pasta do executável de {jogo}. Escolha a pasta manualmente."

    diag = diagnosticar_reshade(pasta)
    if not diag["instalado"]:
        return False, (f"O ReShade não está instalado em {pasta}. Clique em APLICAR NITIDEZ na tela do Roda Liso "
                       f"para instalar automaticamente, ou instale à mão (reshade.me): selecione {info['exe']} "
                       "e escolha a API do jogo (o efeito de nitidez o Roda Liso copia sozinho).")
    if not diag["efeito_ok"]:  # ReShade ok, mas sem o nosso efeito: copia o que vem embutido no programa
        try:
            diag["efeito_caminho"] = instalar_efeito_local(pasta)
        except OSError as e:
            return False, f"Não consegui copiar o efeito {EFEITO_ARQUIVO} para a pasta do jogo: {e}"

    intensidade = NIVEIS_NITIDEZ[nivel]
    param_nitidez, param_contraste = _nomes_parametros(diag["efeito_caminho"])
    try:
        if not os.path.isfile(diag["ini"]):
            _gravar_texto(diag["ini"], _ini_base())
        texto_ini = _ler_texto(diag["ini"])
        backup = diag["ini"] + ".rodaliso.bak"
        if not os.path.exists(backup):
            shutil.copy2(diag["ini"], backup)

        novo_texto, preset_original = _trocar_preset_path(texto_ini, ".\\" + NOME_PRESET)
        estado = _ler_estado()
        ativo = estado["ativos"].get(jogo)
        if ativo and preset_original and preset_original.endswith(NOME_PRESET):
            preset_original = ativo.get("preset_original")  # já era nosso: mantém o original de verdade

        with open(os.path.join(pasta, NOME_PRESET), "w", encoding="utf-8") as f:
            f.write(_conteudo_preset(intensidade, param_nitidez, param_contraste))
        _gravar_texto(diag["ini"], novo_texto)

        estado["ativos"][jogo] = {"pasta": pasta, "preset_original": preset_original, "nivel": nivel}
        estado["pastas"][jogo] = pasta
        _gravar_estado(estado)
    except OSError as e:
        return False, f"Erro ao configurar o ReShade: {e}"

    msg = f"Filtro de nitidez '{nivel}' (intensidade {intensidade:.2f}) configurado em {pasta}."
    if _processo_do_jogo(info["exe"]):
        msg += " O jogo está aberto: feche e abra de novo para valer (o ReShade pode regravar o ReShade.ini ao sair)."
    else:
        msg += " Vale na próxima vez que o jogo abrir."
    if info.get("aviso"):
        msg += " " + info["aviso"]
    return True, msg


def remover_nitidez(jogo: str):
    """Desliga o filtro: o ReShade volta ao preset que estava antes. Retorna (sucesso, mensagem)."""
    estado = _ler_estado()
    ativo = estado["ativos"].get(jogo)
    if not ativo:
        return False, "O Rodaliso não aplicou nenhum filtro de nitidez neste jogo."
    pasta = ativo["pasta"]
    ini = os.path.join(pasta, "ReShade.ini")
    try:
        if os.path.isfile(ini):
            texto = _ler_texto(ini)
            novo, _ = _trocar_preset_path(texto, ativo.get("preset_original") or ".\\ReShadePreset.ini")
            _gravar_texto(ini, novo)
        preset = os.path.join(pasta, NOME_PRESET)
        if os.path.isfile(preset):
            os.remove(preset)
    except OSError as e:
        return False, f"Erro ao remover o filtro: {e}"
    del estado["ativos"][jogo]
    _gravar_estado(estado)
    return True, "Filtro de nitidez removido; o ReShade voltou ao preset anterior."


def status_nitidez(jogo: str) -> str:
    ativo = _ler_estado()["ativos"].get(jogo)
    return f"Ativo: {ativo['nivel']}" if ativo else "Desligado"
