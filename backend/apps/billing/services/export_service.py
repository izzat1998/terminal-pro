"""
Statement export service for Excel and PDF generation.
"""

from io import BytesIO
from typing import TYPE_CHECKING

from django.template.loader import render_to_string
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from apps.core.services.base_service import BaseService


if TYPE_CHECKING:
    from ..models import MonthlyStatement


class StatementExportService(BaseService):
    """Service for exporting statements to Excel and PDF formats."""

    def export_to_excel(self, statement: "MonthlyStatement") -> BytesIO:
        """Generate Excel file from statement."""
        wb = Workbook()
        ws = wb.active
        ws.title = f"Выписка {statement.month:02d}-{statement.year}"

        # Styles
        header_font = Font(bold=True, size=14)
        subheader_font = Font(bold=True, size=11)
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_text = Font(bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Title section
        ws.merge_cells("A1:K1")
        ws["A1"] = f"Выписка за {statement.month_name} {statement.year}"
        ws["A1"].font = header_font
        ws["A1"].alignment = Alignment(horizontal="center")

        ws["A3"] = f"Компания: {statement.company.name}"
        ws["A4"] = f"Метод расчёта: {statement.billing_method_display}"
        ws["A5"] = f"Дата формирования: {statement.generated_at.strftime('%d.%m.%Y %H:%M')}"

        # Summary section
        ws["A7"] = "ИТОГО:"
        ws["A7"].font = subheader_font
        ws["A8"] = f"Контейнеров: {statement.total_containers}"
        ws["A9"] = f"Оплачиваемых дней: {statement.total_billable_days}"
        ws["A10"] = f"Сумма USD: ${statement.total_usd:,.2f}"
        ws["A11"] = f"Сумма UZS: {statement.total_uzs:,.0f} сум"

        # Table headers
        headers = [
            "Контейнер",
            "Размер",
            "Статус",
            "Начало",
            "Конец",
            "Всего дней",
            "Льготных",
            "Оплачиваемых",
            "Ставка USD",
            "Сумма USD",
            "Сумма UZS",
        ]

        row = 13
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_text
            cell.fill = header_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center")

        # Table data
        for item in statement.line_items.all():
            row += 1
            end_display = (
                "На терминале" if item.is_still_on_terminal else item.period_end.strftime("%d.%m.%Y")
            )
            data = [
                item.container_number,
                item.container_size_display,
                item.container_status_display,
                item.period_start.strftime("%d.%m.%Y"),
                end_display,
                item.total_days,
                item.free_days,
                item.billable_days,
                float(item.daily_rate_usd),
                float(item.amount_usd),
                float(item.amount_uzs),
            ]
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col, value=value)
                cell.border = thin_border
                if col >= 6:  # Numbers
                    cell.alignment = Alignment(horizontal="right")

        # Adjust column widths
        column_widths = [15, 10, 12, 12, 14, 10, 10, 12, 12, 12, 15]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    def export_to_pdf(self, statement: "MonthlyStatement") -> BytesIO:
        """Generate PDF from statement using HTML template."""
        from weasyprint import HTML

        # Render HTML template
        html_content = render_to_string(
            "billing/statement_pdf.html",
            {
                "statement": statement,
                "line_items": statement.line_items.all(),
            },
        )

        # Convert to PDF
        output = BytesIO()
        HTML(string=html_content).write_pdf(output)
        output.seek(0)
        return output

    def get_excel_filename(self, statement: "MonthlyStatement") -> str:
        """Generate filename for Excel export."""
        company_slug = statement.company.slug or "company"
        return f"statement_{company_slug}_{statement.year}_{statement.month:02d}.xlsx"

    def get_pdf_filename(self, statement: "MonthlyStatement") -> str:
        """Generate filename for PDF export."""
        company_slug = statement.company.slug or "company"
        return f"statement_{company_slug}_{statement.year}_{statement.month:02d}.pdf"
