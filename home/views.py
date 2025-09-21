from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import os
from .models import LLMList, UserSetting, ChatMessage, Document, DocumentChunk, DocumentSelection
from .llm_service import LLMService
from .rag_service import RAGService

# Create your views here.

def login_view(request):
    """로그인 뷰"""
    if request.user.is_authenticated:
        return redirect('home:index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home:index')
        else:
            messages.error(request, '사용자명 또는 비밀번호가 올바르지 않습니다.')
    
    return render(request, 'home/login.html')

def logout_view(request):
    """로그아웃 뷰"""
    logout(request)
    return redirect('home:login')

@login_required
def index(request):
    """메인 홈페이지 뷰 - 로그인한 사용자만 접근 가능"""
    # LLM 목록을 가져와서 템플릿에 전달
    llm_list = LLMList.objects.all().order_by('name')
    
    # 사용자의 문서 목록 가져오기 (최신순)
    user_documents = Document.objects.filter(user=request.user).order_by('-created_at')
    
    # 각 문서에 파일명 추가
    for document in user_documents:
        document.filename = os.path.basename(document.file.name)
    
    context = {
        'title': '홈',
        'llm_list': llm_list,
        'user_documents': user_documents,
    }
    return render(request, 'home/index.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def save_upload_settings(request):
    """업로드 설정 저장 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # 설정 데이터 검증
        required_fields = ['selected_llm', 'prompt_text', 'chunk_size', 'chunk_overlap']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'success': False, 'message': f'{field} 필드가 필요합니다.'}, status=400)
        
        # LLM 모델 존재 확인
        if data['selected_llm']:
            try:
                llm = LLMList.objects.get(id=data['selected_llm'])
            except LLMList.DoesNotExist:
                return JsonResponse({'success': False, 'message': '선택한 LLM 모델이 존재하지 않습니다.'}, status=400)
        
        # 청킹 설정 검증
        chunk_size = int(data['chunk_size'])
        chunk_overlap = int(data['chunk_overlap'])
        
        if chunk_size < 100 or chunk_size > 5000:
            return JsonResponse({'success': False, 'message': '청크 글자수는 100-5000 사이여야 합니다.'}, status=400)
        
        if chunk_overlap < 0 or chunk_overlap > 1000:
            return JsonResponse({'success': False, 'message': '청크 겹침 글자수는 0-1000 사이여야 합니다.'}, status=400)
        
        if chunk_overlap >= chunk_size:
            return JsonResponse({'success': False, 'message': '청크 겹침 글자수는 청크 글자수보다 작아야 합니다.'}, status=400)
        
        # UserSetting 객체 가져오기 또는 생성
        user_setting, created = UserSetting.objects.get_or_create(
            user=request.user,
            defaults={'upload_settings': {}, 'ask_settings': {}}
        )
        
        # 업로드 설정 업데이트
        user_setting.upload_settings = {
            'selected_llm': data['selected_llm'],
            'prompt_text': data['prompt_text'],
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
        user_setting.save()
        
        return JsonResponse({'success': True, 'message': '설정이 저장되었습니다.'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_upload_settings(request):
    """업로드 설정 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        user_setting = get_object_or_404(UserSetting, user=request.user)
        settings = user_setting.get_upload_settings()
        
        return JsonResponse({'success': True, 'settings': settings})
        
    except UserSetting.DoesNotExist:
        return JsonResponse({'success': True, 'settings': {}})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_chat_message(request):
    """채팅 메시지 전송 API (RAG 지원)"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        selected_documents = data.get('selected_documents', [])  # RAG용 선택된 문서들
        
        if not message:
            return JsonResponse({'success': False, 'message': '메시지를 입력해주세요.'}, status=400)
        
        # RAG 모드인지 확인
        if selected_documents:
            # RAG 서비스 사용
            rag_service = RAGService(request.user)
            result = rag_service.send_rag_message(message, selected_documents)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': result['response'],
                    'message_id': result['message_id'],
                    'referenced_chunks': result['referenced_chunks'],
                    'context_used': result['context_used'],
                    'created_at': ChatMessage.objects.get(id=result['message_id']).created_at.isoformat()
                })
            else:
                return JsonResponse({'success': False, 'message': result['message']}, status=400)
        else:
            # 기존 일반 채팅 모드 (질문 설정 적용)
            llm_service = LLMService(request.user, use_ask_settings=True)
            response = llm_service.send_message(message)
            
            # 채팅 메시지 저장
            chat_message = ChatMessage.objects.create(
                user=request.user,
                req_content=message,
                res_content=response
            )
            
            return JsonResponse({
                'success': True,
                'message': response,
                'message_id': chat_message.id,
                'created_at': chat_message.created_at.isoformat()
            })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_chat_history(request):
    """채팅 이력 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        # 최근 50개 메시지만 가져오기
        messages = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:50]
        
        chat_data = []
        for message in messages:
            chat_data.append({
                'id': message.id,
                'req_content': message.req_content,
                'res_content': message.res_content,
                'created_at': message.created_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'messages': chat_data
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_current_llm(request):
    """현재 선택된 LLM 정보 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        llm_service = LLMService(request.user)
        current_model = llm_service.get_current_model()
        
        return JsonResponse({
            'success': True,
            'model': {
                'id': current_model.id,
                'name': current_model.name,
                'model_type': current_model.model_type,
                'model_provider': current_model.model_provider
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def upload_document(request):
    """문서 업로드 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'message': '파일이 선택되지 않았습니다.'}, status=400)
        
        file = request.FILES['file']
        
        # 파일 크기 제한 (10MB)
        if file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'message': '파일 크기는 10MB를 초과할 수 없습니다.'}, status=400)
        
        # 허용된 파일 확장자
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.png', '.jpg', '.jpeg']
        file_extension = os.path.splitext(file.name)[1].lower()
        
        if file_extension not in allowed_extensions:
            return JsonResponse({'success': False, 'message': '지원되지 않는 파일 형식입니다.'}, status=400)
        
        # 사용자 설정에서 기본값 가져오기
        try:
            user_setting = UserSetting.objects.get(user=request.user)
            settings = user_setting.get_upload_settings()
            prompt_text = settings.get('prompt_text', '')
            selected_llm_id = settings.get('selected_llm')
            chunk_size = settings.get('chunk_size', 1000)
            chunk_overlap = settings.get('chunk_overlap', 200)
        except UserSetting.DoesNotExist:
            prompt_text = ''
            selected_llm_id = None
            chunk_size = 1000
            chunk_overlap = 200
        
        # LLM 모델 가져오기
        selected_llm = None
        if selected_llm_id:
            try:
                selected_llm = LLMList.objects.get(id=selected_llm_id)
            except LLMList.DoesNotExist:
                pass
        
        # Document 객체 생성
        document = Document.objects.create(
            user=request.user,
            file=file,
            prompt_text=prompt_text,
            selected_llm=selected_llm,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            processing_status='pending'  # 초기 상태를 pending으로 설정
        )
        
        # RAG 처리를 위한 백그라운드 작업 시작 (비동기)
        try:
            from .rag_service import RAGService
            rag_service = RAGService(request.user)
            rag_service.process_document_for_rag(document.id)
        except Exception as e:
            print(f"RAG 처리 시작 오류: {e}")
            # RAG 처리 실패해도 문서 업로드는 성공으로 처리
        
        return JsonResponse({
            'success': True,
            'message': '문서가 성공적으로 업로드되었습니다. RAG 처리를 시작합니다.',
            'document': {
                'id': document.id,
                'filename': os.path.basename(document.file.name),
                'created_at': document.created_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def get_user_documents(request):
    """사용자 문서 목록 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        documents = Document.objects.filter(user=request.user).order_by('-created_at')
        
        document_list = []
        for doc in documents:
            document_list.append({
                'id': doc.id,
                'filename': os.path.basename(doc.file.name),
                'created_at': doc.created_at.isoformat(),
                'file_url': doc.file.url,
                'is_processed': doc.is_processed,
                'processing_status': doc.processing_status,
                'total_chunks': doc.total_chunks
            })
        
        return JsonResponse({
            'success': True,
            'documents': document_list
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_documents(request):
    """문서 삭제 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        document_ids = data.get('document_ids', [])
        
        if not document_ids:
            return JsonResponse({'success': False, 'message': '삭제할 문서를 선택해주세요.'}, status=400)
        
        # 사용자의 문서만 삭제 가능하도록 필터링
        documents = Document.objects.filter(user=request.user, id__in=document_ids)
        
        if not documents.exists():
            return JsonResponse({'success': False, 'message': '삭제할 문서를 찾을 수 없습니다.'}, status=404)
        
        deleted_count = 0
        deleted_files = []
        
        for document in documents:
            # 물리적 파일 삭제
            if document.file and document.file.name:
                try:
                    if os.path.isfile(document.file.path):
                        os.remove(document.file.path)
                        deleted_files.append(document.file.name)
                except Exception as e:
                    print(f"파일 삭제 오류: {e}")
            
            # DB에서 문서 삭제
            document.delete()
            deleted_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{deleted_count}개의 문서가 삭제되었습니다.',
            'deleted_count': deleted_count,
            'deleted_files': deleted_files
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


# RAG 관련 새로운 API들

@csrf_exempt
@require_http_methods(["POST"])
def process_document_for_rag(request):
    """문서를 RAG용으로 처리하는 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        
        if not document_id:
            return JsonResponse({'success': False, 'message': '문서 ID가 필요합니다.'}, status=400)
        
        # RAG 서비스로 문서 처리
        rag_service = RAGService(request.user)
        result = rag_service.process_document_for_rag(document_id)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_document_processing_status(request, document_id):
    """문서 처리 상태 확인 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        rag_service = RAGService(request.user)
        result = rag_service.get_document_processing_status(document_id)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_document_chunks(request, document_id):
    """문서의 청크 목록 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        rag_service = RAGService(request.user)
        result = rag_service.get_document_chunks(document_id)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_document_selection(request):
    """사용자의 문서 선택 상태 업데이트 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        selected_document_ids = data.get('selected_documents', [])
        session_id = data.get('session_id', 'default')
        
        # 기존 선택 상태 삭제
        DocumentSelection.objects.filter(user=request.user, session_id=session_id).delete()
        
        # 새로운 선택 상태 생성
        if selected_document_ids:
            # 선택된 문서들이 사용자의 문서인지 확인
            documents = Document.objects.filter(
                id__in=selected_document_ids,
                user=request.user
            )
            
            if documents.exists():
                selection = DocumentSelection.objects.create(
                    user=request.user,
                    session_id=session_id
                )
                selection.selected_documents.set(documents)
                
                return JsonResponse({
                    'success': True,
                    'message': f'{documents.count()}개의 문서가 선택되었습니다.',
                    'selected_documents': [
                        {
                            'id': doc.id,
                            'name': doc.file.name,
                            'is_processed': doc.is_processed
                        } for doc in documents
                    ]
                })
        
        return JsonResponse({
            'success': True,
            'message': '선택된 문서가 없습니다.',
            'selected_documents': []
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_selected_documents(request):
    """현재 선택된 문서 목록 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        session_id = request.GET.get('session_id', 'default')
        
        try:
            selection = DocumentSelection.objects.get(
                user=request.user,
                session_id=session_id
            )
            documents = selection.selected_documents.all()
            
            selected_documents = [
                {
                    'id': doc.id,
                    'name': doc.file.name,
                    'is_processed': doc.is_processed,
                    'processing_status': doc.processing_status,
                    'total_chunks': doc.total_chunks
                } for doc in documents
            ]
            
            return JsonResponse({
                'success': True,
                'selected_documents': selected_documents,
                'count': len(selected_documents)
            })
            
        except DocumentSelection.DoesNotExist:
            return JsonResponse({
                'success': True,
                'selected_documents': [],
                'count': 0
            })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_document_rag_data(request):
    """문서의 RAG 관련 데이터 삭제 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        
        if not document_id:
            return JsonResponse({'success': False, 'message': '문서 ID가 필요합니다.'}, status=400)
        
        rag_service = RAGService(request.user)
        result = rag_service.delete_document_data(document_id)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


# 질문 설정 관련 API들

@csrf_exempt
@require_http_methods(["POST"])
def save_ask_settings(request):
    """질문 설정 저장 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # 설정 데이터 검증
        required_fields = ['selected_llm', 'temperature', 'search_chunks', 'similarity_method', 'system_prompt']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'success': False, 'message': f'{field} 필드가 필요합니다.'}, status=400)
        
        # LLM 모델 존재 확인
        if data['selected_llm']:
            try:
                llm = LLMList.objects.get(id=data['selected_llm'])
            except LLMList.DoesNotExist:
                return JsonResponse({'success': False, 'message': '선택한 LLM 모델이 존재하지 않습니다.'}, status=400)
        
        # Temperature 검증
        temperature = float(data['temperature'])
        if temperature < 0 or temperature > 2:
            return JsonResponse({'success': False, 'message': 'Temperature는 0과 2 사이여야 합니다.'}, status=400)
        
        # 검색 청크 개수 검증
        search_chunks = int(data['search_chunks'])
        if search_chunks < 1 or search_chunks > 20:
            return JsonResponse({'success': False, 'message': '검색 청크 개수는 1-20 사이여야 합니다.'}, status=400)
        
        # 유사도 방식 검증
        similarity_method = data['similarity_method']
        if similarity_method not in ['cosine', 'l2']:
            return JsonResponse({'success': False, 'message': '유사도 방식은 cosine 또는 l2여야 합니다.'}, status=400)
        
        # UserSetting 객체 가져오기 또는 생성
        user_setting, created = UserSetting.objects.get_or_create(
            user=request.user,
            defaults={'upload_settings': {}, 'ask_settings': {}}
        )
        
        # 질문 설정 업데이트
        user_setting.ask_settings = {
            'selected_llm': data['selected_llm'],
            'temperature': temperature,
            'search_chunks': search_chunks,
            'similarity_method': similarity_method,
            'system_prompt': data['system_prompt']
        }
        user_setting.save()
        
        return JsonResponse({'success': True, 'message': '질문 설정이 저장되었습니다.'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '잘못된 JSON 형식입니다.'}, status=400)
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'잘못된 값: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_ask_settings(request):
    """질문 설정 조회 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        user_setting = get_object_or_404(UserSetting, user=request.user)
        settings = user_setting.get_ask_settings()
        
        return JsonResponse({'success': True, 'settings': settings})
        
    except UserSetting.DoesNotExist:
        # 기본 설정 반환
        default_settings = {
            'selected_llm': '',
            'temperature': 0.7,
            'search_chunks': 5,
            'similarity_method': 'cosine',
            'system_prompt': '당신은 도움이 되는 AI 어시스턴트입니다. 주어진 문서를 바탕으로 정확하고 유용한 답변을 제공해주세요.'
        }
        return JsonResponse({'success': True, 'settings': default_settings})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'서버 오류: {str(e)}'}, status=500)