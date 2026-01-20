# 🚗 Eurocar - Sistema de Gestão de Orçamentos

Aplicação Desktop desenvolvida em Python para facilitar a criação, gestão e exportação de orçamentos para oficinas mecânicas e funilarias.

## 📋 Sobre o Projeto
O Eurocar foi desenvolvido para substituir processos manuais, permitindo:
- Cadastro rápido de clientes e veículos.
- Inserção dinâmica de itens e serviços.
- Cálculo automático de valores e mão de obra.
- Geração de orçamentos profissionais em PDF.
- Salvamento de orçamentos editáveis (JSON) para alterações futuras.

## 🚀 Funcionalidades Principais
- [cite_start]**Interface Gráfica Amigável:** Desenvolvida com `FreeSimpleGUI`[cite: 24].
- **Geração de PDF:** Motor de renderização customizado com `fpdf2` que cria documentos prontos para impressão com logo e cabeçalho da empresa.
- [cite_start]**Sistema de Auto-Update:** O software verifica automaticamente no Google Drive se há uma nova versão do executável e realiza a atualização.
- **Persistência de Dados:** Configurações e orçamentos são salvos localmente, permitindo retomar o trabalho de onde parou.
- **Formatação Brasileira:** Tratamento nativo de moeda (R$) e datas.

## 🛠️ Tecnologias Utilizadas
- **Linguagem:** Python 3.x
- **GUI:** FreeSimpleGUI
- **Relatórios:** FPDF2
- **Integração:** Requests (para verificação de updates)
- **Build:** PyInstaller (para criação do executável .exe)
