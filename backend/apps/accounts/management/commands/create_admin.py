from django.core.management.base import BaseCommand

from apps.accounts.models import CustomUser


class Command(BaseCommand):
    help = "Create initial admin user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", type=str, default="admin", help="Admin username"
        )
        parser.add_argument(
            "--email", type=str, default="admin@example.com", help="Admin email"
        )
        parser.add_argument(
            "--password", type=str, default="admin123", help="Admin password"
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if CustomUser.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Admin user "{username}" already exists')
            )
            return

        CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_admin=True,
            is_staff=True,
            is_superuser=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user "{username}"')
        )
