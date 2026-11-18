"""Configurações do Sistema de Controle de Vendas e Estoque da Lojinha do DACOMP."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

CHAVE_DESENVOLVIMENTO = "dev-only-insecure-key-change-me"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", CHAVE_DESENVOLVIMENTO)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

# Na rede local do DA (DEBUG desligado) a chave de desenvolvimento não pode ser usada.
if not DEBUG and SECRET_KEY == CHAVE_DESENVOLVIMENTO:
    raise ImproperlyConfigured("Defina DJANGO_SECRET_KEY no arquivo .env (veja docs/instalacao-rede-local.md).")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "nucleo",
    "contas",
    "catalogo",
    "estoque",
    "vendas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "contas.turno.TurnoMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    # Na rede local (gunicorn, sem DEBUG), o WhiteNoise serve CSS, fontes e imagens
    # coletados em STATIC_ROOT pelo collectstatic.
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "contas.context_processors.perfis",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL, configurado pelas variáveis POSTGRES_* (definidas no docker-compose.yml).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "lojinha"),
        "USER": os.environ.get("POSTGRES_USER", "lojinha"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "contas.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "contas:entrar"

# Sessão por turno: o login vale por um turno de atendimento e termina ao fechar o
# navegador, para ninguém registrar vendas com a conta de outra pessoa (contas/turno.py).
DURACAO_TURNO_MINUTOS = int(os.environ.get("DURACAO_TURNO_MINUTOS", "100"))
SESSION_COOKIE_AGE = DURACAO_TURNO_MINUTOS * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
LOGIN_REDIRECT_URL = "nucleo:inicio"
LOGOUT_REDIRECT_URL = "contas:entrar"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Listagens de produtos, movimentações e vendas usam dez registros por página.
TAMANHO_PAGINA = 10

# UC16 – prazo para devolver itens de uma venda concluída.
PRAZO_DEVOLUCAO_DIAS = 7
