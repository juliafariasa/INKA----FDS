from django.urls import path

from . import views

app_name = 'forum'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('quem-somos/', views.QuemSomosView.as_view(), name='quem_somos'),
    path('sobre-o-projeto/', views.SobreProjetoView.as_view(),
         name='sobre_projeto'),
    path('fale-conosco/', views.FaleConoscoView.as_view(),
         name='fale_conosco'),
    path('estudios/', views.EstudiosView.as_view(), name='estudios'),
    path('estudios/novo/', views.EstudioNovoView.as_view(),
         name='estudio_novo'),
    path('estudios/<int:estudio_id>/', views.EstudioPerfilView.as_view(),
         name='estudio_perfil'),
    path('estudios/<int:estudio_id>/qrcode/',
         views.EstudioQrCodeView.as_view(), name='estudio_qrcode'),
    path('estudios/<int:estudio_id>/diagnostico/',
         views.DiagnosticoView.as_view(), name='estudio_diagnostico'),
    path('estudios/<int:estudio_id>/residuos/',
         views.ResiduosView.as_view(), name='estudio_residuos'),
]
