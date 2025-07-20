from rest_framework import serializers
from utils_app.models import *

class SkillsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']

class SelectSkillsSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = Skill
        fields = ['value', 'label']
    
    def get_value(self, instance):
        return instance.id
    
    def get_label(self, instance):
        return instance.name