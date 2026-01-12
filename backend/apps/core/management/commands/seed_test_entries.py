"""
Seed test container entries with companies and images.
Run: python manage.py seed_test_entries
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Company
from apps.containers.services import ContainerService
from apps.files.models import File, FileAttachment, FileCategory
from apps.terminal_operations.models import ContainerEntry, ContainerOwner


User = get_user_model()


class Command(BaseCommand):
    help = "Seed test container entries with companies and sample images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--entries",
            type=int,
            default=20,
            help="Number of entries to create (default: 20)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Creating test data with companies and images..."))

        # Ensure we have required data
        companies = self._ensure_companies()
        owners = self._ensure_container_owners()
        file_category = self._ensure_file_category()
        admin_user = self._get_or_create_admin()

        # Create container entries with images
        container_service = ContainerService()
        entries_created = 0
        images_created = 0

        # Sample data
        iso_types = ["22G1", "42G1", "45G1", "22R1", "42R1"]
        statuses = ["Порожний", "Гружёный"]
        transport_types = ["Авто", "Вагон"]
        cargo_names = [
            "Хлопок",
            "Текстиль",
            "Автозапчасти",
            "Электроника",
            "Стройматериалы",
            "Продукты питания",
            "Мебель",
            "Оборудование",
        ]
        locations = ["K1", "K2", "K3", "H1", "H2", "A1", "A2", "B1"]

        for i in range(options["entries"]):
            try:
                # Generate container number
                prefix = random.choice(["HDMU", "MSKU", "TCNU", "CMAU", "MAEU"])
                number = f"{prefix}{random.randint(1000000, 9999999)}"

                # Create or get container
                container = container_service.get_or_create_container(
                    container_number=number, iso_type=random.choice(iso_types)
                )

                # Random dates within last 30 days
                entry_time = timezone.now() - timedelta(days=random.randint(0, 30))

                # 30% chance of having exit date
                exit_date = None
                if random.random() < 0.3:
                    exit_date = entry_time + timedelta(days=random.randint(1, 10))

                # Create entry with company
                entry = ContainerEntry.objects.create(
                    container=container,
                    company=random.choice(companies),
                    container_owner=random.choice(owners) if random.random() > 0.3 else None,
                    status=random.choice(statuses),
                    transport_type=random.choice(transport_types),
                    transport_number=self._generate_vehicle_plate() if random.random() > 0.5 else "",
                    entry_train_number=f"П-{random.randint(100, 999)}" if random.random() > 0.7 else "",
                    entry_time=entry_time,
                    exit_date=exit_date,
                    exit_transport_type=random.choice(transport_types) if exit_date else None,
                    cargo_name=random.choice(cargo_names) if random.random() > 0.3 else "",
                    cargo_weight=Decimal(str(random.randint(5, 25))) if random.random() > 0.4 else None,
                    location=random.choice(locations),
                    recorded_by=admin_user,
                    note=f"Тестовая запись #{i + 1}" if random.random() > 0.7 else "",
                )

                entries_created += 1

                # Add 1-3 sample images to ~60% of entries
                if random.random() < 0.6:
                    num_images = random.randint(1, 3)
                    for img_idx in range(num_images):
                        self._create_sample_image(entry, file_category, img_idx)
                        images_created += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Failed to create entry: {e}"))
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully created:\n"
                f"  - {entries_created} container entries\n"
                f"  - {images_created} attached images\n"
                f"  - {len(companies)} companies available"
            )
        )

    def _ensure_companies(self):
        """Create test companies if they don't exist"""
        company_data = [
            {"name": "ООО Транс Логистик", "slug": "trans-logistic"},
            {"name": "АО Карго Экспресс", "slug": "cargo-express"},
            {"name": "ИП Контейнер Сервис", "slug": "container-service"},
            {"name": "ООО Глобал Трейд", "slug": "global-trade"},
            {"name": "АО Азия Транспорт", "slug": "asia-transport"},
        ]

        companies = []
        for data in company_data:
            company, created = Company.objects.get_or_create(
                slug=data["slug"], defaults={"name": data["name"], "is_active": True}
            )
            companies.append(company)
            if created:
                self.stdout.write(f"  Created company: {company.name}")

        return companies

    def _ensure_container_owners(self):
        """Create container owners if they don't exist"""
        from django.utils.text import slugify

        owner_names = [
            "Maersk Line",
            "MSC Mediterranean",
            "CMA CGM",
            "COSCO Shipping",
            "Hapag-Lloyd",
        ]

        owners = []
        for name in owner_names:
            slug = slugify(name)
            owner, created = ContainerOwner.objects.get_or_create(name=name, defaults={"slug": slug})
            owners.append(owner)

        return owners

    def _ensure_file_category(self):
        """Get or create container_image file category"""
        category, created = FileCategory.objects.get_or_create(
            code="container_image",
            defaults={
                "name": "Фото контейнера",
                "description": "Фотографии контейнеров",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 5,
                "is_active": True,
            },
        )
        return category

    def _get_or_create_admin(self):
        """Get or create admin user for recorded_by"""
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(username="admin", password="admin123", user_type="admin")
        return admin

    def _generate_vehicle_plate(self):
        """Generate random Uzbek vehicle plate"""
        region = random.choice(["01", "10", "20", "30", "40", "50", "60", "70", "80", "90"])
        letters = "".join(random.choices("ABCDEFGHKLMNPRSTUVXYZ", k=1))
        numbers = f"{random.randint(100, 999)}"
        suffix = "".join(random.choices("ABCDEFGHKLMNPRSTUVXYZ", k=2))
        return f"{region}{letters}{numbers}{suffix}"

    def _create_sample_image(self, entry: ContainerEntry, category: FileCategory, index: int):
        """Create a sample placeholder image and attach to entry"""
        # Generate a simple colored PNG (placeholder)
        # Using a simple 1x1 pixel PNG with random color
        colors = [
            (52, 152, 219),  # Blue
            (46, 204, 113),  # Green
            (231, 76, 60),  # Red
            (241, 196, 15),  # Yellow
            (155, 89, 182),  # Purple
        ]
        color = random.choice(colors)

        # Create minimal PNG (1x1 pixel, just for testing structure)
        # In real scenarios, you'd have actual container photos
        png_data = self._create_simple_png(color, width=100, height=100)

        # Create File record
        filename = f"container_{entry.container.container_number}_{index + 1}.png"

        file_obj = File.objects.create(
            file_category=category,
            original_filename=filename,
            mime_type="image/png",
            size=len(png_data),
        )

        # Save the actual file
        file_obj.file.save(filename, ContentFile(png_data), save=True)

        # Create FileAttachment linking to ContainerEntry
        content_type = ContentType.objects.get_for_model(ContainerEntry)
        FileAttachment.objects.create(
            file=file_obj,
            content_type=content_type,
            object_id=entry.id,
            attachment_type="container_photo",
            description=f"Фото контейнера #{index + 1}",
            display_order=index,
        )

    def _create_simple_png(self, color: tuple, width: int = 100, height: int = 100) -> bytes:
        """
        Create a simple solid-color PNG image.
        This is a minimal PNG for testing - in production you'd use actual photos.
        """
        import struct
        import zlib

        def make_png(width, height, rgb):
            """Generate minimal PNG bytes"""
            r, g, b = rgb

            # PNG signature
            signature = b"\x89PNG\r\n\x1a\n"

            # IHDR chunk
            ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
            ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

            # IDAT chunk (image data)
            raw_data = b""
            for y in range(height):
                raw_data += b"\x00"  # filter byte
                for x in range(width):
                    raw_data += bytes([r, g, b])

            compressed = zlib.compress(raw_data, 9)
            idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
            idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)

            # IEND chunk
            iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
            iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

            return signature + ihdr + idat + iend

        return make_png(width, height, color)
