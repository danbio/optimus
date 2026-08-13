from django import template
from django.contrib.auth.models import AbstractBaseUser

register = template.Library()


@register.filter
def in_group(user: AbstractBaseUser | None, group_name: str) -> bool:
    """Uso: {% if user|in_group:"Administrador" %}...{% endif %}

    Espelha a checagem de core.permissoes.usuario_pode_acessar: superusuário
    sempre passa. Usado para esconder itens de menu que o middleware de RBAC
    bloquearia de qualquer forma — sem isso, o usuário via o link, clicava e
    caía numa tela de acesso negado sem aviso prévio.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=group_name).exists()
