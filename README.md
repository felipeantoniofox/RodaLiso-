<div align="center">

# RODA LISO

### Performance Hub · Otimização de jogos e do Windows com monitoramento e IA

**Uma central desktop para analisar seu hardware, acompanhar o FPS real, aplicar configurações gráficas, gerenciar recursos e explorar otimizações: com o usuário no controle.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![LangGraph](https://img.shields.io/badge/IA-LangGraph-222222?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/Inference-Groq-F55036?style=for-the-badge)](https://groq.com/)
[![PresentMon](https://img.shields.io/badge/FPS-PresentMon-16A085?style=for-the-badge)](https://github.com/GameTechDev/PresentMon)

[![GitHub last commit](https://img.shields.io/github/last-commit/felipeantoniofox/RodaLiso-?style=flat-square)](https://github.com/felipeantoniofox/RodaLiso-/commits/main)
[![GitHub repo size](https://img.shields.io/github/repo-size/felipeantoniofox/RodaLiso-?style=flat-square)](https://github.com/felipeantoniofox/RodaLiso-)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/felipeantoniofox/RodaLiso-/devsecops.yml?branch=main&style=flat-square&label=DevSecOps)](https://github.com/felipeantoniofox/RodaLiso-/actions)

[**Funcionalidades**](#funcionalidades) · [**Instalação**](#instalação-e-execução) · [**Como usar**](#como-usar) · [**Arquitetura**](#arquitetura-e-fluxo-da-ia) · [**Jogos**](#jogos-e-compatibilidade) · [**Segurança**](#segurança-e-reversão)

> **Projeto em desenvolvimento:** as funcionalidades dependem do jogo, da configuração local, das permissões do Windows e dos serviços externos. Nem todos os jogos listados oferecem presets automáticos.

</div>

---

## Sobre o projeto

O **Roda Liso** é uma aplicação gráfica para Windows, desenvolvida principalmente em **Python + Tkinter/ttk**, que concentra diferentes ferramentas voltadas à experiência de jogos no PC:

- Diagnóstico de compatibilidade entre **CPU, GPU, RAM e requisitos cadastrados** de jogos.
- Monitoramento de **FPS real** por meio do **PresentMon (ETW)**.
- Coleta de telemetria de **CPU, RAM, GPU e VRAM**, conforme a disponibilidade dos contadores.
- **Agente de IA** que analisa déficit de desempenho, explica recomendações e solicita aprovação.
- Aplicação e reversão de **presets gráficos** armazenados no projeto.
- Filtro de **nitidez CAS** via **ReShade**, com intensidades selecionáveis.
- Sugestões de liberação de recursos quando CPU ou RAM estão sob alta utilização.
- Painel de **otimizações do Windows**, com inspeção de estado, backups e reversão quando possível.
- Interface ajustável, com **tema claro/escuro** e atenção a escalas de DPI.

### Objetivo

Facilitar o acesso a ajustes de desempenho e apresentar informações compreensíveis para o jogador, combinando **monitoramento real**, **regras de otimização**, **IA generativa para explicações** e **ações confirmadas pelo usuário**.

> **Importante:** o Roda Liso não aumenta a capacidade física do hardware, não garante ganho de FPS e não substitui benchmarks comparativos. Resultados dependem do jogo, de drivers, temperatura, gargalos e configurações.

---

## Funcionalidades

### 1. Diagnóstico de hardware

A aba **Diagnóstico** permite selecionar ou detectar componentes do computador e compará-los com requisitos previamente cadastrados.

| Recurso | Descrição |
|---|---|
| Detecção de hardware | Consulta o Windows por **PowerShell / CIM / WMI** para identificar CPU, GPU e memória. |
| Avaliação de compatibilidade | Compara pontuações **internas e heurísticas** de CPU/GPU com limites cadastrados para cada jogo. |
| Identificação de gargalo | Sinaliza insuficiência de RAM ou pontuação inferior à referência de CPU/GPU. |
| Capas de jogos | Exibe imagens locais dos títulos cadastrados, quando disponíveis. |

**Como interpretar:** o resultado **“RODA LISO!”** significa que o PC atendeu aos critérios simplificados definidos no código. **Não é uma medição de FPS nem garantia de compatibilidade oficial.** A pontuação não é proveniente de um benchmark automático.

### 2. Central de tutoriais

Reúne acesso a conteúdos sobre:

- Limpeza de sistema e *debloat*;
- *Undervolt* e gerenciamento térmico;
- Ajustes de processadores Ryzen;
- *Overclock* de GPU;
- Conversão de DirectX para Vulkan usando DXVK;
- Instalação e manutenção de drivers antigos.

Os botões abrem links e materiais externos: **não executam automaticamente esses procedimentos**.

### 3. Correção de problemas

Oferece arquivos de configuração para cenários específicos, incluindo:

| Preset / correção cadastrada | Finalidade proposta |
|---|---|
| Assassin's Creed IV: Black Flag | Arquivo voltado a problemas de travamento. |
| Counter-Strike 2 | Configuração `autoexec.cfg` voltada a desempenho. |
| Cyberpunk 2077 | Arquivo com parâmetros de carregamento assíncrono. |
| DXVK (genérico) | Arquivo `dxvk.conf` com parâmetros predefinidos. |

O usuário escolhe onde salvar o arquivo. Quando o destino já existe, o código tenta criar um **backup `.bak`** antes da substituição.

> Esses ajustes são **experimentais e específicos de versão**: certos parâmetros podem ser ignorados, removidos ou incompatíveis com versões atuais dos jogos ou ferramentas. Confira cada caso antes de aplicar.

### 4. Performance AMD

Inclui controles para preparar parâmetros relacionados a:

- Limite de temperatura;
- Limites de energia/TDP;
- Offset de clock da GPU integrada;
- Outros argumentos específicos de tuning.

**Estado atual:** a função principal **monta e exibe os argumentos**. A execução automática de alterações no hardware por uma ferramenta externa **não está demonstrada nesse trecho da implementação**. Ajustes reais de energia e clock exigem validação por hardware e cuidados térmicos.

### 5. Empurrãozinho: presets gráficos

Permite aplicar arquivos de configuração gráfica por nível e restaurar backups.

**The Witcher 3 (2015)** possui seis níveis configurados:

| Nível | Perfil |
|:---:|---|
| 1 | Mais baixo: prioriza FPS |
| 2 | Baixo |
| 3 | Normal |
| 4 | Alto |
| 5 | Muito alto |
| 6 | Ultra |

**Fluxo manual de aplicação de presets**

| Etapa | Ação | Resultado esperado |
|:---:|---|---|
| 1 | Selecionar o jogo | Identifica os presets cadastrados para o título. |
| 2 | Escolher o nível gráfico | Define o arquivo de configuração que será utilizado. |
| 3 | Localizar o arquivo original | Procura os caminhos conhecidos ou solicita a seleção manual. |
| 4 | Criar uma cópia de segurança | Preserva o arquivo original, quando ainda não existe backup. |
| 5 | Aplicar o preset | Substitui o arquivo de configuração pelo nível selecionado. |
| 6 | Reverter, quando necessário | Restaura o arquivo original a partir do backup. |

**Limitação:** embora Cyberpunk 2077 apareça no dicionário de presets, sua lista `niveis` está vazia na versão analisada. Portanto, **não há níveis de preset gráficos prontos para esse jogo nesse módulo**.

### 6. Agente de IA com LangGraph

O projeto utiliza **LangGraph** para orquestrar estados e decisões, **LangChain/ChatGroq** para consultar um modelo de linguagem e **Groq** como serviço de inferência.

O agente pode:

1. Observar o jogo detectado entre os executáveis monitorados.
2. Aguardar o período inicial de estabilização.
3. Medir FPS e utilização dos principais recursos.
4. Comparar o FPS atual com a **meta definida pelo usuário**.
5. Detectar queda persistente abaixo da meta.
6. Calcular o déficit percentual e inspecionar a qualidade gráfica atual, quando suportada.
7. Solicitar à IA uma **explicação textual da otimização recomendada**.
8. Selecionar um nível de preset usando **regras programadas em Python**.
9. Abrir uma janela nativa do Windows para **aprovação**.
10. Quando aprovado e viável: aplicar o preset, configurar nitidez opcional e tentar reiniciar o jogo via atalho configurado.

#### Parâmetros atuais do monitoramento

| Parâmetro | Comportamento padrão no código |
|---|---|
| Aquecimento inicial | **120 s** após a detecção de um jogo |
| Janela de captura de FPS | **2 s** por leitura do PresentMon |
| Queda persistente | **10 s** abaixo da meta antes de invocar o agente |
| Cooldown após acionamento | **120 s** |
| Meta inicial da rotina | **30 FPS** quando não fornecida outra meta |
| Modelo padrão | `openai/gpt-oss-20b` via `ChatGroq` |

O botão **Pausar** suspende novas leituras e sugestões no loop de monitoramento; o botão **Ativar** pode retomar o processo.

> **Como a IA é usada de verdade:** o modelo produz a **justificativa textual**. O nível de preset é definido por condicionais do próprio `agent.py`, considerando o déficit e a qualidade atual. Isso significa que o sistema é **híbrido (IA + regras determinísticas)**, e não um modelo treinado para prever o melhor preset.

> **Atenção ao desligamento:** na rota automática de aplicação, o código pode **encerrar o processo do jogo** antes de substituir a configuração. Salve o progresso antes de permitir uma otimização. O reinício depende do atalho do jogo e não é garantido.

### 7. FPS real com PresentMon

O módulo `fps_presentmon.py` usa o **PresentMon 2.x** para obter dados de apresentação de quadros e calcula uma média de FPS a partir dos intervalos entre frames registrados em CSV.

- Integração com **ETW** (*Event Tracing for Windows*).
- Identificação do jogo pelo nome do processo.
- Capturas temporárias com tratamento de falhas.
- Cálculo baseado nos tempos entre quadros, em vez de contar simplesmente as linhas por um tempo nominal.
- Tratamento de leitura inválida para não confundir falha do monitor com **0 FPS**.
- Para NVIDIA, tentativa de consulta da GPU/VRAM via `nvidia-smi`; para outras GPUs, tentativa de consulta de contadores do Windows.

A captura pode exigir **execução como administrador** ou permissões adequadas de monitoramento de desempenho no Windows.

### 8. Otimização de CPU e RAM

O módulo `otimizador_recursos.py` observa níveis elevados de uso e pode recomendar o fechamento de aplicações conhecidas em segundo plano.

- Gatilho padrão: **95% de CPU ou RAM**, em **3 leituras seguidas**.
- Intervalo entre sugestões: **5 minutos**.
- Lista permitida de candidatos (por exemplo, navegadores, Discord, Spotify e launchers).
- Filtragem de processos protegidos, do sistema e de outros usuários.
- Confirmação antes de tentar fechar aplicações.
- Tentativa de encerramento normal e, se necessário, **forçado**.

> O fechamento pode causar perda de conteúdo não salvo. A lista de aplicações candidatas não implica que todas serão encerradas a cada execução.

### 9. Nitidez com ReShade / CAS

O arquivo `nitidez.py` fornece um **shader de nitidez adaptativa ao contraste**, com integração ao **ReShade**.

| Intensidade | Valor configurado |
|---|---:|
| Baixa (Suave) | `0.30` |
| Média (Padrão) | `0.50` |
| Alta (Nítida) | `0.70` |
| Máxima (Agressiva) | `0.90` |

O módulo pode localizar pastas de jogos, reconhecer instalações do ReShade, instalar o efeito local, criar o preset `RodaLiso_Nitidez.ini`, configurar a seleção do preset e restaurar a configuração anterior.

**Limites de compatibilidade:**

- O instalador automático cobre os jogos e APIs contemplados no módulo, principalmente caminhos **DXGI**.
- Jogos configurados para **Vulkan** podem exigir instalação manual do ReShade.
- O **CS 2 é bloqueado** pelo código de nitidez por precaução com mecanismos anticheat.
- Para **GTA V**, o código alerta para uso apenas no **modo história**.

> **CAS ≠ FSR completo.** Este recurso aplica **nitidez por pós-processamento**, da família de algoritmos de nitidez associados ao FidelityFX. **Não implementa a etapa de upscaling espacial EASU do FSR 1.0**, nem oferece geração de quadros.

### 10. Otimizador de sistema operacional

O painel `otimizador_so.py` reúne **11 grupos de ajustes** para Windows, com verificação de estado, seleção de opções e tentativa de reversão.

| Grupo | Ajuste | Efeito principal |
|---|---|---|
| Essenciais | Consumer Features | Reduz sugestões e conteúdo promocional. |
| Essenciais | Delivery Optimization | Ajusta o compartilhamento P2P de atualizações. |
| Essenciais | Localização | Desativa recursos de localização. |
| Essenciais | Sugestões da Store | Reduz sugestões na pesquisa do Windows. |
| Essenciais | Serviços | Altera o modo de inicialização de serviços selecionados. |
| Essenciais | Telemetria | Altera políticas e serviços de diagnóstico. |
| Essenciais | Widgets | Remove componentes de Widgets. |
| Preferências | Bing no Menu Iniciar | Desativa resultados web na pesquisa local. |
| Avançado | Microsoft Edge | Aplica políticas para reduzir recursos opcionais. |
| Avançado | OneDrive | Remove o aplicativo e interrompe sua sincronização. |
| Avançado | Windows AI | Desativa/remove componentes selecionados de IA e aplicativos. |

**Recursos adicionais:**

- Exibição de descrição, benefícios previstos, impactos e risco de cada opção.
- Estimativas de memória liberada, **não medições verificadas**.
- Registro de estado anterior em `rodaliso_so_backup.json`.
- Leitura do estado após aplicar os ajustes.
- Ações de reversão, inclusive tentativa de reinstalar alguns componentes.
- Opção de criar **ponto de restauração** do sistema.

> **Risco real:** remover OneDrive, Widgets ou componentes de IA pode afetar recursos do Windows e exigir reinstalação, atualização ou reparo. A reversão desses itens **pode ser parcial**. Se o OneDrive sincroniza Documentos, Área de Trabalho ou Imagens, confirme que todos os dados necessários estão disponíveis localmente antes de alterar o aplicativo.

### 11. Interface e personalização

- Temas **noturno** e **claro**.
- Preferência de aparência persistida em `rodaliso_tema.json`.
- Ajustes para escalonamento de tela (DPI).
- Componentes e abas que se reorganizam conforme o espaço disponível.
- Cores de status, indicadores e caixas de confirmação.

---

## Jogos e compatibilidade

As funcionalidades disponíveis **não são iguais para todos os jogos**. A tabela abaixo reflete os cadastros encontrados nos módulos principais da versão analisada.

| Jogo | Diagnóstico | Detecção para monitorar FPS | Preset gráfico pronto | Nitidez: cadastro |
|---|:---:|:---:|:---:|:---:|
| The Witcher 3 (2015) | Não configurado | Sim | Sim: 6 níveis | Sim |
| Cyberpunk 2077 | Sim | Sim | Parcial: sem níveis | Sim |
| Counter-Strike 2 | Sim | Sim | Não configurado | Bloqueado |
| GTA V | Sim | Sim | Não configurado | Restrito ao modo história |
| Red Dead Redemption 2 | Sim | Sim | Não configurado | Instalação manual para Vulkan |
| Call of Duty: MW2 (2009) | Sim | Não configurado | Não configurado | Não configurado |
| Call of Duty: Black Ops II | Sim | Não configurado | Não configurado | Não configurado |
| Call of Duty: MW3 (2011) | Sim | Não configurado | Não configurado | Não configurado |

**Legenda:** Sim = recurso cadastrado; Parcial = implementação incompleta; Bloqueado = recurso desabilitado por segurança; Não configurado = recurso ainda não disponível nesse módulo.

> O monitor de FPS reconhece processos cadastrados em `monitor.py`. **A escolha de um jogo na interface não filtra necessariamente qual processo o monitor detectará na versão atual.**

---

## Tecnologias utilizadas

| Camada | Tecnologias | Aplicação |
|---|---|---|
| Linguagem | **Python** | Lógica de aplicação e integração com Windows |
| Interface | **Tkinter, ttk** | Janelas, abas, menus e controles |
| Orquestração | **LangGraph** | Grafo de estados do agente |
| LLM | **LangChain, langchain-groq, Groq** | Recomendações em linguagem natural |
| Monitoramento | **PresentMon, ETW** | Captura de tempos entre quadros e FPS |
| Processos/recursos | **psutil** | CPU, RAM, processos e gerenciamento |
| Hardware/SO | **PowerShell, CIM/WMI, winreg, ctypes** | Consulta e ajustes no Windows |
| Gráficos | **ReShade, shader CAS** | Nitidez de pós-processamento |
| Persistência | **JSON, arquivos `.ini`, `.cfg` e configurações de jogos** | Preferências, presets e backups |
| Automação | **GitHub Actions** | Pipeline de análise e empacotamento |
| Distribuição experimental | **PyInstaller** | Tentativa de geração de `.exe` |

**Observação:** não há implementação de PostgreSQL, RAG ou treinamento de modelo próprio nos arquivos principais examinados. A base de pontuações de hardware é atualmente definida em estruturas Python.

---

## Instalação e execução

### Pré-requisitos

- **Windows 10 ou 11** (o código utiliza APIs específicas do Windows).
- **Python 3.11** recomendado, pois é a versão declarada no workflow existente.
- **Git**, para clonar o repositório.
- Conexão com a internet para chamadas à **Groq** e eventuais downloads de componentes do ReShade.
- Permissões administrativas ou equivalentes para algumas medições e otimizações de sistema.
- Jogos e arquivos de configuração compatíveis instalados localmente.

### 1. Clone o repositório

```powershell
git clone https://github.com/felipeantoniofox/RodaLiso-.git
cd RodaLiso-
```

### 2. Crie e ative um ambiente virtual

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Se a política de execução do PowerShell impedir a ativação, use o terminal `cmd` com `.venv\Scripts\activate.bat` ou invoque diretamente `.venv\Scripts\python.exe`.

### 3. Instale as dependências Python

A versão inspecionada **ainda não inclui um arquivo `requirements.txt`** na raiz. Instale as dependências externas identificadas pelos imports:

```powershell
python -m pip install --upgrade pip
python -m pip install psutil langgraph langchain-core langchain-groq python-dotenv
```

`tkinter`, `csv`, `ctypes`, `configparser`, `json`, `subprocess`, `urllib`, `zipfile` e outras bibliotecas da biblioteca padrão são utilizadas pelo projeto e não exigem instalação individual por `pip` em uma instalação comum de Python para Windows. Verifique se o seu Python inclui suporte ao Tk.

### 4. Configure o acesso à IA

Crie um arquivo chamado **`api.env`** na raiz do repositório:

```dotenv
GROQ_API_KEY=sua_chave_da_groq_aqui
GROQ_MODEL=openai/gpt-oss-20b
```

Obtenha uma chave no [Groq Console](https://console.groq.com/). O arquivo é carregado em `agent.py` por `python-dotenv`.

**Nunca publique sua chave no GitHub.** O `.gitignore` atual contém uma entrada para `api.env`; confira também os arquivos preparados para commit com `git status` antes de enviar alterações.

> A chamada de IA exige chave válida e acesso ao modelo escolhido. Recursos que dependem do agente podem falhar sem essa configuração.

### 5. Execute a aplicação

```powershell
python roda_liso.py
```

Para o monitoramento de FPS, o repositório inclui `PresentMon.exe` na raiz, onde `fps_presentmon.py` espera encontrá-lo. Caso o monitor retorne falhas de ETW, confirme as permissões do Windows e a compatibilidade do executável.

### 6. Permissões para recursos avançados

Para ações no Registro do Windows, serviços, remoção de componentes e certas medições, talvez seja necessário iniciar o terminal ou aplicativo **como administrador**. Use essas permissões apenas quando realmente precisar do recurso e compreender seus efeitos.

---

## Como usar

<details>
<summary><strong>Fazer um diagnóstico do PC</strong></summary>

1. Abra a aba **Diagnóstico**.
2. Confira os componentes identificados ou selecione CPU, GPU e RAM.
3. Selecione um jogo disponível.
4. Clique em **Verificar Compatibilidade**.
5. Leia o resultado como uma **estimativa heurística**, não como benchmark.

</details>

<details>
<summary><strong>Aplicar um preset gráfico</strong></summary>

1. Abra **Empurrãozinho**.
2. Escolha um jogo que tenha níveis disponíveis (atualmente, The Witcher 3).
3. Selecione o nível de qualidade.
4. Revise a alteração e aplique o preset.
5. Se a localização automática falhar, escolha manualmente o arquivo original.
6. Use **Reverter** para recuperar o backup salvo, quando disponível.

**Recomendação:** feche o jogo e faça uma cópia adicional da configuração antes de alterá-la.

</details>

<details>
<summary><strong>Ativar o agente de IA</strong></summary>

1. Configure `api.env` e confirme a disponibilidade do PresentMon.
2. Abra **Agente de IA**.
3. Selecione o jogo desejado na interface e a meta de FPS.
4. Se desejar, habilite a opção de nitidez e escolha uma intensidade.
5. Clique em **Ativar Agente** e inicie um jogo reconhecido pelo monitor.
6. Aguarde o período inicial de aquecimento e as medições.
7. Em caso de desempenho insuficiente persistente, analise a recomendação.
8. **Aceite ou recuse** a aplicação do preset.
9. Utilize **Pausar Agente** para interromper novas leituras e sugestões.

**Importante:** a detecção do processo, os presets e os atalhos de reinício não são equivalentes para todos os jogos. **Salvar o jogo antes de aprovar uma alteração é essencial.**

</details>

<details>
<summary><strong>Ativar ou remover nitidez</strong></summary>

1. Abra a aba **Agente de IA**.
2. Selecione um jogo cadastrado e o nível de nitidez.
3. Utilize o controle de aplicação do filtro.
4. Se o ReShade não estiver disponível e a API do jogo for compatível, o programa pode oferecer a instalação.
5. Para desfazer, use a opção de remoção do filtro.

**Atenção:** efeitos que se integram ao renderizador podem ser incompatíveis com jogos online, anticheats ou outros injetores. O projeto bloqueia CS 2 para esse recurso.

</details>

<details>
<summary><strong>Usar o otimizador do Windows</strong></summary>

1. Abra **Otimizador de SO**.
2. Leia a descrição, impactos negativos e nível de risco de cada opção.
3. Considere criar um ponto de restauração antes de modificar o Windows.
4. Selecione apenas as alterações que compreende.
5. Aplique as opções desejadas e confira o status.
6. Use a reversão se precisar restaurar o estado anterior, lembrando que remoções de aplicativos podem exigir reinstalação.

**Não aplique indiscriminadamente todos os ajustes, especialmente os classificados como avançados.**

</details>

---

## Arquitetura e fluxo da IA

### Visão dos componentes

| Componente | Responsabilidade | Integração principal |
|---|---|---|
| `roda_liso.py` | Interface principal, seleção de jogos e comandos do usuário. | `monitor.py`, `tema.py` e otimizador do Windows. |
| `monitor.py` | Detecta processos e acompanha o desempenho do jogo. | `fps_presentmon.py` e `otimizador_recursos.py`. |
| `fps_presentmon.py` | Captura tempos entre quadros e calcula o FPS médio. | PresentMon e arquivos CSV temporários. |
| `otimizador_recursos.py` | Identifica uso elevado de CPU ou RAM e solicita autorização para fechar aplicativos. | `psutil` e recursos do Windows. |
| `agent.py` | Coordena a análise de desempenho e a solicitação de autorização. | LangGraph, Groq e `tools.py`. |
| `tools.py` | Realiza backup e aplica arquivos de presets gráficos. | Arquivos de configuração de cada jogo. |
| `nitidez.py` | Configura o filtro CAS e gerencia a integração com ReShade. | ReShade e shaders. |
| `otimizador_so.py` | Aplica e tenta reverter ajustes do sistema operacional. | Registro, serviços e PowerShell. |

### Fluxo do agente de IA

| Etapa | Módulo ou ação | O que acontece |
|:---:|---|---|
| 1 | Interface | O usuário ativa o agente e define a meta de FPS. |
| 2 | `monitor.py` | O aplicativo localiza um jogo compatível em execução. |
| 3 | `fps_presentmon.py` | O PresentMon captura dados de quadros e calcula o FPS. |
| 4 | Verificação de desempenho | O monitor compara o FPS capturado com a meta configurada. |
| 5 | Detecção de queda | Caso a taxa fique abaixo da meta pelo período configurado, o agente é acionado. |
| 6 | `calcular_deficit` | Calcula o déficit percentual e verifica a qualidade gráfica atual, quando possível. |
| 7 | `sugerir_otimizacao` | Consulta o modelo para gerar a explicação e usa regras Python para escolher o preset. |
| 8 | `notificar_windows` | Solicita aprovação do usuário para alterar a configuração. |
| 9A | Usuário recusa | O fluxo termina sem aplicar alterações. |
| 9B | Usuário aprova | O fluxo chama `executar_mudancas`. |
| 10 | `executar_mudancas` | Aplica backup e preset; opcionalmente ajusta a nitidez e tenta reiniciar o jogo. |
| 11 | Encerramento | Registra o resultado da execução. |

### Estados do LangGraph

| Estado | Entrada | Saída / próxima etapa |
|---|---|---|
| `calcular_deficit` | Telemetria e meta de FPS. | Déficit e qualidade atual; continua para `sugerir_otimizacao`. |
| `sugerir_otimizacao` | Déficit, qualidade atual e presets. | Texto de recomendação e preset escolhido; continua para `notificar_windows`. |
| `notificar_windows` | Recomendação e dados do jogo. | Resposta do usuário; passa para a verificação de autorização. |
| `checar_autorizacao` | Resposta do usuário. | Se aprovada, executa mudanças; caso contrário, encerra. |
| `executar_mudancas` | Preset escolhido e autorização. | Status da aplicação; encerra o fluxo. |

O estado compartilhado `RodalisoState` armazena telemetria, déficit percentual, qualidade atual, recomendação, aprovação e status final.

**Fórmula utilizada para o déficit:**

```text
deficit (%) = max(0, (FPS_alvo - FPS_atual) / FPS_alvo × 100)
```

> A regra de escolha de preset tem limites fixos no `agent.py`. O uso de um LLM **não significa que ele execute comandos arbitrários**: a aplicação de configurações passa pelas funções existentes em `tools.py`.

### Principais arquivos

```text
RodaLiso-/
├── roda_liso.py               # Janela principal; diagnóstico e abas
├── agent.py                   # Estados, regras e integração com o LLM
├── monitor.py                 # Detecção de jogos e loop de monitoramento
├── fps_presentmon.py          # Captura de FPS via PresentMon
├── tools.py                   # Backups, presets e utilidades de processos
├── confirmacao.py             # Confirmação nativa do Windows
├── otimizador_recursos.py     # Sugestões de liberação de CPU/RAM
├── otimizador_so.py           # Painel de ajustes do Windows
├── nitidez.py                 # ReShade e nitidez CAS
├── tema.py                    # Temas, estilos e componentes da interface
├── PresentMon.exe             # Ferramenta externa incluída no repositório
├── capas/                     # Imagens de jogos
├── presets/                   # Arquivos de configurações por nível
├── shaders/                   # Arquivos de efeitos gráficos
├── Rodaliso_Backups/          # Backups de configurações
├── rodaliso_tema.json         # Preferência de tema
├── rodaliso_nitidez.json      # Estado do filtro de nitidez
├── rodaliso_so_backup.json    # Snapshots para reversão de ajustes do SO
├── .github/workflows/
│   └── devsecops.yml          # Workflow de segurança e build
└── ...                        # Pastas históricas, experimentos e arquivos de apoio
```

**Nota para contribuidores:** pastas históricas, backups e JSONs de estado são mantidos no repositório atual, mas não são todos necessários como fonte da aplicação. Uma separação entre código, dados de exemplo e dados locais facilitará a manutenção.

---

## Segurança e reversão

O projeto inclui mecanismos de proteção, mas também realiza ações potencialmente invasivas. Antes de usar:

1. **Salve seus jogos e documentos** antes de permitir o fechamento de processos.
2. **Faça backup de configurações**; os backups automáticos dependem de caminhos e permissões válidos.
3. **Não compartilhe `api.env`** nem chaves de API.
4. **Revise alterações no Windows**: Registro, serviços e aplicativos podem ser afetados.
5. **Respeite anticheats e regras de jogos online**; instalar filtros de terceiros pode causar conflitos ou penalidades.
6. **Prefira alterações graduais**, medindo FPS, frametime e estabilidade antes e depois.
7. **Não interprete estimativas de RAM como ganhos garantidos.**

| Ação | Reversão prevista | Observação |
|---|---|---|
| Preset manual | Backup do arquivo original | Depende da cópia ter sido gerada e mantida. |
| Preset via agente | Backup em `Rodaliso_Backups/` | O jogo pode ser encerrado durante a aplicação. |
| Nitidez CAS | Restauração de preset/configuração anterior | Dependência do estado salvo e da instalação do ReShade. |
| Políticas/serviços do Windows | Snapshot de valores anteriores | Requer privilégios, e o resultado depende do Windows. |
| Remoção de aplicativos do Windows | Reinstalação ou recuperação parcial | Pode exigir internet, Store, `winget` ou reparo. |

---

## Integração contínua (DevSecOps)

Existe um workflow em `.github/workflows/devsecops.yml` que, em pushes para `main`/`master`:

1. Obtém o código por `actions/checkout`.
2. Prepara Python **3.11**.
3. Instala ferramentas de análise **Bandit**, **Safety** e **PyInstaller**.
4. Executa uma verificação estática com Bandit.
5. Executa uma verificação de dependências com Safety.
6. Escreve a variável `GROQ_API_KEY` a partir de um **GitHub Actions Secret** no arquivo `api.env`.
7. Tenta gerar um executável com PyInstaller.
8. Envia artefatos da pasta `dist/` para o workflow.

Acompanhe em [**Actions: RodaLiso**](https://github.com/felipeantoniofox/RodaLiso-/actions).

> **Status de maturidade:** as etapas de segurança e build usam `continue-on-error: true`; o workflow **não garante** que os testes tenham passado ou que o `.exe` inclua todos os arquivos auxiliares. O empacotamento precisa considerar `PresentMon.exe`, presets, recursos estáticos e demais dependências de execução. Não há suíte de testes automatizados própria identificada na versão examinada.

---

## Roadmap e oportunidades

Abaixo estão **ideias para evolução**, e **não funcionalidades prometidas como prontas**:

- [ ] Criar `requirements.txt` ou `pyproject.toml` com versões controladas.
- [ ] Adicionar instalador/empacotamento que inclua todos os recursos necessários.
- [ ] Separar arquivos de estado e backups da pasta de código e do controle de versão.
- [ ] Adicionar testes automatizados para regras, caminhos, presets e reversões.
- [ ] Ampliar jogos com presets reais e validados.
- [ ] Fazer a seleção da interface filtrar explicitamente o jogo monitorado.
- [ ] Medir FPS médio, **1% low**, frametime e variação antes/depois de ajustes.
- [ ] Adicionar histórico de benchmarks reproduzíveis e comparações.
- [ ] Aprimorar o tratamento de exceções e mensagens de falha de cada integração.
- [ ] Revisar o risco de alterações agressivas do Windows e exigir confirmações adequadas.
- [ ] Criar documentação de contribuição e capturas reais da interface.

---

## Como contribuir

Sugestões, correções e melhorias podem ser discutidas por meio de [**Issues**](https://github.com/felipeantoniofox/RodaLiso-/issues) e [**Pull Requests**](https://github.com/felipeantoniofox/RodaLiso-/pulls).

Ao propor uma mudança, procure informar:

- Versão do Windows e do Python;
- Jogo, versão e launcher utilizados, quando aplicável;
- Hardware, drivers e etapas para reproduzir o comportamento;
- Logs e mensagens de erro **sem chaves de API, tokens ou dados pessoais**;
- Efeito esperado versus resultado observado;
- Como a alteração foi testada e revertida.

---

## Perguntas frequentes

<details>
<summary><strong>O Roda Liso aumenta FPS automaticamente em qualquer jogo?</strong></summary>

Não. O monitoramento reconhece um conjunto específico de executáveis e a aplicação de presets depende de arquivos cadastrados. Ganhos de desempenho não são garantidos.

</details>

<details>
<summary><strong>Preciso de internet para usar o programa?</strong></summary>

Nem todas as abas exigem internet. As recomendações por LLM dependem do acesso à Groq; instalações e links externos também podem precisar de conexão.

</details>

<details>
<summary><strong>O agente de IA toma decisões sem minha autorização?</strong></summary>

O fluxo de aplicação de presets possui uma etapa de confirmação antes das alterações. Entretanto, outras ações da interface podem modificar arquivos ou o Windows quando acionadas pelo usuário; revise cada operação.

</details>

<details>
<summary><strong>O filtro CAS é o FSR 1.0 completo?</strong></summary>

Não. Ele realiza nitidez pós-processada e não implementa, sozinho, a ampliação de resolução (upscaling) do FSR 1.0.

</details>

<details>
<summary><strong>Posso usar o projeto em Linux ou macOS?</strong></summary>

A implementação atual é direcionada ao Windows e utiliza ETW, Registro, PowerShell e APIs específicas desse sistema. Não há suporte multiplataforma demonstrado.

</details>

<details>
<summary><strong>O projeto utiliza um banco PostgreSQL ou RAG?</strong></summary>

Não nos módulos principais atualmente presentes. As pontuações de hardware são cadastradas no Python, enquanto preferências e snapshots usam JSON. A IA consome um modelo externo por API.

</details>

---

## Referências e ferramentas de terceiros

- [Python](https://www.python.org/): linguagem de programação.
- [LangGraph](https://github.com/langchain-ai/langgraph): orquestração de agentes e estados.
- [LangChain](https://python.langchain.com/): componentes de integração com modelos.
- [Groq](https://groq.com/): serviço de inferência.
- [Intel PresentMon](https://github.com/GameTechDev/PresentMon): ferramenta de análise de apresentação de quadros.
- [ReShade](https://reshade.me/): plataforma de pós-processamento gráfico.
- [AMD FidelityFX](https://gpuopen.com/fidelityfx/): família de tecnologias gráficas.
- [psutil](https://github.com/giampaolo/psutil): informações de recursos e processos.
- [DXVK](https://github.com/doitsujin/dxvk): camada Direct3D/Vulkan citada nos tutoriais e configurações.

**Marcas, jogos e ferramentas mencionados pertencem a seus respectivos titulares.** As integrações com terceiros não implicam endosso oficial.

### Licenciamento

No momento da elaboração deste README, **não havia um arquivo `LICENSE` identificado na raiz do repositório**. Antes de redistribuir ou aceitar contribuições com regras claras, recomenda-se escolher e adicionar uma licença apropriada e revisar as licenças de componentes de terceiros.

---

<div align="center">

### Mais controle. Mais informação. Ajustes conscientes.

**Roda Liso: Performance Hub**

Desenvolvido como projeto de software para explorar **diagnóstico, monitoramento, otimização e integração de IA** na experiência de jogos para PC.

[Voltar ao topo](#roda-liso)

</div>
