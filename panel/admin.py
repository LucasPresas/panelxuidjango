from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin, StackedInline
from .models import Plan, Reseller, Categoria, Canal, UsuarioIPTV
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages

# --- CONFIGURACIÓN DE VENDEDORES ---
class ResellerInline(StackedInline):
    model = Reseller
    can_delete = False
    verbose_name_plural = 'Información de Vendedor'

admin.site.unregister(User)

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    inlines = (ResellerInline,)
    list_display = ('username', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Permisos', {'fields': ('is_active', 'is_staff')}),
    )

@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ('nombre', 'meses', 'horas', 'costo_creditos')

@admin.register(Categoria)
class CategoriaAdmin(ModelAdmin):
    list_display = ('nombre',)

# --- ADMIN DE CANALES CON BOTÓN M3U GRANDE ---
@admin.register(Canal)
class CanalAdmin(ModelAdmin):
    list_display = ('nombre', 'categoria', 'proveedor_id', 'proveedor_source', 'url_origen')
    list_filter = ('categoria', 'proveedor_source')
    search_fields = ('nombre', 'proveedor_id')
    
    # Cambiamos el template de la lista solo para este modelo
    change_list_template = "admin/panel/canal/change_list.html"

@admin.register(UsuarioIPTV)
class UsuarioIPTVAdmin(ModelAdmin):
    list_display = ('username', 'reseller', 'plan', 'fecha_expiracion', 'activo')
    list_filter = ('plan', 'reseller', 'activo')
    search_fields = ('username',)
