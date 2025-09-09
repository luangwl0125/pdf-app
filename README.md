# PDF Tools - Web App (Streamlit)

Uma aplicação web moderna para manipulação e conversão de PDFs, construída com Streamlit.

## 🚀 Funcionalidades

### 📄 Conversões de PDF

- **PDF → Word (DOCX)**: Converte PDFs para documentos Word editáveis
- **PDF → Excel (XLSX)**: Extrai tabelas e dados para planilhas Excel
- **PDF → PowerPoint (PPTX)**: Converte PDFs para apresentações PowerPoint

### 🔄 Manipulação de Páginas

- **Extrair páginas**: Seleciona páginas específicas para criar um novo PDF
- **Girar páginas**: Rotaciona páginas em 90°, 180° ou 270°
- **Remover páginas**: Remove páginas indesejadas do PDF

### 🖼️ PDF ↔ Imagens

- **PDF → Imagens**: Converte páginas do PDF para PNG ou JPEG
- **Imagens → PDF**: Combina múltiplas imagens em um único PDF
- **Configuração de DPI**: Controle da qualidade das imagens geradas

### 📝 Extração de Texto

- **HTML**: Extrai texto e salva em formato HTML
- **XML**: Converte conteúdo para XML estruturado
- **Texto Simples**: Extrai texto puro para edição

## 🛠️ Tecnologias

- **Streamlit**: Framework web para Python
- **PyPDF**: Manipulação de PDFs
- **pdf2image**: Conversão PDF para imagens
- **pdf2docx**: Conversão PDF para Word
- **Pillow**: Processamento de imagens
- **pdfminer**: Extração de texto

## 📦 Instalação Local

1. **Clone o repositório:**

```bash
git clone <seu-repositorio>
cd streamlit
```

2. **Crie um ambiente virtual:**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

4. **Execute a aplicação:**

```bash
streamlit run app.py
```

## ☁️ Deploy no Streamlit Cloud

1. **Faça push do código para o GitHub**

2. **Acesse [share.streamlit.io](https://share.streamlit.io)**

3. **Conecte sua conta GitHub e selecione o repositório**

4. **Configure o deploy:**
   - **Main file path**: `streamlit/app.py`
   - **Python version**: 3.10+

5. **Deploy!** 🚀

## ⚠️ Limitações do Streamlit Cloud

- **LibreOffice**: Conversões Office podem não funcionar devido à ausência do LibreOffice
- **Poppler**: Conversões PDF→Imagem podem ter limitações
- **Arquivos temporários**: Limpeza automática após processamento

## 🎯 Como Usar

1. **Acesse a aplicação web**
2. **Escolha uma ferramenta no menu lateral**
3. **Faça upload do arquivo PDF**
4. **Configure as opções desejadas**
5. **Clique em "Converter" ou "Processar"**
6. **Baixe o resultado**

## 📁 Estrutura do Projeto

```
streamlit/
├── app.py                 # Aplicação principal
├── requirements.txt       # Dependências Python
├── .streamlit/
│   └── config.toml       # Configurações do Streamlit
└── README.md             # Este arquivo
```

## 🔧 Configurações

O arquivo `.streamlit/config.toml` contém:

- **Tema personalizado** com cores azuis
- **Configurações de servidor** otimizadas
- **Desabilitação de coleta de dados**

## 🐛 Solução de Problemas

### Erro de dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Problemas com Poppler (PDF→Imagem)

- Instale Poppler localmente
- Ou use conversões alternativas

### Limitações de memória

- Processe arquivos menores
- Use compressão de imagens

## 📞 Suporte

Para problemas ou sugestões:

1. Abra uma issue no GitHub
2. Verifique a documentação do Streamlit
3. Consulte os logs de erro da aplicação

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

---

**Desenvolvido com ❤️ usando Streamlit**
