from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import json
from .models import LLMList, UserSetting, ChatMessage
from .llm_service import LLMService

# Create your views here.

def index(request):
    """메인 홈페이지 뷰"""
    # LLM 목록을 가져와서 템플릿에 전달
    llm_list = LLMList.objects.all().order_by('name')
    
    context = {
        'title': '홈',
        'llm_list': llm_list,
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
    """채팅 메시지 전송 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': '로그인이 필요합니다.'}, status=401)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'success': False, 'message': '메시지를 입력해주세요.'}, status=400)
        
        # LLM 서비스 초기화 및 메시지 전송
        llm_service = LLMService(request.user)
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