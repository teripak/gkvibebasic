from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Document, LLMList, UserSetting, ChatMessage

# Register your models here.

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'file_name', 'file_size', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at', 'user']
    search_fields = ['user__username', 'file', 'prompt_text']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'file_size_display']
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'file', 'file_size_display')
        }),
        ('프롬프트', {
            'fields': ('prompt_text',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_name(self, obj):
        """파일명만 표시"""
        if obj.file:
            return obj.file.name.split('/')[-1]
        return '-'
    file_name.short_description = '파일명'
    
    def file_size(self, obj):
        """파일 크기 표시"""
        if obj.file:
            try:
                size = obj.file.size
                if size < 1024:
                    return f"{size} B"
                elif size < 1024 * 1024:
                    return f"{size / 1024:.1f} KB"
                else:
                    return f"{size / (1024 * 1024):.1f} MB"
            except:
                return "알 수 없음"
        return '-'
    file_size.short_description = '파일 크기'
    
    def file_size_display(self, obj):
        """파일 크기 상세 표시 (읽기 전용)"""
        return self.file_size(obj)
    file_size_display.short_description = '파일 크기'


@admin.register(LLMList)
class LLMListAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'model_type', 'model_provider', 'has_api_key', 'created_at']
    list_filter = ['model_type', 'model_provider', 'created_at']
    search_fields = ['name', 'model_provider']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('모델 정보', {
            'fields': ('name', 'model_type', 'model_provider')
        }),
        ('API 설정', {
            'fields': ('model_api_key',),
            'description': 'API 키는 보안상 마스킹되어 표시됩니다.'
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_api_key(self, obj):
        """API 키 존재 여부 표시"""
        if obj.model_api_key:
            return format_html('<span style="color: green;">✓ 있음</span>')
        return format_html('<span style="color: red;">✗ 없음</span>')
    has_api_key.short_description = 'API 키'
    
    def get_queryset(self, request):
        """API 키를 마스킹하여 표시"""
        qs = super().get_queryset(request)
        for obj in qs:
            if obj.model_api_key:
                # API 키의 마지막 4자리만 표시
                obj.model_api_key = '*' * (len(obj.model_api_key) - 4) + obj.model_api_key[-4:]
        return qs


@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'has_upload_settings', 'has_ask_settings', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username']
    ordering = ['user__username']
    readonly_fields = ['created_at', 'updated_at', 'upload_settings_preview', 'ask_settings_preview']
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user',)
        }),
        ('업로드 설정', {
            'fields': ('upload_settings', 'upload_settings_preview'),
            'classes': ('collapse',)
        }),
        ('질문 설정', {
            'fields': ('ask_settings', 'ask_settings_preview'),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_upload_settings(self, obj):
        """업로드 설정 존재 여부 표시"""
        if obj.upload_settings:
            return format_html('<span style="color: green;">✓ 설정됨</span>')
        return format_html('<span style="color: gray;">- 없음</span>')
    has_upload_settings.short_description = '업로드 설정'
    
    def has_ask_settings(self, obj):
        """질문 설정 존재 여부 표시"""
        if obj.ask_settings:
            return format_html('<span style="color: green;">✓ 설정됨</span>')
        return format_html('<span style="color: gray;">- 없음</span>')
    has_ask_settings.short_description = '질문 설정'
    
    def upload_settings_preview(self, obj):
        """업로드 설정 미리보기"""
        if obj.upload_settings:
            import json
            try:
                formatted = json.dumps(obj.upload_settings, indent=2, ensure_ascii=False)
                return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
            except:
                return str(obj.upload_settings)
        return '설정 없음'
    upload_settings_preview.short_description = '업로드 설정 미리보기'
    
    def ask_settings_preview(self, obj):
        """질문 설정 미리보기"""
        if obj.ask_settings:
            import json
            try:
                formatted = json.dumps(obj.ask_settings, indent=2, ensure_ascii=False)
                return format_html('<pre style="background: #f5f5f5; padding: 10px; border-radius: 5px;">{}</pre>', formatted)
            except:
                return str(obj.ask_settings)
        return '설정 없음'
    ask_settings_preview.short_description = '질문 설정 미리보기'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'req_content_preview', 'res_content_preview', 'created_at']
    list_filter = ['created_at', 'user']
    search_fields = ['user__username', 'req_content', 'res_content']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('기본 정보', {
            'fields': ('user',)
        }),
        ('메시지 내용', {
            'fields': ('req_content', 'res_content')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def req_content_preview(self, obj):
        """요청 내용 미리보기"""
        if len(obj.req_content) > 50:
            return obj.req_content[:50] + '...'
        return obj.req_content
    req_content_preview.short_description = '요청 내용'
    
    def res_content_preview(self, obj):
        """응답 내용 미리보기"""
        if len(obj.res_content) > 50:
            return obj.res_content[:50] + '...'
        return obj.res_content
    res_content_preview.short_description = '응답 내용'
