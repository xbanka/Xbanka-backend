import logging
from datetime import datetime
from typing import List, Optional, Sequence
from uuid import UUID
from fastapi import HTTPException, status
from psycopg2 import IntegrityError
from sqlalchemy import func, select, and_
from sqlalchemy.dialects.postgresql import UUID as SA_UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.base.services import Service
from app.core.enums import PayoutMethodEnum, PayoutStatusEnum
from app.core.hash import Hasher
from app.models.affiliate import Affiliate
from app.models.erp_user import ERPUser
from app.models.notifications import Notification

from app.models.payouts import Payout
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permissions import RolePermissions
from app.models.user_permissions import UserPermissions
from app.schemas.erp.user import RegisterBase
from app.utils.permissions import calculate_permission_overrides
from app.utils.validators import is_valid_email, is_valid_password
from app.utils.settings import settings


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
    def get_notifications(db: Session):
        stmt = select(Notification).order_by(Notification.created_at.desc()).join(Affiliate)
        notifications = db.execute(stmt).scalars().all()
        return notifications

    @staticmethod
    def mark_notification_as_read(db: Session, id: UUID):
        notif = db.get(Notification, id)
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
    def new_notification(
        db: Session,
        user: ERPUser,
        message: str,
        amount: float | str,
        method: PayoutMethodEnum,
        affiliate_id: SA_UUID,
    ) -> Notification:
        
        notification = Notification(
            message=message, 
            type="system", 
            is_read=False, 
            amount=amount, 
            method=method,
            affiliate_id=affiliate_id
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

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
    def get_payout_details(db: Session, payout_id: UUID) -> Payout:
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payout not found"
            )
        return payout
    
    @staticmethod
    def process_payout(db: Session, payout_id: UUID) -> Payout:
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout not found"
            )
        
        payout.status = PayoutStatusEnum.paid
        payout.paid_at = datetime.now()

        db.commit()
        db.refresh(payout)

        return payout

    
    @staticmethod
    def reject_payout(db: Session, payout_id: UUID) -> Payout:
        payout = db.get(Payout, payout_id)
        if not payout:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payout not found"
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
                detail="Super Admin creation is disabled."
            )

        if obj_in.email not in ["superadmin1@xbankang.com", "superadmin2@xbankang.com", "superadmin3@xbankang.com", "superadmin4@xbankang.com"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to create a Super Admin account."
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
                status_code=status.HTTP_400_BAD_REQUEST, detail="Super Admin with this email already exists"
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
                role=role_obj
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
        stmt = select(ERPUser).join(Role).where(
            and_(
                Role.name != "Super Admin",
                ERPUser.hashed_password.isnot(None)
            )
        ).order_by(ERPUser.created_at.desc())
        staff_users = db.execute(stmt).scalars().all()
        return staff_users
    

    @staticmethod
    def invite_staff(db: Session, email: str, role_name: str, selected_permissions: list[str]) -> ERPUser:
        if not is_valid_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )
        
        stmt = select(ERPUser).where(ERPUser.email == email)
        staff_user = db.execute(stmt).scalars().first()

        if staff_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Staff user with this email already exists"
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
                    detail=f"Permission '{perm}' is forbidden for role '{role_name}' and cannot be assigned."
                )
        
        role_permissions = allowed_permissions 

        # Calculate what needs to be added/removed
        added, removed = calculate_permission_overrides(
            role_permissions,
            selected_permissions
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
                    db.add(UserPermissions(
                        user_id=staff_user.id,
                        permission_id=perm.id,
                        is_active=True
                    ))
            
                # Remove permissions
            for perm_name in removed:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(UserPermissions(
                        user_id=staff_user.id,
                        permission_id=perm.id,
                        is_active=False
                    ))

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
    def get_role_permissions(db: Session, role_name: str) -> tuple[List[str], List[str]]:
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
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        return (
            [name for allowed, name in rows if allowed],
            [name for allowed, name in rows if not allowed]
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
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
                )
            
            existing_user = db.query(ERPUser).filter_by(email=update_request.email).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Another user with this email already exists"
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
    def update_staff_roles_permissions(db: Session, staff_id: UUID, role_name: str, selected_permissions: List[str]) -> ERPUser:
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
        db.query(UserPermissions).filter(UserPermissions.user_id == staff_user.id).delete(synchronize_session=False)
        
        # Get allowed and forbidden permissions for the role
        role_permissions_data = ERPService.get_role_permissions(db, role_name)
        allowed_permissions, forbidden_permissions = role_permissions_data
        
        # Check if any selected permissions are forbidden for the role
        for perm in selected_permissions:
            if perm in forbidden_permissions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Permission '{perm}' is forbidden for role '{role_name}' and cannot be assigned."
                )
        
        role_permissions = allowed_permissions 

        # Calculate what needs to be added/removed
        added, removed = calculate_permission_overrides(
            role_permissions,
            selected_permissions
        )

        try:
            staff_user.role = role

            # Add custom permissions
            for perm_name in added:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(UserPermissions(
                        user_id=staff_user.id,
                        permission_id=perm.id,
                        is_active=True
                    ))
            
                # Remove permissions
            for perm_name in removed:
                perm = db.query(Permission).filter(Permission.name == perm_name).first()
                if perm:
                    db.add(UserPermissions(
                        user_id=staff_user.id,
                        permission_id=perm.id,
                        is_active=False
                    ))

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