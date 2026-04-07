from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UsuarioIPTV, Canal, Categoria, Reseller, Plan
from django.utils import timezone
from datetime import timedelta
import time

# --- 1. API XTREAM CODES (SMARTERS / OTT) ---
def player_api(request):
    u = request.GET.get('username')
    p = request.GET.get('password')
    action = request.GET.get('action')

    try:
        if action:
            user = UsuarioIPTV.objects.get(username=u, activo=True)
        else:
            user = UsuarioIPTV.objects.get(username=u, password=p, activo=True)
    except:
        return JsonResponse({"error": "Auth failed"}, status=403)

    if not action:
        return JsonResponse({
            "user_info": {
                "username": user.username,
                "password": user.password,
                "auth": 1,
                "status": "Active",
                "exp_date": str(int(user.fecha_expiracion.timestamp())),
                "is_trial": "0",
                "active_cons": "0",
                "max_connections": str(user.plan.max_conexiones),
                "allowed_output_formats": ["m3u8", "ts", "rtmp"]
            },
            "server_info": {
                "url": "82.39.109.129",
                "port": "80",
                "https_port": "443",
                "server_protocol": "http",
                "rtmp_port": "8000",
                "timezone": "America/Argentina",
                "timestamp": int(time.time())
            }
        })

    elif action == "get_live_categories":
        data = [{"category_id": str(c.id), "category_name": c.nombre, "parent_id": 0} for c in Categoria.objects.all()]
        return JsonResponse(data, safe=False)

    elif action == "get_live_streams":
        data = [
            {
                "num": i + 1,
                "name": c.nombre,
                "stream_type": "live",
                "stream_id": c.id,
                "stream_icon": c.logo if c.logo else "",
                "category_id": str(c.categoria.id),
                "container_extension": "m3u8",
                "custom_sid": "",
                "direct_source": "",
                "tv_archive": 0
            } for i, c in enumerate(Canal.objects.all())
        ]
        return JsonResponse(data, safe=False)

    # ESTO CORRIGE TUS LOGS: safe=False para listas vacías
    return JsonResponse([], safe=False)

# --- 2. REDIRECCIÓN Y M3U ---
def stream_redirect(request, username, password, stream_id, ext=None):
    try:
        UsuarioIPTV.objects.get(username=username, activo=True)
        canal = Canal.objects.get(id=stream_id)
        return redirect(canal.url_origen)
    except:
        return HttpResponse("Stream no disponible", status=404)

def get_m3u(request):
    u, p = request.GET.get('u'), request.GET.get('p')
    try:
        user = UsuarioIPTV.objects.get(username=u, password=p, activo=True)
        m3u = "#EXTM3U\n"
        for c in Canal.objects.all():
            m3u += f'#EXTINF:-1 tvg-logo="{c.logo}" group-title="{c.categoria.nombre}",{c.nombre}\n'
            m3u += f'http://82.39.109.129/live/{u}/{p}/{c.id}.m3u8\n'
        return HttpResponse(m3u, content_type='audio/x-mpegurl')
    except:
        return HttpResponse("Forbidden", status=403)

# --- 3. PANEL RESELLER ---
@login_required
def reseller_panel(request):
    try:
        reseller = Reseller.objects.get(user=request.user)
    except:
        return HttpResponse("No eres reseller", status=403)

    if request.method == "POST":
        accion = request.POST.get('accion')
        user_id = request.POST.get('user_id')
        if accion == "crear_user":
            u_name, u_pass, p_id = request.POST.get('username'), request.POST.get('password'), request.POST.get('plan_id')
            if not UsuarioIPTV.objects.filter(username=u_name).exists():
                plan = Plan.objects.get(id=p_id)
                UsuarioIPTV.objects.create(username=u_name, password=u_pass, reseller=reseller, plan=plan)
                messages.success(request, "Creado")
        elif accion == "renovar" and user_id:
            u_iptv = UsuarioIPTV.objects.get(id=user_id, reseller=reseller)
            u_iptv.fecha_expiracion = (u_iptv.fecha_expiracion if u_iptv.fecha_expiracion > timezone.now() else timezone.now()) + timedelta(days=30)
            u_iptv.save()
            messages.success(request, "Renovado")
        return redirect('reseller_panel')

    return render(request, 'panel/reseller.html', {
        'reseller': reseller,
        'usuarios': UsuarioIPTV.objects.filter(reseller=reseller),
        'subs': Reseller.objects.filter(padre=reseller),
        'planes': Plan.objects.all()
    })
