from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Plan(models.Model):
    nombre = models.CharField(max_length=100)
    meses = models.IntegerField(default=1)
    max_conexiones = models.IntegerField(default=1)
    costo_creditos = models.IntegerField(default=1)
    def __str__(self): return f"{self.nombre}"

class Reseller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    creditos = models.IntegerField(default=0)
    es_super = models.BooleanField(default=False, help_text="Puede crear otros Resellers")
    padre = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_resellers')

    def __str__(self):
        tipo = "SUPER" if self.es_super else "RES"
        return f"[{tipo}] {self.user.username} ({self.creditos} cr)"

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    def __str__(self): return self.nombre

class Canal(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    url_origen = models.URLField()
    logo = models.URLField(blank=True, null=True)
    def __str__(self): return self.nombre

class UsuarioIPTV(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)
    reseller = models.ForeignKey(Reseller, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.reseller.creditos >= self.plan.costo_creditos:
                self.reseller.creditos -= self.plan.costo_creditos
                self.reseller.save()
                self.fecha_expiracion = timezone.now() + timedelta(days=30 * self.plan.meses)
            else:
                raise Exception("Sin créditos suficientes")
        super().save(*args, **kwargs)
