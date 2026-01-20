import FreeSimpleGUI as sg
from fpdf import FPDF
from datetime import datetime
import json
from pathlib import Path
import appdirs
import os
import sys
import ctypes
import re
import locale
import logging
from typing import Dict, Any
import shutil
from decimal import Decimal, ROUND_HALF_UP
import requests 
import webbrowser 

# ========== CONFIGURAÇÃO INICIAL ==========
# Configuração de locale para formatação de moeda
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, '')

# Configuração de logging
log_dir = os.path.join(appdirs.user_config_dir("Eurocar"), "logs")
os.makedirs(log_dir, exist_ok=True)

log_path = os.path.join(log_dir, "eurocar.log")
logging.basicConfig(filename=log_path, level=logging.ERROR)

# ========== CONFIGURAÇÃO DO ÍCONE ==========
if getattr(sys, 'frozen', False):
    icon_path = os.path.join(sys._MEIPASS, 'assets', 'icone.ico')
else:
    icon_path = os.path.join('assets', 'icone.ico')

# Força o ícone na barra de tarefas (Windows apenas)
if sys.platform == "win32":
    myappid = 'sua.empresa.app.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# ========== CLASSE DE CONFIGURAÇÕES ==========
class ConfigManager:
    _instance = None
    # Usar appdirs para obter o local correto de configurações
    _config_dir = appdirs.user_config_dir("Eurocar")
    _config_file = os.path.join(_config_dir, "config.json")
    
    _default_config = {
        "paths": {
            "orcamentos_pdf": str(Path.home()),
            "orcamentos_editaveis": str(Path.home()),
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            # Garante que o diretório de configuração existe
            os.makedirs(cls._config_dir, exist_ok=True)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Carrega configurações do arquivo ou cria um novo com padrões"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self._merge_defaults()
            else:
                self.config = self._default_config.copy()
                self._save_config()
                self._create_dirs()
        except Exception as e:
            logging.error(f"Erro ao carregar configurações: {e}")
            self.config = self._default_config.copy()

    def _merge_defaults(self):
        """Mescla configurações padrão com as existentes"""
        for section, values in self._default_config.items():
            if section not in self.config:
                self.config[section] = values.copy()
            else:
                for key, value in values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value

    def _save_config(self):
        """Salva configurações no arquivo"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Erro ao salvar configurações: {e}")

    def _create_dirs(self):
        """Cria diretórios padrão se não existirem"""
        for path in self.config["paths"].values():
            os.makedirs(path, exist_ok=True)

    def get(self, section: str, key: str) -> Any:
        """Obtém um valor de configuração"""
        return self.config.get(section, {}).get(key)

    def set(self, section: str, key: str, value: Any, save: bool = True):
        """Define um valor de configuração"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        if save:
            self._save_config()

    def update_section(self, section: str, values: Dict[str, Any], save: bool = True):
        """Atualiza uma seção inteira de configurações"""
        self.config[section] = values
        if save:
            self._save_config()

    def reset_to_defaults(self):
        """Restaura configurações padrão"""
        self.config = self._default_config.copy()
        self._save_config()
        self._create_dirs()

def escolher_pastas_iniciais(config):
    layout = [
        [sg.Text("CONFIGURAÇÃO INICIAL OBRIGATÓRIA", font=("Segoe UI", 14, "bold"), 
                text_color=COR_PRIMARIA)],
        [sg.Text("Você precisa configurar as pastas antes de usar o aplicativo:", 
                pad=(0, 20))],
        
        [sg.Text("Pasta para PDF:"), 
        sg.Input(key="-PDF_PATH-", size=40, background_color='white'), 
        sg.FolderBrowse("📁", button_color=COR_PRIMARIA, size=(4,1))],
        
        [sg.Text("Pasta para Editáveis:"), 
        sg.Input(key="-EDIT_PATH-", size=40, background_color='white'), 
        sg.FolderBrowse("📁", button_color=COR_PRIMARIA, size=(4,1))],
        
        [sg.VPush()],
        [sg.Button("SALVAR", button_color=COR_BOTAO_ADD, size=(10,1), 
                pad=(10,20), bind_return_key=True),
        sg.Button("SAIR", button_color=COR_BOTAO_DEL, size=(10,1), pad=(10,20))]
    ]
    
    janela = sg.Window(
                        "Configuração Inicial - Eurocar", 
                        layout, 
                        modal=True, 
                        icon=resource_path("assets/icone.ico"),
                        element_justification='c',
                        size=(600, 300),
                        finalize=True)
    
    # Foca no primeiro input
    janela["-PDF_PATH-"].set_focus()
    
    while True:
        event, values = janela.read()
        
        if event in (sg.WINDOW_CLOSED, "SAIR"):
            sys.exit()
            
        if event == "SALVAR":
            if not all([values["-PDF_PATH-"], values["-EDIT_PATH-"]]):
                sg.popup_error("Você deve selecionar ambas as pastas!", 
                            title="Configuração Incompleta")
                continue
                
            if values["-PDF_PATH-"].lower() == values["-EDIT_PATH-"].lower():
                sg.popup_error("As pastas não podem ser iguais!", 
                            title="Configuração Inválida")
                continue
                
            try:
                # Salva as configurações
                config.update_section("paths", {
                    "orcamentos_pdf": values["-PDF_PATH-"],
                    "orcamentos_editaveis": values["-EDIT_PATH-"]
                })
                
                # Cria os diretórios
                os.makedirs(values["-PDF_PATH-"], exist_ok=True)
                os.makedirs(values["-EDIT_PATH-"], exist_ok=True)
                
                janela.close()
                return
                
            except Exception as e:
                sg.popup_error(f"ERRO AO CONFIGURAR:\n{str(e)}", 
                            title="Erro na Configuração")
                continue

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ========== PALETA DE CORES ==========
COR_FUNDO = "#1a1a1a"          # Preto escuro (quase preto) - cor de fundo principal
COR_CARTAO = "#2a2a2a"         # Cinza muito escuro - usado para "cartões" ou áreas de conteúdo
COR_PRIMARIA = "#e6b422"       # Amarelo dourado - cor primária de destaque (títulos, elementos importantes)
COR_SECUNDARIA = "#ffffff"     # Branco - usado para textos secundários
COR_TEXTO = "#f0f0f0"          # Branco levemente acinzentado - cor principal para textos
COR_TEXTO_CAIXA = "#000000"    # Preto - usado para texto dentro de caixas de input
COR_DESTAQUE = "#e6b422"       # Amarelo dourado (igual à primária) - para elementos que precisam se destacar

# Cores para feedback/status
COR_SUCESSO = "#2ecc71"        # Verde - indica sucesso 
COR_AVISO = "#f39c12"          # Laranja - indica avisos 

# Cores para botões 
COR_BOTAO_PRE_VIZUALIZAR = "#BB86FC"  # Roxo claro - botão de pré-visualização
COR_BOTAO_GERAR_PDF = "#03DAC6"       # Ciano - botão para gerar PDF
COR_BOTAO_ADD = "#4CAF50"             # Verde - botão para adicionar itens
COR_BOTAO_EDIT = "#2196F3"            # Azul - botão para editar itens
COR_BOTAO_DEL = "#F44336"             # Vermelho - botão para deletar itens
COR_BOTAO_SAIR = "#34495e"            # Azul petróleo escuro - botão de saída/cancelar
COR_BOTAO_CARREGAR = "#9C27B0"        # Roxo - botão para carregar orçamentos
COR_BOTAO_CONFIG = "#607D8B"          # Cinza azulado - botão de configurações

# Configuração do tema
sg.theme_background_color(COR_FUNDO)
sg.theme_text_element_background_color(COR_FUNDO)
sg.theme_text_color(COR_TEXTO)
sg.theme_input_background_color("#2d2d2d")
sg.theme_input_text_color(COR_TEXTO_CAIXA)
sg.theme_element_background_color(COR_CARTAO)
sg.set_options(font=("Segoe UI", 11))

# ========== CLASSE PDF ==========
class EurocarPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=25)
        self.alias_nb_pages()
        
        # Define o caminho da logo de forma confiável
        if getattr(sys, 'frozen', False):
            # Se estiver rodando como executável compilado
            base_path = sys._MEIPASS
        else:
            # Se estiver rodando no código fonte (desenvolvimento)
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.logo_path = os.path.join(base_path, 'assets', 'LOGO_Preta.png')
        
        # DEBUG: Verifica se a logo existe (opcional)
        if not os.path.exists(self.logo_path):
            print(f"⚠️ Logo não encontrada em: {self.logo_path}")

    def header(self):
        self.set_font('Arial', 'B', 17)
        
        if self.page_no() == 1:
            if os.path.exists(self.logo_path):
                self.image(self.logo_path, x=5, y=20, w=45)
            else:
                logging.warning(f"Arquivo de logo não encontrado em {self.logo_path}")
            
            self.set_xy(51, 10)
            self.cell(0, 10, "EUROCAR", 0, 1, 'L')
            self.set_x(51)
            self.set_font('Arial', '', 10)
            self.cell(0, 6, 'CNPJ: 59.152.856/0001-25', 0, 1, 'L')
            self.set_x(51)
            self.cell(0, 6, 'Vitaliano Pereira Serpa', 0, 1, 'L')
            self.set_x(51)
            self.cell(0, 6, 'Rua Juíz de Fora, 12 - Qd 98 - Jardim Guanabara', 0, 1, 'L')
            self.set_x(51)
            self.cell(0, 6, 'Contato: (62) 9 9415-9037', 0, 1, 'L')
            
            self.line(10, 48, 200, 48)
            self.ln(5)
        else:
            if os.path.exists(self.logo_path):
                self.image(self.logo_path, x=10, y=10, w=30)
            self.ln(15)

    def footer(self):
        # Posiciona o rodapé 15mm a partir do final da página
        self.set_y(-15)
        self.set_font('Arial', '', 10)
        
        # Formata a data
        meses = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }
        dias_semana = [
            'Segunda-feira', 'Terça-feira', 'Quarta-feira',
            'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
        ]
        
        hoje = datetime.now()
        nome_dia = dias_semana[hoje.weekday()]
        nome_mes = meses[hoje.month]
        
                # Número de páginas (linha inferior)
        pagina_texto = f"Página {self.page_no()} de {{nb}}"
        self.cell(0, 5, pagina_texto, 0, 1, 'R')  # Mesmo alinhamento da data

        # Data formatada (linha superior)
        data_formatada = f"{nome_dia}, {hoje.day} de {nome_mes} de {hoje.year}"
        self.cell(0, 5, data_formatada, 0, 0, 'R')  # Alinhado à direita, quebra linha após
        


# ========== FUNÇÕES UTILITÁRIAS ==========
def converter_moeda_input(valor_str: str) -> Decimal:
    """
    Converte string brasileira (ex: 1.250,50) para Decimal.
    Resolve o problema de inputs com ponto de milhar.
    """
    try:
        if not valor_str:
            return Decimal("0.00")
        # Remove pontos de milhar e troca vírgula decimal por ponto
        limpo = valor_str.replace('.', '').replace(',', '.')
        return Decimal(limpo)
    except Exception:
        raise ValueError("Formato de valor inválido")

def formatar_moeda(valor) -> str:
    try:
        valor = Decimal(valor)
        valor = valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


def atualizar_totais(window, values, itens):
    """Atualiza os totais usando Decimal para precisão"""
    try:
        # Soma usando Decimal
        total_pecas = sum(
            Decimal(item['quantidade']) * Decimal(item['valor'])
            for item in itens
        )
        
        try:
            # Garante que a mão de obra seja tratada corretamente
            mao_obra_val = values["-MAO_OBRA-"]
            if isinstance(mao_obra_val, (int, float)):
                mao_obra = Decimal(str(mao_obra_val))
            else:
                mao_obra = converter_moeda_input(mao_obra_val)
        except ValueError:
            mao_obra = Decimal("0.00")
            
        window["-TOTAL_PECAS-"].update(formatar_moeda(total_pecas))
        window["-TOTAL_GERAL-"].update(formatar_moeda(total_pecas + mao_obra))
    except Exception as e:
        logging.error(f"Erro ao atualizar totais: {e}")
        # O print abaixo ajuda a debugar se der erro
        print(f"Erro detalhado: {e}")

def criar_pdf(dados: Dict[str, Any]) -> EurocarPDF:
    """Cria um PDF com os dados do orçamento"""
    pdf = EurocarPDF()
    pdf.add_page()

    # Dados do cliente
    pdf.set_font("Arial", "B", 12)
    pdf.cell(20, 10, "Cliente:", 0, 0, 'L')
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, dados.get('nome', 'Não informado'), 0, 0, 'L')

    pdf.set_font("Arial", "B", 12)
    pdf.cell(70, 10, "Veículo:", 0, 0, 'R')
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, dados.get('veiculo', 'Não informado'), 0, 1, 'C')

    pdf.set_font("Arial", "B", 12)
    pdf.cell(20, 10, "Contato:", 0, 0, 'L')
    pdf.set_font("Arial", "", 12)
    pdf.cell(60, 10, dados.get('telefone', 'Não informado'), 0, 0, 'L')

    pdf.set_font("Arial", "B", 12)
    pdf.cell(68, 10, "Placa:", 0, 0, 'R')
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, dados.get('placa', 'Não informado'), 0, 1, 'C')

    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(1)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(100, 10, f"ORÇAMENTO Nº: {datetime.now().strftime('%H%M%S%d%m%y')}", 0, 0, 'L')
    pdf.cell(0, 10, f"Criado em: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.ln(1)

    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    # Tabela de itens
    pdf.set_font("Arial", "B", 12)
    col_widths = [10, 100, 15, 27, 38]

    def draw_table_header():
        pdf.cell(col_widths[0], 10, "Its", "B", 0, "L")
        pdf.cell(col_widths[1], 10, "Descrição", "B", 0, "L")
        pdf.cell(col_widths[2], 10, "Qtd", "B", 0, "C")
        pdf.cell(col_widths[3], 10, "Unitário", "B", 0, "C")
        pdf.cell(col_widths[4], 10, "Total", "B", 1, "C")

    draw_table_header()

    pdf.set_font("Arial", "", 12)
    
    # --- CORREÇÃO 1: Inicializa com Decimal ---
    total_pecas = Decimal("0.00") 

    for idx, item in enumerate(dados['itens']):
        if pdf.get_y() > 260 - (3 * 10):
            pdf.add_page()
            draw_table_header()
        
        # --- CORREÇÃO 2: Converte tudo para Decimal antes de calcular ---
        quantidade = Decimal(str(item.get('quantidade', 1)))
        valor_unitario = Decimal(str(item.get('valor', 0)))
        valor_total = quantidade * valor_unitario
        total_pecas += valor_total

        pdf.cell(col_widths[0], 10, f"{idx+1}.", 0, 0, "C")
        pdf.cell(col_widths[1], 10, item.get('descricao', ''), 0, 0, "L")
        pdf.cell(col_widths[2], 10, str(quantidade), 0, 0, "C")
        pdf.cell(col_widths[3], 10, formatar_moeda(valor_unitario), 0, 0, "C")
        pdf.cell(col_widths[4], 10, formatar_moeda(valor_total), 0, 1, "C")

    if pdf.get_y() > 255:
        pdf.add_page()

    pdf.set_y(-60)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(150, 8, "TOTAL PEÇAS:", 0, 0, "L")
    pdf.cell(30, 8, formatar_moeda(total_pecas), 0, 1, "R")
    
    # --- CORREÇÃO 3: Converte Mão de Obra para Decimal ---
    try:
        val_mo = dados.get('mao_obra', 0)
        mao_obra = Decimal(str(val_mo))
    except:
        mao_obra = Decimal("0.00")
        
    pdf.cell(150, 8, "MÃO DE OBRA:", 0, 0, "L")
    pdf.cell(30, 8, formatar_moeda(mao_obra), 0, 1, "R")
    
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Agora a soma funciona (Decimal + Decimal)
    total_geral = total_pecas + mao_obra
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(150, 8, "TOTAL GERAL:", 0, 0, "L")
    pdf.cell(30, 8, formatar_moeda(total_geral), 0, 1, "R")

    return pdf
def sanitizar_nome_arquivo(nome: str) -> str:
    """Remove caracteres inválidos de nomes de arquivos"""
    return re.sub(r'[\\/:*?"<>|]', '', nome)

def salvar_orcamento_editavel(dados: Dict[str, Any]) -> str:
    """Salva os dados do orçamento em um arquivo JSON convertendo Decimals para float"""
    config = ConfigManager()
    try:
        nome_cliente = sanitizar_nome_arquivo(dados['nome'].strip())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"Orcamento_{nome_cliente}_{timestamp}.json"
        caminho_completo = os.path.join(config.get("paths", "orcamentos_editaveis"), nome_arquivo)
        
        os.makedirs(config.get("paths", "orcamentos_editaveis"), exist_ok=True)
        
        # PREPARAÇÃO DOS DADOS: Converte Decimal para float para o JSON aceitar
        dados_json = dados.copy()
        itens_json = []
        for item in dados['itens']:
            novo_item = item.copy()
            # Converte valor e quantidade para float/int se forem Decimal
            if isinstance(novo_item.get('valor'), Decimal):
                novo_item['valor'] = float(novo_item['valor'])
            if isinstance(novo_item.get('quantidade'), Decimal):
                novo_item['quantidade'] = int(novo_item['quantidade'])
            itens_json.append(novo_item)
        
        dados_json['itens'] = itens_json
        
        # Converte a mão de obra também
        if isinstance(dados_json.get('mao_obra'), Decimal):
            dados_json['mao_obra'] = float(dados_json['mao_obra'])
            
        with open(caminho_completo, 'w', encoding='utf-8') as f:
            json.dump(dados_json, f, ensure_ascii=False, indent=4)
            
        return caminho_completo
    except Exception as e:
        logging.error(f"Erro ao salvar arquivo editável: {e}")
        # Não damos popup de erro aqui para não assustar o usuário se o PDF já deu certo
        print(f"Erro silencioso ao salvar JSON: {e}") 
        return None
    
def carregar_orcamento_editavel() -> Dict[str, Any]:
    """Permite carregar um orçamento salvo anteriormente"""
    config = ConfigManager()
    caminho = sg.popup_get_file("Selecione o orçamento para editar", 
                                file_types=(("Arquivos de Orçamento", "*.json"),),
                                default_path=config.get("paths", "orcamentos_editaveis"))
    if not caminho:
        return None
    
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        return dados
    except Exception as e:
        logging.error(f"Erro ao carregar arquivo: {e}")
        sg.popup_error(f"Erro ao carregar arquivo:\n{str(e)}")
        return None

def create_settings_window(config):
    """Cria janela de configurações"""
    layout = [
        [sg.TabGroup([[
            sg.Tab("Caminhos", [
                [sg.Text("Pasta para Orçamentos PDF:")],
                [sg.Input(config.get("paths", "orcamentos_pdf"), key="-PDF_PATH-", background_color='white'), 
                sg.FolderBrowse("📁", button_color=COR_PRIMARIA, size=(6, 1))],
                
                [sg.Text("Pasta para Orçamentos Editáveis:")],
                [sg.Input(config.get("paths", "orcamentos_editaveis"), key="-EDIT_PATH-", background_color='white'), 
                sg.FolderBrowse("📁", button_color=COR_PRIMARIA, size=(6, 1))],
                
            ]),
        ]], expand_x=True, expand_y=True, background_color=COR_FUNDO)],
        
        [sg.HorizontalSeparator(color=COR_PRIMARIA)],
        [sg.Button("Salvar", key="-SAVE-", button_color=(COR_TEXTO, COR_BOTAO_ADD)),
        sg.Button("Cancelar", key="-CANCEL-", button_color=(COR_TEXTO, COR_BOTAO_DEL))]
    ]

    return sg.Window(
        "Configurações do Sistema", 
        layout, 
        modal=True, 
        finalize=True)

# ========== LAYOUT PRINCIPAL ==========
def create_main_window(config):
    layout = [
        # Cabeçalho com botão de configurações
        [sg.Column([
            [sg.Text("EUROCAR", font=("Segoe UI", 24, "bold"), text_color=COR_PRIMARIA, pad=((0, 0), (0, 5))),
            sg.Push(),
            sg.Button("⚙", key="-CONFIG-", button_color=(COR_TEXTO, COR_FUNDO), border_width=0, 
                        tooltip="Configurações", font=("Segoe UI", 16))],
            [sg.Text("Sistema de Orçamentos", font=("Segoe UI", 14), text_color=COR_SECUNDARIA)]
        ], justification='center', expand_x=True, background_color=COR_FUNDO)],
        
        [sg.HSep(color=COR_PRIMARIA, pad=(0, 15))],
        
        # Seção de dados do cliente
        [sg.Column([
            [sg.Text("Dados do Cliente", font=("Segoe UI", 12, "bold"), 
                    text_color=COR_PRIMARIA, background_color=COR_CARTAO)],
            [sg.Text("Nome:", size=8, background_color=COR_CARTAO), 
            sg.Input(key="-NOME-", size=40, border_width=1, background_color='white')],
            [sg.Text("Telefone:", size=8, background_color=COR_CARTAO), 
            sg.Input(key="-TEL-", size=20, border_width=1, background_color='white', enable_events=True)],
            [sg.Text("Veículo:", size=8, background_color=COR_CARTAO), 
            sg.Input(key="-VEICULO-", size=20, border_width=1, background_color='white'),
            sg.Text("Placa:", pad=(10, 0), background_color=COR_CARTAO), 
            sg.Input(key="-PLACA-", size=10, border_width=1, background_color='white', enable_events=True)]
        ], pad=(20, 15), background_color=COR_CARTAO, expand_x=True)],
        
        
        # Seção de itens do orçamento
        [sg.Column([
            [sg.Text("Itens do Orçamento", font=("Segoe UI", 12, "bold"), 
                    text_color=COR_PRIMARIA, background_color=COR_CARTAO)],
            [sg.Table(values=[], headings=["It.", "Descrição", "Qtd", "Unitário", "Total"], 
                    key="-ITENS-", 
                    col_widths=[5, 30, 8, 15, 15],
                    num_rows=8,
                    auto_size_columns=False, 
                    justification='left',
                    enable_events=True, 
                    select_mode=sg.TABLE_SELECT_MODE_BROWSE,
                    header_background_color=COR_PRIMARIA,
                    header_text_color=COR_TEXTO,
                    row_height=25,
                    background_color=COR_CARTAO,
                    alternating_row_color='#222222',
                    expand_x=True, 
                    expand_y=True)],
            [sg.Column([
                [sg.Text("Mão de Obra R$:", background_color=COR_CARTAO),
                sg.Input("", key="-MAO_OBRA-", size=15, enable_events=True, 
                        background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Text("Total Peças:", background_color=COR_CARTAO),
                sg.Text("R$ 0,00", key="-TOTAL_PECAS-", background_color=COR_CARTAO)],
                [sg.Text("Total Geral:", background_color=COR_CARTAO, font=("Segoe UI", 10, "bold")),
                sg.Text("R$ 0,00", key="-TOTAL_GERAL-", background_color=COR_CARTAO, 
                        font=("Segoe UI", 10, "bold"))]
            ], background_color=COR_CARTAO)],
            [sg.Column([

                [sg.Button("Adicionar Item", button_color=(COR_TEXTO, COR_BOTAO_ADD), 
                    pad=(5, 10), size=15, key="-ADD-"),
                sg.Button("Editar Item", button_color=(COR_TEXTO, COR_BOTAO_EDIT), 
                    pad=(5, 10), size=15, key="-EDIT-"),
                sg.Button("Remover Item", button_color=(COR_TEXTO, COR_BOTAO_DEL), 
                    pad=(5, 10), size=15, key="-DEL-"),
                sg.Button("↑", button_color=(COR_TEXTO, COR_BOTAO_CONFIG), 
                    pad=(2, 10), size=(4, 1), key="-UP-", tooltip="Mover item para cima"),
                sg.Button("↓", button_color=(COR_TEXTO, COR_BOTAO_CONFIG), 
                    pad=((2, 10), 10), size=(4, 1), key="-DOWN-", tooltip="Mover item para baixo")],
            ], justification='center', expand_x=True, background_color=COR_CARTAO)]
        ], pad=(20, 15), background_color=COR_CARTAO, expand_x=True, expand_y=True)],
        
        [sg.HSep(color=COR_PRIMARIA, pad=(0, 15))],
        
        # Botões de ação
        [sg.Column([
            [sg.Button("Pré-visualizar", button_color=(COR_TEXTO, COR_BOTAO_PRE_VIZUALIZAR), pad=5, size=15),
            sg.Button("Gerar PDF", button_color=(COR_TEXTO, COR_BOTAO_GERAR_PDF), pad=5, size=15, key="-PDF-"),
            sg.Button("Carregar Orç.", button_color=(COR_TEXTO, COR_BOTAO_CARREGAR), pad=5, size=15, key="-LOAD-"),
            sg.Button("Sair", button_color=(COR_TEXTO, COR_BOTAO_SAIR), pad=5, size=15)]
        ], justification='center', expand_x=True, background_color=COR_FUNDO)]
    ]

    window = sg.Window(
                    "EUROCAR - Sistema de Orçamentos", 
                    layout, 
                    finalize=True, 
                    icon=resource_path("assets/icone.ico"),
                    size=(900, 850),
                    resizable=True,
                    margins=(10, 10),
                    element_justification='c',
                    background_color=COR_FUNDO,
                    enable_close_attempted_event=True)
    
    window["-ITENS-"].bind('<Delete>', ' -del-')

    window["-MAO_OBRA-"].bind('<Return>', '_ENTER')

    return window

def checar_atualizacao():
    """Verifica versão no Google Drive e baixa direto"""
    
    # --- SUAS CONFIGURAÇÕES ---
    VERSAO_ATUAL = "1.2" 
    
    # 1. ID do arquivo version.txt (Mantivemos o mesmo)
    ID_ARQUIVO_VERSAO = "1Vqrrv9H_y43cD6koq7uWF_3UbeCAvdJJ" 
    
    # 2. ID do App executável (NOVO ID ATUALIZADO)
    ID_DO_APP = "10a9nUhJGASKGcFF05JxmbffPJN9igF-Z"
    
    # Monta o Link de Download Direto
    LINK_DOWNLOAD_DIRETO = f"https://drive.google.com/uc?export=download&id={ID_DO_APP}"
    # --------------------------

    # Link para ler o arquivo de texto
    URL_CHECK_VERSAO = f"https://drive.google.com/uc?export=download&id={ID_ARQUIVO_VERSAO}"

    try:
        print("Buscando atualizações...") 
        resposta = requests.get(URL_CHECK_VERSAO, timeout=3)
        
        if resposta.status_code == 200:
            versao_nuvem = resposta.text.strip()
            
            if versao_nuvem != VERSAO_ATUAL:
                msg = (f"NOVA VERSÃO DISPONÍVEL!\n\n"
                        f"Sua versão: {VERSAO_ATUAL}\n"
                        f"Nova versão: {versao_nuvem}\n\n"
                        f"O sistema irá abrir o navegador para iniciar o download\n"
                        f"e fechará automaticamente para você instalar.\n\n"
                        f"Deseja atualizar agora?")
                
                icon_popup = icon_path if 'icon_path' in globals() else None
                
                if sg.popup_yes_no(msg, title="Atualização Eurocar", icon=icon_popup) == "Yes":
                    # Abre o link de download direto do novo arquivo
                    webbrowser.open(LINK_DOWNLOAD_DIRETO)
                    sys.exit() # Fecha o programa
                    
    except Exception as e:
        print(f"Erro ao atualizar: {e}")
        pass
    
    return False

# ========== FUNÇÃO PRINCIPAL ==========
def main():
    config = ConfigManager()
    checar_atualizacao()

    # Verificação EXTRA para primeira execução
    config_dir = appdirs.user_config_dir("Eurocar")
    first_run_flag = os.path.join(config_dir, ".firstrun")
    
    if not os.path.exists(first_run_flag):
        # Mostra a janela de configuração inicial
        escolher_pastas_iniciais(config)
        
        # Cria o arquivo flag
        with open(first_run_flag, 'w') as f:
            f.write("1")

    window = create_main_window(config)
    itens = []

    window["-MAO_OBRA-"].bind("<Return>", "_ENTER")
    window["-MAO_OBRA-"].bind('<FocusOut>', '_FORMAT')

    window.bind("<Control-n>", "-ADD-")
    window.bind("<Delete>", "-DEL-")
    window.bind("<Control-p>", "-PDF-")
    window.bind("<F5>", "Pré-visualizar")
    window.bind("<Control-e>", "-EDIT-")
    window.bind("<Control-o>", "-LOAD-")
    window.bind("<Control-s>", "-CONFIG-")

    while True:
        event, values = window.read()
        
        if event in (sg.WINDOW_CLOSE_ATTEMPTED_EVENT, "Sair"):
            if itens:
                # Se tem itens, pergunta. Se responder "No" (Não sair), apenas ignora e volta pro app
                if sg.popup_yes_no("Existem itens no orçamento atual.\nDeseja realmente sair?", 
                                title="Confirmar Saída", 
                                icon=icon_path) == "Yes":
                    break
            else:
                # Se não tem itens, sai direto
                break
        
        # Caso de segurança extra (se a janela for destruída forçadamente)
        if event == sg.WINDOW_CLOSED:
            break
            
        elif event in ("-UP-", "-DOWN-") and itens:
            # Verifica se tem algo selecionado
            if not values["-ITENS-"]:
                continue
                
            index_atual = values["-ITENS-"][0]
            novo_index = index_atual
            
            # Mover para CIMA
            if event == "-UP-" and index_atual > 0:
                # Troca o item atual pelo anterior na lista
                itens[index_atual], itens[index_atual - 1] = itens[index_atual - 1], itens[index_atual]
                novo_index = index_atual - 1
                
            # Mover para BAIXO
            elif event == "-DOWN-" and index_atual < len(itens) - 1:
                # Troca o item atual pelo próximo na lista
                itens[index_atual], itens[index_atual + 1] = itens[index_atual + 1], itens[index_atual]
                novo_index = index_atual + 1
            
            # Se a posição mudou, atualiza a tela
            if novo_index != index_atual:
                # Recria a tabela visual com a nova ordem
                window["-ITENS-"].update(values=[
                    [f"{idx+1}.", 
                    item["descricao"], 
                    item["quantidade"], 
                    formatar_moeda(item['valor']), 
                    formatar_moeda(item['quantidade'] * item['valor'])] 
                    for idx, item in enumerate(itens)
                ])
                
                # Mantém a seleção no item que você moveu (para poder clicar várias vezes seguidas)
                window["-ITENS-"].update(select_rows=[novo_index])
            
        elif event == "-PLACA-":
            # Força maiúsculas e limita tamanho
            placa = values["-PLACA-"].upper()
            if len(placa) > 8: placa = placa[:8]
            window["-PLACA-"].update(placa)

        elif event == "-TEL-":
            # Permite apenas números e caracteres comuns de telefone
            tel = ''.join(c for c in values["-TEL-"] if c.isdigit() or c in '()- ')
            window["-TEL-"].update(tel)

        elif event == "-MAO_OBRA-_FORMAT":
            try:
                # 1. Converte o que foi digitado para número
                valor_digitado = converter_moeda_input(values["-MAO_OBRA-"])
                
                # 2. Formata para padrão brasileiro (ex: R$ 1.500,00)
                texto_formatado = formatar_moeda(valor_digitado)
                
                # 3. Remove o "R$" e espaços extras para deixar limpo na caixa (ex: 1.500,00)
                # O replace trata espaços normais e espaços não quebráveis (\xa0) comuns em formatação
                texto_limpo = texto_formatado.replace("R$", "").replace("\xa0", "").strip()
                
                # 4. Atualiza a caixa de texto
                window["-MAO_OBRA-"].update(texto_limpo)
                
                # 5. Garante que os totais lá embaixo estejam certos
                # Precisamos passar o valor novo explicitamente porque o 'values' ainda pode ter o antigo
                values["-MAO_OBRA-"] = texto_limpo
                atualizar_totais(window, values, itens)
                
            except Exception as e:
                pass

        elif event == "-CONFIG-":
            settings_window = create_settings_window(config)
            
            while True:
                event_settings, values_settings = settings_window.read()
                
                if event_settings in (sg.WINDOW_CLOSED, "-CANCEL-"):
                    break
                    
                elif event_settings == "-SAVE-":
                    config.update_section("paths", {
                        "orcamentos_pdf": values_settings["-PDF_PATH-"],
                        "orcamentos_editaveis": values_settings["-EDIT_PATH-"],
                    }, save=True)
                                        
                    sg.popup("Configurações salvas com sucesso!\nAlgumas mudanças podem requerer reinicialização.",
                            title="Sucesso")
                    break
            
            settings_window.close()
            
        elif event == "-ABRIR_PASTA-":
            pasta = config.get("paths", "orcamentos_pdf")
            if os.path.exists(pasta):
                if sys.platform == "win32":
                    os.startfile(pasta)
                else:
                    os.system(f'xdg-open "{pasta}"')
            else:
                sg.popup_error("Pasta não existe!", title="Erro")

        elif event == "-ABRIR_PASTA_EDITAVEIS-":  # Mantido como está
            pasta = config.get("paths", "orcamentos_editaveis")
            if os.path.exists(pasta):
                if sys.platform == "win32":
                    os.startfile(pasta)
                else:
                    os.system(f'xdg-open "{pasta}"')
            else:
                sg.popup_error("Pasta não existe!", title="Erro")
            
            settings_window.close()
        
        elif event in ("Adicionar Item", "-ADD-"):
            layout_item = [
                [sg.Text("Descrição:", text_color=COR_TEXTO), 
                sg.Input(key="-DESC-", size=40, focus=True, background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Text("Quantidade:", text_color=COR_TEXTO), 
                sg.Input(key="-QTD-", size=5, default_text="1", background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Text("Valor Unitário R$:", text_color=COR_TEXTO), 
                sg.Input(key="-VALOR-", size=15, background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Button("Salvar", button_color=(COR_TEXTO, COR_BOTAO_ADD)), 
                sg.Button("Cancelar", button_color=(COR_TEXTO, COR_BOTAO_SAIR))]
            ]
            
            janela_item = sg.Window(
                "Novo Item",
                layout_item, 
                modal=True, 
                background_color=COR_FUNDO)
            
            while True:
                ev_item, vals_item = janela_item.read()
                if ev_item in (sg.WINDOW_CLOSED, "Cancelar"):
                    break
                if ev_item == "Salvar":
                    try:
                        descricao = vals_item["-DESC-"].strip()
                        if not descricao:
                            sg.popup_error("A descrição é obrigatória!", title="Erro")
                            continue
                            
                        quantidade = int(vals_item["-QTD-"] or 1)
                        valor = converter_moeda_input(vals_item["-VALOR-"])
                        
                        itens.append({
                            "descricao": descricao,
                            "quantidade": quantidade,
                            "valor": valor
                        })
                        
                        window["-ITENS-"].update(values=[
                            [f"{idx+1}.", 
                            item["descricao"], 
                            item["quantidade"], 
                            formatar_moeda(item['valor']), 
                            formatar_moeda(item['quantidade'] * item['valor'])] 
                            for idx, item in enumerate(itens)
                        ])
                        atualizar_totais(window, values, itens)
                        break
                    except ValueError as e:
                        sg.popup_error(f"Valor inválido!\nUse números (ex: 150,50)\nErro: {str(e)}", title="Erro")
            janela_item.close()
        
        elif event in ("Editar Item", "-EDIT-") and itens:
            # Verifica se alguma linha está selecionada
            if not values["-ITENS-"]:
                sg.popup_error("Selecione um item para editar!", title="Erro")
                continue
                
            # Pega o índice da linha selecionada (padrão seguro)
            selected_row = values["-ITENS-"][0]
            item_to_edit = itens[selected_row]
            
            # --- Daqui para baixo é o layout da janela de edição (igual ao original) ---
            layout_edicao = [
                [sg.Text("Editar Item:", font=("Arial", 12), text_color=COR_TEXTO)],
                [sg.Text("Descrição:", text_color=COR_TEXTO), 
                sg.Input(item_to_edit["descricao"], key="-EDIT_DESC-", size=40, focus=True, background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Text("Quantidade:", text_color=COR_TEXTO), 
                sg.Input(str(item_to_edit["quantidade"]), key="-EDIT_QTD-", size=5, background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Text("Valor Unitário R$:", text_color=COR_TEXTO), 
                sg.Input(str(item_to_edit["valor"]), key="-EDIT_VALOR-", size=15, background_color="white", text_color=COR_TEXTO_CAIXA)],
                [sg.Button("Salvar", button_color=(COR_TEXTO, COR_BOTAO_EDIT)), 
                sg.Button("Cancelar", button_color=(COR_TEXTO, COR_BOTAO_SAIR))]
            ]
            
            janela_edicao = sg.Window(
                "Editar Item", 
                layout_edicao, 
                modal=True, 
                background_color=COR_FUNDO)
            
            while True:
                ev_edit, vals_edit = janela_edicao.read()
                if ev_edit in (sg.WINDOW_CLOSED, "Cancelar"):
                    break
                if ev_edit == "Salvar":
                    try:
                        descricao = vals_edit["-EDIT_DESC-"].strip()
                        if not descricao:
                            sg.popup_error("A descrição é obrigatória!", title="Erro")
                            continue
                            
                        quantidade = int(vals_edit["-EDIT_QTD-"] or 1)
                        valor = converter_moeda_input(vals_edit["-EDIT_VALOR-"])
                        
                        itens[selected_row] = {
                            "descricao": descricao,
                            "quantidade": quantidade,
                            "valor": valor
                        }
                        
                        window["-ITENS-"].update(values=[
                            [f"{idx+1}.", 
                            item["descricao"], 
                            item["quantidade"], 
                            formatar_moeda(item['valor']), 
                            formatar_moeda(item['quantidade'] * item['valor'])] 
                            for idx, item in enumerate(itens)
                        ])
                        atualizar_totais(window, values, itens)
                        break
                    except ValueError as e:
                        sg.popup_error(f"Valor inválido!\nUse números (ex: 150,50)\nErro: {str(e)}", title="Erro")
            
            janela_edicao.close()
        
        elif event in ("Remover Item", "-DEL-") and itens:
            if values["-ITENS-"]:  
                selected_row = values["-ITENS-"][0]  
                itens.pop(selected_row) 
                window["-ITENS-"].update(values=[
                    [f"{idx+1}.", 
                    item["descricao"], 
                    item["quantidade"], 
                    formatar_moeda(item['valor']), 
                    formatar_moeda(item['quantidade'] * item['valor'])] 
                    for idx, item in enumerate(itens)
                ])
                atualizar_totais(window, values, itens)
            else:
                sg.popup_error("Selecione um item para remover!", title="Erro")
        
        elif event == "-MAO_OBRA-":
            atualizar_totais(window, values, itens)
        
        elif event == "Pré-visualizar":
            if not values["-NOME-"] or not values["-VEICULO-"] or not itens:
                sg.popup_error("Campos obrigatórios faltando!",
                            "Preencha Nome, Veículo e adicione itens.",
                            title="Erro")
                continue
            
            # --- CORREÇÃO: Converter mão de obra para Decimal ---
            try:
                val_mo = values["-MAO_OBRA-"]
                if val_mo:
                    # Remove formatação de milhar se houver e troca vírgula por ponto
                    limpo = str(val_mo).replace('.', '').replace(',', '.')
                    mao_obra = Decimal(limpo)
                else:
                    mao_obra = Decimal("0.00")
            except:
                mao_obra = Decimal("0.00")
            
            preview_text = f"""
    {'CLIENTE:':<10} {values['-NOME-']}
    {'TELEFONE:':<10} {values['-TEL-']}
    {'VEÍCULO:':<10} {values['-VEICULO-']}
    {'PLACA:':<10} {values['-PLACA-']}

    {'='*50}
    {'ITENS DO ORÇAMENTO':^50}
    {'='*50}"""
            
            # Cálculo usando Decimal
            total_itens = sum(Decimal(str(item['quantidade'])) * Decimal(str(item['valor'])) for item in itens)
            
            for idx, item in enumerate(itens, 1):
                qtd = Decimal(str(item['quantidade']))
                val = Decimal(str(item['valor']))
                total_item = qtd * val
                preview_text += f"\n{idx:>2}. {item['descricao'][:30]:<30} {qtd:>3}x {formatar_moeda(val):>10} = {formatar_moeda(total_item):>10}"
            
            total_geral = total_itens + mao_obra
            
            preview_text += f"\n\n{'TOTAL PEÇAS:':<15} {formatar_moeda(total_itens):>20}"
            preview_text += f"\n{'MÃO DE OBRA:':<15} {formatar_moeda(mao_obra):>20}"
            preview_text += f"\n{'TOTAL GERAL:':<15} {formatar_moeda(total_geral):>20}"
            
            layout_preview = [
                [sg.Multiline(
                    preview_text, 
                    size=(80, 25), 
                    font=("Courier New", 10),
                    background_color='white',
                    text_color='black',
                    disabled=True,
                    key='-PREVIEW-'
                )],
                [sg.Button("Fechar", key="-FECHAR-PREVIEW-", button_color=(COR_TEXTO, COR_BOTAO_DEL))]
            ]

            janela_preview = sg.Window(
                "Pré-visualização do Orçamento",
                layout_preview,
                modal=True,
                element_justification='C',
                finalize=True
            )

            while True:
                event_preview, _ = janela_preview.read()
                if event_preview in (sg.WINDOW_CLOSED, "-FECHAR-PREVIEW-"):
                    break

            janela_preview.close()
        
        elif event in ("Gerar PDF", "-PDF-"):
            if not values["-NOME-"] or not values["-VEICULO-"] or not itens:
                sg.popup_error("Campos obrigatórios faltando!",
                            "Preencha Nome, Veículo e adicione itens.",
                            title="Erro")
                continue
            
            try:
                os.makedirs(config.get("paths", "orcamentos_pdf"), exist_ok=True)
                
                try:
                    mao_obra = converter_moeda_input(values["-MAO_OBRA-"])
                except:
                    mao_obra = Decimal("0.00")
                
                dados = {
                    "nome": values["-NOME-"],
                    "telefone": values["-TEL-"],
                    "veiculo": values["-VEICULO-"],
                    "placa": values["-PLACA-"],
                    "mao_obra": mao_obra,
                    "itens": itens
                }
                
                pdf = criar_pdf(dados)

                data_formatada = datetime.now().strftime("%d-%m-%Y")
                nome_cliente = ''.join(c for c in values['-NOME-'].strip() if c.isalnum() or c in ' _-')
                modelo_carro = ''.join(c for c in values['-VEICULO-'].strip() if c.isalnum() or c in ' _-')
                nome_arquivo = f"Orçamento {nome_cliente} {modelo_carro} {data_formatada}.pdf"
                caminho_completo = os.path.join(config.get("paths", "orcamentos_pdf"), nome_arquivo)

                pdf.output(caminho_completo)
                
                caminho_json = salvar_orcamento_editavel(dados)
                
                mensagem = "ORÇAMENTO GERADO COM SUCESSO!"
                if caminho_json:
                    mensagem += f"\n\nArquivo para edição salvo em:\n{caminho_json}"
                
                sg.popup_ok(mensagem,
                        f"PDF salvo em:\n{caminho_completo}",
                        title="Sucesso")
                
                if sg.popup_yes_no("Deseja abrir o orçamento agora?", title="Abrir PDF") == "Yes":
                    if sys.platform == "win32":
                        os.startfile(caminho_completo)
                    else:
                        os.system(f'xdg-open "{caminho_completo}"')
            
            except Exception as e:
                sg.popup_error(f"ERRO AO GERAR PDF:\n{str(e)}", title="Erro")

        elif event == "-LOAD-":
            try:
                # 1. Diálogo para seleção do arquivo
                caminho = sg.popup_get_file(
                    "Selecione o orçamento (.json)",
                    file_types=(("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")),
                    default_path=config.get("paths", "orcamentos_editaveis"),
                    no_window=True,
                    icon=icon_path
                )
                
                if not caminho:  # Usuário cancelou
                    continue

                # 2. Pré-visualização segura
                preview_data = {}
                try:
                    with open(caminho, 'r', encoding='utf-8') as f:
                        preview_data = json.load(f)
                        
                    preview_info = [
                        f"Arquivo: {os.path.basename(caminho)}",
                        f"Cliente: {preview_data.get('nome', 'Não informado')}",
                        f"Veículo: {preview_data.get('veiculo', 'Não informado')}",
                        f"Itens: {len(preview_data.get('itens', []))}",
                        f"Total: {formatar_moeda(sum(item.get('valor', 0) * item.get('quantidade', 1) for item in preview_data.get('itens', [])))}"
                    ]
                except Exception as e:
                    preview_info = [
                        f"Arquivo: {os.path.basename(caminho)}",
                        "⚠ Não foi possível ler o arquivo",
                        f"Erro: {str(e)}"
                    ]

                # 3. Janela de confirmação personalizada
                layout_confirmacao = [
                    [sg.Text("Confirmar carregamento?", font=("Segoe UI", 12))],
                    [sg.Multiline(
                        "\n".join(preview_info),
                        size=(40, 6),
                        disabled=True,
                        background_color="#f0f0f0"
                    )],
                    [sg.Button("Sim", key="-CONFIRMAR-", button_color=(COR_TEXTO, COR_BOTAO_ADD)),
                    sg.Button("Não", key="-CANCELAR-", button_color=(COR_TEXTO, COR_BOTAO_SAIR))]
                ]

                janela_confirmacao = sg.Window(
                    "Confirmar",
                    layout_confirmacao,
                    modal=True,
                    icon=icon_path,
                    element_justification='c'
                )

                confirmado = False
                while True:
                    event_confirm, _ = janela_confirmacao.read()
                    if event_confirm in (sg.WINDOW_CLOSED, "-CANCELAR-"):
                        break
                    elif event_confirm == "-CONFIRMAR-":
                        confirmado = True
                        break
                janela_confirmacao.close()

                if not confirmado:
                    continue

                # 4. Carregamento definitivo
                with open(caminho, 'r', encoding='utf-8') as f:
                    dados = json.load(f)

                # Preenchimento dos campos
                campos = {
                    "-NOME-": dados.get("nome", ""),
                    "-TEL-": dados.get("telefone", ""),
                    "-VEICULO-": dados.get("veiculo", ""),
                    "-PLACA-": dados.get("placa", ""),
                    "-MAO_OBRA-": formatar_moeda(dados.get("mao_obra", 0)).replace("R$", "").strip()
                }
                for key, value in campos.items():
                    window[key].update(value)

                # Processamento seguro dos itens
                itens = []
                for item in dados.get("itens", []):
                    try:
                        itens.append({
                            'descricao': str(item.get('descricao', '')),
                            'quantidade': int(item.get('quantidade', 1)),
                            'valor': Decimal(str(item.get('valor', 0)))
                        })
                    except (ValueError, TypeError):
                        continue

                # Atualização da tabela
                window["-ITENS-"].update(values=[
                    [f"{idx+1}.", item["descricao"], item["quantidade"],
                    formatar_moeda(item['valor']),
                    formatar_moeda(item['quantidade'] * item['valor'])]
                    for idx, item in enumerate(itens)
                ])

                atualizar_totais(window, values, itens)

            except json.JSONDecodeError:
                sg.popup_error("Erro: O arquivo está corrompido ou em formato inválido", title="Erro")
            except Exception as e:
                sg.popup_error(f"Erro inesperado:\n{str(e)}", title="Erro")

if __name__ == "__main__":
    main()