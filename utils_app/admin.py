from django.contrib import admin
from .models import *

@admin.register(Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'province', 'created_at', 'updated_at')
    search_fields = ('name', 'province__name')
    list_filter = ('province', 'created_at')

@admin.register(AppLanguage)
class AppLanguageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

@admin.register(GeneralModel)
class GeneralModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'created_at', 'updated_at')
    search_fields = ('text',)
    list_filter = ('created_at',)

# @admin.register(Skill)
# class SkillAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'created_at', 'updated_at')
#     search_fields = ('name',)
#     list_filter = ('created_at',)
