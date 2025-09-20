from django.db import models
from django.contrib.auth.models import User
import json

# Create your models here.

# RAG 관련 모델들
class LLMList(models.Model):
    """LLM 모델 관리를 위한 모델"""
    MODEL_TYPE_CHOICES = [
        ('local', '로컬'),
        ('external', '외부'),
    ]
    
    MODEL_PROVIDER_CHOICES = [
        ('OpenAI', 'OpenAI'),
        ('Google', 'Google'),
        ('Anthropic', 'Anthropic'),
        ('HuggingFace', 'HuggingFace'),
        ('Ollama', 'Ollama'),
        ('Other', '기타'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='모델명')
    model_type = models.CharField(max_length=20, choices=MODEL_TYPE_CHOICES, verbose_name='모델 타입')
    model_provider = models.CharField(max_length=50, choices=MODEL_PROVIDER_CHOICES, verbose_name='모델 제공자')
    model_api_key = models.CharField(max_length=500, blank=True, null=True, verbose_name='API 키')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = 'LLM 모델'
        verbose_name_plural = 'LLM 모델들'
        ordering = ['name']
    
    def __str__(self):
        return f'{self.name} ({self.get_model_type_display()})'


class Document(models.Model):
    """문서 업로드 및 저장을 위한 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    file = models.FileField(upload_to='documents/%Y/%m/%d/', verbose_name='파일')
    prompt_text = models.TextField(verbose_name='프롬프트 텍스트')
    selected_llm = models.ForeignKey(LLMList, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='선택된 LLM 모델')
    chunk_size = models.IntegerField(default=1000, verbose_name='청크 글자수')
    chunk_overlap = models.IntegerField(default=200, verbose_name='청크 겹침 글자수')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '문서'
        verbose_name_plural = '문서들'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.file.name}'


class UserSetting(models.Model):
    """사용자별 설정을 저장하는 모델"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='사용자')
    upload_settings = models.JSONField(blank=True, null=True, verbose_name='업로드 설정')
    ask_settings = models.JSONField(blank=True, null=True, verbose_name='질문 설정')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '사용자 설정'
        verbose_name_plural = '사용자 설정들'
    
    def __str__(self):
        return f'{self.user.username} 설정'
    
    def get_upload_settings(self):
        """업로드 설정을 딕셔너리로 반환"""
        if self.upload_settings:
            return self.upload_settings
        return {}
    
    def get_ask_settings(self):
        """질문 설정을 딕셔너리로 반환"""
        if self.ask_settings:
            return self.ask_settings
        return {}


class ChatMessage(models.Model):
    """채팅 메시지를 저장하는 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    req_content = models.TextField(verbose_name='요청 내용')
    res_content = models.TextField(verbose_name='응답 내용')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '채팅 메시지'
        verbose_name_plural = '채팅 메시지들'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.username} - {self.req_content[:50]}...'
