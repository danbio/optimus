import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

_SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not _SECRET_KEY:
    # Em desenvolvimento, usa chave insegura com aviso; em produção exige .env
    import sys

    if "runserver" in sys.argv or os.environ.get("DJANGO_ENV") != "production":
        _SECRET_KEY = "django-insecure-dev-only-nao-usar-em-producao"
    else:
        raise RuntimeError("SECRET_KEY não configurada. Defina no arquivo .env antes de iniciar em produção.")
SECRET_KEY = _SECRET_KEY

IS_PRODUCTION = os.environ.get("DJANGO_ENV") == "production"

DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes", "on")
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]

# Origens confiáveis para CSRF — obrigatório no Django 4+ quando o site roda
# atrás de proxy/HTTPS. Informar com esquema: "https://erp.optimusto.com.br".
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Apps do projeto
    "core",
    "clientes",
    "estoque",
    "solar",
    "servicos",
    "ordens_servico",
    "financeiro",
    "balcao",
    "pos_venda",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Precisa vir depois da autenticação: usa request.user para decidir acesso.
    "core.middleware.ControleDeAcessoPorGrupoMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Banco: SQLite em dev, PostgreSQL em produção via DATABASE_URL.
# Formato: postgres://usuario:senha@host:porta/nome_do_banco
# Sem DATABASE_URL definida, cai no SQLite local — dev continua sem configuração.
_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

if _DATABASE_URL:
    from urllib.parse import unquote, urlparse

    _url = urlparse(_DATABASE_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _url.path.lstrip("/"),
            "USER": unquote(_url.username or ""),
            "PASSWORD": unquote(_url.password or ""),
            "HOST": _url.hostname or "",
            "PORT": str(_url.port or ""),
            # Reaproveita conexões por 10 min: em plataforma gerenciada, abrir
            # conexão nova a cada request custa caro.
            "CONN_MAX_AGE": 600,
            "OPTIONS": {"sslmode": os.environ.get("DATABASE_SSLMODE", "require")},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Araguaina"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Segurança em produção ─────────────────────────────────────────────────────
# Só liga com DJANGO_ENV=production: em dev o servidor é HTTP, e forçar cookie
# seguro/redirect HTTPS quebraria o login local.
if IS_PRODUCTION:
    # Plataformas gerenciadas e proxies reversos entregam a requisição em HTTP
    # internamente; este header é como o Django sabe que o cliente veio por HTTPS.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # HSTS: instrui o navegador a só acessar por HTTPS. Começa em 1h — depois de
    # confirmar que o certificado está estável, subir para 31536000 (1 ano).
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Autenticação
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

# Tags de mensagens Django
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}
