"""
LLM 서비스 모듈
OpenAI API 및 로컬 LLM과의 통신을 담당
"""
import openai
from django.conf import settings
from .models import LLMList, UserSetting
from .local_llm_service import LocalLLMService


class LLMService:
    """LLM 서비스 클래스"""
    
    def __init__(self, user, use_ask_settings=False):
        self.user = user
        self.client = None
        self.local_llm = None
        self.selected_llm = None
        self.use_ask_settings = use_ask_settings
        self._setup_client()
    
    def _setup_client(self):
        """사용자 설정에 따라 LLM 클라이언트 설정 (OpenAI 또는 로컬)"""
        try:
            # 사용자 설정에서 선택된 LLM 가져오기
            user_setting = UserSetting.objects.get(user=self.user)
            
            if self.use_ask_settings:
                # 질문 설정 사용
                ask_settings = user_setting.get_ask_settings()
                selected_llm_id = ask_settings.get('selected_llm')
            else:
                # 업로드 설정 사용
                upload_settings = user_setting.get_upload_settings()
                selected_llm_id = upload_settings.get('selected_llm')
            
            if selected_llm_id:
                self.selected_llm = LLMList.objects.get(id=selected_llm_id)
            else:
                # 기본적으로 사용 가능한 첫 번째 모델 사용
                self.selected_llm = LLMList.objects.first()
            
            if not self.selected_llm:
                raise Exception("사용 가능한 LLM 모델이 없습니다.")
            
            # 로컬 모델인지 확인
            if self.selected_llm.model_type == 'local':
                # 로컬 모델 사용
                self.local_llm = LocalLLMService(self.selected_llm.name)
                if not self.local_llm.is_available():
                    raise Exception(f"로컬 모델을 로드할 수 없습니다: {self.selected_llm.name}")
            else:
                # 외부 API 모델 사용 (OpenAI 등)
                if self.selected_llm.model_api_key:
                    openai.api_key = self.selected_llm.model_api_key
                else:
                    # Django settings에서 API 키 가져오기
                    openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)
                
                if not openai.api_key:
                    raise Exception("API 키가 설정되지 않았습니다.")
                
                self.client = openai.OpenAI(api_key=openai.api_key)
            
        except UserSetting.DoesNotExist:
            # 사용자 설정이 없으면 기본 모델 사용
            self.selected_llm = LLMList.objects.first()
            
            if not self.selected_llm:
                raise Exception("사용 가능한 LLM 모델이 없습니다.")
            
            # 로컬 모델인지 확인
            if self.selected_llm.model_type == 'local':
                self.local_llm = LocalLLMService(self.selected_llm.name)
                if not self.local_llm.is_available():
                    raise Exception(f"로컬 모델을 로드할 수 없습니다: {self.selected_llm.name}")
            else:
                if self.selected_llm.model_api_key:
                    openai.api_key = self.selected_llm.model_api_key
                    self.client = openai.OpenAI(api_key=openai.api_key)
                else:
                    raise Exception("사용자 설정이 없고 기본 LLM 모델도 없습니다.")
    
    def send_message(self, message, system_prompt=None):
        """
        LLM에 메시지 전송하고 응답 받기
        
        Args:
            message (str): 사용자 메시지
            system_prompt (str): 시스템 프롬프트 (선택사항)
            
        Returns:
            str: LLM 응답
        """
        if not self.client and not self.local_llm:
            raise Exception("LLM 클라이언트가 초기화되지 않았습니다.")
        
        try:
            # 로컬 모델 사용
            if self.local_llm:
                # 시스템 프롬프트 설정
                if system_prompt:
                    system_content = system_prompt
                elif self.use_ask_settings:
                    # 질문 설정에서 시스템 프롬프트 가져오기
                    try:
                        user_setting = UserSetting.objects.get(user=self.user)
                        ask_settings = user_setting.get_ask_settings()
                        system_content = ask_settings.get('system_prompt', '당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요.')
                    except:
                        system_content = "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요."
                else:
                    system_content = "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요."
                
                # Temperature 설정
                temperature = 0.7  # 기본값
                if self.use_ask_settings:
                    try:
                        user_setting = UserSetting.objects.get(user=self.user)
                        ask_settings = user_setting.get_ask_settings()
                        temperature = ask_settings.get('temperature', 0.7)
                    except:
                        pass
                
                # 로컬 모델로 응답 생성
                response = self.local_llm.generate_response(
                    prompt=message,
                    max_tokens=1000,
                    temperature=temperature,
                    system_prompt=system_content
                )
                
                return response
            
            # 외부 API 모델 사용 (OpenAI 등)
            else:
                # 모델명 설정 (GPT-4o 또는 선택된 모델)
                model_name = "gpt-4o"  # GPT-5는 아직 공개되지 않았으므로 GPT-4o 사용
                
                # 시스템 프롬프트 설정
                if system_prompt:
                    system_content = system_prompt
                elif self.use_ask_settings:
                    # 질문 설정에서 시스템 프롬프트 가져오기
                    try:
                        user_setting = UserSetting.objects.get(user=self.user)
                        ask_settings = user_setting.get_ask_settings()
                        system_content = ask_settings.get('system_prompt', '당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요.')
                    except:
                        system_content = "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요."
                else:
                    system_content = "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정확하고 유용한 답변을 제공해주세요."
                
                # Temperature 설정
                temperature = 0.7  # 기본값
                if self.use_ask_settings:
                    try:
                        user_setting = UserSetting.objects.get(user=self.user)
                        ask_settings = user_setting.get_ask_settings()
                        temperature = ask_settings.get('temperature', 0.7)
                    except:
                        pass
                
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system", 
                            "content": system_content
                        },
                        {
                            "role": "user", 
                            "content": message
                        }
                    ],
                    max_completion_tokens=1000,
                    temperature=temperature
                )
                
                return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM API 호출 중 오류가 발생했습니다: {str(e)}")
    
    def get_available_models(self):
        """사용 가능한 LLM 모델 목록 반환"""
        return LLMList.objects.all()
    
    def get_current_model(self):
        """현재 선택된 모델 정보 반환"""
        return self.selected_llm
