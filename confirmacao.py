import ctypes

def abrir_janela_confirmacao(nome_jogo: str, nivel_sugerido: str, gap_desempenho: float, mensagem_ia: str) -> bool:
    titulo = "Roda Liso - Otimização Necessária"
    texto = (
        f"O jogo {nome_jogo} está com déficit de {gap_desempenho:.1f}% no desempenho.\n\n"
        f"Recomendação da IA:\n{mensagem_ia}\n\n"
        f"Deseja aplicar o {nivel_sugerido} agora?\n\n"
        f"ATENÇÃO: o jogo será FECHADO e reaberto automaticamente. Salve seu progresso antes de clicar em Sim."
    )
    
    # 4 = Botões Sim/Não | 32 = Ícone de Interrogação | 4096 = Força a janela a ficar no topo
    resposta = ctypes.windll.user32.MessageBoxW(0, texto, titulo, 4 | 32 | 4096)
    
    # Retorna True se o usuário clicou em "Sim" (código 6 do Windows)
    return resposta == 6