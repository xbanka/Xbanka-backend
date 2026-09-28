"""seed roles, permissions and default role_permissions grants

Revision ID: 51b03fe4c709
Revises: e7c5b93f1a24
Create Date: 2026-09-27 00:00:00.000000

Roles and permissions have never had a seed in version control (see repo
history / PERMISSIONS.md) - every environment except prod has had to be
seeded by hand, and a from-scratch database (a rebuilt staging, CI, a new
prod) starts with none of this and can't even bootstrap a Super Admin.

Data below is prod's actual current state (dumped 2026-09-27), not the
`Permission` enum in app/core/enums.py or the JOB_ROLE_PERMISSIONS mapping -
both have drifted from what prod's `role_permissions` table actually grants,
so they're not a reliable source for a seed. Two exceptions, added here even
though prod doesn't have them yet, because they're enum-defined permissions
that were never created anywhere:
    - customers:flag
    - customers:manage_kyc
Neither gets a default role grant (matching how rates:approve_changes has
none) - assign them per-role or per-staff-member as needed.

Ids are preserved from prod so every environment converges on the same rows;
ON CONFLICT DO NOTHING makes this a no-op wherever the row already exists
(prod itself included) and additive wherever it's missing.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "51b03fe4c709"
down_revision: Union[str, Sequence[str], None] = "e7c5b93f1a24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (name, id, category)
PERMISSIONS = [
    ("affiliate:view_payouts", "72c8d40e-b4af-441e-8e1f-948bc1084d21", "Affiliate Payments"),
    ("affiliate:approve_payouts", "8f717114-c568-4154-86b3-5c36289eec1b", "Affiliate Payments"),
    ("affiliate:hold_payouts", "839da915-9338-4f25-a721-06f0bbcf2e06", "Affiliate Payments"),
    ("audit:view_logs", "c131c8f8-9e2e-484e-8b99-e50c40fb83f8", "Audit"),
    ("audit:export_logs", "6f773b76-99b0-4aae-a573-b167d1adf756", "Audit"),
    ("audit:bypass_logging", "98b3a5a0-9128-4c74-92d9-362fd0dc6cb1", "Audit"),
    ("customers:view", "49d40569-3192-4893-97f2-e4a3d3b1ae56", "Customers"),
    ("customers:manage", "038e3f98-fa0c-4777-96dc-94e8b210e0af", "Customers"),
    ("customers:update", "253f8cd6-a3e5-4192-83a6-71a8499416aa", "Customers"),
    ("customers:edit", "96eef42a-1803-47e5-ab85-c35f1f5d8e6e", "Customers"),
    ("customers:add", "0a11bb9f-709b-4753-8e0b-84641e13cdb3", "Customers"),
    ("customers:export", "0da9f7b0-f8fd-4670-b7fb-e6717a24a28a", "Customers"),
    ("dashboard:view", "d98f5016-0af2-4ca5-90d0-0d70f061749f", "Dashboard & Reports"),
    ("reports:view", "05ccd24f-9b82-4c96-ba37-bbc07650bc24", "Dashboard & Reports"),
    ("reports:export_operational", "cf4ed7e4-28e7-4862-8ee3-2de788eea82c", "Dashboard & Reports"),
    ("reports:export_readonly", "44f09615-e2a3-4ba9-a7a5-c8d78f7ffd27", "Dashboard & Reports"),
    ("finance:view_payments", "66057cbe-caa2-4b80-80d5-58b654164b15", "Finance"),
    ("finance:approve_payments", "d0494073-19a0-4535-a205-9aa6c696c5e2", "Finance"),
    ("finance:reject_payments", "cd8b23d7-0631-419a-bd44-009274ea91e5", "Finance"),
    ("finance:flag_payments", "72dab4fa-6cd5-4c9a-8755-c338804213d4", "Finance"),
    ("finance:hold_payments", "4d3da7da-a3e3-4830-bfe9-8422830d112a", "Finance"),
    ("finance:release_payments", "cbc65f49-ab7c-4ca8-91be-9a6b620b9d2c", "Finance"),
    ("finance:adjust_balance", "4aca7654-aeee-4805-af24-90606dd27915", "Finance"),
    ("finance:bypass_approvals", "ed3d13f3-f28b-41ab-9006-d61686ebc38c", "Finance"),
    ("finance:view_profit", "7754e2be-d80a-4ba6-b3b1-aab902ddce4e", "Finance"),
    ("finance:reverse_settlements", "7a0d3297-1b65-4e04-b8ea-a67fa10b5a46", "Finance"),
    ("finance:retry_payments", "9f0a7561-d2bc-48e9-b8d3-db1a2e6b7db1", "Finance"),
    ("finance:export_reports", "c9c8d726-467f-4d50-971c-4ea1577673b4", "Finance"),
    ("tasks:edit", "453e5f29-c96e-4a0c-b958-995beddb4e34", "Finance"),
    ("transactions:recommend_reversal", "81500d6d-cc4f-443f-a914-1ad0fb9f127c", "Finance"),
    ("finance:view_summaries", "f6a22bbd-a87f-4d7b-ae73-c105177fb0a8", "Finance"),
    ("kyc:approve", "ccc74ca3-9e37-4184-bd6e-0b92b5976192", "KYC"),
    ("kyc:reject", "0e55f2f0-5c2d-4d5b-82a0-6b8df6590f0e", "KYC"),
    ("kyc:flag", "d017c818-a899-4603-baa2-b10b5bf2271c", "KYC"),
    ("kyc:upload_documents", "c5de1fc5-f2e3-42c3-be43-e89f49530a36", "KYC"),
    ("kyc:view_data", "92680fa0-3b0f-4b94-b47c-758b41898542", "KYC"),
    ("kyc:view_status", "675ea860-7210-41f9-9180-cdc2c47cc975", "KYC"),
    ("kyc:update_status", "2aa5eaad-1b7c-4d87-8a23-65852fe0862d", "KYC"),
    ("kyc:touch", "d71f429a-d0f2-4e2e-8101-0d5b0d8d5673", "KYC"),
    ("kyc:flag_review", "67d6be10-dd74-4792-b0b7-9534cf955f8f", "KYC"),
    ("rates:propose_changes", "2c762724-e00e-478f-adf1-76b7a8e8b8ec", "Rates"),
    ("rates:approve_changes", "e0fa07cd-2fd5-429d-9b32-d849e056560f", "Rates"),
    ("rates:change_override", "35636b28-147c-4edc-807f-4a58c5b44cd1", "Rates"),
    ("rates:view", "4d188f99-b68e-4eb7-8a3c-2da380cf0425", "Rates"),
    ("reconciliation:view", "b9241e35-6eb9-4585-a6ec-6463070df6f0", "Reconciliation"),
    ("records:delete", "1fd55a09-e725-4340-923d-926b3d5a123a", "Records"),
    ("transactions:view_assigned", "5daa0aea-d843-43e7-a33d-16c8b9f2628d", "Scoped Views"),
    ("transactions:view_limited", "803fa4c8-dd49-45da-8a1a-3850931cc7b0", "Scoped Views"),
    ("customers:view_assigned", "508a69bc-428c-499a-a813-2cdf9de2992f", "Scoped Views"),
    ("staff:view_list", "f9dfeb61-87ac-4e5b-b9dc-1c25967ee151", "Staff & Access Mgt"),
    ("staff:add", "7e9b4277-e724-42d1-b1cb-b9c2757f8e29", "Staff & Access Mgt"),
    ("staff:edit_roles", "94bd0174-c76a-4e1c-a590-d78ac0fe8b88", "Staff & Access Mgt"),
    ("staff:edit_permissions", "603cf919-d225-4198-9983-43afd4a85ddc", "Staff & Access Mgt"),
    ("staff:suspend_activate", "5e39ae48-f8e0-4cce-b09f-96f5f23ef54b", "Staff & Access Mgt"),
    ("staff:reset_password", "0b686831-ce0a-4a83-86df-c7fc67cf3642", "Staff & Access Mgt"),
    ("staff:resend_invites", "93ecc6d4-168f-4496-8f31-adf841d6b56e", "Staff & Access Mgt"),
    ("system:view_settings", "018ca5aa-6fe7-4193-86fd-0edf03c5ddc0", "System & Settings"),
    ("system:edit_settings", "32df90b9-2e6e-433a-8e98-b69336a55a1b", "System & Settings"),
    ("tasks:view", "5f56fd58-93b8-403d-a583-9d354472d7e4", "Tasks"),
    ("tasks:create", "23cb430a-6124-489c-95e4-3e59b0fc8d2b", "Tasks"),
    ("tasks:assign", "7f1a28c1-76bd-4874-8091-90978fa4a5db", "Tasks"),
    ("tasks:update_status", "e6296d69-0ecc-45dd-b38f-f38ae5e0324b", "Tasks"),
    ("tasks:view_progress", "d8d6b7e8-c785-4b25-ace5-f5f886c25fed", "Tasks"),
    ("tasks:view_analytics", "747f5d0c-1615-4981-b483-c261d579d8b6", "Tasks"),
    ("tasks:comment", "5a5b6034-7556-4cac-9f99-c6b2e4ba0ef4", "Tasks"),
    ("tasks:attach_documents", "e25af88b-a51b-4584-811d-967eb61b1fd3", "Tasks"),
    ("tasks:create_compliance", "fbae1c8f-173f-411e-9aec-b65487a5adaa", "Tasks"),
    ("tasks:delete", "42ce5889-93cd-4456-8e6d-5dc7b25736bf", "Tasks"),
    ("tasks:view_assigned", "0cf7f380-83c8-4dd9-ae8f-3185e46b4b27", "Tasks"),
    ("tasks:view_board", "6e70ed17-4541-4ae5-90d5-6aec445d4380", "Tasks"),
    ("transactions:view", "c3b41f84-4edd-49cd-bbc8-df03b8398777", "Transactions"),
    ("transactions:create", "aae300ce-f18f-4743-85d8-e95c26be2833", "Transactions"),
    ("transactions:verify", "2156db70-70e3-4aa7-8528-ed64f32a363c", "Transactions"),
    ("transactions:settle", "bda09c46-c841-4ba2-aaa1-64913e094b5c", "Transactions"),
    ("transactions:refund", "fb0aaea4-bdb7-4c84-a1ab-f029259058c6", "Transactions"),
    ("transactions:flag", "cc57e299-bc97-4aa5-a81f-4de7b10d3fcf", "Transactions"),
    ("transactions:freeze", "7090952b-b7a5-4090-907b-993ca5a286ae", "Transactions"),
    ("transactions:update_status", "2934027d-5083-4677-ace1-2f138ee27648", "Transactions"),
    ("transactions:execute", "0d043738-2981-4362-9239-1e758a986ac2", "Transactions"),
    ("transactions:edit", "61b3d0cc-8c84-4f0e-bed0-27ccabc4d1de", "Transactions"),
    ("transactions:merge", "eb25925a-1901-4806-8a9a-4eaf212c312a", "Transactions"),
    ("transactions:mark_complete", "86d91418-a2eb-4ed2-8d25-b0bf3d005a10", "Transactions"),
    ("transactions:export", "09bc43d8-360e-446a-95e4-862dc8c589d6", "Transactions"),
]

# Enum-defined permissions with no row anywhere in version control until now.
NEW_PERMISSIONS = [
    ("customers:flag", "797821d6-5c0d-4558-beb6-a44db5268935", "Customers"),
    ("customers:manage_kyc", "41954142-40c1-4571-9595-d89eee89dd55", "Customers"),
]

# (name, id)
ROLES = [
    ("Super Admin", "3627f802-ca79-449a-9111-d2a7f041c519"),
    ("Admin", "9b962836-864b-4f9c-8ddc-8110ccd61ebf"),
    ("Manager", "5d41683e-3b26-402b-94fa-9e68596cb330"),
    ("Customer Rep", "b7b41b03-2fbe-4fb9-899c-380c112f5a50"),
    ("Compliance", "5b7ea7b0-afc2-4570-80ef-c1bcb62a34a6"),
    ("Viewer", "1424364b-c7d2-433b-a965-ad0059edc46b"),
    ("Operations", "efa7e037-79ae-45d7-9f56-06ef041c724f"),
    ("Finance", "2127681d-97f3-451d-8e8d-ad5e32ce4651"),
    ("Staff", "a0e94e68-04bf-43fb-b247-76fa6c57a6fc"),
]

# (role_name, permission_name) - the default grants each role currently has in prod.
ROLE_GRANTS = [
    ("Super Admin", "affiliate:approve_payouts"),
    ("Super Admin", "affiliate:hold_payouts"),
    ("Super Admin", "affiliate:view_payouts"),
    ("Super Admin", "audit:bypass_logging"),
    ("Super Admin", "audit:export_logs"),
    ("Super Admin", "audit:view_logs"),
    ("Super Admin", "customers:manage"),
    ("Super Admin", "customers:view"),
    ("Super Admin", "customers:view_assigned"),
    ("Super Admin", "dashboard:view"),
    ("Super Admin", "finance:adjust_balance"),
    ("Super Admin", "finance:approve_payments"),
    ("Super Admin", "finance:bypass_approvals"),
    ("Super Admin", "finance:flag_payments"),
    ("Super Admin", "finance:hold_payments"),
    ("Super Admin", "finance:reject_payments"),
    ("Super Admin", "finance:release_payments"),
    ("Super Admin", "finance:view_payments"),
    ("Super Admin", "finance:view_profit"),
    ("Super Admin", "kyc:approve"),
    ("Super Admin", "kyc:flag"),
    ("Super Admin", "kyc:reject"),
    ("Super Admin", "kyc:update_status"),
    ("Super Admin", "kyc:upload_documents"),
    ("Super Admin", "kyc:view_data"),
    ("Super Admin", "kyc:view_status"),
    ("Super Admin", "reconciliation:view"),
    ("Super Admin", "reports:view"),
    ("Super Admin", "staff:add"),
    ("Super Admin", "staff:edit_permissions"),
    ("Super Admin", "staff:edit_roles"),
    ("Super Admin", "staff:resend_invites"),
    ("Super Admin", "staff:reset_password"),
    ("Super Admin", "staff:suspend_activate"),
    ("Super Admin", "staff:view_list"),
    ("Super Admin", "system:edit_settings"),
    ("Super Admin", "system:view_settings"),
    ("Super Admin", "tasks:assign"),
    ("Super Admin", "tasks:attach_documents"),
    ("Super Admin", "tasks:comment"),
    ("Super Admin", "tasks:create"),
    ("Super Admin", "tasks:create_compliance"),
    ("Super Admin", "tasks:update_status"),
    ("Super Admin", "tasks:view"),
    ("Super Admin", "tasks:view_analytics"),
    ("Super Admin", "tasks:view_progress"),
    ("Super Admin", "transactions:create"),
    ("Super Admin", "transactions:edit"),
    ("Super Admin", "transactions:execute"),
    ("Super Admin", "transactions:flag"),
    ("Super Admin", "transactions:freeze"),
    ("Super Admin", "transactions:mark_complete"),
    ("Super Admin", "transactions:refund"),
    ("Super Admin", "transactions:settle"),
    ("Super Admin", "transactions:update_status"),
    ("Super Admin", "transactions:verify"),
    ("Super Admin", "transactions:view"),
    ("Super Admin", "transactions:view_assigned"),
    ("Super Admin", "transactions:view_limited"),
    ("Admin", "customers:export"),
    ("Admin", "customers:manage"),
    ("Admin", "customers:view"),
    ("Admin", "dashboard:view"),
    ("Admin", "kyc:update_status"),
    ("Admin", "kyc:view_data"),
    ("Admin", "rates:view"),
    ("Admin", "staff:add"),
    ("Admin", "staff:edit_permissions"),
    ("Admin", "staff:edit_roles"),
    ("Admin", "staff:suspend_activate"),
    ("Admin", "staff:view_list"),
    ("Admin", "system:view_settings"),
    ("Admin", "tasks:assign"),
    ("Admin", "tasks:create"),
    ("Admin", "tasks:update_status"),
    ("Admin", "tasks:view"),
    ("Admin", "tasks:view_progress"),
    ("Admin", "transactions:export"),
    ("Admin", "transactions:verify"),
    ("Admin", "transactions:view"),
    ("Manager", "customers:view"),
    ("Manager", "dashboard:view"),
    ("Manager", "kyc:view_status"),
    ("Manager", "rates:view"),
    ("Manager", "tasks:assign"),
    ("Manager", "tasks:update_status"),
    ("Manager", "tasks:view"),
    ("Manager", "tasks:view_analytics"),
    ("Manager", "transactions:view"),
    ("Customer Rep", "customers:add"),
    ("Customer Rep", "customers:manage"),
    ("Customer Rep", "customers:view"),
    ("Customer Rep", "dashboard:view"),
    ("Customer Rep", "kyc:upload_documents"),
    ("Customer Rep", "kyc:view_status"),
    ("Customer Rep", "tasks:comment"),
    ("Customer Rep", "tasks:update_status"),
    ("Customer Rep", "tasks:view"),
    ("Customer Rep", "transactions:create"),
    ("Customer Rep", "transactions:view_assigned"),
    ("Compliance", "audit:view_logs"),
    ("Compliance", "dashboard:view"),
    ("Compliance", "kyc:approve"),
    ("Compliance", "kyc:flag"),
    ("Compliance", "kyc:reject"),
    ("Compliance", "kyc:view_data"),
    ("Compliance", "tasks:comment"),
    ("Compliance", "tasks:create_compliance"),
    ("Compliance", "tasks:view"),
    ("Compliance", "transactions:flag"),
    ("Compliance", "transactions:freeze"),
    ("Compliance", "transactions:view"),
    ("Viewer", "dashboard:view"),
    ("Viewer", "reports:view"),
    ("Viewer", "tasks:view"),
    ("Operations", "customers:add"),
    ("Operations", "customers:view"),
    ("Operations", "dashboard:view"),
    ("Operations", "kyc:flag"),
    ("Operations", "kyc:upload_documents"),
    ("Operations", "kyc:view_data"),
    ("Operations", "rates:propose_changes"),
    ("Operations", "rates:view"),
    ("Operations", "tasks:attach_documents"),
    ("Operations", "tasks:comment"),
    ("Operations", "tasks:update_status"),
    ("Operations", "tasks:view"),
    ("Operations", "transactions:create"),
    ("Operations", "transactions:execute"),
    ("Operations", "transactions:mark_complete"),
    ("Operations", "transactions:update_status"),
    ("Finance", "affiliate:approve_payouts"),
    ("Finance", "affiliate:hold_payouts"),
    ("Finance", "affiliate:view_payouts"),
    ("Finance", "dashboard:view"),
    ("Finance", "finance:approve_payments"),
    ("Finance", "finance:flag_payments"),
    ("Finance", "finance:hold_payments"),
    ("Finance", "finance:reject_payments"),
    ("Finance", "finance:release_payments"),
    ("Finance", "finance:view_payments"),
    ("Finance", "rates:view"),
    ("Finance", "tasks:comment"),
    ("Finance", "tasks:view"),
    ("Finance", "transactions:view"),
    ("Staff", "dashboard:view"),
    ("Staff", "tasks:update_status"),
    ("Staff", "tasks:view"),
    ("Staff", "transactions:view"),
]


def upgrade() -> None:
    conn = op.get_bind()

    for name, pid, category in PERMISSIONS + NEW_PERMISSIONS:
        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, name, category, created_at, updated_at)
                VALUES (:id, :name, :category, now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"id": pid, "name": name, "category": category},
        )

    for name, rid in ROLES:
        conn.execute(
            sa.text(
                """
                INSERT INTO roles (id, name, created_at, updated_at)
                VALUES (:id, :name, now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"id": rid, "name": name},
        )

    for role_name, permission_name in ROLE_GRANTS:
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.name = :role_name AND p.name = :permission_name
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {"role_name": role_name, "permission_name": permission_name},
        )


def downgrade() -> None:
    """Removes exactly what upgrade() added, by name.

    Destructive on any database where this data is in real use: deleting a
    permission cascades to any role_permissions/user_permissions rows still
    pointing at it (including per-staff overrides added after upgrade() ran),
    and deleting a role that any erp_users row still references fails outright
    on the roles.id foreign key (no ondelete rule there) rather than silently
    orphaning staff - drop those staff or reassign their role first.
    """
    conn = op.get_bind()

    for role_name, permission_name in ROLE_GRANTS:
        conn.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                USING roles r, permissions p
                WHERE role_permissions.role_id = r.id
                  AND role_permissions.permission_id = p.id
                  AND r.name = :role_name
                  AND p.name = :permission_name
                """
            ),
            {"role_name": role_name, "permission_name": permission_name},
        )

    for name, _rid in ROLES:
        conn.execute(
            sa.text("DELETE FROM roles WHERE name = :name"),
            {"name": name},
        )

    for name, _pid, _category in PERMISSIONS + NEW_PERMISSIONS:
        conn.execute(
            sa.text("DELETE FROM permissions WHERE name = :name"),
            {"name": name},
        )
