import streamlit as st
import os
import tempfile
from pathlib import Path
import zipfile
import shutil
from typing import List, Optional
import io
import subprocess

# Imports diretos das bibliotecas (evita import circular com app.py da raiz)
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_path
from PIL import Image
from pdfminer.high_level import extract_text
from pdf2docx import Converter as PDF2DocxConverter

# Registrar suporte para HEIC/HEIF
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass  # Se pillow-heif não estiver instalado, continua sem suporte HEIC

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


def _libreoffice_convert(input_path: str, output_dir: str, target_filter: str) -> str:
    """Converte via LibreOffice headless. Retorna caminho convertido.
    Observação: no Streamlit Cloud, LibreOffice pode não estar disponível.
    """
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        target_filter,
        "--outdir",
        output_dir,
        input_path,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        # Tentativa em Windows/nome alternativo
        cmd[0] = "soffice.exe"
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    target = target_filter.lower()
    if target.startswith("pdf"):
        converted = os.path.join(output_dir, f"{base_name}.pdf")
    elif target.startswith("docx"):
        converted = os.path.join(output_dir, f"{base_name}.docx")
    elif target.startswith("pptx"):
        converted = os.path.join(output_dir, f"{base_name}.pptx")
    elif target.startswith("xlsx"):
        converted = os.path.join(output_dir, f"{base_name}.xlsx")
    else:
        raise RuntimeError("Formato alvo não suportado pelo conversor.")
    if not os.path.exists(converted):
        raise RuntimeError("Falha na conversão via LibreOffice: arquivo convertido não encontrado.")
    return converted


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
            "🖼️ HEIC → JPEG",
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
    elif tool == "🖼️ HEIC → JPEG":
        show_heic_to_jpeg()
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
                "Escolha imagens (PNG, JPG, JPEG, HEIC)",
                type=['png', 'jpg', 'jpeg', 'heic', 'heif'],
                accept_multiple_files=True,
                help="Faça upload das imagens para converter em PDF. Arquivos HEIC serão convertidos automaticamente para JPEG."
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
                    # Verificar se é arquivo HEIC/HEIF
                    file_ext = uploaded_file.name.split('.')[-1].lower()
                    if file_ext in ['heic', 'heif']:
                        # Converter HEIC para JPEG temporariamente
                        img = Image.open(uploaded_file)
                        # Converter para RGB se necessário
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        pil_images.append(img)
                    else:
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

def show_heic_to_jpeg():
    st.header("🖼️ HEIC → JPEG")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Upload de Arquivos HEIC")
        uploaded_files = st.file_uploader(
            "Escolha arquivos HEIC/HEIF",
            type=['heic', 'heif'],
            accept_multiple_files=True,
            help="Faça upload dos arquivos HEIC para converter em JPEG"
        )
    
    with col2:
        st.subheader("⚙️ Configurações")
        st.info("💡 Arquivos HEIC serão convertidos para JPEG com qualidade 95%")
        quality = st.slider("Qualidade JPEG:", 50, 100, 95)
        st.warning("⚠️ Requer pillow-heif instalado. Instale com: pip install pillow-heif")
    
    if uploaded_files and st.button("🚀 Converter para JPEG", type="primary"):
        with st.spinner("Convertendo arquivos HEIC para JPEG..."):
            try:
                converted_files = []
                temp_dir = tempfile.mkdtemp()
                
                for uploaded_file in uploaded_files:
                    # Abrir imagem HEIC
                    img = Image.open(uploaded_file)
                    
                    # Converter para RGB se necessário
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    
                    # Criar nome do arquivo de saída
                    base_name = os.path.splitext(uploaded_file.name)[0]
                    output_path = os.path.join(temp_dir, f"{base_name}.jpeg")
                    
                    # Salvar como JPEG
                    img.save(output_path, "JPEG", quality=quality)
                    converted_files.append((output_path, f"{base_name}.jpeg"))
                
                if not converted_files:
                    st.error("❌ Nenhum arquivo convertido.")
                    return
                
                # Se houver múltiplos arquivos, criar ZIP
                if len(converted_files) > 1:
                    zip_path = "heic_convertidos.zip"
                    with zipfile.ZipFile(zip_path, 'w') as zip_file:
                        for file_path, file_name in converted_files:
                            zip_file.write(file_path, file_name)
                    
                    # Download do ZIP
                    with open(zip_path, "rb") as file:
                        st.download_button(
                            label=f"📥 Baixar ZIP com {len(converted_files)} imagens JPEG",
                            data=file.read(),
                            file_name=zip_path,
                            mime="application/zip"
                        )
                    st.success(f"✅ Conversão concluída! {len(converted_files)} arquivos convertidos para JPEG.")
                    
                    # Limpar ZIP
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                else:
                    # Download único
                    file_path, file_name = converted_files[0]
                    with open(file_path, "rb") as file:
                        st.download_button(
                            label=f"📥 Baixar {file_name}",
                            data=file.read(),
                            file_name=file_name,
                            mime="image/jpeg"
                        )
                    st.success(f"✅ Conversão concluída! {file_name} está pronto para download.")
                
            except Exception as e:
                error_msg = str(e)
                if "heif" in error_msg.lower() or "heic" in error_msg.lower():
                    st.error(f"❌ Erro: Não foi possível abrir o arquivo HEIC. Certifique-se de que pillow-heif está instalado: pip install pillow-heif")
                else:
                    st.error(f"❌ Erro na conversão: {error_msg}")
            finally:
                # Limpar arquivos temporários
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)

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
