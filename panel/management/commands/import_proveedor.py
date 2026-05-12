"""
Management command to import all ProveedorTV channels into the Canal model.
Usage: python manage.py import_proveedor [--force]
"""
from django.core.management.base import BaseCommand, CommandError
from panel.proveedor_provider import sync_canales


class Command(BaseCommand):
    help = "Importa todos los canales del proveedor a las tablas Canal y Categoria"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignorar caché y forzar fetch desde el proveedor",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        if force:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write("Caché limpiada. Forzando fetch...")

        self.stdout.write("Sincronizando canales desde el proveedor...")
        try:
            result = sync_canales()
            self.stdout.write(self.style.SUCCESS(
                f"✓ {result['created']} canales creados, "
                f"{result['updated']} actualizados, "
                f"{result['total']} total"
            ))
        except Exception as e:
            raise CommandError(f"Error importando canales: {e}")
