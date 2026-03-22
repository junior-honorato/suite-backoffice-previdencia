# 🏦 Suíte Backoffice Previdência

Uma suíte de ferramentas (Multi-Page App) desenvolvida em Python para otimizar, automatizar e garantir a conformidade (Compliance) das operações diárias de Backoffice em entidades previdenciárias e financeiras.

O objetivo deste produto é eliminar o trabalho manual repetitivo, reduzir erros operacionais e fornecer uma interface unificada e amigável para os analistas, mantendo **100% da segurança dos dados operando localmente (LGPD)**.

## 📦 Módulos Integrados

A suíte consolida as seguintes ferramentas em uma única interface Web (Streamlit):

### 1. 🧮 Ajuste de Valor - Portabilidade de Saída (SIDE)
* **Problema:** Arquivos de texto posicional gerados com diferenças de centavos por dízimas travam a integração com os sistemas do SIDE/ePrev.
* **Solução:** O sistema analisa o TXT, identifica o valor total atual, permite o input do valor correto e executa o ajuste matemático de deltas na primeira linha de movimento.
* **Segurança:** Possui um guard-rail (trava de compliance) que impede ajustes automáticos superiores a R$ 1,00, exigindo revisão manual para grandes divergências.

### 2. 📄 Conversor de Excel para TXT (Padrão SIDE)
* **Problema:** Sistemas legados exigem importações em TXT de largura fixa (posicional), mas os relatórios de contribuição chegam em planilhas Excel.
* **Solução:** Um motor de conversão que mapeia as colunas de datas e valores no Excel, aplica preenchimento de zeros à esquerda (`zfill`) e espaços à direita (`ljust`), gerando o arquivo pronto para upload.
* **Segurança:** Suporte nativo para leitura de planilhas criptografadas/protegidas por senha diretamente na interface.

## 🛠️ Tecnologias Utilizadas
* **Frontend/Interface:** Streamlit
* **Engenharia de Dados:** Pandas, Openpyxl, xlrd
* **Segurança/Criptografia:** msoffcrypto-tool
* **Empacotamento:** PyInstaller

## 🚀 Como Executar Localmente (Modo Desenvolvimento)

1. Clone este repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/suite-backoffice-previdencia.git
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Inicie o motor da aplicação:
   ```bash
   python iniciar_sistema.py
   ```
   *(O sistema abrirá automaticamente uma aba no seu navegador padrão).*

## 🏗️ Como Gerar o Executável (.exe) para a Operação

Para distribuir a ferramenta para analistas que não possuem o Python instalado, o projeto já conta com um arquivo de especificação (`.spec`) configurado com os *hooks* necessários para o Streamlit e bibliotecas de criptografia.

Basta rodar o comando abaixo na raiz do projeto:
```bash
pyinstaller iniciar_sistema.spec --clean
```
O arquivo `.exe` finalizado estará disponível dentro da pasta `dist/`.

---
👤 **Autor:** Arlindo Júnior Honorato  
Technical Product Manager | Focado em eficiência de Backoffice e automação de processos.
