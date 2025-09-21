"""
문서 처리 서비스 모듈
다양한 파일 형식의 문서를 텍스트로 추출하고 청킹하는 기능을 제공
"""
import os
import re
from typing import List, Dict, Any
import PyPDF2
from docx import Document as DocxDocument
import pytesseract
from PIL import Image
import tiktoken


class DocumentProcessor:
    """문서 처리 클래스"""
    
    def __init__(self, document):
        self.document = document
        self.file_path = document.file.path
        self.file_extension = os.path.splitext(self.file_path)[1].lower()
        
    def extract_text(self) -> str:
        """파일 형식에 따라 텍스트 추출"""
        try:
            if self.file_extension == '.pdf':
                return self._extract_pdf_text()
            elif self.file_extension in ['.doc', '.docx']:
                return self._extract_docx_text()
            elif self.file_extension == '.txt':
                return self._extract_txt_text()
            elif self.file_extension in ['.png', '.jpg', '.jpeg']:
                return self._extract_image_text()
            else:
                raise ValueError(f"지원되지 않는 파일 형식: {self.file_extension}")
        except Exception as e:
            raise Exception(f"텍스트 추출 중 오류 발생: {str(e)}")
    
    def _extract_pdf_text(self) -> str:
        """PDF 파일에서 텍스트 추출"""
        text = ""
        with open(self.file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- 페이지 {page_num + 1} ---\n"
                    text += page_text
        return text
    
    def _extract_docx_text(self) -> str:
        """DOCX 파일에서 텍스트 추출"""
        doc = DocxDocument(self.file_path)
        text = ""
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text += paragraph.text + "\n"
        return text
    
    def _extract_txt_text(self) -> str:
        """TXT 파일에서 텍스트 추출"""
        with open(self.file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def _extract_image_text(self) -> str:
        """이미지 파일에서 OCR로 텍스트 추출"""
        try:
            image = Image.open(self.file_path)
            text = pytesseract.image_to_string(image, lang='kor+eng')
            return text
        except Exception as e:
            # OCR 실패 시 빈 문자열 반환
            print(f"OCR 추출 실패: {e}")
            return ""
    
    def preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        # 불필요한 공백 제거
        text = re.sub(r'\s+', ' ', text)
        # 특수문자 정규화
        text = re.sub(r'[^\w\s가-힣.,!?;:()\-]', '', text)
        # 빈 줄 제거
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()
    
    def create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """텍스트를 청크로 분할"""
        # 텍스트 전처리
        processed_text = self.preprocess_text(text)
        
        # 청크 크기와 겹침 설정
        chunk_size = self.document.chunk_size
        chunk_overlap = self.document.chunk_overlap
        
        # tiktoken을 사용하여 토큰 기반 청킹
        encoding = tiktoken.get_encoding("cl100k_base")
        
        # 텍스트를 문장 단위로 분할
        sentences = re.split(r'[.!?]\s+', processed_text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_tokens = len(encoding.encode(sentence))
            
            # 현재 청크에 문장을 추가했을 때 크기 초과 여부 확인
            if current_tokens + sentence_tokens > chunk_size and current_chunk:
                # 현재 청크를 저장
                chunks.append({
                    'content': current_chunk.strip(),
                    'chunk_index': chunk_index,
                    'metadata': {
                        'tokens': current_tokens,
                        'document_id': self.document.id,
                        'file_name': os.path.basename(self.file_path)
                    }
                })
                chunk_index += 1
                
                # 겹침을 고려한 새로운 청크 시작
                if chunk_overlap > 0:
                    # 이전 청크의 마지막 부분을 새로운 청크의 시작으로 사용
                    overlap_text = self._get_overlap_text(current_chunk, chunk_overlap, encoding)
                    current_chunk = overlap_text + " " + sentence
                    current_tokens = len(encoding.encode(current_chunk))
                else:
                    current_chunk = sentence
                    current_tokens = sentence_tokens
            else:
                # 현재 청크에 문장 추가
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
                current_tokens += sentence_tokens
        
        # 마지막 청크 처리
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'chunk_index': chunk_index,
                'metadata': {
                    'tokens': current_tokens,
                    'document_id': self.document.id,
                    'file_name': os.path.basename(self.file_path)
                }
            })
        
        return chunks
    
    def _get_overlap_text(self, text: str, overlap_tokens: int, encoding) -> str:
        """겹침을 위한 텍스트 추출"""
        tokens = encoding.encode(text)
        if len(tokens) <= overlap_tokens:
            return text
        
        # 마지막 overlap_tokens만큼의 토큰을 가져와서 텍스트로 변환
        overlap_tokens_list = tokens[-overlap_tokens:]
        return encoding.decode(overlap_tokens_list)
    
    def process_document(self) -> Dict[str, Any]:
        """문서 전체 처리 프로세스"""
        try:
            # 문서 상태를 'processing'으로 변경
            self.document.processing_status = 'processing'
            self.document.save()
            
            # 텍스트 추출
            text = self.extract_text()
            
            if not text.strip():
                raise Exception("추출된 텍스트가 비어있습니다.")
            
            # 청킹
            chunks = self.create_chunks(text)
            
            # 기존 청크들 삭제 (재처리 시)
            from .models import DocumentChunk
            DocumentChunk.objects.filter(document=self.document).delete()
            
            # 청크들을 데이터베이스에 저장
            for chunk_data in chunks:
                DocumentChunk.objects.create(
                    document=self.document,
                    chunk_index=chunk_data['chunk_index'],
                    content=chunk_data['content'],
                    metadata=chunk_data['metadata']
                )
            
            # 문서 상태 업데이트
            self.document.is_processed = True
            self.document.processing_status = 'completed'
            self.document.total_chunks = len(chunks)
            self.document.save()
            
            return {
                'success': True,
                'total_chunks': len(chunks),
                'message': '문서 처리가 완료되었습니다.'
            }
            
        except Exception as e:
            # 오류 발생 시 상태 업데이트
            self.document.processing_status = 'failed'
            self.document.save()
            
            return {
                'success': False,
                'error': str(e),
                'message': f'문서 처리 중 오류가 발생했습니다: {str(e)}'
            }
