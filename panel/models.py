from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    def __str__(self): return self.nombre

class Canal(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    url_origen = models.URLField(blank=True, null=True)
    logo = models.URLField(blank=True, null=True)
    proveedor_id = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    proveedor_source = models.CharField(max_length=20, blank=True, null=True, help_text="stix / claro / directo")
    proveedor_data = models.JSONField(blank=True, null=True, help_text="Metadata cruda del proveedor")
    def __str__(self): return self.nombre

class Plan(models.Model):
    nombre = models.CharField(max_length=100)
    meses = models.IntegerField(default=0)
    horas = models.IntegerField(default=0)
    max_conexiones = models.IntegerField(default=1)
    costo_creditos = models.IntegerField(default=1)    
    
    def calcular_expiracion(self, desde_fecha=None):
        """Calcula la fecha de vencimiento priorizando horas si existen."""
        base = desde_fecha if desde_fecha and desde_fecha > timezone.now() else timezone.now()
        
        # Si el plan tiene horas (ej. Demo de 2hs), sumamos horas.
        if self.horas > 0:
            return base + timedelta(hours=self.horas)
        
        # Si no tiene horas, sumamos meses (30 días por mes).
        return base + timedelta(days=30 * self.meses)

    @property
    def es_demo(self):
        """Un plan es demo si no cuesta créditos."""
        return self.costo_creditos == 0

    def calcular_expiracion(self, desde_fecha=None):
        """Calcula la fecha de vencimiento según horas o meses."""
        base = desde_fecha if desde_fecha and desde_fecha > timezone.now() else timezone.now()
        if self.horas > 0:
            return base + timedelta(hours=self.horas)
        return base + timedelta(days=30 * self.meses)

    def __str__(self): return self.nombre

class Reseller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    creditos = models.IntegerField(default=0)
    es_super = models.BooleanField(default=False)
    padre = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_resellers')
    password_plano = models.CharField(max_length=128, blank=True, null=True) # <--- AÑADIR ESTO
    def __str__(self): return self.user.username

class UsuarioIPTV(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    reseller = models.ForeignKey(Reseller, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    ultima_actividad = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    @property
    def is_online(self):
        if self.ultima_actividad:
            return timezone.now() < self.ultima_actividad + timedelta(minutes=5)
        return False

    @property
    def activo_status(self):
        return self.activo and self.fecha_expiracion > timezone.now()

    def __str__(self): return self.username