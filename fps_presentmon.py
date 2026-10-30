"""Medição de FPS real via PresentMon 2.6.0 (console).

Mudanças em relação à versão antiga do monitor.py:
  1. Argumentos com dois hífens (formato oficial do PresentMon 2.x).
  2. --terminate_after_timed: o PresentMon encerra sozinho ao fim da captura.
  3. --session_name + --stop_existing_session: evita erro de sessão ETW "já em uso".
  4. --v1_metrics: CSV com o schema clássico (coluna msBetweenPresents).
  5. FPS calculado pelo tempo real entre frames (1000 / média do tempo de frame)
     em vez de (linhas do CSV / duração nominal).
  6. Falha de leitura devolve None (e não 0.0), para não contar como "FPS baixo".
  7. Quando algo dá errado, mostra o motivo (código de saída, stdout e stderr).
"""
import csv
import ctypes
import os
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRESENTMON_PATH = os.path.join(BASE_DIR, "PresentMon.exe")
CSV_TEMP = os.path.join(BASE_DIR, "temp_fps.csv")
SESSION_NAME = "RodaLiso"

# Colunas com o tempo entre dois frames, em milissegundos.
# msBetweenPresents = schema --v1_metrics | FrameTime = schema padrão do 2.x
COLUNAS_TEMPO_FRAME_MS = ("msBetweenPresents", "MsBetweenPresents", "FrameTime")

# Evita que uma janela de console pisque na frente do jogo a cada medição
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def rodando_como_admin() -> bool:
    """O PresentMon (ETW) exige admin ou o grupo 'Performance Log Users'."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def calcular_fps_do_csv(caminho_csv: str):
    """Lê o CSV do PresentMon e devolve (fps, n_frames, segundos_capturados).

    Devolve None se o arquivo não tiver nenhuma coluna de tempo de frame conhecida.
    Devolve (0.0, 0, 0.0) se o CSV existir mas não tiver frames.
    """
    with open(caminho_csv, "r", newline="", encoding="utf-8-sig") as f:
        leitor = csv.DictReader(f)
        cabecalho = leitor.fieldnames or []
        coluna = next((c for c in COLUNAS_TEMPO_FRAME_MS if c in cabecalho), None)

        if coluna is None:
            print(f"[ERRO FPS] Nenhuma coluna de tempo de frame no CSV. Cabeçalho recebido: {cabecalho}")
            return None

        tempos_ms = []
        for linha in leitor:
            try:
                valor = float(linha[coluna])
            except (TypeError, ValueError, KeyError):
                continue
            if valor > 0:  # o 1º frame costuma vir com 0 (não há frame anterior)
                tempos_ms.append(valor)

    if not tempos_ms:
        return 0.0, 0, 0.0

    segundos = sum(tempos_ms) / 1000.0
    fps = len(tempos_ms) / segundos  # equivale a 1000 / tempo médio de frame
    return round(fps, 1), len(tempos_ms), round(segundos, 2)


def medir_fps_presentmon(exe_jogo: str, duracao_segundos: int = 2, debug: bool = False):
    """Mede o FPS médio do jogo durante `duracao_segundos`.

    Retorna float (FPS) ou None se não foi possível medir.
    """
    if not exe_jogo.lower().endswith(".exe"):
        print(f"[ERRO FPS] Precisa do nome do executável (ex.: 'witcher3.exe'). Recebido: '{exe_jogo}'")
        return None

    if not os.path.exists(PRESENTMON_PATH):
        print(f"[ERRO FPS] PresentMon.exe não encontrado em: {PRESENTMON_PATH}")
        return None

    # Remove CSV antigo que tenha ficado preso por erro anterior
    if os.path.exists(CSV_TEMP):
        try:
            os.remove(CSV_TEMP)
        except OSError:
            pass

    cmd = [
        PRESENTMON_PATH,
        "--process_name", exe_jogo,
        "--timed", str(duracao_segundos),
        "--terminate_after_timed",
        "--output_file", CSV_TEMP,
        "--v1_metrics",
        "--no_console_stats",
        "--session_name", SESSION_NAME,
        "--stop_existing_session",
    ]

    try:
        resultado = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=duracao_segundos + 10,
            creationflags=_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        print("[ERRO FPS] O PresentMon não encerrou a tempo (timeout).")
        return None
    except OSError as e:
        print(f"[ERRO FPS] Não consegui executar o PresentMon: {e}")
        return None

    if not os.path.exists(CSV_TEMP):
        print("[ERRO FPS] O PresentMon não gerou o CSV.")
        print(f"           código de saída: {resultado.returncode}")
        if resultado.stdout.strip():
            print(f"           stdout: {resultado.stdout.strip()}")
        if resultado.stderr.strip():
            print(f"           stderr: {resultado.stderr.strip()}")
        if not rodando_como_admin():
            print("           DICA: rode o terminal/VS Code como Administrador "
                  "(ou adicione seu usuário ao grupo 'Performance Log Users').")
        return None

    try:
        medicao = calcular_fps_do_csv(CSV_TEMP)
    finally:
        try:
            os.remove(CSV_TEMP)
        except OSError:
            pass

    if medicao is None:
        return None

    fps, n_frames, segundos = medicao
    if n_frames == 0:
        print(f"[ERRO FPS] '{exe_jogo}' foi monitorado, mas 0 frames foram capturados "
              "(jogo minimizado, em tela de carregamento ou nome do .exe diferente?).")
        return None

    if debug:
        print(f"[DEBUG FPS] {n_frames} frames em {segundos}s de captura efetiva "
              f"(janela pedida: {duracao_segundos}s) -> {fps} FPS")
    return fps
