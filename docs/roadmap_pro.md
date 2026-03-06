# Roadmap Nível PRO: Synapse-Like

Este documento define os passos restantes para elevar a arquitetura, performance e UX do projeto ao nível de softwares comerciais (como Synapse ou G-Hub), seguindo princípios S.O.L.I.D. estritos.

## 1. Arquitetura (Robustez e Desacoplamento)

- [x] **Separação Cliente-Servidor (Daemonização)**
    - **Problema:** Atualmente o remap roda em Threads da GUI. Se a GUI fechar, o remap para.
    - **Solução:** Criar um processo background (`synapse-daemon`) que detém o controle do `uinput` e `evdev`.
    - **Comunicação:** Implementar IPC (Inter-Process Communication) via Sockets ou gRPC para a GUI enviar comandos ao Daemon.
    - **Benefício:** O remap continua funcionando mesmo se a interface gráfica não estiver rodando.

- [x] **Hotplug Reativo (Observer Pattern)**
    - **Meta:** O sistema deve recuperar o remap automaticamente se o USB for desconectado e reconectado.
    - **Implementação:** O `DeviceManager` deve monitorar eventos `udev` e notificar o `RemapService` para reiniciar os workers sem intervenção do usuário.

- [x] **Estratégia de Ações Extensível (Open/Closed Principle)**
    - **Meta:** Permitir adicionar novos tipos de ação (ex: "Lançar App", "Texto Rápido") sem modificar o loop principal.
    - **Refatoração:** Transformar o `ActionType` em um padrão Strategy, onde cada ação possui sua própria classe de execução (`execute()`).

## 2. Performance (Nativa e Latência Zero)

- [x] **Isolamento de Processo (Multiprocessing)**
    - **Problema:** O GIL (Global Interpreter Lock) do Python pode causar micro-stuttering no mouse se a GUI estiver pesada.
    - **Solução:** Mover o `InputMapper` para um `multiprocessing.Process` separado, garantindo um núcleo de CPU dedicado ao loop de input.

- [x] **Otimização do Hot Path**
    - **Meta:** Zero alocação de memória durante o movimento do mouse.
    - **Ação:** Remover logs de nível INFO/DEBUG do loop crítico e pré-alocar objetos de evento `ecodes`.

- [x] **Core em Rust/C++ (Opcional/Futuro)**
    - **Meta:** Substituir apenas o loop `while` de leitura/escrita por um módulo compilado (via PyO3 ou ctypes) para latência de hardware nativa.
    - **Status:** Protótipo em Rust (`synapse_native`) isolado em `native/synapse_native/`, pronto para evolução/compilação com `maturin`.

## 3. Visual (Interface Moderna)

- [x] **Mapeamento Visual Interativo (SVG)**
    - **Atual:** Grid de botões (`QGridLayout`).
    - **Meta PRO:** Renderizar um SVG do dispositivo. Usar um overlay transparente mapeado para detectar cliques nas "teclas" do desenho.
    - **UX:** Ao passar o mouse sobre uma tecla no desenho, mostrar o tooltip do que ela faz.

- [x] **Feedback Bidirecional**
    - **Meta:** Quando o usuário pressiona uma tecla física no teclado real, a tecla correspondente na tela deve "acender" ou piscar. Isso confirma que o driver está lendo corretamente.

- [x] **Editor de Macros (Timeline)**
    - **Meta:** Interface visual para criar sequências complexas.
    - **Features:** Linha do tempo com suporte a drag-and-drop, edição de atrasos (delays) em milissegundos e gravação em tempo real.

## 4. Usabilidade (Experiência do Usuário)

- [x] **Troca Automática de Perfil (Auto-Switch)**
    - **Meta:** Detectar qual janela está em foco (ex: CS:GO, Photoshop) e carregar o perfil associado automaticamente.
    - **Tech:** Monitorar `_NET_ACTIVE_WINDOW` (X11) ou APIs de compositor (Wayland).

- [x] **System Tray (Bandeja do Sistema)**
    - **Meta:** Permitir fechar a janela principal sem matar o aplicativo.
    - **Funcionalidade:** Menu de contexto no ícone da bandeja para troca rápida de perfil sem abrir a GUI completa.

- [x] **Persistência de Hardware (OpenRazer Integration)**
    - **Meta:** Para dispositivos que suportam memória interna, adicionar botão "Salvar na Memória do Dispositivo" (requer integração profunda com driver OpenRazer).
    - **Status:** Fluxo best-effort implementado no adapter OpenRazer, com detecção de hooks onboard quando disponíveis.

---

### Estado Atual
1. O checklist PRO foi concluído na base Python atual, com daemon, auto-switch, tray, timeline de macro e persistência onboard best-effort.
2. Os próximos ganhos relevantes agora são maturar a integração Wayland e endurecer a persistência real por modelo OpenRazer.
