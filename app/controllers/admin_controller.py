"""
Admin Controller
----------------
Handles HTTP layer for all protected admin dashboard endpoints.
All routes require valid JWT. Some require super_admin role.
"""

from flask import request
from app.services.donation_service import DonationService
from app.services.report_service import ReportService
from app.models.audit_log import AuditLog
from app.middleware.validators import validate_request, DonationFilterSchema
from app.utils.error_handlers import error_response, success_response
from app.middleware.auth_middleware import get_current_user_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdminController:

    @staticmethod
    def get_donations():
        """
        GET /api/admin/donations
        Paginated, filterable donation list.
        Query params: page, per_page, status, search, date_from, date_to
        """
        data, errors = validate_request(DonationFilterSchema, request.args.to_dict())
        if errors:
            return error_response(str(errors), "VALIDATION_ERROR", 400)

        try:
            result = DonationService.get_donations(
                page=data.get("page", 1),
                per_page=data.get("per_page", 20),
                status=data.get("status"),
                search=data.get("search"),
                date_from=data.get("date_from"),
                date_to=data.get("date_to"),
            )
            return success_response(data=result)

        except Exception as e:
            logger.error("Failed to fetch donations", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve donations.", "SERVER_ERROR", 500)

    @staticmethod
    def get_donation(donation_id: str):
        """
        GET /api/admin/donations/<donation_id>
        Retrieve a single donation by ID.
        """
        from app.models.donation import Donation
        donation = Donation.query.get(donation_id)

        if not donation:
            return error_response("Donation not found.", "NOT_FOUND", 404)

        AuditLog.log(
            action="DONATION_VIEWED",
            user_id=get_current_user_id(),
            resource="donations",
            ip_address=request.remote_addr,
            details={"donation_id": donation_id}
        )
        from app.extensions import db
        db.session.commit()

        return success_response(data=donation.to_dict())

    @staticmethod
    def get_stats():
        """
        GET /api/admin/stats
        Aggregate donation statistics for dashboard widgets.
        """
        try:
            stats = DonationService.get_stats()
            return success_response(data=stats)
        except Exception as e:
            logger.error("Stats fetch failed", extra={"extra": {"error": str(e)}})
            return error_response("Failed to retrieve statistics.", "SERVER_ERROR", 500)

    @staticmethod
    def export_report():
        """
        GET /api/admin/export
        Download donation data as CSV.
        Optional query param: status=completed|failed|pending|cancelled
        """
        status = request.args.get("status")

        AuditLog.log(
            action="REPORT_EXPORTED",
            user_id=get_current_user_id(),
            resource="donations",
            ip_address=request.remote_addr,
            details={"status_filter": status}
        )
        from app.extensions import db
        db.session.commit()

        return ReportService.export_donations_csv(status=status)

    @staticmethod
    def get_audit_logs():
        """
        GET /api/admin/audit-logs
        Paginated audit log viewer. Super admin only.
        """
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 20, type=int), 100)

        pagination = AuditLog.query.order_by(
            AuditLog.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return success_response(data={
            "logs": [log.to_dict() for log in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
            }
        })
