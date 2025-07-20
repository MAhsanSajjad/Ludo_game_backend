from utils_app.models import Skill
from utils_app.serializers import SelectSkillsSerializer, SkillsSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class SkillAPIView(APIView):
    def get(self, request):
        try:
            skill = Skill.objects.all()
            serializer = SelectSkillsSerializer(skill, many=True)
            return Response({'success':True, 'response':{'data': serializer.data}}, status=status.HTTP_200_OK)
        except:
            return Response({'success':False, 'response':{'data': serializer.errors}}, status=status.HTTP_400_BAD_REQUEST)
