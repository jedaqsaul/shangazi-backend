"""
Report Service
--------------
Generates exportable reports from donation data.
Currently supports CSV. Can be extended to Excel/PDF.
"""

import csv
import io
from flask import make_response
from app.services.donation_service import DonationService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReportService:

    @staticmethod
    def export_donations_csv(status: str | None = None) -> object:
        """
        Generate a CSV file of all donations and return a Flask response.
        Filters by status if provided.
        """
        donations = DonationService.get_all_for_export(status=status)

        output = io.StringIO()

        if not donations:
            writer = csv.writer(output)
            writer.writerow(["No donations found matching the selected filters."])
        else:
            fieldnames = list(donations[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(donations)

        filename = f"shangazi_donations{'_' + status if status else ''}.csv"

        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = "text/csv"

        logger.info(
            "Donation report exported",
            extra={"extra": {"total_records": len(donations), "status_filter": status}}
        )

        return response
