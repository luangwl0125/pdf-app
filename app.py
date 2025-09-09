import streamlit as st
import os
import tempfile
from typing import List, Optional

# Imports diretos das bibliotecas
from pypdf import PdfReader, PdfWriter
from PIL import Image
from pdfminer.high_level import extract_text
from pdf2docx import Converter as PDF2DocxConverter

# Configuração da página
st.set_page_config(
    page_title="PDF Tools - Especialmente para o Kleber",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .feature-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Utilitários locais

def _save_writer(writer: PdfWriter, output_path: str) -> None:
    with open(output_path, "wb") as f:
        writer.write(f)


def _parse_pages(pages: str, max_index: int) -> List[int]:
    """Converte "1,2,5-8" (1-based) em índices 0-based ordenados e únicos."""
    indices: List[int] = []
    if not pages:
        return indices
    parts = [p.strip() for p in pages.split(",") if p.strip()]
    for part in parts:
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s)
            end = int(end_s)
            if start < 1 or end < start or end > max_index:
                raise ValueError("Intervalo de páginas inválido.")
            indices.extend(list(range(start - 1, end)))
        else:
            idx = int(part)
            if idx < 1 or idx > max_index:
                raise ValueError("Número de página fora do intervalo.")
            indices.append(idx - 1)
    # Remover duplicatas mantendo ordem
    seen = set()
    ordered: List[int] = []
    for i in indices:
        if i not in seen:
            seen.add(i)
            ordered.append(i)
    return ordered




def main():
    st.markdown('<h1 class="main-header">📄 PDF Tools - Especialmente para o Kleber</h1>', unsafe_allow_html=True)
    
    # Sidebar para navegação
    st.sidebar.title("🔧 Ferramentas")
    
    # Menu de opções
    tool = st.sidebar.selectbox(
        "Escolha uma ferramenta:",
        [
            "📄 PDF → Word",
            "🔄 Manipulação de Páginas", 
            "🖼️ Imagens → PDF",
            "📝 Texto (HTML/XML)"
        ]
    )
    
    if tool == "📄 PDF → Word":
        show_pdf_to_word()
    elif tool == "🔄 Manipulação de Páginas":
        show_page_manipulation()
    elif tool == "🖼️ Imagens → PDF":
        show_images_to_pdf()
    elif tool == "📝 Texto (HTML/XML)":
        show_text_extractions()

def show_pdf_to_word():
    st.header("📄 PDF → Word")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload de PDF")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo PDF",
            type=['pdf'],
            help="Faça upload do arquivo PDF que deseja converter para Word"
        )
    
    with col2:
        st.subheader("⚙️ Conversão")
        st.info("💡 Converte PDF para documento Word editável (DOCX)")
        st.warning("⚠️ A qualidade da conversão depende do layout do PDF original")
    
    if uploaded_file and st.button("🚀 Converter para Word", type="primary"):
        with st.spinner("Convertendo PDF para Word..."):
            try:
                # Salvar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Converter para Word
                output_name = "documento.docx"
                conv = PDF2DocxConverter(tmp_path)
                conv.convert(output_name)
                conv.close()
                
                # Limpar arquivo temporário
                os.unlink(tmp_path)
                
                # Download
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.docx",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                st.success("✅ Conversão concluída! documento.docx está pronto para download.")
                
            except Exception as e:
                st.error(f"❌ Erro na conversão: {str(e)}")
            finally:
                # Limpar arquivos gerados
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_page_manipulation():
    st.header("🔄 Manipulação de Páginas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload de PDF")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo PDF",
            type=['pdf'],
            help="Faça upload do arquivo PDF que deseja manipular"
        )
    
    with col2:
        st.subheader("⚙️ Operações")
        
        operation = st.selectbox(
            "Operação:",
            ["Extrair páginas", "Girar páginas", "Remover páginas"]
        )
        
        if operation == "Extrair páginas":
            pages_input = st.text_input(
                "Páginas para extrair (ex: 1-3,7,10-12):",
                placeholder="1-3,7,10-12",
                help="Use números e intervalos separados por vírgula"
            )
        elif operation == "Girar páginas":
            col_a, col_b = st.columns(2)
            with col_a:
                angle = st.selectbox("Ângulo:", ["90", "180", "270"])
            with col_b:
                pages_input = st.text_input(
                    "Páginas para girar (vazio = todas):",
                    placeholder="1,3,5 ou deixe vazio para todas"
                )
        else:  # Remover páginas
            pages_input = st.text_input(
                "Páginas para remover (ex: 2,5,8-10):",
                placeholder="2,5,8-10",
                help="Use números e intervalos separados por vírgula"
            )
    
    if uploaded_file and st.button("🚀 Processar", type="primary"):
        with st.spinner("Processando PDF..."):
            try:
                # Salvar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                writer = PdfWriter()
                
                if operation == "Extrair páginas":
                    if not pages_input:
                        st.error("❌ Especifique as páginas para extrair.")
                        return
                    indices = _parse_pages(pages_input, len(reader.pages))
                    for i in indices:
                        writer.add_page(reader.pages[i])
                    output_name = "paginas_extraidas.pdf"
                    
                elif operation == "Girar páginas":
                    indices = set(_parse_pages(pages_input, len(reader.pages))) if pages_input else set(range(len(reader.pages)))
                    angle_val = int(angle)
                    for i, page in enumerate(reader.pages):
                        if i in indices:
                            page.rotate(angle_val)
                        writer.add_page(page)
                    output_name = f"rotacionado_{angle}graus.pdf"
                    
                else:  # Remover páginas
                    if not pages_input:
                        st.error("❌ Especifique as páginas para remover.")
                        return
                    remove_set = set(_parse_pages(pages_input, len(reader.pages)))
                    for i, page in enumerate(reader.pages):
                        if i not in remove_set:
                            writer.add_page(page)
                    output_name = "paginas_removidas.pdf"
                
                # Salvar resultado
                _save_writer(writer, output_name)
                
                # Limpar arquivo temporário
                os.unlink(tmp_path)
                
                # Download
                with open(output_name, "rb") as file:
                    st.download_button(
                        label=f"📥 Baixar {output_name}",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                
                st.success(f"✅ Operação concluída! {output_name} está pronto para download.")
                
            except Exception as e:
                st.error(f"❌ Erro no processamento: {str(e)}")
            finally:
                # Limpar arquivos gerados
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_images_to_pdf():
    st.header("🖼️ Imagens → PDF")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload de Imagens")
        uploaded_files = st.file_uploader(
            "Escolha imagens (PNG, JPG, JPEG)",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            help="Faça upload das imagens para converter em PDF"
        )
    
    with col2:
        st.subheader("⚙️ Configurações")
        st.info("💡 As imagens serão convertidas na ordem de upload")
        st.warning("⚠️ Imagens RGBA serão convertidas para RGB automaticamente")
    
    if uploaded_files and st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo imagens para PDF..."):
            try:
                pil_images = []
                for uploaded_file in uploaded_files:
                    img = Image.open(uploaded_file)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    pil_images.append(img)
                
                if not pil_images:
                    st.error("❌ Nenhuma imagem válida encontrada.")
                    return
                
                # Criar PDF
                output_name = "imagens_convertidas.pdf"
                primeira, restantes = pil_images[0], pil_images[1:]
                primeira.save(output_name, save_all=True, append_images=restantes)
                
                # Download
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                
                st.success(f"✅ Conversão concluída! PDF com {len(pil_images)} imagens gerado.")
                
            except Exception as e:
                st.error(f"❌ Erro na conversão: {str(e)}")
            finally:
                # Limpar arquivos gerados
                if os.path.exists(output_name):
                    os.remove(output_name)


def show_text_extractions():
    st.header("📝 Extração de Texto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload de PDF")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo PDF",
            type=['pdf'],
            help="Faça upload do arquivo PDF para extrair texto"
        )
    
    with col2:
        st.subheader("⚙️ Formato de Saída")
        output_format = st.selectbox(
            "Formato:",
            ["HTML", "XML", "Texto Simples"]
        )
    
    if uploaded_file and st.button("🚀 Extrair Texto", type="primary"):
        with st.spinner("Extraindo texto..."):
            try:
                # Salvar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Extrair texto
                texto = extract_text(tmp_path) or ""
                
                if output_format == "HTML":
                    content = f"""<!DOCTYPE html><html lang="pt-br"><meta charset="utf-8"><body><pre>{texto}</pre></body></html>"""
                    output_name = "texto_extraido.html"
                    mime_type = "text/html"
                elif output_format == "XML":
                    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<documento>
  <conteudo>{texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</conteudo>
</documento>"""
                    output_name = "texto_extraido.xml"
                    mime_type = "application/xml"
                else:  # Texto simples
                    content = texto
                    output_name = "texto_extraido.txt"
                    mime_type = "text/plain"
                
                # Salvar arquivo
                with open(output_name, "w", encoding="utf-8") as f:
                    f.write(content)
                
                # Limpar arquivo temporário
                os.unlink(tmp_path)
                
                # Download
                with open(output_name, "rb") as file:
                    st.download_button(
                        label=f"📥 Baixar {output_name}",
                        data=file.read(),
                        file_name=output_name,
                        mime=mime_type
                    )
                
                # Mostrar preview do texto
                st.subheader("👀 Preview do Texto")
                st.text_area("Texto extraído:", texto, height=200)
                
                st.success(f"✅ Extração concluída! {output_name} está pronto para download.")
                
            except Exception as e:
                st.error(f"❌ Erro na extração: {str(e)}")
            finally:
                # Limpar arquivos gerados
                if os.path.exists(output_name):
                    os.remove(output_name)

if __name__ == "__main__":
    main()
