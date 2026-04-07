from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UsuarioIPTV, Canal, Categoria, Reseller, Plan
from django.utils import timezone
from datetime import timedelta
import time

# --- API XTREAM CODES (FIXED FOR WEB PLAYER) ---
def player_api(request):
    u, p, action = request.GET.get('username'), request.GET.get('password'), request.GET.get('action')
    try:
        user = UsuarioIPTV.objects.get(username=u, password=p, activo=True)
        user.ultima_actividad = timezone.now(); user.save()
    except: return JsonResponse({"error": "Auth failed"}, status=403)
    
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
                "revocation": "0",
                "trial_finished": False
            },
            "server_info": {
                "url": "1.lurzatv.com.ar",
                "port": "80",
                "https_port": "443",
                "server_protocol": "http",
                "rtmp_port": "80",
                "timezone": "America/Argentina/Buenos_Aires",
                "timestamp": int(time.time())
            }
        })
    elif action == "get_live_categories": 
        return JsonResponse([{"category_id": str(c.id), "category_name": c.nombre} for c in Categoria.objects.all()], safe=False)
    elif action == "get_live_streams": 
        return JsonResponse([{"num": i+1, "name": c.nombre, "stream_id": c.id, "category_id": str(c.categoria.id), "container_extension": "m3u8"} for i, c in enumerate(Canal.objects.all())], safe=False)
    return JsonResponse([], safe=False)

# (El resto de tus funciones stream_redirect, get_m3u y reseller_panel se mantienen igual...)
def stream_redirect(request, username, password, stream_id, ext=None):
    try:
        user = UsuarioIPTV.objects.get(username=username, password=password, activo=True)
        user.ultima_actividad = timezone.now(); user.save()
        return redirect(Canal.objects.get(id=stream_id).url_origen)
    except: return HttpResponse("Offline", status=404)

def get_m3u(request):
    u, p = request.GET.get('u'), request.GET.get('p')
    try:
        user = UsuarioIPTV.objects.get(username=u, password=p, activo=True)
        m3u = "#EXTM3U\n"
        for c in Canal.objects.all(): m3u += f'#EXTINF:-1 tvg-logo="{c.logo}",{c.nombre}\nhttp://1.lurzatv.com.ar/live/{u}/{p}/{c.id}.m3u8\n'
        return HttpResponse(m3u, content_type='audio/x-mpegurl')
    except: return HttpResponse("Forbidden", status=403)

@login_required
def reseller_panel(request):
    try: reseller = Reseller.objects.get(user=request.user)
    except: return HttpResponse("No eres reseller", status=403)
    if request.method == "POST":
        accion = request.POST.get('accion'); u_id = request.POST.get('user_id'); s_id = request.POST.get('sub_id')
        if accion == "crear_user":
            u_n, u_p, p_id = request.POST.get('username'), request.POST.get('password'), request.POST.get('plan_id')
            plan = Plan.objects.get(id=p_id)
            exp = timezone.now() + (timedelta(hours=plan.horas) if plan.horas > 0 else timedelta(days=30 * plan.meses))
            UsuarioIPTV.objects.create(username=u_n, password=u_p, reseller=reseller, plan=plan, fecha_expiracion=exp)
            messages.success(request, f"Cliente {u_n} creado.")
        elif accion == "editar_user" and u_id:
            ui = UsuarioIPTV.objects.get(id=u_id, reseller=reseller)
            ui.username, ui.password = request.POST.get('username'), request.POST.get('password')
            ui.save(); messages.success(request, "Cliente actualizado.")
        elif accion == "renovar" and u_id:
            ui = UsuarioIPTV.objects.get(id=u_id, reseller=reseller)
            if ui.plan.horas == 0 and reseller.creditos >= ui.plan.costo_creditos:
                ui.fecha_expiracion = (ui.fecha_expiracion if ui.fecha_expiracion > timezone.now() else timezone.now()) + timedelta(days=30)
                reseller.creditos -= ui.plan.costo_creditos
                reseller.save(); ui.save(); messages.success(request, "Renovado.")
            else: messages.error(request, "Créditos insuficientes.")
        elif accion == "borrar" and u_id:
            UsuarioIPTV.objects.get(id=u_id, reseller=reseller).delete(); messages.warning(request, "Borrado.")
        elif reseller.es_super:
            if accion == "crear_sub":
                sn, sp, sc = request.POST.get('sub_username'), request.POST.get('sub_password'), int(request.POST.get('sub_creditos', 0))
                if reseller.creditos >= sc:
                    new_u = User.objects.create_user(username=sn, password=sp)
                    Reseller.objects.create(user=new_u, creditos=sc, padre=reseller)
                    reseller.creditos -= sc; reseller.save(); messages.success(request, "Vendedor creado.")
            elif accion == "editar_reseller" and s_id:
                sub = Reseller.objects.get(id=s_id, padre=reseller)
                sub.user.username = request.POST.get('sub_username')
                if request.POST.get('sub_password'): sub.user.set_password(request.POST.get('sub_password'))
                sub.user.save(); messages.success(request, "Vendedor actualizado.")
            elif accion == "cargar_creditos" and s_id:
                amt = int(request.POST.get('extra_creditos', 0))
                if reseller.creditos >= amt:
                    sub = Reseller.objects.get(id=s_id, padre=reseller)
                    sub.creditos += amt; sub.save()
                    reseller.creditos -= amt; reseller.save(); messages.success(request, "Créditos cargados.")
            elif accion == "borrar_reseller" and s_id:
                sub = Reseller.objects.get(id=s_id, padre=reseller)
                u_del = sub.user; sub.delete(); u_del.delete(); messages.error(request, "Vendedor eliminado.")
        return redirect('reseller_panel')
    return render(request, 'panel/reseller.html', {
        'reseller': reseller, 'usuarios': UsuarioIPTV.objects.filter(reseller=reseller),
        'planes': Plan.objects.all(), 'subs': Reseller.objects.filter(padre=reseller) if reseller.es_super else None
    })
