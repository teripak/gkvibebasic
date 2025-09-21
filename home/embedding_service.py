"""
임베딩 서비스 모듈
텍스트를 벡터로 변환하고 유사도 검색을 수행하는 기능을 제공
"""
import json
import numpy as np
from typing import List, Dict, Any, Tuple
import openai
from django.conf import settings
from .models import DocumentChunk


class EmbeddingService:
    """임베딩 서비스 클래스"""
    
    def __init__(self, user=None):
        self.user = user
        self.client = None
        self.embedding_model = "text-embedding-3-small"  # OpenAI의 최신 임베딩 모델
        self._setup_client()
    
    def _setup_client(self):
        """사용자 설정에 따라 OpenAI 클라이언트 설정"""
        try:
            if self.user:
                # 사용자 설정에서 선택된 LLM 가져오기
                from .models import UserSetting, LLMList
                user_setting = UserSetting.objects.get(user=self.user)
                upload_settings = user_setting.get_upload_settings()
                selected_llm_id = upload_settings.get('selected_llm')
                
                if selected_llm_id:
                    selected_llm = LLMList.objects.get(id=selected_llm_id)
                    api_key = selected_llm.model_api_key
                else:
                    # 기본적으로 GPT-5 사용 (또는 사용 가능한 첫 번째 OpenAI 모델)
                    selected_llm = LLMList.objects.filter(
                        model_provider='OpenAI'
                    ).first()
                    api_key = selected_llm.model_api_key if selected_llm else None
                
                if not api_key:
                    # Django settings에서 API 키 가져오기
                    api_key = getattr(settings, 'OPENAI_API_KEY', None)
            else:
                # Django settings에서 API 키 가져오기
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
            
            if not api_key:
                raise Exception("OpenAI API 키가 설정되지 않았습니다.")
            
            self.client = openai.OpenAI(api_key=api_key)
            
        except Exception as e:
            # 폴백: Django settings에서 API 키 가져오기
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
            else:
                raise Exception(f"OpenAI API 키 설정 실패: {str(e)}")
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"임베딩 생성 중 오류 발생: {str(e)}")
    
    def calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def calculate_l2_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """L2 거리 유사도 계산 (거리가 가까울수록 높은 값)"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        l2_distance = np.linalg.norm(vec1 - vec2)
        # 거리를 유사도로 변환 (0~1 범위)
        similarity = 1.0 / (1.0 + l2_distance)
        return similarity
    
    def generate_chunk_embeddings(self, document_chunks: List[DocumentChunk]) -> Dict[int, List[float]]:
        """청크들의 임베딩을 생성"""
        embeddings = {}
        
        for chunk in document_chunks:
            try:
                # 이미 임베딩이 있는지 확인
                if chunk.embedding:
                    embeddings[chunk.id] = chunk.embedding
                else:
                    # 새로 임베딩 생성
                    embedding = self.get_embedding(chunk.content)
                    
                    # 데이터베이스에 저장
                    chunk.embedding = embedding
                    chunk.save()
                    
                    embeddings[chunk.id] = embedding
                    
            except Exception as e:
                print(f"청크 {chunk.id} 임베딩 생성 실패: {e}")
                continue
        
        return embeddings
    
    def search_similar_chunks(self, query: str, document_chunks: List[DocumentChunk], top_k: int = 5, similarity_method: str = 'cosine') -> List[Dict[str, Any]]:
        """유사한 청크들을 검색"""
        try:
            # 쿼리 임베딩 생성
            query_embedding = self.get_embedding(query)
            
            # 청크들의 임베딩 생성 또는 가져오기
            chunk_embeddings = self.generate_chunk_embeddings(document_chunks)
            
            # 유사도 계산
            similarities = []
            for chunk in document_chunks:
                if chunk.id in chunk_embeddings:
                    if similarity_method == 'l2':
                        similarity = self.calculate_l2_similarity(
                            query_embedding, 
                            chunk_embeddings[chunk.id]
                        )
                    else:  # 기본값은 코사인 유사도
                        similarity = self.calculate_cosine_similarity(
                            query_embedding, 
                            chunk_embeddings[chunk.id]
                        )
                    
                    similarities.append({
                        'chunk': chunk,
                        'similarity': similarity,
                        'content': chunk.content,
                        'metadata': chunk.metadata
                    })
            
            # 유사도 순으로 정렬하고 상위 k개 반환
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            raise Exception(f"유사 청크 검색 중 오류 발생: {str(e)}")
    
    def search_multiple_documents(self, query: str, documents, top_k_per_doc: int = 3, total_top_k: int = 5, similarity_method: str = 'cosine') -> List[Dict[str, Any]]:
        """여러 문서에서 유사한 청크들을 검색"""
        all_results = []
        
        for document in documents:
            try:
                # 해당 문서의 청크들 가져오기
                chunks = DocumentChunk.objects.filter(document=document)
                
                if not chunks.exists():
                    continue
                
                # 해당 문서에서 검색
                doc_results = self.search_similar_chunks(query, list(chunks), top_k_per_doc, similarity_method)
                
                # 문서 정보 추가
                for result in doc_results:
                    result['document_id'] = document.id
                    result['document_name'] = document.file.name
                    result['document_user'] = document.user.username
                
                all_results.extend(doc_results)
                
            except Exception as e:
                print(f"문서 {document.id} 검색 중 오류: {e}")
                continue
        
        # 전체 결과를 유사도 순으로 정렬
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return all_results[:total_top_k]
    
    def get_chunk_context(self, chunk: DocumentChunk, context_window: int = 2) -> str:
        """청크의 주변 컨텍스트를 가져오기"""
        try:
            # 같은 문서의 앞뒤 청크들 가져오기
            all_chunks = DocumentChunk.objects.filter(
                document=chunk.document
            ).order_by('chunk_index')
            
            chunk_list = list(all_chunks)
            current_index = chunk_list.index(chunk)
            
            start_index = max(0, current_index - context_window)
            end_index = min(len(chunk_list), current_index + context_window + 1)
            
            context_chunks = chunk_list[start_index:end_index]
            
            context_parts = []
            for ctx_chunk in context_chunks:
                if ctx_chunk.id == chunk.id:
                    context_parts.append(f"[{ctx_chunk.chunk_index}] {ctx_chunk.content}")
                else:
                    context_parts.append(f"[{ctx_chunk.chunk_index}] {ctx_chunk.content}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            return chunk.content  # 오류 시 원본 청크 내용만 반환
