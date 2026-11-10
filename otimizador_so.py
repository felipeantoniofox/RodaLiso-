"""Roda Liso - Otimizador de SO (debloat reversível, embutido na aba do roda_liso.py).

As 11 opções reproduzem os tweaks do WinUtil (Chris Titus) que foram testados no notebook:
  Essenciais : ConsumerFeatures, Delivery Optimization, Location Tracking, Sugestões da Store na
               pesquisa, Serviços em manual, Telemetria, Widgets (remover)
  Preferências: Bing no Menu Iniciar
  Avançado    : Edge (debloat), OneDrive (remover), Windows AI (desativar e remover)

Como a reversão funciona:
  1. Antes de aplicar, o estado atual é salvo em rodaliso_so_backup.json (snapshot).
  2. Depois de aplicar, o resultado é conferido de verdade (lê o Registro/serviço de volta).
  3. "Reverter" restaura o snapshot. Se o item já estava aplicado ANTES do Roda Liso (ex.: você usou o
     WinUtil), não existe snapshot: nesse caso restaura o PADRÃO DO WINDOWS.
  4. Itens que REMOVEM apps (Widgets, OneDrive, IA) só voltam reinstalando o app: o Roda Liso tenta
     (winget) ou abre a página da Microsoft Store. Isso depende de internet e não é instantâneo.
"""
import ctypes
import fnmatch
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

try:
    import winreg
except ImportError:  # permite importar fora do Windows (testes)
    winreg = None

try:
    import psutil
except ImportError:
    psutil = None

import tema

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQ_BACKUP = os.path.join(BASE_DIR, "rodaliso_so_backup.json")
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def rodando_como_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ======================================================================================
# Registro, serviços e PowerShell
# ======================================================================================
def _hive(nome):
    return {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}[nome]


def _acesso(base):
    return base | getattr(winreg, "KEY_WOW64_64KEY", 0)


def ler_reg(hive, sub, nome):
    try:
        with winreg.OpenKey(_hive(hive), sub, 0, _acesso(winreg.KEY_READ)) as k:
            valor, regtype = winreg.QueryValueEx(k, nome)
            return {"existia": True, "valor": valor, "regtype": regtype}
    except OSError:
        return {"existia": False}


def escrever_reg(hive, sub, nome, valor, regtype):
    with winreg.CreateKeyEx(_hive(hive), sub, 0, _acesso(winreg.KEY_WRITE)) as k:
        winreg.SetValueEx(k, nome, 0, regtype, valor)


def apagar_reg(hive, sub, nome):
    try:
        with winreg.OpenKey(_hive(hive), sub, 0, _acesso(winreg.KEY_WRITE)) as k:
            winreg.DeleteValue(k, nome)
    except FileNotFoundError:
        pass


def _regtype(txt):
    return winreg.REG_SZ if txt == "sz" else winreg.REG_DWORD


def _sub_svc(nome):
    return rf"SYSTEM\CurrentControlSet\Services\{nome}"


def _estado_svc(nome):
    r = ler_reg("HKLM", _sub_svc(nome), "Start")
    if not r["existia"]:
        return {"existe": False}
    atraso = ler_reg("HKLM", _sub_svc(nome), "DelayedAutostart")
    return {"existe": True, "start": r["valor"], "atrasado": bool(atraso["existia"] and atraso["valor"])}


def _sc_config(nome, start, atrasado=False):
    modo = {2: "delayed-auto" if atrasado else "auto", 3: "demand", 4: "disabled"}[start]
    r = subprocess.run(["sc", "config", nome, "start=", modo], capture_output=True, text=True,
                       creationflags=_NO_WINDOW, timeout=30)
    if r.returncode != 0:
        raise RuntimeError(f"não consegui configurar o serviço {nome} (sc retornou {r.returncode})")


def ps(script, timeout=180):
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, text=True, errors="replace", creationflags=_NO_WINDOW, timeout=timeout)
    return r.returncode, r.stdout or "", r.stderr or ""


_PACOTES = None  # nomes (minúsculos) dos pacotes Appx instalados; None = ainda não carregado


def carregar_pacotes():
    global _PACOTES
    try:
        rc, out, _ = ps("Get-AppxPackage -AllUsers | ForEach-Object { $_.Name }", timeout=120)
        if rc == 0:
            _PACOTES = {l.strip().lower() for l in out.splitlines() if l.strip()}
    except Exception:
        pass
    return _PACOTES


def _pacote_presente(padrao):
    return any(fnmatch.fnmatch(n, padrao.lower()) for n in (_PACOTES or ()))


# --- arquivo store.db (sugestões da Store) ---
def _caminho_store_db():
    return os.path.expandvars(r"%LOCALAPPDATA%\Packages\Microsoft.WindowsStore_8wekyb3d8bbwe\LocalState\store.db")


def _tem_deny(caminho):
    r = subprocess.run(["icacls", caminho], capture_output=True, text=True, errors="replace",
                       creationflags=_NO_WINDOW, timeout=15)
    return "(DENY)" in (r.stdout or "").upper()


def _icacls(caminho, *args):
    r = subprocess.run(["icacls", caminho, *args], capture_output=True, text=True, errors="replace",
                       creationflags=_NO_WINDOW, timeout=15)
    if r.returncode != 0:
        raise RuntimeError("icacls falhou: " + (r.stderr or r.stdout).strip()[:120])


# --- OneDrive ---
def _exes_onedrive():
    return [os.path.expandvars(p) for p in (
        r"%LOCALAPPDATA%\Microsoft\OneDrive\OneDrive.exe",
        r"%ProgramFiles%\Microsoft OneDrive\OneDrive.exe",
        r"%ProgramFiles(x86)%\Microsoft OneDrive\OneDrive.exe")]


def _onedrive_instalado():
    return any(os.path.exists(p) for p in _exes_onedrive())


def onedrive_protege_pastas():
    """True se Desktop/Documentos/Imagens do Windows apontam para dentro do OneDrive."""
    for nome in ("Desktop", "Personal", "My Pictures"):
        r = ler_reg("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders", nome)
        if r["existia"] and "onedrive" in str(r["valor"]).lower():
            return True
    return False


def _remover_onedrive():
    setup = next((p for p in (os.path.expandvars(r"%SystemRoot%\System32\OneDriveSetup.exe"),
                              os.path.expandvars(r"%SystemRoot%\SysWOW64\OneDriveSetup.exe")) if os.path.exists(p)), None)
    if not setup:
        raise RuntimeError("OneDriveSetup.exe não encontrado no Windows")
    subprocess.run(["taskkill", "/f", "/im", "OneDrive.exe"], capture_output=True, creationflags=_NO_WINDOW)
    subprocess.run([setup, "/uninstall"], capture_output=True, creationflags=_NO_WINDOW, timeout=300)
    for _ in range(30):  # o desinstalador pode terminar depois de devolver o controle
        if not _onedrive_instalado():
            return
        time.sleep(1)
    raise RuntimeError("o OneDrive continuou instalado após o desinstalador")


def _reinstalar_onedrive():
    r = subprocess.run(["winget", "install", "-e", "--id", "Microsoft.OneDrive", "--source", "winget",
                        "--accept-package-agreements", "--accept-source-agreements"],
                       capture_output=True, text=True, errors="replace", creationflags=_NO_WINDOW, timeout=900)
    if r.returncode != 0 and not _onedrive_instalado():
        raise RuntimeError(f"o winget não conseguiu reinstalar o OneDrive (código {r.returncode}); "
                           "baixe em microsoft.com/onedrive")


def _abrir(uri):
    try:
        os.startfile(uri)
    except Exception:
        pass


# ======================================================================================
# Definição das ações e das opções
# ======================================================================================
def REG(hive, sub, nome, valor, padrao=None, tipo="dword"):
    """valor=None -> o tweak REMOVE o valor. padrao=None -> o padrão do Windows é não existir."""
    return {"tipo": "reg", "hive": hive, "sub": sub, "nome": nome, "valor": valor, "padrao": padrao, "regtype": tipo}


def SVC(nome, start, padrao=3, atrasado=False):  # 2 automático | 3 manual | 4 desativado
    return {"tipo": "svc", "nome": nome, "start": start, "padrao": padrao, "atrasado": atrasado}


LOJA_DB = {"tipo": "loja_db"}
ONEDRIVE = {"tipo": "onedrive"}


def APPX(pacotes, aplicar, desfazer, loja):
    return {"tipo": "appx", "pacotes": pacotes, "aplicar": aplicar, "desfazer": desfazer, "loja": loja}


_PS_WIDGETS = """$ErrorActionPreference='SilentlyContinue'
Get-Process -Name Widgets,WidgetService | Stop-Process -Force
Get-AppxPackage Microsoft.WidgetsPlatformRuntime -AllUsers | Remove-AppxPackage -AllUsers
Get-AppxPackage MicrosoftWindows.Client.WebExperience -AllUsers | Remove-AppxPackage -AllUsers"""

_PS_IA = """$ErrorActionPreference='SilentlyContinue'
$Appx = (Get-AppxPackage MicrosoftWindows.Client.CoreAI).PackageFullName
$Sid = (Get-LocalUser $Env:UserName).Sid.Value
if ($Appx -and $Sid) { New-Item "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Appx\\AppxAllUserStore\\EndOfLife\\$Sid\\$Appx" -Force | Out-Null }
Get-AppxPackage -AllUsers "*Copilot*" | Remove-AppxPackage -AllUsers
winget uninstall -e --name "Copilot" --silent --force --accept-source-agreements 2>$null | Out-Null
Get-AppxPackage -AllUsers Microsoft.MicrosoftOfficeHub | Remove-AppxPackage -AllUsers
if ($Appx) { Remove-AppxPackage $Appx }
Disable-WindowsOptionalFeature -FeatureName Recall -Online -NoRestart | Out-Null"""

_PS_IA_UNDO = """$ErrorActionPreference='SilentlyContinue'
$Sid = (Get-LocalUser $Env:UserName).Sid.Value
Get-ChildItem "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Appx\\AppxAllUserStore\\EndOfLife\\$Sid" | Where-Object { $_.PSChildName -like 'MicrosoftWindows.Client.CoreAI*' } | Remove-Item -Recurse -Force
Enable-WindowsOptionalFeature -FeatureName Recall -Online -NoRestart | Out-Null"""

_CDM_POL = r"SOFTWARE\Policies\Microsoft\Windows"
_EDGE = r"SOFTWARE\Policies\Microsoft\Edge"
_TELE = [
    ("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", 0),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", 0),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo", "Enabled", 0),
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Privacy", "TailoredExperiencesWithDiagnosticDataEnabled", 0),
    ("HKCU", r"Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy", "HasAccepted", 0),
    ("HKCU", r"Software\Microsoft\Input\TIPC", "Enabled", 0),
    ("HKCU", r"Software\Microsoft\InputPersonalization", "RestrictImplicitInkCollection", 1),
    ("HKCU", r"Software\Microsoft\InputPersonalization", "RestrictImplicitTextCollection", 1),
    ("HKCU", r"Software\Microsoft\InputPersonalization\TrainedDataStore", "HarvestContacts", 0),
    ("HKCU", r"Software\Microsoft\Personalization\Settings", "AcceptedPrivacyPolicy", 0),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\DataCollection", "DoNotShowFeedbackNotifications", 1),
    ("HKCU", r"Software\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", 0),
    ("HKCU", r"Software\Microsoft\Siuf\Rules", "PeriodInNanoSeconds", None),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableTailoredExperiencesWithDiagnosticData", 1),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "DisabledByGroupPolicy", 1),
    ("HKLM", r"SOFTWARE\Policies\Microsoft\Windows\Windows Error Reporting", "Disabled", 1),
    ("HKLM", r"SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", 1),
]
_EDGE_VALORES = [
    ("Edge", "PersonalizationReportingEnabled", 0), ("Edge", "ShowRecommendationsEnabled", 0),
    ("Edge", "HideFirstRunExperience", 1), ("Edge", "UserFeedbackAllowed", 0),
    ("Edge", "ConfigureDoNotTrack", 1), ("Edge", "AlternateErrorPagesEnabled", 0),
    ("Edge", "EdgeCollectionsEnabled", 0), ("Edge", "EdgeShoppingAssistantEnabled", 0),
    ("Edge", "MicrosoftEdgeInsiderPromotionEnabled", 0), ("Edge", "ShowMicrosoftRewards", 0),
    ("Edge", "WebWidgetAllowed", 0), ("Edge", "DiagnosticData", 0),
    ("Edge", "EdgeAssetDeliveryServiceEnabled", 0), ("Edge", "WalletDonationEnabled", 0),
    ("Edge", "DefaultBrowserSettingsCampaignEnabled", 0), ("EdgeUpdate", "CreateDesktopShortcutDefault", 0),
]

# ram = (mín, máx) em MB: ESTIMATIVA baseada em valores típicos, não medida. Varia de PC para PC.
OPCOES = {
    "consumer": {
        "nome": "ConsumerFeatures - desativar", "grupo": "ESSENCIAIS", "risco": "baixo", "ram": (0, 30),
        "desc": "Impede o Windows de instalar sozinho apps promovidos e de mostrar sugestões de apps da Microsoft Store.",
        "pos": "Evita apps e jogos promocionais instalados sem você pedir e reduz tarefas de conteúdo em segundo plano. Ganho de RAM pequeno: ~0 a 30 MB.",
        "neg": "Você deixa de receber apps 'sugeridos' pelo Windows. Em Windows Home/Pro o efeito dessa política pode ser limitado.",
        "reinicio": "Faça logoff/login para valer por completo.",
        "acoes": [REG("HKLM", _CDM_POL + r"\CloudContent", "DisableWindowsConsumerFeatures", 1)],
    },
    "delivery": {
        "nome": "Delivery Optimization - desativar", "grupo": "ESSENCIAIS", "risco": "baixo", "ram": (20, 50),
        "desc": "Impede o Windows de usar a sua internet para enviar atualizações a outros computadores (P2P).",
        "pos": "Libera cerca de 20 a 50 MB de RAM e poupa upload, rede e CPU em segundo plano enquanto você joga.",
        "neg": "As atualizações passam a vir só dos servidores da Microsoft; sem prejuízo prático na maioria das casas.",
        "reinicio": "",
        "acoes": [REG("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\DeliveryOptimization\Config", "DODownloadMode", 0, padrao=1)],
    },
    "location": {
        "nome": "Rastreamento de localização - desativar", "grupo": "ESSENCIAIS", "risco": "baixo", "ram": (10, 30),
        "desc": "Desliga o serviço de localização do Windows e nega o acesso de localização aos apps.",
        "pos": "Libera cerca de 10 a 30 MB de RAM e melhora a privacidade (o PC deixa de registrar onde você está).",
        "neg": "Apps que usam localização (Mapas, Clima, 'Encontrar meu dispositivo', fuso horário automático) podem parar de funcionar direito.",
        "reinicio": "Reinicie o Windows.",
        "acoes": [
            REG("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location", "Value", "Deny", padrao="Allow", tipo="sz"),
            REG("HKLM", r"SYSTEM\CurrentControlSet\Services\lfsvc\Service\Configuration", "Status", 0, padrao=1),
            REG("HKLM", r"SYSTEM\Maps", "AutoUpdateEnabled", 0, padrao=1),
            SVC("lfsvc", 4),
        ],
    },
    "storesearch": {
        "nome": "Sugestões da Microsoft Store na pesquisa - desativar", "grupo": "ESSENCIAIS", "risco": "baixo", "ram": (0, 0),
        "desc": "Bloqueia o arquivo de recomendações da Microsoft Store para a pesquisa não mostrar apps sugeridos.",
        "pos": "Pesquisa do Menu Iniciar mais limpa, sem apps patrocinados. Não libera RAM: o ganho é de limpeza e privacidade.",
        "neg": "Se a Microsoft Store apresentar erro ao abrir, reverta este item. Só funciona depois que a Store já foi aberta uma vez.",
        "reinicio": "",
        "acoes": [LOJA_DB],
    },
    "services": {
        "nome": "Serviços - colocar em manual ou desativar", "grupo": "ESSENCIAIS", "risco": "médio", "ram": (20, 80),
        "desc": "Arquivos Offline (CscService) e Compartilhamento de Conexão (SharedAccess) desativados; Mapas (MapsBroker) e Armazenamento (StorSvc) em manual. (O serviço de telemetria fica no item Telemetria.)",
        "pos": "Menos serviços iniciando com o Windows: boot mais leve e cerca de 20 a 80 MB de RAM livres.",
        "neg": "Desativar o Compartilhamento de Conexão (SharedAccess) impede o Hotspot Móvel do Windows de funcionar. Mapas offline deixam de atualizar sozinhos.",
        "reinicio": "Reinicie o Windows.",
        "acoes": [SVC("CscService", 4), SVC("SharedAccess", 4),
                  SVC("MapsBroker", 3, padrao=2, atrasado=True), SVC("StorSvc", 3, padrao=2)],
    },
    "telemetry": {
        "nome": "Telemetria - desativar", "grupo": "ESSENCIAIS", "risco": "médio", "ram": (30, 100),
        "desc": "Desativa os serviços de telemetria (DiagTrack) e de Relatório de Erros (WerSvc) e vários rastreadores de uso e publicidade personalizada.",
        "pos": "Libera cerca de 30 a 100 MB de RAM e reduz CPU, disco e rede usados em segundo plano.",
        "neg": "Sem o Relatório de Erros, o Windows não envia diagnósticos de travamentos à Microsoft. O nível 0 de telemetria só é plenamente respeitado em Enterprise/Education; o serviço desativado é o que de fato interrompe a coleta.",
        "reinicio": "Reinicie o Windows.",
        "acoes": [REG(h, s, n, v) for h, s, n, v in _TELE] + [SVC("DiagTrack", 4, padrao=2), SVC("WerSvc", 4)],
    },
    "widgets": {
        "nome": "Widgets - remover", "grupo": "ESSENCIAIS", "risco": "médio", "ram": (100, 250),
        "desc": "Remove o painel de Widgets do Windows 11 e os pacotes que o executam.",
        "pos": "Um dos maiores ganhos da lista: cerca de 100 a 250 MB de RAM e menos processos em segundo plano.",
        "neg": "Remove pacotes do sistema. Para voltar é preciso reinstalar pela Microsoft Store ('Windows Web Experience Pack'), com internet.",
        "reinicio": "Faça logoff/login (ou reinicie o Explorer) para o ícone sumir da barra.",
        "acoes": [APPX(["Microsoft.WidgetsPlatformRuntime", "MicrosoftWindows.Client.WebExperience"], _PS_WIDGETS, "",
                       "Windows Web Experience Pack")],
    },
    "bing": {
        "nome": "Pesquisa Bing no Menu Iniciar - desativar", "grupo": "PREFERÊNCIAS", "risco": "baixo", "ram": (20, 80),
        "desc": "Faz a busca do Menu Iniciar procurar apenas no seu PC.",
        "pos": "Busca mais rápida, sem consultas à internet a cada tecla, e cerca de 20 a 80 MB de RAM a menos no processo de pesquisa.",
        "neg": "Você perde resultados da web e cálculos/conversões diretos na busca.",
        "reinicio": "Reinicie o Explorer (ou faça logoff).",
        "acoes": [REG("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Search", "BingSearchEnabled", 0, padrao=1)],
    },
    "edge": {
        "nome": "Microsoft Edge - reduzir (debloat)", "grupo": "AVANÇADO - CUIDADO", "risco": "médio", "ram": (0, 100),
        "desc": "Desliga por política as recomendações, Rewards, assistente de compras, coleções, widget web, diagnósticos e atalho automático do Edge. O Edge continua instalado.",
        "pos": "Menos pop-ups, notificações e telemetria do Edge. Ganho de RAM de baixo a médio: ~0 a 100 MB.",
        "neg": "Você perde recursos opcionais do Edge (Coleções, compras) e o navegador passa a mostrar 'gerenciado pela sua organização' em edge://policy.",
        "reinicio": "Feche e reabra o Edge.",
        "acoes": [REG("HKLM", rf"SOFTWARE\Policies\Microsoft\{pasta}", n, v) for pasta, n, v in _EDGE_VALORES]
                 + [REG("HKLM", _EDGE + r"\ExtensionInstallBlocklist", "1", "ofefcgjbeghpigppfmkologfjadafddi", tipo="sz")],
    },
    "onedrive": {
        "nome": "Microsoft OneDrive - remover", "grupo": "AVANÇADO - CUIDADO", "risco": "ALTO", "ram": (100, 250),
        "desc": "Desinstala o OneDrive e para a sincronização em segundo plano.",
        "pos": "Libera cerca de 100 a 250 MB de RAM e reduz uso de CPU, disco e rede.",
        "neg": "Seus arquivos NÃO são apagados, mas arquivos que existem só na nuvem ('somente online') deixam de ficar acessíveis no PC. Se Desktop/Documentos/Imagens estão no OneDrive, sincronize e baixe tudo antes. Para voltar é preciso reinstalar (winget).",
        "reinicio": "Faça logoff/login.",
        "acoes": [ONEDRIVE],
    },
    "ai": {
        "nome": "Windows AI (Copilot, Recall) - desativar e remover", "grupo": "AVANÇADO - CUIDADO", "risco": "ALTO", "ram": (50, 300),
        "desc": "Desativa recursos de IA do Windows (IA no Bloco de Notas, página de componentes de IA, serviço WSAIFabricSvc, Recall) e remove o Copilot e o app Microsoft 365 (Office).",
        "pos": "Libera cerca de 50 a 300 MB de RAM e elimina processos de IA em segundo plano.",
        "neg": "Remove apps do sistema e marca um componente protegido (CoreAI) para remoção. A reversão é PARCIAL: Registro e serviços voltam, mas os apps precisam ser reinstalados pela Microsoft Store e alguns componentes só voltam com atualização/reparo do Windows.",
        "reinicio": "Reinicie o Windows.",
        "acoes": [
            REG("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer", "SettingsPageVisibility", "hide:aicomponents;appactions;", tipo="sz"),
            REG("HKLM", r"SOFTWARE\Policies\WindowsNotepad", "DisableAIFeatures", 1),
            SVC("WSAIFabricSvc", 4),
            APPX(["Microsoft.Copilot*", "Microsoft.MicrosoftOfficeHub"], _PS_IA, _PS_IA_UNDO, "Copilot"),
        ],
    },
}
GRUPOS = ["ESSENCIAIS", "PREFERÊNCIAS", "AVANÇADO - CUIDADO"]
RECOMENDADOS = [i for i, o in OPCOES.items() if o["grupo"] != "AVANÇADO - CUIDADO"]


# ======================================================================================
# Detecção de estado
# ======================================================================================
def _checar_alvo(a):
    """True = aplicado | False = não aplicado | None = não se aplica/indeterminado."""
    t = a["tipo"]
    if t == "reg":
        if a["valor"] is None:
            return None
        atual = ler_reg(a["hive"], a["sub"], a["nome"])
        return bool(atual["existia"] and atual["valor"] == a["valor"])
    if t == "svc":
        e = _estado_svc(a["nome"])
        return None if not e["existe"] else e["start"] == a["start"]
    if t == "loja_db":
        p = _caminho_store_db()
        return _tem_deny(p) if os.path.exists(p) else None
    if t == "appx":
        return None if _PACOTES is None else not any(_pacote_presente(p) for p in a["pacotes"])
    if t == "onedrive":
        return not _onedrive_instalado()
    return None


def estado_opcao(op):
    """'ativo' | 'parcial' | 'inativo' | 'n/a' (não se aplica a este PC) | 'verificando'."""
    resultados = [_checar_alvo(a) for a in op["acoes"]]
    if any(a["tipo"] == "appx" for a in op["acoes"]) and _PACOTES is None and all(r is None for r in resultados):
        return "verificando"
    validos = [r for r in resultados if r is not None]
    if not validos:
        return "n/a"
    if all(validos):
        return "ativo"
    return "parcial" if any(validos) else "inativo"


# ======================================================================================
# Backup (snapshot)
# ======================================================================================
def carregar_backup():
    try:
        with open(ARQ_BACKUP, "r", encoding="utf-8") as f:
            d = json.load(f)
            d.setdefault("opcoes", {})
            return d
    except (OSError, ValueError):
        return {"versao": 2, "opcoes": {}}


def salvar_backup(d):
    tmp = ARQ_BACKUP + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ARQ_BACKUP)


def _ler_alvo(a):
    t = a["tipo"]
    if t == "reg":
        return {"tipo": "reg", **ler_reg(a["hive"], a["sub"], a["nome"])}
    if t == "svc":
        return {"tipo": "svc", **_estado_svc(a["nome"])}
    if t == "loja_db":
        p = _caminho_store_db()
        return {"tipo": "loja_db", "negado": _tem_deny(p) if os.path.exists(p) else False}
    if t == "appx":
        if _PACOTES is None:
            carregar_pacotes()
        return {"tipo": "appx", "presentes": [p for p in a["pacotes"] if _pacote_presente(p)]}
    return {"tipo": "onedrive", "instalado": _onedrive_instalado()}


# ======================================================================================
# Aplicar
# ======================================================================================
def _aplicar_alvo(a):
    """Devolve lista de avisos (strings)."""
    t = a["tipo"]
    if t == "reg":
        if a["valor"] is None:
            apagar_reg(a["hive"], a["sub"], a["nome"])
        else:
            escrever_reg(a["hive"], a["sub"], a["nome"], a["valor"], _regtype(a["regtype"]))
    elif t == "svc":
        if _estado_svc(a["nome"])["existe"]:
            _sc_config(a["nome"], a["start"])
            if a["start"] == 4:  # para o serviço agora (se falhar, ele só não sobe no próximo boot)
                subprocess.run(["sc", "stop", a["nome"]], capture_output=True, creationflags=_NO_WINDOW, timeout=30)
    elif t == "loja_db":
        p = _caminho_store_db()
        if not os.path.exists(p):
            raise RuntimeError("a Microsoft Store ainda não criou o arquivo store.db (abra a Store uma vez)")
        _icacls(p, "/deny", "*S-1-1-0:F")
    elif t == "appx":
        ps(a["aplicar"], timeout=300)
        carregar_pacotes()
        restantes = [p for p in a["pacotes"] if _pacote_presente(p)]
        if restantes:
            return ["pacotes que continuam instalados (o Windows não permitiu remover): " + ", ".join(restantes)]
    elif t == "onedrive":
        _remover_onedrive()
    return []


def _rotulo(a):
    return a.get("nome") or a["tipo"]


def aplicar_opcao(oid):
    """Devolve (ok, mensagem, avisos)."""
    op = OPCOES[oid]
    if estado_opcao(op) == "ativo":
        return True, "já estava ativo (nada a fazer)", []
    backup = carregar_backup()
    novo = oid not in backup["opcoes"]
    antes = []
    if novo:  # snapshot só na primeira vez (senão guardaria o estado já alterado)
        antes = [_ler_alvo(a) for a in op["acoes"]]
        backup["opcoes"][oid] = {"aplicado_em": time.strftime("%d/%m/%Y %H:%M"), "antes": antes}
        salvar_backup(backup)  # salvo ANTES de mexer: se travar no meio, ainda dá para reverter

    erros, avisos = [], []
    for a in op["acoes"]:
        try:
            avisos += _aplicar_alvo(a)
        except Exception as e:
            erros.append(f"{_rotulo(a)}: {e}")
    for a in op["acoes"]:  # conferência real (remoção de apps é "melhor esforço" e só gera aviso)
        if a["tipo"] != "appx" and _checar_alvo(a) is False:
            erros.append(f"{_rotulo(a)}: não confirmou depois de aplicar")

    if erros:
        if novo:
            for a, s in reversed(list(zip(op["acoes"], antes))):
                if a["tipo"] in ("reg", "svc", "loja_db"):
                    try:
                        _restaurar(a, s)
                    except Exception:
                        pass
            b = carregar_backup()
            b["opcoes"].pop(oid, None)
            salvar_backup(b)
        return False, "; ".join(erros), avisos
    return True, "aplicado e confirmado", avisos


# ======================================================================================
# Reverter
# ======================================================================================
def _loja_restaurar_apps(a, havia):
    if a["desfazer"]:
        ps(a["desfazer"], timeout=120)
    carregar_pacotes()
    faltando = [p for p in (havia if havia is not None else a["pacotes"]) if not _pacote_presente(p)]
    if faltando:
        _abrir("ms-windows-store://search/?query=" + a["loja"].replace(" ", "%20"))
        return [f"Reinstale pela Microsoft Store (abri a página de '{a['loja']}'): " + ", ".join(faltando)]
    return []


def _restaurar(a, s):
    """Restaura a partir do snapshot `s`. Devolve avisos."""
    t = a["tipo"]
    if t == "reg":
        if s["existia"]:
            escrever_reg(a["hive"], a["sub"], a["nome"], s["valor"], s["regtype"])
        else:
            apagar_reg(a["hive"], a["sub"], a["nome"])
    elif t == "svc":
        if s["existe"]:
            _sc_config(a["nome"], s["start"], s["atrasado"])
    elif t == "loja_db":
        p = _caminho_store_db()
        if not s["negado"] and os.path.exists(p) and _tem_deny(p):
            _icacls(p, "/remove:d", "*S-1-1-0")
    elif t == "appx":
        return _loja_restaurar_apps(a, s["presentes"])
    elif t == "onedrive":
        if s["instalado"] and not _onedrive_instalado():
            _reinstalar_onedrive()
    return []


def _restaurar_padrao(a):
    """Sem snapshot: volta ao padrão do Windows."""
    t = a["tipo"]
    if t == "reg":
        if a["padrao"] is None:
            apagar_reg(a["hive"], a["sub"], a["nome"])
        else:
            escrever_reg(a["hive"], a["sub"], a["nome"], a["padrao"], _regtype(a["regtype"]))
    elif t == "svc":
        if _estado_svc(a["nome"])["existe"]:
            _sc_config(a["nome"], a["padrao"], a["atrasado"])
    elif t == "loja_db":
        p = _caminho_store_db()
        if os.path.exists(p) and _tem_deny(p):
            _icacls(p, "/remove:d", "*S-1-1-0")
    elif t == "appx":
        return _loja_restaurar_apps(a, None)
    elif t == "onedrive":
        if not _onedrive_instalado():
            _reinstalar_onedrive()
    return []


def reverter_opcao(oid):
    """Devolve (ok, mensagem, avisos)."""
    op = OPCOES[oid]
    backup = carregar_backup()
    reg = backup["opcoes"].get(oid)
    erros, avisos = [], []
    if reg and len(reg["antes"]) == len(op["acoes"]):
        for a, s in reversed(list(zip(op["acoes"], reg["antes"]))):
            try:
                avisos += _restaurar(a, s)
            except Exception as e:
                erros.append(f"{_rotulo(a)}: {e}")
        if erros:
            return False, "; ".join(erros), avisos  # mantém o snapshot para tentar de novo
        backup["opcoes"].pop(oid, None)
        salvar_backup(backup)
        return True, "restaurado ao estado de antes", avisos

    if estado_opcao(op) in ("inativo", "n/a"):
        if reg:
            backup["opcoes"].pop(oid, None)
            salvar_backup(backup)
        return True, "já estava desativado (nada a reverter)", []
    for a in reversed(op["acoes"]):  # já estava aplicado fora do Roda Liso -> padrão do Windows
        try:
            avisos += _restaurar_padrao(a)
        except Exception as e:
            erros.append(f"{_rotulo(a)}: {e}")
    if erros:
        return False, "; ".join(erros), avisos
    return True, "restaurado ao padrão do Windows (o item já estava aplicado antes do Roda Liso)", avisos


def criar_ponto_restauracao():
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "Checkpoint-Computer -Description 'Roda Liso' -RestorePointType MODIFY_SETTINGS -ErrorAction Stop"],
            capture_output=True, text=True, errors="replace", creationflags=_NO_WINDOW, timeout=120)
    except Exception as e:
        return False, str(e)
    if r.returncode == 0:
        return True, "ponto de restauração solicitado (o Windows só cria 1 a cada 24 h)"
    return False, (r.stderr or r.stdout or "falha desconhecida").strip().splitlines()[0][:200]


# ======================================================================================
# Interface (painel embutido na aba)
# ======================================================================================
FT = {"titulo": 11, "texto": 10, "pequeno": 9}


class CaixaMarcar(tk.Canvas):
    def __init__(self, master, variavel, lado, comando=None):
        try:
            fundo = master.cget("bg")
        except tk.TclError:
            fundo = "#121212"
        super().__init__(
            master, width=lado, height=lado, bg=fundo, cursor="hand2",
            bd=0, highlightthickness=0, takefocus=1
        )
        self._lado = lado
        self._var, self._comando = variavel, comando
        self._cores = {
            "campo": "#1a1a1a", "borda": "#222222", "azul": "#2f81f7",
            "texto": "#ffffff", "suave": "#8b949e",
        }
        self.bind("<Button-1>", self._alternar)
        self.bind("<Return>", self._alternar)
        self.bind("<space>", self._alternar)
        self._trace = variavel.trace_add("write", lambda *a: self._pintar())
        self.bind("<Destroy>", self._ao_destruir)
        self._pintar()

    def _forma(self, x1, y1, x2, y2, raio, **opcoes):
        pontos = [
            x1 + raio, y1, x2 - raio, y1, x2, y1, x2, y1 + raio,
            x2, y2 - raio, x2, y2, x2 - raio, y2, x1 + raio, y2,
            x1, y2, x1, y2 - raio, x1, y1 + raio, x1, y1,
        ]
        return self.create_polygon(pontos, smooth=True, splinesteps=24, **opcoes)

    def _alternar(self, _e=None):
        self._var.set(not self._var.get())
        if self._comando:
            self._comando()
        return "break"

    def _pintar(self):
        try:
            marcado = bool(self._var.get())
            self.delete("all")
            preenchimento = self._cores["azul"] if marcado else self._cores["campo"]
            borda = self._cores["azul"] if marcado else self._cores["suave"]
            self._forma(
                1, 1, self._lado - 1, self._lado - 1, max(4, self._lado // 5),
                fill=preenchimento, outline=borda, width=1
            )
            if marcado:
                self.create_line(
                    self._lado * 0.25, self._lado * 0.52,
                    self._lado * 0.43, self._lado * 0.70,
                    self._lado * 0.76, self._lado * 0.32,
                    fill="#ffffff", width=max(2, self._lado // 10),
                    capstyle="round", joinstyle="round"
                )
        except tk.TclError:
            pass

    def _aplicar_paleta(self, pal):
        for chave in self._cores:
            if chave in pal:
                self._cores[chave] = pal[chave]
        try:
            self.configure(bg=self.master.cget("bg"))
        except tk.TclError:
            pass
        self._pintar()

    def _ao_destruir(self, e):
        if e.widget is self:
            try:
                self._var.trace_remove("write", self._trace)
            except Exception:
                pass


class PainelOtimizadorSO(tk.Frame):
    def __init__(self, master, painel_cls=None):
        super().__init__(master, bg="#000000")
        self._painel_cls = painel_cls
        self.vars = {i: tk.BooleanVar(value=False) for i in OPCOES}
        self.var_restore = tk.BooleanVar(value=True)
        self._ocupado = False
        self._progresso = ""
        self._ponto_criado = False
        self._rotulos = []
        self._montar()
        self._desenhar()
        threading.Thread(target=self._carregar_pacotes_bg, daemon=True).start()
        self._atualizar_ram()

    # ----- layout -----
    def _lado(self, pt, fator, minimo, maximo, negrito=False):
        """Lado (px) de uma caixa de marcação proporcional à altura de linha da fonte (acompanha a escala do Windows)."""
        altura = tkfont.Font(root=self, font=(tema.FONTE, pt, "bold" if negrito else "normal")).metrics("linespace")
        return int(max(minimo, min(maximo, altura * fator)))

    def _montar(self):
        self._lado_caixa = self._lado(FT["texto"], 1.45, 23, 28, negrito=True)
        topo = tk.Frame(self, bg="#000000")
        topo.pack(fill="x", pady=(0, 7))
        self.lbl_ram = tk.Label(topo, text="", font=(tema.FONTE, FT["texto"], "bold"), fg="#38b6ff", bg="#000000")
        self.lbl_ram.pack(side="left")
        dica = tk.Label(topo, text="  •  Selecione os ajustes desejados. Todas as alterações podem ser revertidas.",
                        font=(tema.FONTE, FT["texto"]), fg="#aaaaaa", bg="#000000", justify="left", anchor="w")
        dica.pack(side="left", fill="x", expand=True)
        topo.bind("<Configure>", lambda e: dica.configure(
            wraplength=max(220, e.width - self.lbl_ram.winfo_reqwidth() - 16)))

        if not rodando_como_admin():
            faixa = tk.Frame(self, bg="#121212", highlightbackground="#ff9800", highlightthickness=1)
            faixa.pack(fill="x", pady=(0, 6))
            btn_admin = tk.Button(faixa, text="REABRIR COMO ADMINISTRADOR", bg="#ff9800", fg="white", relief="flat",
                                  font=(tema.FONTE, FT["texto"], "bold"), padx=10, pady=4, cursor="hand2",
                                  command=self._reabrir_como_admin)
            btn_admin.pack(side="right", padx=10, pady=6)
            aviso_admin = tk.Label(faixa, text="Permissão de administrador necessária para alterar Registro e serviços.",
                                   font=(tema.FONTE, FT["texto"]), fg="#ff9800", bg="#121212", justify="left", anchor="w")
            aviso_admin.pack(side="left", padx=10, pady=6, fill="x", expand=True)
            faixa.bind("<Configure>", lambda e: aviso_admin.configure(
                wraplength=max(200, e.width - btn_admin.winfo_reqwidth() - 50)))

        meio = tk.Frame(self, bg="#000000")
        meio.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(meio, bg="#000000", highlightthickness=0)
        self.barra = tk.Scrollbar(meio, orient="vertical", command=self.canvas.yview)
        self.lista = tk.Frame(self.canvas, bg="#000000")
        self._janela = self.canvas.create_window((0, 0), window=self.lista, anchor="nw")
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.barra.pack(side="right", fill="y")
        self.lista.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._ao_redimensionar)
        for w in (self.canvas, self.lista):  # rolagem só quando o mouse está sobre a lista
            w.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._roda))
            w.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

        rodape = tk.Frame(self, bg="#000000")
        rodape.pack(fill="x", pady=(10, 0))
        self.lbl_estimativa = tk.Label(rodape, text="", font=(tema.FONTE, FT["texto"], "bold"), fg="#28a745",
                                       bg="#000000", justify="left")
        self.lbl_estimativa.pack(anchor="w")
        rodape.bind("<Configure>", self._ao_redimensionar_rodape)

        # Linha do ponto de restauração: texto à esquerda, caixa de marcação à direita (mesma coluna das opções)
        self.linha_restore = tk.Frame(rodape, bg="#000000")
        self.linha_restore.pack(fill="x", pady=(8, 0))
        lbl_restore = tk.Label(self.linha_restore, text="Criar ponto de restauração antes de aplicar (recomendado)",
                               font=(tema.FONTE, FT["texto"]), fg="#ffffff", bg="#000000", cursor="hand2")
        lbl_restore.pack(side="left")
        lbl_restore.bind("<Button-1>", lambda e: self.var_restore.set(not self.var_restore.get()))
        CaixaMarcar(self.linha_restore, self.var_restore, self._lado(FT["texto"], 1.35, 22, 26)).pack(side="right")

        # Botões de uma ponta a outra, com a mesma largura
        botoes = tk.Frame(rodape, bg="#000000")
        botoes.pack(fill="x", pady=(12, 0))
        self._botoes_frame, self._botoes = botoes, []
        for texto, cor, cmd in (("APLICAR", "#2f81f7", self.aplicar_selecionados),
                                ("REVERTER", "#4b5563", self.reverter_selecionados),
                                ("RECOMENDADOS", "#4b5563", self.selecionar_recomendados),
                                ("LIMPAR SELEÇÃO", "#4b5563", self.limpar_selecao)):
            self._botoes.append(tk.Button(botoes, text=texto, bg=cor, activebackground=cor,
                                          fg="white", activeforeground="white",
                                          font=(tema.FONTE, FT["texto"], "bold"), relief="flat", bd=0,
                                          padx=12, pady=12, cursor="hand2", command=cmd))
        self._colunas_botoes = None
        botoes.bind("<Configure>", self._organizar_botoes)
        self._organizar_botoes()
        self.lbl_status = tk.Label(rodape, text="", font=(tema.FONTE, FT["texto"]), fg="#aaaaaa", bg="#000000", justify="left")
        self.lbl_status.pack(anchor="w", pady=(8, 0))
        self.after_idle(self._alinhar_rodape)

    def _organizar_botoes(self, _e=None):
        """4 botões em uma linha se couberem; senão 2 por linha (janela estreita, ex.: metade da tela)."""
        try:
            largura = self._botoes_frame.winfo_width()
            if largura <= 1:
                return
            precisa = sum(b.winfo_reqwidth() for b in self._botoes) + 8 * (len(self._botoes) - 1)
            colunas = len(self._botoes) if largura >= precisa else 2
            if colunas == self._colunas_botoes:
                return
            self._colunas_botoes = colunas
            for i in range(len(self._botoes)):
                self._botoes_frame.grid_columnconfigure(i, weight=0, uniform="")
            for c in range(colunas):
                self._botoes_frame.grid_columnconfigure(c, weight=1, uniform="botoes")
            for i, b in enumerate(self._botoes):
                lin, col = divmod(i, colunas)
                b.grid(row=lin, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=(0 if lin == 0 else 8, 0))
        except tk.TclError:
            pass

    def _ao_redimensionar_rodape(self, e):
        for lbl in (self.lbl_estimativa, self.lbl_status):
            lbl.configure(wraplength=max(220, e.width - 8))

    def _alinhar_rodape(self):
        """Alinha a caixa do ponto de restauração com a coluna das caixas das opções (descontando a barra de rolagem)."""
        try:
            self.update_idletasks()
            self.linha_restore.pack_configure(padx=(0, self.barra.winfo_reqwidth() + 8 + 14 + 1))
        except tk.TclError:
            pass

    def _roda(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def _largura_texto(self, largura_canvas):
        return max(300, largura_canvas - self._lado_caixa - 115)

    def _ao_redimensionar(self, e):
        self.canvas.itemconfigure(self._janela, width=e.width)
        for lbl in self._rotulos:
            if lbl.winfo_exists():
                lbl.configure(wraplength=self._largura_texto(e.width))

    def _desenhar(self):
        pos = self.canvas.yview()[0]
        for w in self.lista.winfo_children():
            w.destroy()
        self._rotulos = []
        backup = carregar_backup()["opcoes"]
        largura = self._largura_texto(self.canvas.winfo_width())
        for grupo in GRUPOS:
            tk.Label(self.lista, text=grupo.upper(), font=(tema.FONTE, FT["pequeno"], "bold"), fg="#38b6ff",
                     bg="#000000").pack(anchor="w", pady=(10, 3))
            for oid, op in OPCOES.items():
                if op["grupo"] == grupo:
                    self._cartao(oid, op, backup, largura)
        tema.reaplicar(self)
        self.update_idletasks()
        self.canvas.yview_moveto(pos)
        self._atualizar_estimativa()

    def _cartao(self, oid, op, backup, largura):
        est = estado_opcao(op)
        if self._painel_cls:
            painel = self._painel_cls(self.lista, raio=12, padding=12)
            painel.pack(fill="x", padx=(0, 8), pady=4)
            c = painel.conteudo
        else:
            c = tk.Frame(self.lista, bg="#121212", highlightbackground="#222222", highlightthickness=1, padx=14, pady=12)
            c.pack(fill="x", padx=(0, 8), pady=5)
        c.grid_columnconfigure(0, weight=1)

        topo = tk.Frame(c, bg="#121212")
        topo.grid(row=0, column=0, columnspan=2, sticky="ew")
        lbl_nome = tk.Label(topo, text=op["nome"], font=(tema.FONTE, FT["titulo"], "bold"), fg="#ffffff", bg="#121212",
                            justify="left", anchor="w")
        lbl_nome.grid(row=0, column=0, sticky="w")
        etiquetas = tk.Frame(topo, bg="#121212")
        topo.grid_columnconfigure(0, weight=1)
        if est == "ativo":
            origem = f"aplicado pelo Roda Liso em {backup[oid]['aplicado_em']}" if oid in backup else "já estava ativo antes do Roda Liso"
            chip, cor = f"● ATIVO ({origem})", "#28a745"
        elif est == "parcial":
            chip, cor = "◐ PARCIALMENTE ATIVO", "#ff9800"
        elif est == "n/a":
            chip, cor = "não se aplica a este PC", "#aaaaaa"
        elif est == "verificando":
            chip, cor = "… verificando", "#aaaaaa"
        else:
            chip, cor = "○ desativado", "#aaaaaa"
        tk.Label(etiquetas, text=chip, font=(tema.FONTE, FT["pequeno"]), fg=cor, bg="#121212").pack(side="right")
        cor_risco = {"baixo": "#28a745", "médio": "#ff9800", "ALTO": "#dc3545"}[op["risco"]]
        tk.Label(etiquetas, text=f"RISCO {op['risco'].upper()}", font=(tema.FONTE, FT["pequeno"], "bold"), fg=cor_risco,
                 bg="#121212").pack(side="right", padx=10)

        def _posicionar(e, nome=lbl_nome, et=etiquetas, t=topo):
            # cabe tudo na mesma linha? senão, as etiquetas descem para uma linha própria, alinhadas à direita
            cabe = nome.winfo_reqwidth() + et.winfo_reqwidth() + 20 <= e.width
            if cabe:
                et.grid(row=0, column=1, sticky="e")
            else:
                et.grid(row=1, column=0, columnspan=2, sticky="e", pady=(4, 0))

        topo.bind("<Configure>", _posicionar)

        lo, hi = op["ram"]
        ram = "RAM: sem ganho relevante" if hi == 0 else f"RAM estimada: ~{lo} a {hi} MB"
        linhas = [(op["desc"], "#e0e0e0", (tema.FONTE, FT["texto"])),
                  (f"Benefício · {op['pos']}", "#28a745", (tema.FONTE, FT["texto"])),
                  (f"Atenção · {op['neg']}", "#ff9800", (tema.FONTE, FT["texto"])),
                  (f"{ram}" + (f"  ·  {op['reinicio']}" if op["reinicio"] else ""), "#aaaaaa",
                   (tema.FONTE, FT["pequeno"], "italic"))]
        for i, (texto, cor_t, fonte) in enumerate(linhas):
            lbl = tk.Label(c, text=texto, font=fonte, fg=cor_t, bg="#121212", justify="left", anchor="w",
                           wraplength=largura)
            lbl.grid(row=1 + i, column=0, sticky="w", pady=(5 if i else 8, 0))
            self._rotulos.append(lbl)
        area_check = tk.Frame(c, bg="#121212")
        area_check.grid(row=1, column=1, rowspan=len(linhas), padx=(16, 0), sticky="n")
        tk.Label(
            area_check, text="Selecionar", font=(tema.FONTE, FT["pequeno"]),
            fg="#aaaaaa", bg="#121212"
        ).pack(pady=(8, 5))
        CaixaMarcar(area_check, self.vars[oid], self._lado_caixa, comando=self._atualizar_estimativa).pack()

    # ----- estimativa -----
    def _atualizar_estimativa(self):
        lo = hi = n = 0
        for oid, v in self.vars.items():
            if v.get() and estado_opcao(OPCOES[oid]) != "ativo":
                lo += OPCOES[oid]["ram"][0]
                hi += OPCOES[oid]["ram"][1]
                n += 1
        if n == 0:
            self.lbl_estimativa.config(text="Nenhum item novo selecionado.")
        else:
            self.lbl_estimativa.config(
                text=f"{n} item(ns) a aplicar - ganho estimado de RAM: ~{lo} a {hi} MB (aproximado; varia de PC para PC e os valores se sobrepõem em parte)")

    def selecionar_recomendados(self):
        for oid, v in self.vars.items():
            v.set(oid in RECOMENDADOS)
        self._atualizar_estimativa()

    def limpar_selecao(self):
        for v in self.vars.values():
            v.set(False)
        self._atualizar_estimativa()

    # ----- execução em segundo plano -----
    def _rodar(self, tarefa, final):
        if self._ocupado:
            return
        self._ocupado = True
        self.winfo_toplevel().config(cursor="watch")
        resultado = {}

        def alvo():
            try:
                resultado["valor"] = tarefa()
            except Exception as e:
                resultado["erro"] = str(e)

        t = threading.Thread(target=alvo, daemon=True)
        t.start()

        def acompanhar():
            self.lbl_status.config(text=self._progresso)
            if t.is_alive():
                self.after(200, acompanhar)
                return
            self._ocupado = False
            self.winfo_toplevel().config(cursor="")
            final(resultado)

        acompanhar()

    def _checar_admin(self):
        if rodando_como_admin():
            return True
        messagebox.showwarning("Administrador necessário",
                               "Reabra o Roda Liso como Administrador (botão laranja no topo da aba).")
        return False

    def _selecionados(self):
        return [i for i, v in self.vars.items() if v.get()]

    def aplicar_selecionados(self):
        if self._ocupado or not self._checar_admin():
            return
        ids = [i for i in self._selecionados() if estado_opcao(OPCOES[i]) != "ativo"]
        if not ids:
            messagebox.showinfo("Aplicar", "Nenhum item novo selecionado (os marcados já estão ativos).")
            return
        texto = "Aplicar estas otimizações?\n\n" + "\n".join(f"  • {OPCOES[i]['nome']}" for i in ids)
        altos = [i for i in ids if OPCOES[i]["risco"] == "ALTO"]
        if altos:
            texto += "\n\nATENÇÃO: itens de risco ALTO (removem programas/componentes):\n" + "\n".join(f"  • {OPCOES[i]['nome']}" for i in altos)
            texto += "\nPara voltar atrás é preciso reinstalar pela Microsoft Store/winget."
        if "onedrive" in ids and onedrive_protege_pastas():
            texto += ("\n\n⚠ Suas pastas Desktop/Documentos/Imagens estão dentro do OneDrive. Certifique-se de que "
                      "TUDO está baixado no PC (botão direito > 'Sempre manter neste dispositivo') antes de continuar.")
        if not messagebox.askyesno("Confirmar", texto + "\n\nContinuar?"):
            return
        usar_restore = self.var_restore.get() and not self._ponto_criado

        def tarefa():
            res = []
            if usar_restore:
                self._progresso = "Criando ponto de restauração..."
                ok, msg = criar_ponto_restauracao()
                self._ponto_criado = True
                res.append(("__restore__", ok, msg, []))
            for i in ids:
                self._progresso = f"Aplicando: {OPCOES[i]['nome']}..."
                ok, msg, avisos = aplicar_opcao(i)
                res.append((i, ok, msg, avisos))
            return res

        self._rodar(tarefa, lambda r: self._mostrar_resultado("Resultado", r))

    def reverter_selecionados(self):
        if self._ocupado or not self._checar_admin():
            return
        ids = self._selecionados()
        if not ids:
            messagebox.showinfo("Reverter", "Marque os itens que deseja reverter.")
            return
        texto = "Voltar estes itens ao estado de antes?\n\n" + "\n".join(f"  • {OPCOES[i]['nome']}" for i in ids)
        if any(a["tipo"] in ("appx", "onedrive") for i in ids for a in OPCOES[i]["acoes"]):
            texto += "\n\nItens que removem apps serão reinstalados (internet necessária) ou abrirão a Microsoft Store."
        if not messagebox.askyesno("Confirmar reversão", texto):
            return

        def tarefa():
            res = []
            for i in ids:
                self._progresso = f"Revertendo: {OPCOES[i]['nome']}..."
                ok, msg, avisos = reverter_opcao(i)
                res.append((i, ok, msg, avisos))
            return res

        self._rodar(tarefa, lambda r: self._mostrar_resultado("Reversão", r))

    def _mostrar_resultado(self, titulo, r):
        self._desenhar()
        self.lbl_status.config(text="")
        if "erro" in r:
            messagebox.showerror(titulo, f"Erro inesperado: {r['erro']}")
            return
        linhas, falhas, avisos = [], 0, []
        for oid, ok, msg, av in r["valor"]:
            if oid == "__restore__":
                linhas.append(f"{'✓' if ok else '⚠'} Ponto de restauração: {msg}")
                continue
            falhas += 0 if ok else 1
            linhas.append(f"{'✓' if ok else '✗'} {OPCOES[oid]['nome']}: {msg}")
            avisos += [f"• {OPCOES[oid]['nome']}: {a}" for a in av]
        texto = "\n".join(linhas)
        if avisos:
            texto += "\n\nAvisos:\n" + "\n".join(avisos)
        texto += "\n\nReinicie o Windows para concluir os itens que pedem reinício."
        (messagebox.showwarning if falhas else messagebox.showinfo)(titulo, texto)

    # ----- diversos -----
    def _carregar_pacotes_bg(self):
        carregar_pacotes()
        try:
            self.after(0, self._desenhar_se_livre)
        except (tk.TclError, RuntimeError):
            pass

    def _desenhar_se_livre(self):
        if not self._ocupado and self.winfo_exists():
            self._desenhar()

    def _atualizar_ram(self):
        try:
            if psutil:
                m = psutil.virtual_memory()
                self.lbl_ram.config(text=f"RAM em uso agora: {m.used / 1024**3:.1f} / {m.total / 1024**3:.1f} GB ({m.percent:.0f}%)")
            self._organizar_botoes()  # a fonte do tema pode mudar a largura dos botões depois da criação
            self.after(2000, self._atualizar_ram)
        except tk.TclError:
            pass

    def _reabrir_como_admin(self):
        try:
            args = " ".join(f'"{a}"' for a in [os.path.abspath(sys.argv[0]), *sys.argv[1:]])
            if ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, os.getcwd(), 1) > 32:
                self.winfo_toplevel().destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível reabrir como administrador: {e}")


# ======================================================================================
# Execução avulsa (python otimizador_so.py)
# ======================================================================================
if __name__ == "__main__":
    if not rodando_como_admin():
        try:
            args = " ".join(f'"{a}"' for a in [os.path.abspath(__file__), *sys.argv[1:]])
            if ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, BASE_DIR, 1) > 32:
                sys.exit(0)
        except Exception:
            pass
    janela = tk.Tk()
    janela.title("Roda Liso - Otimizador de SO")
    janela.geometry("980x720")
    janela.configure(bg="#000000")
    painel = PainelOtimizadorSO(janela)
    painel.pack(fill="both", expand=True, padx=10, pady=10)
    tema.instalar(janela, antes_de=painel, subtitulo="Otimizador de SO")
    janela.mainloop()
