# 🚀 Guia de Deploy - Streamlit Cloud

## Pré-requisitos

1. **Conta no GitHub** (gratuita)
2. **Repositório público** com o código
3. **Conta no Streamlit Cloud** (gratuita)

## Passo a Passo

### 1. Preparar o Repositório

```bash
# No diretório streamlit/
git init
git add .
git commit -m "Initial commit: PDF Tools Web App"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

### 2. Acessar Streamlit Cloud

1. Vá para [share.streamlit.io](https://share.streamlit.io)
2. Clique em "Sign in with GitHub"
3. Autorize o Streamlit a acessar seus repositórios

### 3. Criar Nova App

1. Clique em "New app"
2. Preencha os campos:
   - **Repository**: `SEU_USUARIO/SEU_REPOSITORIO`
   - **Branch**: `main`
   - **Main file path**: `streamlit/app.py`
   - **App URL**: `pdf-tools-webapp` (ou escolha outro nome)

### 4. Configurações Avançadas (Opcional)

Se precisar de configurações especiais, adicione um arquivo `.streamlit/secrets.toml`:

```toml
# .streamlit/secrets.toml
[general]
debug_mode = false
max_file_size = "200MB"
```

### 5. Deploy

1. Clique em "Deploy!"
2. Aguarde o build (2-5 minutos)
3. Sua app estará disponível em: `https://pdf-tools-webapp.streamlit.app`

## 🔧 Configurações Importantes

### Arquivo Principal

- **Caminho**: `streamlit/app.py`
- **Nome**: Deve ser `app.py` ou especificar no deploy

### Dependências

- **Arquivo**: `requirements.txt` na raiz do projeto
- **Versões**: Especifique versões exatas para estabilidade

### Limitações do Streamlit Cloud

- **Memória**: 1GB RAM
- **CPU**: 1 core
- **Armazenamento**: 1GB
- **Timeout**: 30 segundos por request

## 🐛 Solução de Problemas

### Erro de Build

```bash
# Verificar logs no Streamlit Cloud
# Verificar se requirements.txt está correto
# Verificar se app.py está no caminho correto
```

### Dependências Externas

- **LibreOffice**: Não disponível (conversões Office limitadas)
- **Poppler**: Não disponível (PDF→Imagem limitado)

### Alternativas

```python
# Para PDF→Imagem, use:
from pdf2image import convert_from_path
# Pode não funcionar sem Poppler

# Para Office, use:
# Apenas PDF→Word com pdf2docx funciona
```

## 📊 Monitoramento

### Logs

- Acesse a dashboard do Streamlit Cloud
- Veja logs em tempo real
- Monitore uso de recursos

### Métricas

- **Visitas**: Número de usuários únicos
- **Uptime**: Tempo de disponibilidade
- **Performance**: Tempo de resposta

## 🔄 Atualizações

### Deploy Automático

- Push para `main` = deploy automático
- Push para outras branches = não afeta produção

### Deploy Manual

1. Vá para a dashboard da app
2. Clique em "Reboot app"
3. Aguarde o restart

## 💡 Dicas de Otimização

### Performance

```python
# Cache de funções pesadas
@st.cache_data
def process_pdf(file):
    # processamento
    return result
```

### Memória

```python
# Limpeza de arquivos temporários
import tempfile
import os

# Sempre limpar após uso
os.unlink(temp_file)
```

### UX

```python
# Progress bars para operações longas
with st.spinner("Processando..."):
    result = process_file()
```

## 🎯 Próximos Passos

1. **Teste localmente** antes do deploy
2. **Monitore performance** após deploy
3. **Colete feedback** dos usuários
4. **Itere e melhore** baseado no uso

## 📞 Suporte

- **Streamlit Docs**: [docs.streamlit.io](https://docs.streamlit.io)
- **Community**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **GitHub Issues**: Para bugs específicos

---

**Boa sorte com seu deploy! 🚀**
