"""
Aplicação PDF Tools - Web App Completa
Inclui módulo de scanner de documentos e todas as funcionalidades de manipulação de PDF
"""

# ============================================================================
# PARTE 1: MÓDULO DE SCANNER DE DOCUMENTOS (OCR)
# ============================================================================

import os
import tempfile
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from pypdf import PdfReader


class DocumentScanner:
    """Classe para escanear e processar documentos PDF e imagens"""
    
    def __init__(self):
        self.tesseract_available = TESSERACT_AVAILABLE
        self.pdf2image_available = PDF2IMAGE_AVAILABLE
        
    def preprocess_image(self, image: Image.Image, enhance_quality: bool = True) -> Image.Image:
        """
        Pré-processa imagem para melhorar a qualidade do OCR
        
        Args:
            image: Imagem PIL a ser processada
            enhance_quality: Se True, aplica melhorias de qualidade
            
        Returns:
            Imagem processada
        """
        if not CV2_AVAILABLE:
            # Se OpenCV não estiver disponível, usar apenas PIL
            if enhance_quality:
                return self.enhance_image(image)
            return image.convert('L') if image.mode != 'L' else image
        
        # Converter para numpy array para processamento OpenCV
        img_array = np.array(image)
        
        # Converter para escala de cinza se necessário
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        if enhance_quality:
            # Aplicar desfoque gaussiano para reduzir ruído
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # Aplicar threshold adaptativo para melhorar contraste
            thresh = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # Converter de volta para PIL Image
            processed = Image.fromarray(thresh)
        else:
            processed = Image.fromarray(gray)
        
        return processed
    
    def enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Melhora a qualidade da imagem para OCR
        
        Args:
            image: Imagem PIL
            
        Returns:
            Imagem melhorada
        """
        # Aumentar contraste
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Aumentar nitidez
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Aumentar brilho se necessário
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        return image
    
    def extract_text_from_image(
        self, 
        image: Image.Image, 
        lang: str = 'por',
        preprocess: bool = True,
        enhance: bool = True
    ) -> Dict[str, any]:
        """
        Extrai texto de uma imagem usando OCR
        
        Args:
            image: Imagem PIL
            lang: Idioma para OCR (padrão: português)
            preprocess: Se True, aplica pré-processamento
            enhance: Se True, melhora a qualidade da imagem
            
        Returns:
            Dicionário com texto extraído e metadados
        """
        if not self.tesseract_available:
            raise ImportError(
                "pytesseract não está instalado. "
                "Instale com: pip install pytesseract\n"
                "E instale o Tesseract OCR: https://github.com/tesseract-ocr/tesseract"
            )
        
        # Pré-processar imagem
        if preprocess:
            processed_image = self.preprocess_image(image, enhance_quality=enhance)
        else:
            processed_image = image
        
        # Melhorar qualidade se solicitado
        if enhance and not preprocess:
            processed_image = self.enhance_image(processed_image)
        
        # Extrair texto usando Tesseract
        try:
            # Configuração do Tesseract para melhor precisão
            custom_config = r'--oem 3 --psm 6'
            
            # Extrair texto simples
            text = pytesseract.image_to_string(processed_image, lang=lang, config=custom_config)
            
            # Extrair dados estruturados
            data = pytesseract.image_to_data(
                processed_image, 
                lang=lang, 
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Extrair informações de confiança
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence,
                'word_count': len(text.split()),
                'char_count': len(text),
                'data': data
            }
        except Exception as e:
            return {
                'text': '',
                'confidence': 0,
                'word_count': 0,
                'char_count': 0,
                'error': str(e),
                'data': {}
            }
    
    def extract_text_from_pdf(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
        lang: str = 'por',
        dpi: int = 300,
        preprocess: bool = True,
        enhance: bool = True
    ) -> Dict[str, any]:
        """
        Extrai texto de um PDF usando OCR
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            pages: Lista de páginas para processar (None = todas)
            lang: Idioma para OCR
            dpi: Resolução para conversão de PDF para imagem
            preprocess: Se True, aplica pré-processamento
            enhance: Se True, melhora a qualidade
            
        Returns:
            Dicionário com texto extraído por página e estatísticas
        """
        if not self.pdf2image_available:
            raise ImportError(
                "pdf2image não está instalado. "
                "Instale com: pip install pdf2image\n"
                "E instale o poppler: https://poppler.freedesktop.org/"
            )
        
        # Ler PDF
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # Determinar páginas para processar
        if pages is None:
            pages_to_process = list(range(total_pages))
        else:
            # Converter de 1-based para 0-based
            pages_to_process = [p - 1 for p in pages if 1 <= p <= total_pages]
        
        # Converter PDF para imagens
        images = convert_from_path(pdf_path, dpi=dpi, first_page=1, last_page=total_pages)
        
        results = {
            'total_pages': total_pages,
            'processed_pages': len(pages_to_process),
            'pages': {},
            'full_text': '',
            'total_confidence': 0,
            'total_words': 0,
            'total_chars': 0
        }
        
        # Processar cada página
        for page_idx in pages_to_process:
            if page_idx < len(images):
                image = images[page_idx]
                page_result = self.extract_text_from_image(
                    image, 
                    lang=lang, 
                    preprocess=preprocess, 
                    enhance=enhance
                )
                
                results['pages'][page_idx + 1] = page_result
                results['full_text'] += f"\n\n--- Página {page_idx + 1} ---\n\n"
                results['full_text'] += page_result.get('text', '')
                results['total_words'] += page_result.get('word_count', 0)
                results['total_chars'] += page_result.get('char_count', 0)
                
                if 'confidence' in page_result:
                    results['total_confidence'] += page_result['confidence']
        
        # Calcular confiança média
        if results['processed_pages'] > 0:
            results['avg_confidence'] = results['total_confidence'] / results['processed_pages']
        else:
            results['avg_confidence'] = 0
        
        return results
    
    def scan_document(
        self,
        file_path: str,
        file_type: str = 'auto',
        lang: str = 'por',
        dpi: int = 300,
        preprocess: bool = True,
        enhance: bool = True,
        pages: Optional[List[int]] = None
    ) -> Dict[str, any]:
        """
        Escaneia um documento (PDF ou imagem) e extrai texto
        
        Args:
            file_path: Caminho para o arquivo
            file_type: Tipo do arquivo ('pdf', 'image', 'auto')
            lang: Idioma para OCR
            dpi: Resolução para PDFs
            preprocess: Aplicar pré-processamento
            enhance: Melhorar qualidade
            pages: Páginas específicas para PDFs (None = todas)
            
        Returns:
            Dicionário com resultados do scan
        """
        # Detectar tipo de arquivo
        if file_type == 'auto':
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                file_type = 'pdf'
            elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                file_type = 'image'
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {ext}")
        
        if file_type == 'pdf':
            return self.extract_text_from_pdf(
                file_path, 
                pages=pages, 
                lang=lang, 
                dpi=dpi,
                preprocess=preprocess,
                enhance=enhance
            )
        elif file_type == 'image':
            image = Image.open(file_path)
            result = self.extract_text_from_image(
                image, 
                lang=lang, 
                preprocess=preprocess, 
                enhance=enhance
            )
            return {
                'full_text': result.get('text', ''),
                'confidence': result.get('confidence', 0),
                'word_count': result.get('word_count', 0),
                'char_count': result.get('char_count', 0),
                'pages': {1: result}
            }
        else:
            raise ValueError(f"Tipo de arquivo inválido: {file_type}")
    
    def batch_scan(
        self,
        file_paths: List[str],
        lang: str = 'por',
        dpi: int = 300,
        preprocess: bool = True,
        enhance: bool = True
    ) -> Dict[str, any]:
        """
        Escaneia múltiplos documentos em lote
        
        Args:
            file_paths: Lista de caminhos de arquivos
            lang: Idioma para OCR
            dpi: Resolução para PDFs
            preprocess: Aplicar pré-processamento
            enhance: Melhorar qualidade
            
        Returns:
            Dicionário com resultados de todos os documentos
        """
        results = {
            'total_files': len(file_paths),
            'processed_files': 0,
            'files': {},
            'errors': []
        }
        
        for file_path in file_paths:
            try:
                file_result = self.scan_document(
                    file_path,
                    lang=lang,
                    dpi=dpi,
                    preprocess=preprocess,
                    enhance=enhance
                )
                results['files'][file_path] = file_result
                results['processed_files'] += 1
            except Exception as e:
                results['errors'].append({
                    'file': file_path,
                    'error': str(e)
                })
        
        return results
    
    def is_available(self) -> bool:
        """Verifica se as dependências necessárias estão disponíveis"""
        return self.tesseract_available and self.pdf2image_available
    
    def is_opencv_available(self) -> bool:
        """Verifica se OpenCV está disponível"""
        return CV2_AVAILABLE
    
    def get_supported_languages(self) -> List[str]:
        """Retorna lista de idiomas suportados pelo Tesseract"""
        if not self.tesseract_available:
            return []
        
        try:
            langs = pytesseract.get_languages()
            return langs
        except:
            return ['por', 'eng']  # Idiomas padrão


def create_scanner() -> DocumentScanner:
    """Factory function para criar instância do scanner"""
    return DocumentScanner()


# ============================================================================
# PARTE 2: APLICAÇÃO STREAMLIT COMPLETA
# ============================================================================

import streamlit as st
import zipfile
import shutil
import io
import subprocess
from collections import defaultdict

# Imports diretos das bibliotecas
from pypdf import PdfWriter
from pdfminer.high_level import extract_text
from pdf2docx import Converter as PDF2DocxConverter

# Verificar disponibilidade do scanner (agora no mesmo arquivo)
SCANNER_AVAILABLE = TESSERACT_AVAILABLE and PDF2IMAGE_AVAILABLE

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
    elif target.startswith("rtf"):
        converted = os.path.join(output_dir, f"{base_name}.rtf")
    else:
        raise RuntimeError("Formato alvo não suportado pelo conversor.")
    if not os.path.exists(converted):
        raise RuntimeError("Falha na conversão via LibreOffice: arquivo convertido não encontrado.")
    return converted


def main():
    st.markdown('<h1 class="main-header">📄 PDF Tools - Web App</h1>', unsafe_allow_html=True)
    
    # Sidebar para navegação
    st.sidebar.title("🔧 Ferramentas")
    
    # Menu de opções - 5 seções principais
    section = st.sidebar.selectbox(
        "Escolha uma seção:",
        [
            "📤 Converter PDF para outros formatos",
            "📥 Converter arquivos em arquivos PDF",
            "📑 Gerenciar páginas",
            "🗜️ Compactar e anotar",
            "🔍 Escanear documentos (OCR)"
        ]
    )
    
    if section == "📤 Converter PDF para outros formatos":
        show_convert_pdf_to_other_formats()
    elif section == "📥 Converter arquivos em arquivos PDF":
        show_convert_files_to_pdf()
    elif section == "📑 Gerenciar páginas":
        show_manage_pages()
    elif section == "🗜️ Compactar e anotar":
        show_compress_and_annotate()
    elif section == "🔍 Escanear documentos (OCR)":
        show_scan_documents()

# ============================================================================
# SEÇÃO 1: Converter PDF para outros formatos
# ============================================================================

def show_convert_pdf_to_other_formats():
    st.header("📤 Converter PDF para outros formatos")
    
    conversion_type = st.selectbox(
        "Selecione o tipo de conversão:",
        [
            "PDF para Word",
            "PDF para Excel",
            "PDF para PPT",
            "PDF para PNG",
            "PDF para JPEG",
            "PDF para XML",
            "PDF para TXT",
            "PDF para RTF",
            "PDF para Páginas Web"
        ]
    )
    
    uploaded_file = st.file_uploader(
        "Escolha um arquivo PDF",
        type=['pdf'],
        help="Faça upload do arquivo PDF que deseja converter"
    )
    
    if uploaded_file:
        if conversion_type == "PDF para Word":
            convert_pdf_to_word(uploaded_file)
        elif conversion_type == "PDF para Excel":
            convert_pdf_to_excel(uploaded_file)
        elif conversion_type == "PDF para PPT":
            convert_pdf_to_ppt(uploaded_file)
        elif conversion_type == "PDF para PNG":
            convert_pdf_to_png(uploaded_file)
        elif conversion_type == "PDF para JPEG":
            convert_pdf_to_jpeg(uploaded_file)
        elif conversion_type == "PDF para XML":
            convert_pdf_to_xml(uploaded_file)
        elif conversion_type == "PDF para TXT":
            convert_pdf_to_txt(uploaded_file)
        elif conversion_type == "PDF para RTF":
            convert_pdf_to_rtf(uploaded_file)
        elif conversion_type == "PDF para Páginas Web":
            convert_pdf_to_html(uploaded_file)

def convert_pdf_to_word(uploaded_file):
    """Converte PDF para Word (DOCX)"""
    if st.button("🚀 Converter para Word", type="primary"):
        with st.spinner("Convertendo PDF para Word..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "documento.docx"
                conv = PDF2DocxConverter(tmp_path)
                conv.convert(output_name)
                conv.close()
                
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.docx",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_pdf_to_excel(uploaded_file):
    """Converte PDF para Excel (XLSX)"""
    if st.button("🚀 Converter para Excel", type="primary"):
        with st.spinner("Convertendo PDF para Excel..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "planilha.xlsx"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "xlsx")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar planilha.xlsx",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_pdf_to_ppt(uploaded_file):
    """Converte PDF para PowerPoint (PPTX)"""
    if st.button("🚀 Converter para PPT", type="primary"):
        with st.spinner("Convertendo PDF para PowerPoint..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "apresentacao.pptx"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "pptx")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar apresentacao.pptx",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_pdf_to_png(uploaded_file):
    """Converte PDF para PNG"""
    dpi = st.slider("DPI:", 100, 300, 200)
    pages_input = st.text_input("Páginas (vazio = todas):", placeholder="1,3,5 ou deixe vazio")
    
    if st.button("🚀 Converter para PNG", type="primary"):
        with st.spinner("Convertendo PDF para PNG..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                temp_dir = tempfile.mkdtemp()
                reader = PdfReader(tmp_path)
                pages = _parse_pages(pages_input, len(reader.pages)) if pages_input else list(range(len(reader.pages)))
                
                for idx in pages:
                    imgs = convert_from_path(tmp_path, dpi=dpi, first_page=idx + 1, last_page=idx + 1)
                    img = imgs[0]
                    output_path = os.path.join(temp_dir, f"pagina_{idx+1}.png")
                    img.save(output_path)
                
                zip_path = "imagens_png.zip"
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for file_name in os.listdir(temp_dir):
                        zip_file.write(os.path.join(temp_dir, file_name), file_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(zip_path, "rb") as file:
                    st.download_button(
                        label=f"📥 Baixar ZIP com {len(pages)} imagens PNG",
                        data=file.read(),
                        file_name=zip_path,
                        mime="application/zip"
                    )
                st.success(f"✅ {len(pages)} imagens PNG geradas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)

def convert_pdf_to_jpeg(uploaded_file):
    """Converte PDF para JPEG"""
    dpi = st.slider("DPI:", 100, 300, 200)
    quality = st.slider("Qualidade JPEG:", 50, 100, 95)
    pages_input = st.text_input("Páginas (vazio = todas):", placeholder="1,3,5 ou deixe vazio")
    
    if st.button("🚀 Converter para JPEG", type="primary"):
        with st.spinner("Convertendo PDF para JPEG..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                temp_dir = tempfile.mkdtemp()
                reader = PdfReader(tmp_path)
                pages = _parse_pages(pages_input, len(reader.pages)) if pages_input else list(range(len(reader.pages)))
                
                for idx in pages:
                    imgs = convert_from_path(tmp_path, dpi=dpi, first_page=idx + 1, last_page=idx + 1)
                    img = imgs[0].convert("RGB")
                    output_path = os.path.join(temp_dir, f"pagina_{idx+1}.jpeg")
                    img.save(output_path, "JPEG", quality=quality)
                
                zip_path = "imagens_jpeg.zip"
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for file_name in os.listdir(temp_dir):
                        zip_file.write(os.path.join(temp_dir, file_name), file_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(zip_path, "rb") as file:
                    st.download_button(
                        label=f"📥 Baixar ZIP com {len(pages)} imagens JPEG",
                        data=file.read(),
                        file_name=zip_path,
                        mime="application/zip"
                    )
                st.success(f"✅ {len(pages)} imagens JPEG geradas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)

def convert_pdf_to_xml(uploaded_file):
    """Converte PDF para XML"""
    if st.button("🚀 Converter para XML", type="primary"):
        with st.spinner("Convertendo PDF para XML..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                texto = extract_text(tmp_path) or ""
                content = f"""<?xml version="1.0" encoding="UTF-8"?>
<documento>
  <conteudo>{texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")}</conteudo>
</documento>"""
                output_name = "documento.xml"
                
                with open(output_name, "w", encoding="utf-8") as f:
                    f.write(content)
                
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.xml",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/xml"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_pdf_to_txt(uploaded_file):
    """Converte PDF para TXT"""
    if st.button("🚀 Converter para TXT", type="primary"):
        with st.spinner("Convertendo PDF para TXT..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                texto = extract_text(tmp_path) or ""
                output_name = "documento.txt"
                
                with open(output_name, "w", encoding="utf-8") as f:
                    f.write(texto)
                
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.txt",
                        data=file.read(),
                        file_name=output_name,
                        mime="text/plain"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_pdf_to_rtf(uploaded_file):
    """Converte PDF para RTF"""
    if st.button("🚀 Converter para RTF", type="primary"):
        with st.spinner("Convertendo PDF para RTF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "documento.rtf"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "rtf")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.rtf",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/rtf"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_pdf_to_html(uploaded_file):
    """Converte PDF para HTML (Páginas Web)"""
    if st.button("🚀 Converter para HTML", type="primary"):
        with st.spinner("Convertendo PDF para HTML..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                texto = extract_text(tmp_path) or ""
                content = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documento PDF Convertido</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; line-height: 1.6; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <pre>{texto}</pre>
</body>
</html>"""
                output_name = "documento.html"
                
                with open(output_name, "w", encoding="utf-8") as f:
                    f.write(content)
                
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.html",
                        data=file.read(),
                        file_name=output_name,
                        mime="text/html"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

# ============================================================================
# SEÇÃO 2: Converter arquivos em arquivos PDF
# ============================================================================

def show_convert_files_to_pdf():
    st.header("📥 Converter arquivos em arquivos PDF")
    
    conversion_type = st.selectbox(
        "Selecione o tipo de conversão:",
        [
            "Word para PDF",
            "Excel para PDF",
            "Imagem para PDF",
            "PPT para PDF",
            "TXT para PDF",
            "RTF para PDF"
        ]
    )
    
    if conversion_type == "Imagem para PDF":
        uploaded_files = st.file_uploader(
            "Escolha imagens",
            type=['png', 'jpg', 'jpeg', 'heic', 'heif'],
            accept_multiple_files=True
        )
        if uploaded_files:
            convert_images_to_pdf(uploaded_files)
    else:
        file_type_map = {
            "Word para PDF": ['docx', 'doc'],
            "Excel para PDF": ['xlsx', 'xls'],
            "PPT para PDF": ['pptx', 'ppt'],
            "TXT para PDF": ['txt'],
            "RTF para PDF": ['rtf']
        }
        uploaded_file = st.file_uploader(
            f"Escolha um arquivo {conversion_type.split(' para ')[0]}",
            type=file_type_map[conversion_type]
        )
        
        if uploaded_file:
            if conversion_type == "Word para PDF":
                convert_word_to_pdf(uploaded_file)
            elif conversion_type == "Excel para PDF":
                convert_excel_to_pdf(uploaded_file)
            elif conversion_type == "PPT para PDF":
                convert_ppt_to_pdf(uploaded_file)
            elif conversion_type == "TXT para PDF":
                convert_txt_to_pdf(uploaded_file)
            elif conversion_type == "RTF para PDF":
                convert_rtf_to_pdf(uploaded_file)

def convert_word_to_pdf(uploaded_file):
    """Converte Word para PDF"""
    if st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo Word para PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "documento.pdf"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "pdf")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.pdf",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_excel_to_pdf(uploaded_file):
    """Converte Excel para PDF"""
    if st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo Excel para PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "planilha.pdf"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "pdf")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar planilha.pdf",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_ppt_to_pdf(uploaded_file):
    """Converte PowerPoint para PDF"""
    if st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo PowerPoint para PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{uploaded_file.name.split(".")[-1]}') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "apresentacao.pdf"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "pdf")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar apresentacao.pdf",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_images_to_pdf(uploaded_files):
    """Converte imagens para PDF"""
    if st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo imagens para PDF..."):
            try:
                pil_images = []
                for uploaded_file in uploaded_files:
                    img = Image.open(uploaded_file)
                    if uploaded_file.name.lower().endswith(('.heic', '.heif')):
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                    else:
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                    pil_images.append(img)
                
                if not pil_images:
                    st.error("❌ Nenhuma imagem válida encontrada.")
                    return
                
                output_name = "imagens_convertidas.pdf"
                primeira, restantes = pil_images[0], pil_images[1:]
                primeira.save(output_name, save_all=True, append_images=restantes)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success(f"✅ PDF com {len(pil_images)} imagens gerado!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_txt_to_pdf(uploaded_file):
    """Converte TXT para PDF"""
    font_size = st.slider("Tamanho da fonte:", 8, 24, 12)
    
    if st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo TXT para PDF..."):
            try:
                from reportlab.lib.pagesizes import letter, A4
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import inch
                
                texto = uploaded_file.read().decode('utf-8', errors='ignore')
                output_name = "documento.pdf"
                
                c = canvas.Canvas(output_name, pagesize=A4)
                width, height = A4
                margin = inch
                y = height - margin
                line_height = font_size * 1.2
                
                lines = texto.split('\n')
                for line in lines:
                    if y < margin:
                        c.showPage()
                        y = height - margin
                    c.setFont("Helvetica", font_size)
                    c.drawString(margin, y, line[:100])  # Limitar largura
                    y -= line_height
                
                c.save()
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.pdf",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def convert_rtf_to_pdf(uploaded_file):
    """Converte RTF para PDF"""
    if st.button("🚀 Converter para PDF", type="primary"):
        with st.spinner("Convertendo RTF para PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.rtf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                output_name = "documento.pdf"
                temp_dir = tempfile.mkdtemp()
                converted_path = _libreoffice_convert(tmp_path, temp_dir, "pdf")
                os.rename(converted_path, output_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar documento.pdf",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Conversão concluída!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

# ============================================================================
# SEÇÃO 3: Gerenciar páginas
# ============================================================================

def show_manage_pages():
    st.header("📑 Gerenciar páginas")
    
    operation = st.selectbox(
        "Selecione a operação:",
        [
            "Mesclar PDF",
            "Dividir PDF",
            "Eliminar páginas",
            "Inserir páginas",
            "Cortar páginas",
            "Extrair páginas",
            "Girar páginas"
        ]
    )
    
    if operation == "Mesclar PDF":
        show_merge_pdfs()
    elif operation == "Dividir PDF":
        show_split_pdf()
    elif operation == "Eliminar páginas":
        show_remove_pages()
    elif operation == "Inserir páginas":
        show_insert_pages()
    elif operation == "Cortar páginas":
        show_crop_pages()
    elif operation == "Extrair páginas":
        show_extract_pages()
    elif operation == "Girar páginas":
        show_rotate_pages()

def show_merge_pdfs():
    """Mescla múltiplos PDFs"""
    uploaded_files = st.file_uploader(
        "Escolha múltiplos arquivos PDF",
        type=['pdf'],
        accept_multiple_files=True
    )
    
    if uploaded_files and len(uploaded_files) > 1 and st.button("🚀 Mesclar PDFs", type="primary"):
        with st.spinner("Mesclando PDFs..."):
            try:
                writer = PdfWriter()
                
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    reader = PdfReader(tmp_path)
                    for page in reader.pages:
                        writer.add_page(page)
                    os.unlink(tmp_path)
                
                output_name = "pdf_mesclado.pdf"
                _save_writer(writer, output_name)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF mesclado",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success(f"✅ {len(uploaded_files)} PDFs mesclados com sucesso!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_split_pdf():
    """Divide PDF em páginas individuais"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    
    if uploaded_file and st.button("🚀 Dividir PDF", type="primary"):
        with st.spinner("Dividindo PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                temp_dir = tempfile.mkdtemp()
                
                for i, page in enumerate(reader.pages):
                    writer = PdfWriter()
                    writer.add_page(page)
                    output_path = os.path.join(temp_dir, f"pagina_{i+1}.pdf")
                    _save_writer(writer, output_path)
                
                zip_path = "pdf_dividido.zip"
                with zipfile.ZipFile(zip_path, 'w') as zip_file:
                    for file_name in os.listdir(temp_dir):
                        zip_file.write(os.path.join(temp_dir, file_name), file_name)
                
                os.unlink(tmp_path)
                shutil.rmtree(temp_dir)
                
                with open(zip_path, "rb") as file:
                    st.download_button(
                        label=f"📥 Baixar ZIP com {len(reader.pages)} páginas",
                        data=file.read(),
                        file_name=zip_path,
                        mime="application/zip"
                    )
                st.success(f"✅ PDF dividido em {len(reader.pages)} páginas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)

def show_remove_pages():
    """Remove páginas do PDF"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    pages_input = st.text_input("Páginas para remover (ex: 2,5,8-10):", placeholder="2,5,8-10")
    
    if uploaded_file and st.button("🚀 Remover páginas", type="primary"):
        with st.spinner("Removendo páginas..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                writer = PdfWriter()
                remove_set = set(_parse_pages(pages_input, len(reader.pages)))
                
                for i, page in enumerate(reader.pages):
                    if i not in remove_set:
                        writer.add_page(page)
                
                output_name = "paginas_removidas.pdf"
                _save_writer(writer, output_name)
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Páginas removidas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_insert_pages():
    """Insere páginas de um PDF em outro"""
    col1, col2 = st.columns(2)
    with col1:
        base_pdf = st.file_uploader("PDF base", type=['pdf'])
    with col2:
        insert_pdf = st.file_uploader("PDF a inserir", type=['pdf'])
    
    position = st.number_input("Inserir após a página:", min_value=0, value=0)
    
    if base_pdf and insert_pdf and st.button("🚀 Inserir páginas", type="primary"):
        with st.spinner("Inserindo páginas..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_base:
                    tmp_base.write(base_pdf.getvalue())
                    tmp_base_path = tmp_base.name
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_insert:
                    tmp_insert.write(insert_pdf.getvalue())
                    tmp_insert_path = tmp_insert.name
                
                base_reader = PdfReader(tmp_base_path)
                insert_reader = PdfReader(tmp_insert_path)
                writer = PdfWriter()
                
                # Adicionar páginas até a posição
                for i in range(min(position, len(base_reader.pages))):
                    writer.add_page(base_reader.pages[i])
                
                # Inserir páginas do segundo PDF
                for page in insert_reader.pages:
                    writer.add_page(page)
                
                # Adicionar páginas restantes do primeiro PDF
                for i in range(position, len(base_reader.pages)):
                    writer.add_page(base_reader.pages[i])
                
                output_name = "pdf_com_insercao.pdf"
                _save_writer(writer, output_name)
                os.unlink(tmp_base_path)
                os.unlink(tmp_insert_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Páginas inseridas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_crop_pages():
    """Corta páginas do PDF (extrai parte específica)"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    pages_input = st.text_input("Páginas para cortar (ex: 1-3,7,10-12):", placeholder="1-3,7,10-12")
    
    if uploaded_file and st.button("🚀 Cortar páginas", type="primary"):
        with st.spinner("Cortando páginas..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                writer = PdfWriter()
                indices = _parse_pages(pages_input, len(reader.pages))
                
                for i in indices:
                    writer.add_page(reader.pages[i])
                
                output_name = "paginas_cortadas.pdf"
                _save_writer(writer, output_name)
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Páginas cortadas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_extract_pages():
    """Extrai páginas específicas"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    pages_input = st.text_input("Páginas para extrair (ex: 1-3,7,10-12):", placeholder="1-3,7,10-12")
    
    if uploaded_file and st.button("🚀 Extrair páginas", type="primary"):
        with st.spinner("Extraindo páginas..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                writer = PdfWriter()
                indices = _parse_pages(pages_input, len(reader.pages))
                
                for i in indices:
                    writer.add_page(reader.pages[i])
                
                output_name = "paginas_extraidas.pdf"
                _save_writer(writer, output_name)
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Páginas extraídas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_rotate_pages():
    """Gira páginas do PDF"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    col1, col2 = st.columns(2)
    with col1:
        angle = st.selectbox("Ângulo:", ["90", "180", "270"])
    with col2:
        pages_input = st.text_input("Páginas para girar (vazio = todas):", placeholder="1,3,5 ou vazio")
    
    if uploaded_file and st.button("🚀 Girar páginas", type="primary"):
        with st.spinner("Girando páginas..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                writer = PdfWriter()
                indices = set(_parse_pages(pages_input, len(reader.pages))) if pages_input else set(range(len(reader.pages)))
                angle_val = int(angle)
                
                for i, page in enumerate(reader.pages):
                    if i in indices:
                        page.rotate(angle_val)
                    writer.add_page(page)
                
                output_name = f"rotacionado_{angle}graus.pdf"
                _save_writer(writer, output_name)
                os.unlink(tmp_path)
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ Páginas giradas!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

# ============================================================================
# SEÇÃO 4: Compactar e anotar
# ============================================================================

def show_compress_and_annotate():
    st.header("🗜️ Compactar e anotar")
    
    operation = st.selectbox(
        "Selecione a operação:",
        [
            "Comprimir PDF",
            "Anotar em PDF",
            "Preencher formulário"
        ]
    )
    
    if operation == "Comprimir PDF":
        show_compress_pdf()
    elif operation == "Anotar em PDF":
        show_annotate_pdf()
    elif operation == "Preencher formulário":
        st.info("🚧 Funcionalidade em desenvolvimento. Em breve você poderá preencher formulários PDF interativamente.")
        st.warning("⚠️ Esta funcionalidade requer bibliotecas adicionais para manipulação de campos de formulário.")

def show_compress_pdf():
    """Comprime PDF"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    compression_level = st.selectbox(
        "Nível de compressão:",
        ["Alto (menor tamanho)", "Médio (balanceado)", "Baixo (melhor qualidade)"]
    )
    
    if uploaded_file and st.button("🚀 Comprimir PDF", type="primary"):
        with st.spinner("Comprimindo PDF..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                reader = PdfReader(tmp_path)
                writer = PdfWriter()
                
                # Copiar todas as páginas
                for page in reader.pages:
                    writer.add_page(page)
                
                # Configurar compressão baseado no nível
                if compression_level == "Alto (menor tamanho)":
                    # Comprimir imagens e conteúdo
                    for page_num in range(len(writer.pages)):
                        writer.pages[page_num].compress_content_streams()
                elif compression_level == "Médio (balanceado)":
                    # Compressão moderada
                    for page_num in range(len(writer.pages)):
                        writer.pages[page_num].compress_content_streams()
                
                output_name = "pdf_comprimido.pdf"
                _save_writer(writer, output_name)
                
                # Mostrar tamanhos
                original_size = os.path.getsize(tmp_path)
                compressed_size = os.path.getsize(output_name)
                reduction = ((original_size - compressed_size) / original_size) * 100
                
                os.unlink(tmp_path)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Tamanho original", f"{original_size / 1024:.2f} KB")
                with col2:
                    st.metric("Tamanho comprimido", f"{compressed_size / 1024:.2f} KB")
                with col3:
                    st.metric("Redução", f"{reduction:.1f}%")
                
                with open(output_name, "rb") as file:
                    st.download_button(
                        label="📥 Baixar PDF comprimido",
                        data=file.read(),
                        file_name=output_name,
                        mime="application/pdf"
                    )
                st.success("✅ PDF comprimido!")
            except Exception as e:
                st.error(f"❌ Erro: {str(e)}")
            finally:
                if os.path.exists(output_name):
                    os.remove(output_name)

def show_annotate_pdf():
    """Anota PDF com texto ou marca d'água"""
    uploaded_file = st.file_uploader("Escolha um arquivo PDF", type=['pdf'])
    annotation_type = st.selectbox(
        "Tipo de anotação:",
        ["Texto", "Marca d'água"]
    )
    
    if uploaded_file:
        if annotation_type == "Texto":
            text = st.text_area("Texto da anotação:")
            x = st.number_input("Posição X:", value=100)
            y = st.number_input("Posição Y:", value=100)
            font_size = st.slider("Tamanho da fonte:", 8, 72, 12)
            
            if st.button("🚀 Adicionar anotação", type="primary"):
                st.info("🚧 Funcionalidade em desenvolvimento. Em breve você poderá adicionar anotações de texto aos PDFs.")
        else:
            watermark_text = st.text_input("Texto da marca d'água:")
            opacity = st.slider("Opacidade:", 0.0, 1.0, 0.5)
            
            if st.button("🚀 Adicionar marca d'água", type="primary"):
                st.info("🚧 Funcionalidade em desenvolvimento. Em breve você poderá adicionar marcas d'água aos PDFs.")

# ============================================================================
# SEÇÃO 5: Escanear documentos (OCR)
# ============================================================================

def show_scan_documents():
    """Interface para escanear documentos usando OCR"""
    st.header("🔍 Escanear Documentos (OCR)")
    
    # Verificar status das dependências
    missing_deps = []
    if not TESSERACT_AVAILABLE:
        missing_deps.append("pytesseract")
    if not PDF2IMAGE_AVAILABLE:
        missing_deps.append("pdf2image")
    if not CV2_AVAILABLE:
        missing_deps.append("opencv-python (opcional)")
    
    # Verificar se o scanner está disponível (pytesseract e pdf2image são obrigatórios)
    if not SCANNER_AVAILABLE:
        st.error("❌ Módulo de scanner não está disponível.")
        
        # Mostrar quais dependências estão faltando
        if missing_deps:
            st.warning(f"⚠️ Dependências faltando: {', '.join([d for d in missing_deps if 'opcional' not in d])}")
        
        # Instruções detalhadas
        with st.expander("📋 Instruções de Instalação", expanded=True):
            st.markdown("""
            **Para usar o scanner de documentos, você precisa instalar:**
            
            ### 1. Bibliotecas Python (obrigatórias):
            ```bash
            pip install pytesseract pdf2image
            ```
            
            ### 2. Tesseract OCR (obrigatório):
            - **Windows**: Baixe e instale de https://github.com/UB-Mannheim/tesseract/wiki
            - **Linux**: `sudo apt-get install tesseract-ocr` (Ubuntu/Debian) ou `sudo yum install tesseract` (CentOS/RHEL)
            - **macOS**: `brew install tesseract`
            
            ### 3. Poppler (obrigatório para PDF):
            - **Windows**: Baixe de https://github.com/oschwartz10612/poppler-windows/releases
            - **Linux**: `sudo apt-get install poppler-utils`
            - **macOS**: `brew install poppler`
            
            ### 4. OpenCV (opcional, melhora a qualidade):
            ```bash
            pip install opencv-python
            ```
            
            **Nota**: O OpenCV é opcional. O scanner funcionará sem ele, mas com qualidade reduzida.
            """)
        
        # Mostrar status detalhado
        col1, col2, col3 = st.columns(3)
        with col1:
            status = "✅" if TESSERACT_AVAILABLE else "❌"
            st.markdown(f"**pytesseract**: {status}")
        with col2:
            status = "✅" if PDF2IMAGE_AVAILABLE else "❌"
            st.markdown(f"**pdf2image**: {status}")
        with col3:
            status = "✅" if CV2_AVAILABLE else "⚠️ (opcional)"
            st.markdown(f"**opencv-python**: {status}")
        
        return
    
    # Criar instância do scanner
    try:
        scanner = create_scanner()
        if not scanner.is_available():
            st.warning("⚠️ Dependências do scanner não estão totalmente disponíveis.")
            st.info("""
            **Dependências necessárias:**
            - pytesseract
            - Tesseract OCR instalado no sistema
            - pdf2image
            - poppler (para processar PDFs)
            """)
            return
    except Exception as e:
        st.error(f"❌ Erro ao inicializar scanner: {str(e)}")
        import traceback
        with st.expander("🔍 Detalhes do erro"):
            st.code(traceback.format_exc())
        return
    
    # Seleção de tipo de arquivo
    file_type = st.radio(
        "Tipo de documento:",
        ["PDF", "Imagem"],
        horizontal=True
    )
    
    # Upload de arquivo
    if file_type == "PDF":
        uploaded_file = st.file_uploader(
            "Escolha um arquivo PDF",
            type=['pdf'],
            help="Faça upload de um PDF para extrair texto usando OCR"
        )
    else:
        uploaded_file = st.file_uploader(
            "Escolha uma imagem",
            type=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
            help="Faça upload de uma imagem de documento para extrair texto usando OCR"
        )
    
    # Configurações de OCR
    with st.expander("⚙️ Configurações Avançadas"):
        lang = st.selectbox(
            "Idioma:",
            ["por", "eng", "por+eng"],
            help="Idioma para reconhecimento de texto"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            dpi = st.slider(
                "DPI (apenas PDF):",
                150, 600, 300,
                help="Resolução para conversão de PDF para imagem"
            )
            preprocess = st.checkbox(
                "Pré-processar imagem",
                value=True,
                help="Aplica filtros para melhorar a qualidade do OCR"
            )
        with col2:
            enhance = st.checkbox(
                "Melhorar qualidade",
                value=True,
                help="Aumenta contraste e nitidez da imagem"
            )
        
        # Seleção de páginas (apenas para PDF)
        if file_type == "PDF" and uploaded_file:
            pages_input = st.text_input(
                "Páginas específicas (vazio = todas):",
                placeholder="1,3,5-8 ou deixe vazio",
                help="Especifique páginas para processar ou deixe vazio para todas"
            )
        else:
            pages_input = None
    
    # Processar arquivo
    if uploaded_file and st.button("🚀 Escanear Documento", type="primary"):
        with st.spinner("Processando documento com OCR..."):
            try:
                # Salvar arquivo temporário
                file_ext = uploaded_file.name.split('.')[-1].lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Determinar páginas para processar
                pages = None
                if file_type == "PDF" and pages_input:
                    reader = PdfReader(tmp_path)
                    pages = _parse_pages(pages_input, len(reader.pages))
                    # Converter para 1-based para o scanner
                    pages = [p + 1 for p in pages]
                
                # Escanear documento
                if file_type == "PDF":
                    result = scanner.scan_document(
                        tmp_path,
                        file_type='pdf',
                        lang=lang,
                        dpi=dpi,
                        preprocess=preprocess,
                        enhance=enhance,
                        pages=pages
                    )
                else:
                    result = scanner.scan_document(
                        tmp_path,
                        file_type='image',
                        lang=lang,
                        preprocess=preprocess,
                        enhance=enhance
                    )
                
                # Mostrar resultados
                st.success("✅ Documento escaneado com sucesso!")
                
                # Estatísticas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if 'total_pages' in result:
                        st.metric("Total de Páginas", result.get('total_pages', 0))
                    else:
                        st.metric("Tipo", "Imagem")
                with col2:
                    st.metric("Palavras", result.get('word_count', result.get('total_words', 0)))
                with col3:
                    st.metric("Caracteres", result.get('char_count', result.get('total_chars', 0)))
                with col4:
                    confidence = result.get('confidence', result.get('avg_confidence', 0))
                    st.metric("Confiança OCR", f"{confidence:.1f}%")
                
                # Mostrar texto extraído
                st.subheader("📄 Texto Extraído")
                
                if 'pages' in result and len(result['pages']) > 1:
                    # Múltiplas páginas - mostrar em abas
                    tabs = st.tabs([f"Página {p}" for p in result['pages'].keys()])
                    for idx, (page_num, page_data) in enumerate(result['pages'].items()):
                        with tabs[idx]:
                            st.text_area(
                                f"Texto da página {page_num}:",
                                page_data.get('text', ''),
                                height=300,
                                key=f"page_{page_num}"
                            )
                            if 'confidence' in page_data:
                                st.caption(f"Confiança: {page_data['confidence']:.1f}%")
                else:
                    # Texto único
                    full_text = result.get('full_text', result.get('text', ''))
                    st.text_area(
                        "Texto extraído:",
                        full_text,
                        height=400
                    )
                
                # Opções de download
                st.subheader("💾 Download")
                
                # Obter texto completo para download
                full_text = result.get('full_text', result.get('text', ''))
                
                # Salvar texto em arquivo
                output_name = f"texto_extraido_{Path(uploaded_file.name).stem}.txt"
                html_name = f"texto_extraido_{Path(uploaded_file.name).stem}.html"
                
                with open(output_name, "w", encoding="utf-8") as f:
                    f.write(full_text)
                
                col1, col2 = st.columns(2)
                with col1:
                    with open(output_name, "rb") as file:
                        st.download_button(
                            label="📥 Baixar como TXT",
                            data=file.read(),
                            file_name=output_name,
                            mime="text/plain"
                        )
                
                with col2:
                    # Criar HTML formatado
                    html_content = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="utf-8">
    <title>Texto Extraído - {uploaded_file.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; line-height: 1.6; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <h1>Texto Extraído de: {uploaded_file.name}</h1>
    <pre>{full_text.replace('<', '&lt;').replace('>', '&gt;')}</pre>
</body>
</html>"""
                    with open(html_name, "w", encoding="utf-8") as f:
                        f.write(html_content)
                    
                    with open(html_name, "rb") as file:
                        st.download_button(
                            label="📥 Baixar como HTML",
                            data=file.read(),
                            file_name=html_name,
                            mime="text/html"
                        )
                
                # Limpar arquivos temporários
                os.unlink(tmp_path)
                
            except Exception as e:
                st.error(f"❌ Erro ao escanear documento: {str(e)}")
                import traceback
                with st.expander("🔍 Detalhes do erro"):
                    st.code(traceback.format_exc())
            finally:
                # Limpar arquivos gerados
                for file_name in [output_name, html_name]:
                    if 'file_name' in locals() and os.path.exists(file_name):
                        try:
                            os.remove(file_name)
                        except:
                            pass

if __name__ == "__main__":
    main()
