from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Canal, Categoria
import re

def importar_m3u(request):
    if request.method == "POST":
        m3u_text = request.POST.get("m3u_text")
        # Regex simple para encontrar Nombre y URL en formato M3U
        # #EXTINF:-1...,Nombre
        # http://...
        matches = re.findall(r'#EXTINF:.*?,(.*?)\n(http.*?)$', m3u_text, re.MULTILINE)
        
        count = 0
        if matches:
            # Creamos una categoría por defecto para la importación
            cat, _ = Categoria.objects.get_or_create(nombre="Importados M3U")
            for name, url in matches:
                Canal.objects.get_or_create(nombre=name.strip(), categoria=cat, url_origen=url.strip())
                count += 1
            messages.success(request, f"¡Éxito! Se importaron {count} canales.")
        else:
            messages.error(request, "No se encontraron canales válidos en el texto.")
        return redirect('/admin/panel/canal/')
    
    return render(request, "admin/panel/canal/importar.html")
