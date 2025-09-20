"""
LLM 서비스 모듈
OpenAI API를 통한 LLM과의 통신을 담당
"""
import openai
from django.conf import settings
from .models import LLMList, UserSetting


class LLMService:
    """LLM 서비스 클래스"""
    
    def __init__(self, user):
        self.user = user
        self.client = None
        self.selected_llm = None
        self._setup_client()
    
    def _setup_client(self):
        """사용자 설정에 따라 OpenAI 클라이언트 설정"""
        try:
            # 사용자 설정에서 선택된 LLM 가져오기
            user_setting = UserSetting.objects.get(user=self.user)
            upload_settings = user_setting.get_upload_settings()
            selected_llm_id = upload_settings.get('selected_llm')
            
            if selected_llm_id:
                self.selected_llm = LLMList.objects.get(id=selected_llm_id)
            else:
                # 기본적으로 GPT-5 사용 (또는 사용 가능한 첫 번째 OpenAI 모델)
                self.selected_llm = LLMList.objects.filter(
                    model_provider='OpenAI'
                ).first()
            
            if not self.selected_llm:
                raise Exception("사용 가능한 LLM 모델이 없습니다.")
            
            # OpenAI 클라이언트 설정
            if self.selected_llm.model_api_key:
                openai.api_key = self.selected_llm.model_api_key
            else:
                # Django settings에서 API 키 가져오기
                openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)
            
            if not openai.api_key:
                raise Exception("OpenAI API 키가 설정되지 않았습니다.")
            
            self.client = openai.OpenAI(api_key=openai.api_key)
            
        except UserSetting.DoesNotExist:
            # 사용자 설정이 없으면 기본 OpenAI 모델 사용
            self.selected_llm = LLMList.objects.filter(
                model_provider='OpenAI'
            ).first()
            
            if self.selected_llm and self.selected_llm.model_api_key:
                openai.api_key = self.selected_llm.model_api_key
                self.client = openai.OpenAI(api_key=openai.api_key)
            else:
                raise Exception("사용자 설정이 없고 기본 LLM 모델도 없습니다.")
    
    def send_message(self, message):
        """
        LLM에 메시지 전송하고 응답 받기
        
        Args:
            message (str): 사용자 메시지
            
        Returns:
            str: LLM 응답
        """
        if not self.client:
            raise Exception("LLM 클라이언트가 초기화되지 않았습니다.")
        
        try:
            # 모델명 설정 (GPT-4o 또는 선택된 모델)
            model_name = "gpt-4o"  # GPT-5는 아직 공개되지 않았으므로 GPT-4o 사용
            
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system", 
                        "content": "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요."
                    },
                    {
                        "role": "user", 
                        "content": message
                    }
                ],
                max_completion_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM API 호출 중 오류가 발생했습니다: {str(e)}")
    
    def get_available_models(self):
        """사용 가능한 LLM 모델 목록 반환"""
        return LLMList.objects.filter(model_provider='OpenAI')
    
    def get_current_model(self):
        """현재 선택된 모델 정보 반환"""
        return self.selected_llm
