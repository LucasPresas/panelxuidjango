from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from panel import views, views_admin, views_auth

urlpatterns = [
    # Si alguien entra a la IP pelada, lo mandamos al login de reseller por defecto
    path('', lambda r: redirect('login_reseller')),
    
    # RUTA RESELLER
    path('login/', views_auth.login_reseller, name='login_reseller'),
    path('logout/', views_auth.logout_reseller, name='logout_reseller'),
    path('reseller/', views.reseller_panel, name='reseller_panel'),
    
    # RUTA ADMIN
    path('admin/importar-m3u/', views_admin.importar_m3u, name='importar_m3u'),
    path('admin/', admin.site.urls),
    
    # API / STREAMS (No tocar, Smarters las necesita)
    path('player_api.php', views.player_api, name='player_api'),
    path('xmltv.php', views.player_api, name='xmltv'),
    path('live/<str:username>/<str:password>/<int:stream_id>.<str:ext>', views.stream_redirect, name='stream_redirect'),
    path('get.php', views.get_m3u, name='get_m3u'),
]
