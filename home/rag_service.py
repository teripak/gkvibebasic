"""
RAG (Retrieval-Augmented Generation) 서비스 모듈
문서 검색과 LLM을 통한 답변 생성을 통합하는 기능을 제공
"""
from typing import List, Dict, Any
from .llm_service import LLMService
from .embedding_service import EmbeddingService
from .models import Document, DocumentChunk, ChatMessage


class RAGService:
    """RAG 서비스 클래스"""
    
    def __init__(self, user):
        self.user = user
        self.llm_service = LLMService(user)
        self.embedding_service = EmbeddingService(user)
    
    def process_document_for_rag(self, document_id: int) -> Dict[str, Any]:
        """문서를 RAG용으로 처리"""
        try:
            document = Document.objects.get(id=document_id, user=self.user)
            
            # 문서 처리 서비스로 텍스트 추출 및 청킹
            from .document_processor import DocumentProcessor
            processor = DocumentProcessor(document)
            result = processor.process_document()
            
            if result['success']:
                # 임베딩 생성
                chunks = DocumentChunk.objects.filter(document=document)
                self.embedding_service.generate_chunk_embeddings(list(chunks))
                
                return {
                    'success': True,
                    'message': '문서 처리가 완료되었습니다.',
                    'total_chunks': result['total_chunks']
                }
            else:
                return result
                
        except Document.DoesNotExist:
            return {'success': False, 'message': '문서를 찾을 수 없습니다.'}
        except Exception as e:
            return {'success': False, 'message': f'문서 처리 중 오류 발생: {str(e)}'}
    
    def search_relevant_chunks(self, query: str, selected_documents: List[int], top_k: int = 5) -> List[Dict[str, Any]]:
        """선택된 문서들에서 관련 청크들을 검색"""
        try:
            # 선택된 문서들 가져오기
            documents = Document.objects.filter(
                id__in=selected_documents,
                user=self.user,
                is_processed=True
            )
            
            if not documents.exists():
                return []
            
            # 여러 문서에서 검색
            relevant_chunks = self.embedding_service.search_multiple_documents(
                query=query,
                documents=documents,
                total_top_k=top_k
            )
            
            return relevant_chunks
            
        except Exception as e:
            print(f"청크 검색 중 오류: {e}")
            return []
    
    def build_context_from_chunks(self, chunks: List[Dict[str, Any]]) -> str:
        """검색된 청크들로부터 컨텍스트 구성"""
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk_info in enumerate(chunks, 1):
            chunk = chunk_info['chunk']
            similarity = chunk_info['similarity']
            
            context_part = f"""
[참조 {i}] (유사도: {similarity:.3f})
문서: {chunk_info['document_name']}
청크 {chunk.chunk_index}: {chunk.content}
"""
            context_parts.append(context_part.strip())
        
        return "\n\n".join(context_parts)
    
    def build_rag_prompt(self, query: str, context: str, selected_documents_info: List[str]) -> str:
        """RAG 프롬프트 구성"""
        documents_list = "\n".join([f"- {doc}" for doc in selected_documents_info])
        
        prompt = f"""당신은 주어진 문서들을 기반으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공하는 AI 어시스턴트입니다.

참조 문서들:
{documents_list}

관련 문서 내용:
{context}

사용자 질문: {query}

위의 관련 문서 내용을 바탕으로 사용자의 질문에 정확하게 답변해주세요. 
답변 시 다음 사항을 지켜주세요:
1. 문서에 명시적으로 나와 있는 내용만을 바탕으로 답변하세요.
2. 답변에 확실하지 않은 내용이 있다면 "문서에 명시되지 않음"이라고 표시하세요.
3. 답변의 근거가 되는 문서의 해당 부분을 참조해주세요.
4. 한국어로 명확하고 이해하기 쉽게 답변해주세요.
"""
        return prompt
    
    def send_rag_message(self, message: str, selected_documents: List[int]) -> Dict[str, Any]:
        """RAG 기반 메시지 전송"""
        try:
            # 선택된 문서들이 처리되었는지 확인
            processed_docs = Document.objects.filter(
                id__in=selected_documents, 
                user=self.user, 
                is_processed=True
            )
            
            if not processed_docs.exists():
                return {
                    'success': False,
                    'message': '선택된 문서들이 아직 처리되지 않았습니다. 문서 처리가 완료될 때까지 기다려주세요.'
                }
            
            # 선택된 문서들에서 관련 청크 검색
            relevant_chunks = self.search_relevant_chunks(message, selected_documents)
            
            if not relevant_chunks:
                return {
                    'success': False,
                    'message': '선택된 문서들에서 관련 정보를 찾을 수 없습니다. 다른 문서를 선택하거나 질문을 다시 작성해보세요.'
                }
            
            # 컨텍스트 구성
            context = self.build_context_from_chunks(relevant_chunks)
            
            # 선택된 문서들의 이름 가져오기
            documents = Document.objects.filter(id__in=selected_documents)
            documents_info = [doc.file.name for doc in documents]
            
            # RAG 프롬프트 구성
            rag_prompt = self.build_rag_prompt(message, context, documents_info)
            
            # LLM에 전송하여 답변 생성
            response = self.llm_service.send_message(rag_prompt)
            
            # 채팅 메시지 저장
            chat_message = ChatMessage.objects.create(
                user=self.user,
                req_content=message,
                res_content=response
            )
            
            # 선택된 문서들과 참조 청크들 연결
            chat_message.selected_documents.set(selected_documents)
            
            # 참조 청크 정보 저장
            referenced_chunks_info = []
            search_scores = {}
            
            for chunk_info in relevant_chunks:
                chunk = chunk_info['chunk']
                similarity = chunk_info['similarity']
                
                referenced_chunks_info.append({
                    'chunk_id': chunk.id,
                    'document_id': chunk.document.id,
                    'document_name': chunk_info['document_name'],
                    'chunk_index': chunk.chunk_index,
                    'content': chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    'similarity': similarity
                })
                
                search_scores[str(chunk.id)] = similarity
            
            chat_message.referenced_chunks = referenced_chunks_info
            chat_message.search_scores = search_scores
            chat_message.save()
            
            return {
                'success': True,
                'response': response,
                'message_id': chat_message.id,
                'referenced_chunks': referenced_chunks_info,
                'context_used': context[:500] + "..." if len(context) > 500 else context
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'RAG 처리 중 오류가 발생했습니다: {str(e)}'
            }
    
    def get_document_processing_status(self, document_id: int) -> Dict[str, Any]:
        """문서 처리 상태 확인"""
        try:
            document = Document.objects.get(id=document_id, user=self.user)
            
            return {
                'success': True,
                'is_processed': document.is_processed,
                'processing_status': document.processing_status,
                'total_chunks': document.total_chunks,
                'created_at': document.created_at.isoformat(),
                'updated_at': document.updated_at.isoformat()
            }
            
        except Document.DoesNotExist:
            return {'success': False, 'message': '문서를 찾을 수 없습니다.'}
    
    def get_document_chunks(self, document_id: int) -> Dict[str, Any]:
        """문서의 청크 목록 조회"""
        try:
            document = Document.objects.get(id=document_id, user=self.user)
            chunks = DocumentChunk.objects.filter(document=document).order_by('chunk_index')
            
            chunk_list = []
            for chunk in chunks:
                chunk_list.append({
                    'id': chunk.id,
                    'chunk_index': chunk.chunk_index,
                    'content': chunk.content,
                    'metadata': chunk.metadata,
                    'has_embedding': bool(chunk.embedding)
                })
            
            return {
                'success': True,
                'document_name': document.file.name,
                'total_chunks': len(chunk_list),
                'chunks': chunk_list
            }
            
        except Document.DoesNotExist:
            return {'success': False, 'message': '문서를 찾을 수 없습니다.'}
    
    def delete_document_data(self, document_id: int) -> Dict[str, Any]:
        """문서의 RAG 관련 데이터 삭제"""
        try:
            document = Document.objects.get(id=document_id, user=self.user)
            
            # 관련 청크들 삭제
            DocumentChunk.objects.filter(document=document).delete()
            
            # 문서 상태 초기화
            document.is_processed = False
            document.processing_status = 'pending'
            document.total_chunks = 0
            document.save()
            
            return {
                'success': True,
                'message': '문서의 RAG 데이터가 삭제되었습니다.'
            }
            
        except Document.DoesNotExist:
            return {'success': False, 'message': '문서를 찾을 수 없습니다.'}
