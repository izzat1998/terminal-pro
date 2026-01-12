"""
Management command to seed initial file categories.
"""

from django.core.management.base import BaseCommand

from apps.files.models import FileCategory


class Command(BaseCommand):
    help = "Seed initial file categories for ERP system"

    def handle(self, *args, **kwargs):
        """Create default file categories."""

        categories = [
            {
                "code": "container_image",
                "name": "Container Image",
                "description": "Photos and images of containers",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 10,
            },
            {
                "code": "invoice_pdf",
                "name": "Invoice",
                "description": "Invoice documents",
                "allowed_mime_types": ["application/pdf"],
                "max_file_size_mb": 5,
            },
            {
                "code": "bill_of_lading",
                "name": "Bill of Lading",
                "description": "Shipping documents",
                "allowed_mime_types": ["application/pdf", "image/jpeg", "image/png"],
                "max_file_size_mb": 10,
            },
            {
                "code": "general_document",
                "name": "General Document",
                "description": "General documents and files",
                "allowed_mime_types": [
                    "application/pdf",
                    "application/msword",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "image/jpeg",
                    "image/png",
                ],
                "max_file_size_mb": 15,
            },
            {
                "code": "truck_photo",
                "name": "Truck Photo",
                "description": "Photos of trucks for pre-orders",
                "allowed_mime_types": ["image/jpeg", "image/png", "image/webp"],
                "max_file_size_mb": 10,
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories:
            category, created = FileCategory.objects.update_or_create(
                code=cat_data["code"],
                defaults={
                    "name": cat_data["name"],
                    "description": cat_data["description"],
                    "allowed_mime_types": cat_data["allowed_mime_types"],
                    "max_file_size_mb": cat_data["max_file_size_mb"],
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✓ Created: {category.name}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"⟳ Updated: {category.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Completed! Created {created_count}, Updated {updated_count}"
            )
        )
