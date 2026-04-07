from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UsuarioIPTV, Canal, Categoria, Reseller, Plan
from django.utils import timezone
from datetime import timedelta
import time

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UsuarioIPTV, Canal, Categoria, Reseller, Plan
from django.utils import timezone
from datetime import timedelta
import time

# --- API XTREAM CODES (PARA REPRODUCTORES Y WEB PLAYER) ---
def player_api(request):
    u = request.GET.get('username')
    p = request.GET.get('password')
    action = request.GET.get('action')

    try:
        user = UsuarioIPTV.objects.get(username=u, password=p, activo=True)
        if not action:
            user.ultima_actividad = timezone.now()
            user.save()
    except UsuarioIPTV.DoesNotExist:
        return JsonResponse({"error": "Unauthorized"}, status=403)

    # 1. LOGIN INICIAL (Configurado para forzar puerto 80)
    if not action:
        return JsonResponse({
            "user_info": {
                "auth": 1,
                "status": "Active",
                "exp_date": str(int(user.fecha_expiracion.timestamp())),
                "username": user.username,
                "password": user.password,
                "message": "Bienvenido a Lurzavic",
                "active_cons": "0",
                "max_connections": str(user.plan.max_conexiones),
                "is_trial": "0",
                "revocation": "0",
                "trial_finished": False
            },
            "server_info": {
                "url": "1.lurzatv.com.ar",
                "port": "80",
                "https_port": "80", # Engañamos a la app para que no salte a 443
                "server_protocol": "http", # <--- FORZAMOS HTTP
                "rtmp_port": "80",
                "timezone": "America/Argentina/Buenos_Aires",
                "timestamp": int(time.time())
            }
        })

    # 2. CATEGORÍAS
    elif action == "get_live_categories":
        return JsonResponse([
            {
                "category_id": str(c.id), 
                "category_name": c.nombre, 
                "parent_id": 0 
            } 
            for c in Categoria.objects.all()
        ], safe=False)

    # 3. CANALES (Copia exacta de tu lógica de Flask)
    elif action == "get_live_streams":
        category_id = request.GET.get('category_id')
        canales = Canal.objects.all()
        
        if category_id and category_id != "0":
            canales = canales.filter(categoria_id=category_id)

        streams = []
        for i, c in enumerate(canales):
            streams.append({
                "num": i + 1,
                "name": c.nombre,
                "stream_type": "live", 
                "stream_id": int(c.id),
                "stream_icon": c.logo if c.logo else "",
                "epg_channel_id": "", 
                "added": "1625000000",
                "category_id": str(c.categoria.id),
                "custom_sid": "",
                "tv_archive": 0,
                "direct_source": "",
                "thumbnail": "",
                "container_extension": "m3u8"
            })
        return JsonResponse(streams, safe=False)

    # 4. VOD y SERIES (Vacío pero formato correcto)
    elif action in ["get_vod_streams", "get_vod_categories", "get_series", "get_series_categories"]:
        return JsonResponse([], safe=False) 

    return JsonResponse({"error": "Unknown action"}, status=400)

# --- FUNCIONES DE STREAMING ---
def stream_redirect(request, username, password, stream_id, ext=None):
    """Valida al usuario y lo redirige a la fuente original del video."""
    try:
        user = UsuarioIPTV.objects.get(username=username, password=password, activo=True)
        canal = Canal.objects.get(id=stream_id)
        
        # Agregamos los headers de tu script de Flask
        response = redirect(canal.url_origen)
        response['Access-Control-Allow-Origin'] = '*'
        response['Cache-Control'] = 'no-cache'
        return response
    except:
        return HttpResponse("Error", status=404)

# (El resto de funciones get_m3u y reseller_panel quedan igual)

def get_m3u(request):
    """Genera el archivo .m3u dinámico para el usuario."""
    u, p = request.GET.get('u'), request.GET.get('p')
    try:
        user = UsuarioIPTV.objects.get(username=u, password=p, activo=True)
        
        # Construcción de la lista con formato estándar
        m3u_content = ["#EXTM3U"]
        
        dominio = "1.lurzatv.com.ar"
        canales = Canal.objects.all()
        
        for c in canales:
            # Formato: #EXTINF:-1 tvg-id="ID" tvg-name="Nombre" tvg-logo="URL",Nombre
            linea_info = f'#EXTINF:-1 tvg-logo="{c.logo}" group-title="{c.categoria.nombre}",{c.nombre}'
            m3u_content.append(linea_info)
            
            # URL del stream que apunta a tu redirect
            url_stream = f'http://{dominio}/live/{u}/{p}/{c.id}.m3u8'
            m3u_content.append(url_stream)
        
        # Unimos todo con saltos de línea
        full_m3u = "\n".join(m3u_content)
        
        # Importante: El content_type debe ser application/x-mpegurl para Smarters
        return HttpResponse(full_m3u, content_type='application/x-mpegurl')
        
    except UsuarioIPTV.DoesNotExist:
        return HttpResponse("Usuario no encontrado o inactivo", status=403)
    except Exception as e:
        return HttpResponse(f"Error interno: {str(e)}", status=500)

# --- PANEL DE RESELLERS ---
@login_required
def reseller_panel(request):
    try:
        reseller = Reseller.objects.get(user=request.user)
    except Reseller.DoesNotExist:
        return HttpResponse("No eres reseller", status=403)

    if request.method == "POST":
        accion = request.POST.get('accion')
        u_id = request.POST.get('user_id')
        s_id = request.POST.get('sub_id')

        # --- GESTIÓN DE USUARIOS IPTV ---
        if accion == "crear_user":
            u_n, u_p = request.POST.get('username'), request.POST.get('password')
            plan = Plan.objects.get(id=request.POST.get('plan_id'))
            
            if reseller.creditos >= plan.costo_creditos:
                # Usa la lógica del modelo para calcular horas (demo) o meses (pago)
                exp = plan.calcular_expiracion()
                UsuarioIPTV.objects.create(
                    username=u_n, password=u_p, 
                    reseller=reseller, plan=plan, 
                    fecha_expiracion=exp
                )
                
                if plan.costo_creditos > 0:
                    reseller.creditos -= plan.costo_creditos
                    reseller.save()
                    messages.success(request, f"Cliente {u_n} creado ({plan.meses} mes/es).")
                else:
                    messages.success(request, f"Demo {u_n} creada por {plan.horas} horas.")
            else:
                messages.error(request, "Créditos insuficientes para este plan.")

        elif accion == "renovar" and u_id:
            ui = UsuarioIPTV.objects.get(id=u_id, reseller=reseller)
            
            # CONVERSIÓN: De Demo a Plan Real
            if ui.plan.costo_creditos == 0:
                # Buscamos plan de 1 mes que cueste créditos
                plan_mensual = Plan.objects.filter(costo_creditos__gt=0, meses__gte=1).first()
                
                if not plan_mensual:
                    messages.error(request, "No hay un plan mensual de pago configurado.")
                elif reseller.creditos >= plan_mensual.costo_creditos:
                    ui.plan = plan_mensual
                    ui.fecha_expiracion = timezone.now() + timedelta(days=30)
                    ui.save()
                    reseller.creditos -= plan_mensual.costo_creditos
                    reseller.save()
                    messages.success(request, f"¡{ui.username} ahora es cliente oficial por 1 mes!")
                else:
                    messages.error(request, "Créditos insuficientes para convertir demo.")
            
            # RENOVACIÓN NORMAL: Sumar tiempo al plan actual
            else:
                if reseller.creditos >= ui.plan.costo_creditos:
                    ui.fecha_expiracion = ui.plan.calcular_expiracion(ui.fecha_expiracion)
                    reseller.creditos -= ui.plan.costo_creditos
                    reseller.save()
                    ui.save()
                    messages.success(request, f"Usuario {ui.username} renovado.")
                else:
                    messages.error(request, "Créditos insuficientes.")

        elif accion == "editar_user" and u_id:
            ui = UsuarioIPTV.objects.get(id=u_id, reseller=reseller)
            ui.username = request.POST.get('username')
            ui.password = request.POST.get('password')
            ui.save()
            messages.success(request, "Datos actualizados.")

        elif accion == "borrar" and u_id:
            UsuarioIPTV.objects.get(id=u_id, reseller=reseller).delete()
            messages.warning(request, "Usuario eliminado.")

        # --- GESTIÓN DE SUB-RESELLERS (SUPER) ---
        elif reseller.es_super:
            if accion == "crear_sub":
                sn, sp = request.POST.get('sub_username'), request.POST.get('sub_password')
                sc = int(request.POST.get('sub_creditos', 0))
                if reseller.creditos >= sc:
                    new_u = User.objects.create_user(username=sn, password=sp)
                    Reseller.objects.create(user=new_u, creditos=sc, padre=reseller, password_plano=sp)
                    reseller.creditos -= sc
                    reseller.save()
                    messages.success(request, f"Vendedor {sn} creado.")
                else:
                    messages.error(request, "No tienes créditos suficientes.")

            elif accion == "cargar_creditos" and s_id:
                amt = int(request.POST.get('extra_creditos', 0))
                if reseller.creditos >= amt:
                    sub = Reseller.objects.get(id=s_id, padre=reseller)
                    sub.creditos += amt
                    reseller.creditos -= amt
                    sub.save(); reseller.save()
                    messages.success(request, "Créditos cargados al sub-reseller.")
                else:
                    messages.error(request, "Saldo insuficiente para transferir.")

            elif accion == "editar_reseller" and s_id:
                # CORRECCIÓN AQUÍ: Guardar el objeto User correctamente
                sub_reseller = Reseller.objects.get(id=s_id, padre=reseller)
                user_to_edit = sub_reseller.user
                
                nuevo_nombre = request.POST.get('sub_username')
                nueva_pass = request.POST.get('sub_password')
                
                if nuevo_nombre:
                    user_to_edit.username = nuevo_nombre
                if nueva_pass:
                    user_to_edit.set_password(nueva_pass)
                    sub_reseller.password_plano = nueva_pass
                
                user_to_edit.save() # Guardar el User es lo que persiste el cambio de nombre
                messages.success(request, f"Vendedor {nuevo_nombre} actualizado correctamente.")        

            elif accion == "borrar_reseller" and s_id:
                sub = Reseller.objects.get(id=s_id, padre=reseller)
                u_del = sub.user
                sub.delete(); u_del.delete()
                messages.error(request, "Vendedor eliminado.")

        return redirect('reseller_panel')

    return render(request, 'panel/reseller.html', {
        'reseller': reseller, 
        'usuarios': UsuarioIPTV.objects.filter(reseller=reseller),
        'planes': Plan.objects.all(), 
        'subs': Reseller.objects.filter(padre=reseller) if reseller.es_super else None
    })