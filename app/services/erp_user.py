from decimal import Decimal
import logging
from datetime import datetime
from typing import List, Optional, Sequence
from uuid import UUID

from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile, status
from psycopg2 import IntegrityError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import UUID as SA_UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.base.services import Service
from app.core.enums import (
    NotificationReferenceTypeEnum,
    PayoutMethodEnum,
    PayoutStatusEnum,
    UploadStatusEnum,
)
from app.core.hash import Hasher
from app.models.affiliate import Affiliate
from app.models.erp_user import ERPUser
from app.models.notifications import Notification
from app.models.payouts import Payout
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.models.user_permissions import UserPermissions
from app.schemas.payout import ProcessPayoutRequest
from app.services.affiliate import AffiliateService
from app.schemas.erp.payout import ERPPayoutDetailResponse
from app.schemas.erp.user import RegisterBase
from app.utils.permissions import calculate_permission_overrides
from app.utils.s3_utils import upload_file, validate_file
from app.utils.settings import settings
from app.utils.validators import is_valid_email, is_valid_password

S3_BUCKET_PAYOUTS = settings.S3_BUCKET_PAYOUTS

logger = logging.getLogger(__name__)


ALLOW_SUPER_ADMIN_BOOTSTRAP = settings.ALLOW_SUPER_ADMIN_BOOTSTRAP


class ERPService(Service):
    @staticmethod
    def create(db: Session, obj_in: RegisterBase) -> ERPUser:
        if not is_valid_email(obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )

        stmt = select(ERPUser).where(ERPUser.email == obj_in.email)
        erp_user = db.execute(stmt).scalars().first()

        if not erp_user:
            raise HTTPException(
                status_code=403, detail="ERP user has not been initialized."
            )

        if not is_valid_password(obj_in.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",
            )

        try:
            erp_user.first_name = obj_in.first_name
            erp_user.last_name = obj_in.last_name
            erp_user.hashed_password = Hasher.get_password_hash(obj_in.password)
            db.commit()

        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred saving entity: {e}"
            )
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return erp_user

    @staticmethod
    def get_user_by_id(db: Session, id: UUID) -> ERPUser:
        erp_user = db.query(ERPUser).get(id)
        if not erp_user:
            raise HTTPException(status_code=404, detail="ERP user not found")

        return erp_user

    @staticmethod
    def get_user_by_mail(db: Session, email: str) -> ERPUser:
        erp_user = db.query(ERPUser).filter_by(email=email).first()
        if not erp_user:
            raise HTTPException(status_code=404, detail="ERP user not found")

        return erp_user

    @staticmethod
    def get_current_user(db: Session):
        pass

    @staticmethod
    def get_notifications(db: Session, user_id: UUID):
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .options(joinedload(Notification.affiliate))
            .order_by(Notification.created_at.desc())
        )
        notifications = db.execute(stmt).scalars().all()
        return notifications

    @staticmethod
    def mark_notification_as_read(db: Session, id: UUID, user_id: UUID):
        # scoping on user_id doubles as authorization: a notification belonging
        # to another user is indistinguishable from one that doesn't exist
        notif = db.scalar(
            select(Notification).where(
                Notification.id == id,
                Notification.user_id == user_id,
            )
        )
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
            )

        notif.is_read = True
        notif.read_at = datetime.now()
        db.commit()
        db.refresh(notif)
        return notif

    @staticmethod
    def get_users_with_permission(db: Session, permission_name: str) -> List[ERPUser]:
        """ERP users holding `permission_name`, honouring per-user overrides.

        Mirrors the resolution in get_staff_permissions: a role's defaults apply
        unless the user has an explicit user_permissions row, which wins either way.
        """
        perm = db.scalar(select(Permission).where(Permission.name == permission_name))
        if not perm:
            logger.warning("Unknown permission %s, notifying nobody", permission_name)
            return []

        granting_roles = select(RolePermissions.role_id).where(
            RolePermissions.permission_id == perm.id,
            RolePermissions.is_allowed.is_(True),
        )

        # at most one row per (user, permission) thanks to the composite PK
        override = (
            select(UserPermissions.is_active)
            .where(
                UserPermissions.user_id == ERPUser.id,
                UserPermissions.permission_id == perm.id,
            )
            .scalar_subquery()
        )

        stmt = (
            select(ERPUser)
            .join(Role, Role.id == ERPUser.role_id)
            .where(
                or_(
                    override.is_(True),
                    and_(
                        override.is_(None),
                        or_(
                            Role.name == "Super Admin",
                            ERPUser.role_id.in_(granting_roles),
                        ),
                    ),
                )
            )
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def notify_permission_holders(
        db: Session,
        permission_name: str,
        *,
        exclude_user_id: UUID | None = None,
        **kwargs,
    ) -> List[Notification]:
        """Fan a notification out to everyone holding `permission_name`."""
        users = ERPService.get_users_with_permission(db, permission_name)
        return ERPService.new_notification(
            db,
            recipients=[u for u in users if u.id != exclude_user_id],
            **kwargs,
        )

    @staticmethod
    def new_notification(
        db: Session,
        *,
        recipients: Sequence[ERPUser | UUID],
        message: str,
        reference_type: NotificationReferenceTypeEnum,
        amount: Decimal | str | None = None,
        method: PayoutMethodEnum | None = None,
        affiliate_id: SA_UUID | None = None,
        reference_id: SA_UUID | None = None
    ) -> List[Notification]:
        """Create one notification row per recipient, so read state is per-user."""
        user_ids = {r.id if isinstance(r, ERPUser) else r for r in recipients}
        if not user_ids:
            logger.warning("No recipients for notification %r, skipping", message)
            return []

        notifications = [
            Notification(
                user_id=user_id,
                message=message,
                type="system",
                is_read=False,
                amount=amount,
                method=method,
                reference_type=reference_type,
                affiliate_id=affiliate_id,
                reference_id=reference_id,
            )
            for user_id in user_ids
        ]
        db.add_all(notifications)
        db.commit()
        return notifications

    @staticmethod
    def get_all_payouts(
        db: Session, page: int, limit: int, status: Optional[PayoutStatusEnum] = None
    ):
        stmt = select(Payout).join(Affiliate)

        if status:
            stmt = stmt.where(Payout.status == status)

        stmt = (
            stmt.order_by(Payout.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = db.execute(stmt)
        payouts = result.scalars().all()

        total = (
            db.scalar(select(func.count()).select_from(select(Payout).subquery())) or 0
        )

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "data": payouts,
        }

    @staticmethod
    def get_payout_details(db: Session, payout_id: UUID) -> ERPPayoutDetailResponse:
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found"
            )
        
        affiliate_summary = AffiliateService.build_affiliate_summary(db, payout.affiliate)

        return ERPPayoutDetailResponse(
            id=UUID(str(payout.id)),
            amount=payout.amount,
            status=payout.status,
            payment_ref=payout.payment_ref,
            paid_at=payout.paid_at,
            bank=payout.bank,
            affiliate=affiliate_summary,
            upload_status=payout.upload_status,
            notes=payout.note,
            attachment_url=payout.attachment_url,
        )

    @staticmethod
    def process_payout(db: Session, payout_id: UUID, process_request: ProcessPayoutRequest) -> Payout:
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found"
            )

        payout.status = PayoutStatusEnum.paid
        payout.paid_at = datetime.now()

        payout.note = process_request.note

        db.commit()
        db.refresh(payout)

        return payout

    @staticmethod
    def reject_payout(db: Session, payout_id: UUID) -> Payout:
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found"
            )

        payout.status = PayoutStatusEnum.rejected

        db.commit()
        db.refresh(payout)

        return payout

    @staticmethod
    def create_superadmin(db: Session, obj_in: RegisterBase) -> ERPUser:
        if not ALLOW_SUPER_ADMIN_BOOTSTRAP:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super Admin creation is disabled.",
            )

        if obj_in.email not in [
            "superadmin1@xbankang.com",
            "superadmin2@xbankang.com",
            "superadmin3@xbankang.com",
            "superadmin4@xbankang.com",
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create a Super Admin account.",
            )

        if not is_valid_email(obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )

        if not is_valid_password(obj_in.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",
            )

        stmt = select(ERPUser).where(ERPUser.email == obj_in.email)
        superadmin_user = db.execute(stmt).scalars().first()

        if superadmin_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Super Admin with this email already exists",
            )

        role_obj = db.query(Role).filter_by(name="Super Admin").first()
        if not role_obj:
            raise ValueError("Role 'Super Admin' not found")

        try:
            superadmin_user = ERPUser(
                first_name=obj_in.first_name,
                last_name=obj_in.last_name,
                email=obj_in.email,
                hashed_password=Hasher.get_password_hash(obj_in.password),
                verified=True,
                role=role_obj,
            )

            db.add(superadmin_user)
            db.commit()
            db.refresh(superadmin_user)
        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred saving entity: {e}"
            )
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return superadmin_user

    @staticmethod
    def get_all_staff(db: Session) -> Sequence[ERPUser]:
        stmt = (
            select(ERPUser)
            .join(Role)
            .where(
                and_(Role.name != "Super Admin", ERPUser.hashed_password.isnot(None))
            )
            .order_by(ERPUser.created_at.desc())
        )
        staff_users = db.execute(stmt).scalars().all()
        return staff_users

    @staticmethod
    def _resolve_permission_changes(
        db: Session, role_name: str, selected_permissions: List[str]
    ) -> tuple[List[str], List[str], dict]:
        """Validate selected_permissions against a role's allowed/forbidden sets and
        return (added, removed, permissions_by_name) to apply as UserPermissions overrides."""
        allowed_permissions, forbidden_permissions = ERPService.get_role_permissions(
            db, role_name
        )

        for perm in selected_permissions:
            if perm in forbidden_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission '{perm}' is forbidden for role '{role_name}' and cannot be assigned.",
                )

        permissions_by_name = {
            perm.name: perm
            for perm in db.query(Permission)
            .filter(
                Permission.name.in_(set(selected_permissions) | set(allowed_permissions))
            )
            .all()
        }
        unknown_permissions = set(selected_permissions) - permissions_by_name.keys()
        if unknown_permissions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown permission(s): {', '.join(sorted(unknown_permissions))}",
            )

        added, removed = calculate_permission_overrides(
            allowed_permissions, selected_permissions
        )
        return added, removed, permissions_by_name

    @staticmethod
    def invite_staff(
        db: Session, email: str, role_name: str, selected_permissions: list[str]
    ) -> ERPUser:
        if not is_valid_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )

        stmt = select(ERPUser).where(ERPUser.email == email)
        staff_user = db.execute(stmt).scalars().first()

        if staff_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Staff user with this email already exists",
            )

        # Get role's default permissions
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        # Get allowed and forbidden permissions for the role
        role_permissions_data = ERPService.get_role_permissions(db, role_name)
        allowed_permissions, forbidden_permissions = role_permissions_data

        # Check if any selected permissions are forbidden for the role
        for perm in selected_permissions:
            if perm in forbidden_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission '{perm}' is forbidden for role '{role_name}' and cannot be assigned.",
                )

        role_permissions = allowed_permissions

        # Calculate what needs to be added/removed
        added, removed = calculate_permission_overrides(
            role_permissions, selected_permissions
        )

        try:
            staff_user = ERPUser(
                first_name="",
                last_name="",
                email=email,
                role_id=role.id,
                verified=True,
            )

            db.add(staff_user)
            db.commit()
            db.refresh(staff_user)

            # Add custom permissions
            for perm_name in added:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(
                        UserPermissions(
                            user_id=staff_user.id, permission_id=perm.id, is_active=True
                        )
                    )

                # Remove permissions
            for perm_name in removed:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(
                        UserPermissions(
                            user_id=staff_user.id,
                            permission_id=perm.id,
                            is_active=False,
                        )
                    )

            db.commit()

        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred saving entity: {e}"
            )
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return staff_user

    @staticmethod
    def get_role_permissions(
        db: Session, role_name: str
    ) -> tuple[List[str], List[str]]:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        if role_name == "Super Admin":
            all_permissions = db.query(Permission).all()
            perm_names = [perm.name for perm in all_permissions]
            return (perm_names, [])

        rows = (
            db.query(RolePermissions.is_allowed, Permission.name)
            .join(Role, Role.id == RolePermissions.role_id)
            .join(Permission, Permission.id == RolePermissions.permission_id)
            .filter(Role.name == role_name)
            .all()
        )

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        return (
            [name for allowed, name in rows if allowed],
            [name for allowed, name in rows if not allowed],
        )

    @staticmethod
    def get_staff_permissions(db: Session, staff_id: UUID) -> List[str]:
        staff_user = db.query(ERPUser).get(staff_id)
        if not staff_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found"
            )

        # permissions = staff_user.role.permissions

        permissions = {p.name for p in staff_user.role.permissions}

        for user_perms in staff_user.permissions:
            if user_perms.is_active:
                permissions.add(user_perms.permission.name)
            else:
                permissions.discard(user_perms.permission.name)

        return list(permissions)

    @staticmethod
    def remove_staff_member(db: Session, staff_id: UUID):
        staff_user = db.get(ERPUser, staff_id)
        if not staff_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found"
            )

        try:
            db.delete(staff_user)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Failed to delete staff member %s", staff_id)
            raise HTTPException(
                status_code=500, detail="An error occurred deleting staff member"
            )

    @staticmethod
    def update_staff_details(db: Session, staff_id: UUID, update_request) -> ERPUser:
        staff_user = db.query(ERPUser).get(staff_id)
        if not staff_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found"
            )

        if staff_user.email != update_request.email:
            if not is_valid_email(update_request.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email address.",
                )

            existing_user = (
                db.query(ERPUser).filter_by(email=update_request.email).first()
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another user with this email already exists",
                )

        staff_user.first_name = update_request.first_name
        staff_user.last_name = update_request.last_name
        staff_user.email = update_request.email

        try:
            db.commit()
            db.refresh(staff_user)
        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred saving entity: {e}"
            )
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return staff_user

    @staticmethod
    def update_staff_roles_permissions(
        db: Session, staff_id: UUID, role_name: str, selected_permissions: List[str]
    ) -> ERPUser:
        staff_user = db.query(ERPUser).get(staff_id)
        if not staff_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found"
            )

        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
            )

        # clear all user_permission records
        db.query(UserPermissions).filter(
            UserPermissions.user_id == staff_user.id
        ).delete(synchronize_session=False)

        # Get allowed and forbidden permissions for the role
        role_permissions_data = ERPService.get_role_permissions(db, role_name)
        allowed_permissions, forbidden_permissions = role_permissions_data

        # Check if any selected permissions are forbidden for the role
        for perm in selected_permissions:
            if perm in forbidden_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Permission '{perm}' is forbidden for role '{role_name}' and cannot be assigned.",
                )

        role_permissions = allowed_permissions

        # Calculate what needs to be added/removed
        added, removed = calculate_permission_overrides(
            role_permissions, selected_permissions
        )

        try:
            staff_user.role = role

            # Add custom permissions
            for perm_name in added:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(
                        UserPermissions(
                            user_id=staff_user.id, permission_id=perm.id, is_active=True
                        )
                    )

                # Remove permissions
            for perm_name in removed:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(
                        UserPermissions(
                            user_id=staff_user.id,
                            permission_id=perm.id,
                            is_active=False,
                        )
                    )

            db.commit()
            db.refresh(staff_user)

        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred saving entity: {e}"
            )
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return staff_user


    @staticmethod
    def upload_attachment(db: Session, payout_id: UUID, attachment: UploadFile):
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(status_code=404, detail="Payout not found.")

        try:
            attachment_key = validate_file(attachment, payout_id)
            attachment_url = f"payouts/{attachment_key}"

            upload_file(attachment.file, S3_BUCKET_PAYOUTS, attachment_url)

            payout.attachment_url = attachment_url
            payout.upload_status = UploadStatusEnum.completed
            db.commit()
            db.refresh(payout)

            return payout

        except ClientError as e:
            logging.error(e)
            payout.upload_status = UploadStatusEnum.failed
            db.commit()

            raise HTTPException(
                status_code=500, detail="An error occured. Attachment upload failed"
            )