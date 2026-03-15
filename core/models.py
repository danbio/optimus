from django.db import models


class BaseModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="atualizado em")

    class Meta:
        abstract = True
