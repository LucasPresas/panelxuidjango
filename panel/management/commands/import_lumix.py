"""
Management command to import all LUMIXTV channels into the Canal model.
Usage: python manage.py import_lumix [--force]
"""
from django.core.management.base import BaseCommand, CommandError
from panel.lumix_provider import sync_canales


class Command(BaseCommand):
    help = "Importa todos los canales de LUMIXTV a las tablas Canal y Categoria"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Ignorar caché y forzar fetch desde lumixtv.es",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        if force:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write("Caché limpiada. Forzando fetch desde lumixtv.es...")

        self.stdout.write("Sincronizando canales desde LUMIXTV...")
        try:
            result = sync_canales()
            self.stdout.write(self.style.SUCCESS(
                f"✓ {result['created']} canales creados, "
                f"{result['updated']} actualizados, "
                f"{result['total']} total"
            ))
        except Exception as e:
            raise CommandError(f"Error importando canales: {e}")
