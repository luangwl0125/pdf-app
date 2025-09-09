import streamlit as st
import os
import tempfile
from pathlib import Path
import zipfile
from typing import List, Optional
import io

# Importar funções do app principal
import sys
sys.path.append('..')
from app import (
    _get_first_pdf, _parse_pages, _save_writer, _libreoffice_convert,
    PdfReader, PdfWriter, convert_from_path, Image, extract_text,
    PDF2DocxConverter
)

# Configuração da página
st.set_page_config(
    page_title="PDF Tools - Web App",
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

def main():
    st.markdown('<h1 class="main-header">📄 PDF Tools - Web App</h1>', unsafe_allow_html=True)
    
    # Sidebar para navegação
    st.sidebar.title("🔧 Ferramentas")
    
    # Menu de opções
    tool = st.sidebar.selectbox(
        "Escolha uma ferramenta:",
        [
            "📄 Conversões de PDF",
            "🔄 Manipulação de Páginas", 
            "🖼️ PDF ↔ Imagens",
            "📊 Office ↔ PDF",
            "📝 Texto (HTML/XML)"
        ]
    )
    
    if tool == "📄 Conversões de PDF":
        show_pdf_conversions()
    elif tool == "🔄 Manipulação de Páginas":
        show_page_manipulation()
    elif tool == "🖼️ PDF ↔ Imagens":
        show_image_conversions()
    elif tool == "📊 Office ↔ PDF":
        show_office_conversions()
    elif tool == "📝 Texto (HTML/XML)":
        show_text_extractions()

def show_pdf_conversions():
    st.header("📄 Conversões de PDF")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload de PDF")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo PDF",
            type=['pdf'],
            help="Faça upload do arquivo PDF que deseja converter"
        )
    
    with col2:
        st.subheader("⚙️ Opções de Conversão")
        
        conversion_type = st.selectbox(
            "Tipo de conversão:",
            ["PDF → Word (DOCX)", "PDF → Excel (XLSX)", "PDF → PowerPoint (PPTX)"]
        )
        
        if conversion_type == "PDF → Word (DOCX)":
            output_format = "docx"
            output_name = "documento.docx"
        elif conversion_type == "PDF → Excel (XLSX)":
            output_format = "xlsx"
            output_name = "planilha.xlsx"
        else:  # PowerPoint
            output_format = "pptx"
            output_name = "apresentacao.pptx"
    
    if uploaded_file and st.button("🚀 Converter", type="primary"):
        with st.spinner("Convertendo arquivo..."):
            try:
                # Salvar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Converter
                if output_format == "docx":
                    conv = PDF2DocxConverter(tmp_path)
                    conv.convert(output_name)
                    conv.close()
                else:
                    # Para Excel e PPT, usar LibreOffice
                    temp_dir = tempfile.mkdtemp()
                    converted_path = _libreoffice_convert(tmp_path, temp_dir, output_format)
                    os.rename(converted_path, output_name)
                
                # Limpar arquivo temporário
                os.unlink(tmp_path)
                
                # Download
                with open(output_name, "rb") as file:
                    st.download_button(
                        label=f"📥 Baixar {output_name}",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/octet-stream"
                    )
                
                st.success(f"✅ Conversão concluída! {output_name} está pronto para download.")
                
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

def show_image_conversions():
    st.header("🖼️ PDF ↔ Imagens")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload")
        conversion_direction = st.radio(
            "Direção da conversão:",
            ["PDF → Imagens", "Imagens → PDF"]
        )
        
        if conversion_direction == "PDF → Imagens":
            uploaded_file = st.file_uploader(
                "Escolha um arquivo PDF",
                type=['pdf'],
                help="Faça upload do arquivo PDF para converter em imagens"
            )
        else:
            uploaded_files = st.file_uploader(
                "Escolha imagens (PNG, JPG, JPEG)",
                type=['png', 'jpg', 'jpeg'],
                accept_multiple_files=True,
                help="Faça upload das imagens para converter em PDF"
            )
    
    with col2:
        st.subheader("⚙️ Configurações")
        
        if conversion_direction == "PDF → Imagens":
            col_a, col_b = st.columns(2)
            with col_a:
                format_img = st.selectbox("Formato:", ["png", "jpeg"])
            with col_b:
                dpi = st.slider("DPI:", 100, 300, 200)
            
            pages_input = st.text_input(
                "Páginas (vazio = todas):",
                placeholder="1,3,5 ou deixe vazio para todas"
            )
        else:
            st.info("As imagens serão convertidas na ordem de upload.")
    
    if uploaded_file and conversion_direction == "PDF → Imagens" and st.button("🚀 Converter para Imagens", type="primary"):
        with st.spinner("Convertendo PDF para imagens..."):
            try:
                # Salvar arquivo temporário
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Criar diretório temporário para imagens
                temp_dir = tempfile.mkdtemp()
                
                reader = PdfReader(tmp_path)
                pages = _parse_pages(pages_input, len(reader.pages)) if pages_input else list(range(len(reader.pages)))
                
                # Converter páginas
                for idx in pages:
                    imgs = convert_from_path(tmp_path, dpi=dpi, first_page=idx + 1, last_page=idx + 1)
                    img = imgs[0]
                    output_path = os.path.join(temp_dir, f"pagina_{idx+1}.{format_img}")
                    if format_img.lower() == "jpeg":
                        img = img.convert("RGB")
                    img.save(output_path, quality=95) if format_img.lower() == "jpeg" else img.save(output_path)
                
                # Criar ZIP com as imagens
                zip_path = "imagens_convertidas.zip"
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for file_name in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, file_name)
                        zip_file.write(file_path, file_name)
                
                # Limpar arquivos temporários
                os.unlink(tmp_path)
                import shutil
                shutil.rmtree(temp_dir)
                
                # Download
                with open(zip_path, "rb") as file:
                    st.download_button(
                        label="📥 Baixar ZIP com imagens",
                        data=file.read(),
                        file_name=zip_path,
                        mime="application/zip"
                    )
                
                st.success(f"✅ Conversão concluída! {len(pages)} imagens geradas.")
                
            except Exception as e:
                st.error(f"❌ Erro na conversão: {str(e)}")
            finally:
                # Limpar arquivos gerados
                if os.path.exists(zip_path):
                    os.remove(zip_path)
    
    elif uploaded_files and conversion_direction == "Imagens → PDF" and st.button("🚀 Converter para PDF", type="primary"):
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

def show_office_conversions():
    st.header("📊 Office ↔ PDF")
    
    st.info("⚠️ Conversões Office requerem LibreOffice instalado. Funcionalidade limitada em ambiente web.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload")
        uploaded_file = st.file_uploader(
            "Escolha um arquivo Office ou PDF",
            type=['pdf', 'docx', 'xlsx', 'pptx'],
            help="Faça upload do arquivo para converter"
        )
    
    with col2:
        st.subheader("⚙️ Conversão")
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()
            
            if file_type == 'pdf':
                conversion_options = ["PDF → Word", "PDF → Excel", "PDF → PowerPoint"]
            else:
                conversion_options = [f"{file_type.upper()} → PDF"]
            
            conversion = st.selectbox("Converter para:", conversion_options)
    
    if uploaded_file and st.button("🚀 Converter", type="primary"):
        st.warning("⚠️ Conversões Office podem não funcionar em ambiente web devido a dependências do LibreOffice.")

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
