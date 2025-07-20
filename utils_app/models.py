from django.db import models
from utils_app.requestMW import get_request

from django.conf import settings
from django_extensions.db.fields import CreationDateTimeField, ModificationDateTimeField
# Create your models here.


class BaseModelWithCreatedInfo(models.Model):
    created_at = CreationDateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   models.SET_NULL, related_name="+", editable=False, blank=True, null=True)
    updated_at = ModificationDateTimeField()
    # updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,
    #                                on_delete=models.SET_NULL, editable=False, null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def save(self, **kwargs):
        # used only for objects created by web (not api or through scripts)

        request = get_request()

        if not self.id and not self.created_by:
            if request != None and request.user.is_authenticated:
                self.created_by = request.user
                self.updated_by = request.user

        if request and request.method == "PATCH":
            self.updated_by = request.user

        return super(BaseModelWithCreatedInfo, self).save(**kwargs)

    def _str_(self):
        return "{}".format(self.id)
    

class Province(BaseModelWithCreatedInfo):
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class City(BaseModelWithCreatedInfo):
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name
    
class AppLanguage(BaseModelWithCreatedInfo):
    name = models.CharField(max_length=255, null=True, blank=True)

class GeneralModel(BaseModelWithCreatedInfo):
    # field_type = models.CharField(max_length=255, choices=)
    text = models.TextField(null=True, blank=True)

class Skill(BaseModelWithCreatedInfo):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name