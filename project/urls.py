"""Configuração de URLs do projeto INKA.

urlpatterns é a lista de rotas do projeto. A função include delega para o
arquivo forum/urls.py todas as rotas da aplicação.

O guia da prática sugere um RedirectView na raiz, mas RedirectView é uma
generic view, e o enunciado do projeto pede para não usá-las. Como a aplicação
ocupa a raiz do site, incluímos forum.urls diretamente em ''.
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('forum.urls')),
]
