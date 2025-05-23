
import tkinter as tk
from tkinter import ttk
import plotly.express as px
import os
import subprocess
import webbrowser
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket

# --- 1. Criar o Gráfico Plotly ---
# Carrega o conjunto de dados 'iris' do Plotly, um conjunto de dados clássico para classificação.
df = px.data.iris()
# Cria um gráfico de dispersão interativo usando Plotly Express.
# 'sepal_width' no eixo X, 'sepal_length' no eixo Y, e as cores são baseadas na 'species'.
# O título do gráfico é "Gráfico Interativo Iris".
fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species",
                 title="Gráfico Interativo Iris")

# --- 2. Configurações de arquivo ---
# Obtém o diretório atual do script em execução.
current_dir = os.path.dirname(os.path.abspath(__file__))
# Define o nome do arquivo HTML onde o gráfico Plotly será salvo.
html_file_name = "plotly_graph_webview.html"
# Constrói o caminho completo para o arquivo HTML.
html_file_path = os.path.join(current_dir, html_file_name)

def generate_plotly_html():
    """Gera o arquivo HTML do gráfico Plotly"""
    print(f"Tentando salvar o gráfico em: {html_file_path}")
    try:
        # Salva o objeto 'fig' (o gráfico Plotly) como um arquivo HTML.
        # 'auto_open=False' impede que o navegador abra automaticamente após a gravação.
        fig.write_html(html_file_path, auto_open=False)
        print(f"Arquivo HTML '{html_file_path}' salvo com sucesso.")
        # Verifica se o arquivo realmente existe após a tentativa de gravação.
        if not os.path.exists(html_file_path):
            print(f"ERRO: O arquivo HTML não foi encontrado em {html_file_path} após a escrita.")
            return False
        return True
    except Exception as e:
        # Captura e imprime quaisquer erros que ocorram durante a gravação do arquivo.
        print(f"ERRO ao salvar o arquivo HTML: {e}")
        return False

def find_free_port():
    """Encontra uma porta livre para o servidor HTTP"""
    # Cria um socket temporário para encontrar uma porta disponível.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Liga o socket a um endereço IP vazio (localhost) e a uma porta 0, que significa
        # que o sistema operacional irá atribuir uma porta livre.
        s.bind(('', 0))
        # Começa a escutar por conexões (apenas uma, pois é temporário).
        s.listen(1)
        # Retorna o número da porta atribuída.
        port = s.getsockname()[1]
    return port

class LocalHTTPServer:
    """Servidor HTTP local para servir os arquivos HTML"""
    def __init__(self):
        self.server = None  # Objeto do servidor HTTP.
        self.server_thread = None  # Thread onde o servidor será executado.
        self.port = find_free_port()  # Encontra uma porta livre para o servidor.
        self.running = False  # Flag para indicar se o servidor está rodando.

    def start_server(self):
        """Inicia o servidor HTTP local"""
        if self.running:
            # Se o servidor já estiver rodando, retorna a URL existente.
            return f"http://localhost:{self.port}/{html_file_name}"

        try:
            # Muda o diretório de trabalho atual para o diretório onde o arquivo HTML está.
            # Isso é importante para que o SimpleHTTPRequestHandler encontre o arquivo.
            os.chdir(current_dir)

            # Cria uma instância do servidor HTTP na porta encontrada, usando SimpleHTTPRequestHandler
            # para servir arquivos estáticos do diretório atual.
            self.server = HTTPServer(('localhost', self.port), SimpleHTTPRequestHandler)

            def run_server():
                """Função que será executada na thread do servidor."""
                print(f"[HTTP Server] Iniciando servidor na porta {self.port}")
                self.running = True
                # Inicia o servidor e o mantém rodando indefinidamente.
                self.server.serve_forever()

            # Cria uma nova thread para executar o servidor.
            # 'daemon=True' faz com que a thread seja encerrada automaticamente quando o programa principal termina.
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()

            # Aguarda um pequeno período para garantir que o servidor tenha tempo para inicializar.
            time.sleep(0.5)

            # Constrói a URL completa para o arquivo HTML no servidor local.
            url = f"http://localhost:{self.port}/{html_file_name}"
            print(f"[HTTP Server] Servidor iniciado em: {url}")
            return url

        except Exception as e:
            # Captura e imprime erros que ocorram durante a inicialização do servidor.
            print(f"[HTTP Server] Erro ao iniciar servidor: {e}")
            return None

    def stop_server(self):
        """Para o servidor HTTP"""
        if self.server and self.running:
            print("[HTTP Server] Parando servidor...")
            # Encerra o servidor de forma graciosa.
            self.server.shutdown()
            # Fecha as conexões do servidor.
            self.server.server_close()
            self.running = False

class WebViewManager:
    """Gerencia diferentes métodos de visualização web"""
    def __init__(self):
        self.http_server = LocalHTTPServer()  # Instância do servidor HTTP local.
        self.webview_process = None  # Variável para armazenar o processo do PyWebView (se usado).
        self.method = "browser"  # Método de visualização padrão: "browser", "webview_process" ou "webview_separate".

    def show_graph_browser(self, url):
        """Abre o gráfico no navegador padrão"""
        try:
            print(f"[WebView Manager] Abrindo no navegador: {url}")
            # Abre a URL no navegador web padrão do sistema.
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"[WebView Manager] Erro ao abrir navegador: {e}")
            return False

    def show_graph_webview_process(self, url):
        """Abre o gráfico em um processo separado do PyWebView"""
        try:
            # Cria um script Python temporário que irá usar PyWebView para exibir a URL.
            # O encoding é especificado para evitar problemas em diferentes sistemas.
            webview_script = f'''# -*- coding: utf-8 -*-
import webview
import sys

try:
    webview.create_window("Gráfico Plotly", "{url}", width=800, height=600)
    webview.start(debug=False)
except Exception as e:
    print(f"Erro no WebView: {{e}}")
    sys.exit(1)
'''
            # Define o caminho para o script temporário.
            script_path = os.path.join(current_dir, "temp_webview.py")
            # Salva o conteúdo do script temporário no arquivo.
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(webview_script)

            # Executa o script PyWebView em um processo separado usando subprocess.Popen.
            print(f"[WebView Manager] Iniciando PyWebView em processo separado")
            self.webview_process = subprocess.Popen([
                'python', script_path
            ], cwd=current_dir,
            # 'creationflags' é específico para Windows para criar uma nova janela de console,
            # tornando o processo mais independente.
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)

            return True

        except Exception as e:
            print(f"[WebView Manager] Erro ao iniciar processo WebView: {e}")
            return False

    def show_graph_webview_separate(self):
        """Abre o PyWebView usando uma abordagem de alternância melhorada.
        Isso minimiza a janela Tkinter e a restaura após o fechamento do WebView."""
        try:
            print("[WebView Manager] Modo WebView alternado - preparando...")

            # Inicia o servidor HTTP para obter a URL do gráfico.
            url = self.http_server.start_server()
            if not url:
                print("[WebView Manager] Erro ao iniciar servidor HTTP")
                return False

            # Função que será executada após um pequeno atraso para iniciar o PyWebView.
            def delayed_webview():
                try:
                    print("[WebView Manager] Iniciando PyWebView...")
                    # Importa PyWebView aqui para evitar importações globais que possam interferir.
                    import webview

                    # Cria a janela PyWebView.
                    window = webview.create_window(
                        "Gráfico Plotly - PyWebView",
                        url,
                        width=800,
                        height=600,
                        resizable=True
                    )

                    # Inicia o loop principal do PyWebView.
                    webview.start(debug=False)

                except Exception as e:
                    print(f"[WebView Manager] Erro no WebView: {e}")
                finally:
                    # Após o fechamento do PyWebView, reagenda a restauração da janela Tkinter.
                    print("[WebView Manager] WebView fechado, restaurando Tkinter...")
                    root.after(100, root.deiconify) # 'deiconify' restaura a janela.

            # Minimiza a janela Tkinter antes de iniciar o PyWebView.
            root.withdraw() # 'withdraw' oculta a janela.
            print("[WebView Manager] Tkinter minimizado")

            # Agenda a execução da função 'delayed_webview' após 500ms.
            # Isso dá tempo para a janela Tkinter ser minimizada antes do PyWebView ser iniciado.
            root.after(500, delayed_webview)

            return True

        except Exception as e:
            print(f"[WebView Manager] Erro no modo alternado: {e}")
            root.deiconify()  # Restaura a janela Tkinter em caso de erro.
            return False

    def show_graph(self):
        """Mostra o gráfico usando o método selecionado"""
        # Verifica se o arquivo HTML do gráfico existe; se não, tenta gerá-lo.
        if not os.path.exists(html_file_path):
            if not generate_plotly_html():
                print("[WebView Manager] Falha ao gerar HTML do gráfico.")
                return False

        # Com base no método selecionado, chama a função apropriada.
        if self.method == "browser":
            # Inicia o servidor HTTP e, se bem-sucedido, abre no navegador.
            url = self.http_server.start_server()
            if url:
                return self.show_graph_browser(url)

        elif self.method == "webview_process":
            # Inicia o servidor HTTP e, se bem-sucedido, abre PyWebView em processo separado.
            url = self.http_server.start_server()
            if url:
                return self.show_graph_webview_process(url)

        elif self.method == "webview_separate":
            # Chama a função para o modo WebView alternado.
            return self.show_graph_webview_separate()

        return False

    def set_method(self, method):
        """Define o método de visualização"""
        self.method = method
        print(f"[WebView Manager] Método alterado para: {method}")

    def cleanup(self):
        """Limpa recursos: para o servidor HTTP e encerra processos PyWebView"""
        self.http_server.stop_server()
        if self.webview_process:
            try:
                # Tenta encerrar o processo PyWebView.
                self.webview_process.terminate()
            except:
                pass

        # Remove o script temporário do PyWebView, se existir.
        temp_script = os.path.join(current_dir, "temp_webview.py")
        if os.path.exists(temp_script):
            try:
                os.remove(temp_script)
            except:
                pass

# Instância global do gerenciador de WebView.
# Isso permite que as funções da GUI interajam com ele.
webview_manager = WebViewManager()

def handle_show_graph_button():
    """Manipula o clique do botão para mostrar o gráfico"""
    print("[Tkinter] Botão de mostrar gráfico clicado")
    # Atualiza o status na GUI.
    update_status("Carregando gráfico...")

    # Tenta mostrar o gráfico usando o método selecionado.
    success = webview_manager.show_graph()
    if success:
        update_status(f"Gráfico aberto - Método: {webview_manager.method}")
    else:
        update_status("Erro ao abrir gráfico")

def handle_method_change():
    """Muda o método de visualização quando um Radiobutton é selecionado."""
    method = method_var.get()  # Obtém o valor selecionado do Radiobutton.
    webview_manager.set_method(method)  # Define o método no gerenciador.
    update_status(f"Método alterado: {method}")

# --- Configurar a Janela Tkinter ---
root = tk.Tk()  # Cria a janela principal do Tkinter.
root.title("JANELA TKINTER PRINCIPAL - Múltiplos Métodos WebView")  # Define o título da janela.
root.geometry("500x450")  # Define o tamanho inicial da janela.
root.configure(bg='lightblue')  # Define a cor de fundo da janela.

# Labels informativos para a interface.
title_label = tk.Label(
    root,
    text="Tkinter + Plotly + WebView\n(Múltiplas Soluções)",
    bg='lightblue',
    fg='navy',
    font=("Arial", 14, "bold")
)
title_label.pack(pady=10) # Adiciona um espaçamento vertical.

info_label = tk.Label(
    root,
    text="Esta janela permanece responsiva!\nEscolha um método de visualização:",
    bg='lightblue',
    fg='black',
    font=("Arial", 10),
    wraplength=450 # Permite que o texto quebre linhas.
)
info_label.pack(pady=(0, 15)) # Adiciona um espaçamento vertical.

# Frame para seleção de método.
method_frame = tk.LabelFrame(root, text="Método de Visualização", bg='lightblue', fg='navy')
method_frame.pack(pady=10, padx=20, fill='x') # Preenche horizontalmente e adiciona preenchimento.

method_var = tk.StringVar(value="browser") # Variável de controle para os Radiobuttons, padrão é "browser".

# Radiobuttons para selecionar o método de visualização.
# Cada um chama 'handle_method_change' quando selecionado.
rb1 = tk.Radiobutton(method_frame, text="Navegador Padrão (Recomendado)",
                     variable=method_var, value="browser", bg='lightblue',
                     command=handle_method_change)
rb1.pack(anchor='w', padx=10, pady=2) # Alinha à esquerda e adiciona preenchimento.

rb2 = tk.Radiobutton(method_frame, text="PyWebView em Processo Separado",
                     variable=method_var, value="webview_process", bg='lightblue',
                     command=handle_method_change)
rb2.pack(anchor='w', padx=10, pady=2)

rb3 = tk.Radiobutton(method_frame, text="PyWebView Alternado (Fecha Tkinter temporariamente)",
                     variable=method_var, value="webview_separate", bg='lightblue',
                     command=handle_method_change)
rb3.pack(anchor='w', padx=10, pady=2)

# Frame para botões principais.
button_frame = tk.Frame(root, bg='lightblue')
button_frame.pack(pady=20)

# Botão para mostrar o gráfico.
btn_show_graph = ttk.Button(
    button_frame,
    text="📊 Mostrar Gráfico Interativo",
    command=handle_show_graph_button, # Chama a função ao clicar.
    width=25
)
btn_show_graph.pack(pady=5)

# Botão de teste de responsividade.
# Simplesmente imprime uma mensagem e atualiza o status.
test_button = ttk.Button(
    button_frame,
    text="🔍 Teste de Responsividade",
    command=lambda: (print("[Tkinter] Interface totalmente responsiva!"),
                     update_status("Interface funcionando perfeitamente!")),
    width=25
)
test_button.pack(pady=5)

# Função para gerar um novo gráfico com dados diferentes.
def generate_new_graph():
    """Gera um novo gráfico com dados diferentes"""
    global fig # Declara que 'fig' é uma variável global para modificá-la.
    # Usa um conjunto de dados diferente do Plotly ('tips').
    df_new = px.data.tips()
    # Cria um novo gráfico de dispersão.
    fig = px.scatter(df_new, x="total_bill", y="tip", color="day",
                     title="Gráfico de Gorjetas por Conta Total")
    # Tenta gerar o HTML do novo gráfico.
    if generate_plotly_html():
        update_status("Novo gráfico gerado!")
    else:
        update_status("Erro ao gerar novo gráfico")

# Botão para gerar um novo gráfico.
btn_new_graph = ttk.Button(
    button_frame,
    text="🔄 Gerar Novo Gráfico",
    command=generate_new_graph, # Chama a função para gerar novo gráfico.
    width=25
)
btn_new_graph.pack(pady=5)

# Label de status na parte inferior da interface.
status_label = tk.Label(
    root,
    text="Status: Pronto",
    bg='lightblue',
    fg='darkgreen',
    font=("Arial", 10, "bold"),
    relief='sunken', # Estilo de borda.
    bd=1 # Largura da borda.
)
status_label.pack(pady=15, padx=20, fill='x') # Preenche horizontalmente.

def update_status(message):
    """Atualiza o status na interface"""
    status_label.config(text=f"Status: {message}")
    root.update_idletasks() # Força a atualização imediata da GUI.

# Frame para informações sobre os métodos.
info_frame = tk.LabelFrame(root, text="Informações dos Métodos", bg='lightblue', fg='navy')
info_frame.pack(pady=10, padx=20, fill='both', expand=True) # Preenche e expande.

# Widget Text para exibir informações detalhadas.
info_text = tk.Text(info_frame, height=6, wrap=tk.WORD, bg='white', fg='black', font=("Arial", 9))
info_text.pack(padx=5, pady=5, fill='both', expand=True)

# Conteúdo informativo para o widget Text.
info_content = """
• Navegador Padrão: Abre o gráfico no seu navegador (Chrome, Firefox, etc.) - Mais estável ✅
• PyWebView Processo: Cria uma janela PyWebView em processo separado - Boa integração
• PyWebView Alternado: Fecha Tkinter temporariamente e abre PyWebView - Experimental

Recomendação: Use "Navegador Padrão" para máxima estabilidade!
O método do navegador está funcionando perfeitamente! 🎉
"""

# Insere o conteúdo no widget Text e o torna somente leitura.
info_text.insert('1.0', info_content)
info_text.config(state='disabled')

# --- Protocolo de Fechamento do Tkinter ---
def on_tkinter_closing():
    """Função chamada quando a janela Tkinter é fechada."""
    print("[Tkinter] Fechando a aplicação...")
    update_status("Encerrando...")

    # Limpa todos os recursos gerenciados (servidor HTTP, processos WebView).
    webview_manager.cleanup()

    root.destroy() # Destrói a janela principal do Tkinter, encerrando a aplicação.

# Associa a função 'on_tkinter_closing' ao evento de fechamento da janela (protocolo WM_DELETE_WINDOW).
root.protocol("WM_DELETE_WINDOW", on_tkinter_closing)

# --- Ponto Principal da Execução ---
if __name__ == "__main__":
    print("[Tkinter] Gerando arquivo HTML inicial...")
    # Tenta gerar o arquivo HTML inicial do gráfico.
    if not generate_plotly_html():
        print("[Tkinter] Falha ao gerar o arquivo HTML inicial.")
        update_status("Erro ao gerar HTML inicial")
    else:
        update_status("Pronto - Selecione um método e clique em 'Mostrar Gráfico'")

    print("[Tkinter] Iniciando interface Tkinter...")

    # Inicia o loop principal do Tkinter. Isso mantém a janela da GUI aberta e responsiva
    # até que seja fechada pelo usuário ou pelo código.
    root.mainloop()

    print("[Tkinter] Aplicação encerrada.")
