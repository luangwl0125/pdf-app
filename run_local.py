#!/usr/bin/env python3
"""
Script para executar a aplicação Streamlit localmente
"""

import subprocess
import sys
import os

def main():
    """Executa a aplicação Streamlit"""
    
    # Verificar se estamos no diretório correto
    if not os.path.exists("app.py"):
        print("❌ Erro: Execute este script no diretório streamlit/")
        print("   cd streamlit")
        print("   python run_local.py")
        sys.exit(1)
    
    # Verificar se streamlit está instalado
    try:
        import streamlit
        print(f"✅ Streamlit {streamlit.__version__} encontrado")
    except ImportError:
        print("❌ Streamlit não encontrado. Instalando...")
        subprocess.run([sys.executable, "-m", "pip", "install", "streamlit"])
    
    # Verificar dependências
    print("🔍 Verificando dependências...")
    try:
        import pypdf
        import pdf2image
        import PIL
        print("✅ Dependências principais encontradas")
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("   Execute: pip install -r requirements.txt")
        sys.exit(1)
    
    # Executar Streamlit
    print("🚀 Iniciando aplicação Streamlit...")
    print("   Acesse: http://localhost:8501")
    print("   Pressione Ctrl+C para parar")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.port", "8501"
        ])
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao executar: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
