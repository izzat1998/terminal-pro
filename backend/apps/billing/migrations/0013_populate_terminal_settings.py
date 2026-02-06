"""
Data migration: populate TerminalSettings singleton with MTT company details.

Source: С-фактура_Интерейл_Июль_2_.xlsx (official Счёт-фактура template).
"""

from decimal import Decimal

from django.db import migrations


def populate_terminal_settings(apps, schema_editor):
    TerminalSettings = apps.get_model("billing", "TerminalSettings")
    obj, created = TerminalSettings.objects.get_or_create(pk=1)

    obj.company_name = 'ООО "MULTIMODAL TRANS TERMINAL"'
    obj.legal_address = (
        "Таш.обл., Зангиатинский р-н, ссг Назарбек, ул. Лойихачи, дом № 7"
    )
    obj.phone = "1503388"

    obj.bank_name = 'АКБ "Xamkor Bank", Яккасарой ф-л, г. Ташкент'
    obj.bank_account = "2020 8000 2002 7354 8001"
    obj.mfo = "00083"
    obj.inn = "207202576"
    obj.vat_registration_code = "327040006645"
    obj.vat_rate = Decimal("12.00")

    obj.director_name = "Талипов Х.Х."
    obj.director_title = "Руководитель"
    obj.accountant_name = "Иристаева Н.Т."
    obj.basis_document = "Устава"
    obj.default_usd_uzs_rate = Decimal("12591.57")

    obj.save()


def clear_terminal_settings(apps, schema_editor):
    """Reverse: reset to blank defaults (does not delete the row)."""
    TerminalSettings = apps.get_model("billing", "TerminalSettings")
    TerminalSettings.objects.filter(pk=1).update(
        company_name="",
        legal_address="",
        phone="",
        bank_name="",
        bank_account="",
        mfo="",
        inn="",
        vat_registration_code="",
        vat_rate=Decimal("12.00"),
        director_name="",
        director_title="Руководитель",
        accountant_name="",
        basis_document="Устава",
        default_usd_uzs_rate=Decimal("0.00"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0012_add_terminal_settings_model"),
    ]

    operations = [
        migrations.RunPython(
            populate_terminal_settings,
            clear_terminal_settings,
        ),
    ]
