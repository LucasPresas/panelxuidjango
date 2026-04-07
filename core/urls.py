from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from panel import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Login/Logout - Usamos las vistas nativas pero con nuestros templates
    path('login/', auth_views.LoginView.as_view(template_name='panel/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    path('reseller/', views.reseller_panel, name='reseller_panel'),
    path('player_api.php', views.player_api),
    path('get.php', views.get_m3u),
    path('live/<str:username>/<str:password>/<int:stream_id>.<str:ext>', views.stream_redirect),
]
