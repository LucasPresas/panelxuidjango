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
    url_origen = models.URLField()
    logo = models.URLField(blank=True, null=True)
    def __str__(self): return self.nombre

class Plan(models.Model):
    nombre = models.CharField(max_length=100)
    meses = models.IntegerField(default=0)
    horas = models.IntegerField(default=0)
    max_conexiones = models.IntegerField(default=1)
    costo_creditos = models.IntegerField(default=1)
    def __str__(self): return self.nombre

class Reseller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    creditos = models.IntegerField(default=0)
    es_super = models.BooleanField(default=False)
    padre = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_resellers')
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
