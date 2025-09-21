"""
로컬 LLM 서비스 모듈
Gemma-3 모델을 로컬에서 실행하여 문서 업로드 및 질문 기능을 제공
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logger.warning("llama-cpp-python이 설치되지 않았습니다. pip install llama-cpp-python을 실행하세요.")

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers가 설치되지 않았습니다. pip install transformers torch를 실행하세요.")


class LocalLLMService:
    """로컬 LLM 서비스 클래스"""
    
    def __init__(self, model_name: str, model_path: Optional[str] = None):
        """
        로컬 LLM 서비스 초기화
        
        Args:
            model_name: 모델 이름 (예: 'gemma-3-4b-it-Q4_1')
            model_path: 모델 파일 경로 (None이면 자동으로 찾음)
        """
        self.model_name = model_name
        self.model_path = model_path or self._find_model_path()
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _find_model_path(self) -> str:
        """모델 파일 경로를 자동으로 찾기"""
        # 프로젝트 루트의 llm_models 폴더에서 모델 찾기
        project_root = Path(__file__).parent.parent
        models_dir = project_root / "llm_models"
        
        if not models_dir.exists():
            raise FileNotFoundError(f"모델 디렉토리를 찾을 수 없습니다: {models_dir}")
        
        # 모델 이름에 해당하는 .gguf 파일 찾기
        model_files = list(models_dir.glob(f"{self.model_name}.gguf"))
        
        if not model_files:
            # 대안으로 모델 이름이 포함된 파일 찾기
            model_files = list(models_dir.glob(f"*{self.model_name}*.gguf"))
        
        if not model_files:
            available_models = list(models_dir.glob("*.gguf"))
            raise FileNotFoundError(
                f"모델 파일을 찾을 수 없습니다: {self.model_name}.gguf\n"
                f"사용 가능한 모델: {[f.name for f in available_models]}"
            )
        
        return str(model_files[0])
    
    def _load_model(self):
        """모델 로드"""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {self.model_path}")
        
        logger.info(f"모델 로딩 중: {self.model_path}")
        
        # llama-cpp-python 사용 (GGUF 파일용)
        if self.model_path.endswith('.gguf') and LLAMA_CPP_AVAILABLE:
            try:
                self.model = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,  # 컨텍스트 길이
                    n_threads=4,  # CPU 스레드 수
                    verbose=False
                )
                logger.info("llama-cpp-python으로 모델이 로드되었습니다.")
                return
            except Exception as e:
                logger.error(f"llama-cpp-python 로딩 실패: {e}")
        
        # transformers 사용 (대안)
        if TRANSFORMERS_AVAILABLE:
            try:
                # 모델이 HuggingFace Hub에 있는 경우
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else "cpu"
                )
                logger.info("transformers로 모델이 로드되었습니다.")
                return
            except Exception as e:
                logger.error(f"transformers 로딩 실패: {e}")
        
        raise RuntimeError("모델을 로드할 수 없습니다. llama-cpp-python 또는 transformers를 설치하세요.")
    
    def generate_response(
        self, 
        prompt: str, 
        max_tokens: int = 512, 
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        프롬프트에 대한 응답 생성
        
        Args:
            prompt: 사용자 프롬프트
            max_tokens: 최대 토큰 수
            temperature: 생성 온도 (0.0-1.0)
            system_prompt: 시스템 프롬프트 (선택사항)
            
        Returns:
            생성된 응답 텍스트
        """
        if not self.model:
            raise RuntimeError("모델이 로드되지 않았습니다.")
        
        try:
            # 시스템 프롬프트가 있으면 추가
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
            
            # llama-cpp-python 사용
            if hasattr(self.model, 'create_completion'):
                response = self.model.create_completion(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["User:", "System:"]
                )
                return response['choices'][0]['text'].strip()
            
            # transformers 사용
            elif self.tokenizer and hasattr(self.model, 'generate'):
                inputs = self.tokenizer.encode(full_prompt, return_tensors="pt")
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        inputs,
                        max_new_tokens=max_tokens,
                        temperature=temperature,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                # 프롬프트 부분 제거하고 응답만 반환
                if "Assistant:" in response:
                    response = response.split("Assistant:")[-1].strip()
                return response
            
            else:
                raise RuntimeError("지원되지 않는 모델 타입입니다.")
                
        except Exception as e:
            logger.error(f"응답 생성 중 오류 발생: {e}")
            raise RuntimeError(f"응답 생성 실패: {str(e)}")
    
    def is_available(self) -> bool:
        """모델이 사용 가능한지 확인"""
        return self.model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        return {
            'name': self.model_name,
            'path': self.model_path,
            'available': self.is_available(),
            'type': 'local'
        }


def create_local_llm_service(model_name: str) -> LocalLLMService:
    """
    로컬 LLM 서비스 인스턴스 생성
    
    Args:
        model_name: 모델 이름
        
    Returns:
        LocalLLMService 인스턴스
    """
    return LocalLLMService(model_name)


# 사용 예시
if __name__ == "__main__":
    # 테스트
    try:
        # Gemma-3 4B 모델 테스트
        llm = create_local_llm_service("gemma-3-4b-it-Q4_1")
        
        if llm.is_available():
            print("모델이 성공적으로 로드되었습니다.")
            
            # 간단한 테스트
            response = llm.generate_response(
                "안녕하세요! 간단한 인사말을 해주세요.",
                max_tokens=100,
                temperature=0.7
            )
            print(f"응답: {response}")
        else:
            print("모델을 로드할 수 없습니다.")
            
    except Exception as e:
        print(f"오류 발생: {e}")
