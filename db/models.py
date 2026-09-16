# db/models.py
from sqlalchemy import (
    Column, Integer, Float, BigInteger, String, DateTime, JSON, func, Index
)
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean, ForeignKey,
    JSON, TIMESTAMP, Index, UniqueConstraint, Numeric
)
from sqlalchemy.orm import relationship
from db.async_db import Base

# class AllUsers(Base):
#     __tablename__ = "all_users"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(BigInteger, unique=True, index=True, nullable=False)   # telegram id
#     user_name = Column(String, nullable=True)
#     user_full_name = Column(String, nullable=True)

#     user_id_who_invited = Column(BigInteger, nullable=True, index=True)
#     quantity_guests_paid = Column(Integer, nullable=False)
#     quantity_guests_paid_potent = Column(Integer, nullable=False)

#     free_subs_given = Column(Integer, unique=False, nullable=False)

#     subscription_server_id_1 = Column(Integer, unique=False, nullable=True)
#     subscription_autopay_id_1 = Column(Integer, unique=False, nullable=True)
#     subscription_stop_id_1 = Column(Integer, unique=False, nullable=True)

#     subscription_server_id_2 = Column(Integer, unique=False, nullable=True)
#     subscription_autopay_id_2 = Column(Integer, unique=False, nullable=True)
#     subscription_stop_id_2 = Column(Integer, unique=False, nullable=True)

#     subscription_server_id_3 = Column(Integer, unique=False, nullable=True)
#     subscription_autopay_id_3 = Column(Integer, unique=False, nullable=True)
#     subscription_stop_id_3 = Column(Integer, unique=False, nullable=True)

#     subscription_server_id_4 = Column(Integer, unique=False, nullable=True)
#     subscription_autopay_id_4 = Column(Integer, unique=False, nullable=True)
#     subscription_stop_id_4 = Column(Integer, unique=False, nullable=True)

#     subscription_server_id_5 = Column(Integer, unique=False, nullable=True)
#     subscription_autopay_id_5 = Column(Integer, unique=False, nullable=True)
#     subscription_stop_id_5 = Column(Integer, unique=False, nullable=True)


#     user_promo_new = Column(Integer, default=0, nullable=False)             # 1 = promo granted
#     user_promo_new_days = Column(BigInteger, nullable=True)    
    
#     user_time_rating = Column(Integer, unique=False, nullable=True) # сюда пишем каждую оплату подписки.
#     user_server_rating = Column(Integer, unique=False, nullable=True) # сюда пишем если чувак был на заблоченном сервере клиентом
#     user_blocked = Column(Integer, default=0, nullable=False)
#     user_balance = Column(Float, default=0.0, nullable=False)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())


#     is_partner = Column(Integer, unique=False, nullable=True, default=0)
#     partner_procent = Column(Float, unique=False, nullable=True, default=0)
#     partner_http = Column(String, unique=False, nullable=True)
#     partner_wallet = Column(String, unique=True, nullable=True)

#     last_mnth_total_earned = Column(Float, unique=False, nullable=True, default=0)
#     last_mnth_total_paid = Column(Float, unique=False, nullable=True, default=0)

#     total_earned = Column(Float, unique=False, nullable=True, default=0)
#     total_paid = Column(Float, unique=False, nullable=True, default=0)
#     last_pay = Column(Float, unique=False, nullable=True, default=0)

#     balance_earner = Column(Float, unique=False, nullable=True, default=0)
#     balance_earner_fact = Column(Float, unique=False, nullable=True, default=0)

#     asked_redirect = Column(Integer, unique=False, nullable=True)
#     asked_redirect_yes = Column(Integer, unique=False, nullable=True)
#     asked_time = Column(Integer, unique=False, nullable=True)

#     __table_args__ = (
#         Index("ix_all_users_user_id", "user_id"),
#     )

# class SubscriptionTransaction(Base):
#     __tablename__ = "subscription_transactions"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(BigInteger, index=True, nullable=False)
#     source = Column(String, nullable=False)            # e.g., "promo", "manual"
#     status = Column(String, nullable=False, index=True) # pending, in_progress, completed, failed
#     requested_end_ts = Column(BigInteger, nullable=True)   # desired end timestamp in ms
#     previous_end_ts = Column(BigInteger, nullable=True)
#     external_id = Column(String, nullable=True)        # id from external server
#     payload = Column(JSON, nullable=True)               # provisioning details
#     error = Column(String, nullable=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

#     __table_args__ = (
#         Index("ix_sub_tx_user_status", "user_id", "status"),
#     )

# ------------------------------------

# db/models.py
from datetime import datetime, timezone
# from sqlalchemy import (
#     Column, Integer, BigInteger, String, Text, Boolean, ForeignKey,
#     JSON, TIMESTAMP, Index, UniqueConstraint
# )
# from sqlalchemy.orm import relationship, declarative_base

# Base = declarative_base()


def now_ts():
    return datetime.now(timezone.utc)

# def _utc_now():
#     return datetime.now(timezone.utc)


class AllUsers(Base):
    __tablename__ = "all_users"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=True)
    user_full_name = Column(String(255), nullable=True)
    user_balance = Column(BigInteger, nullable=False, default=0)

    user_blocked = Column(Integer, nullable=False, default=0)
    user_server_rating = Column(Integer, nullable=True)
    user_time_rating = Column(Integer, nullable=True)

    partner_balance = Column(BigInteger, nullable=False, default=0)
    user_id_who_invited = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=True)
    is_partner = Column(Boolean, nullable=False, default=False)
    partner_pct = Column(Float(), nullable=False, default=0.0)
    partner_http = Column(String(255), nullable=True)
    partner_wallet = Column(String(255), nullable=True)

    user_promo_new = Column(Integer, nullable=False, default=0)             # 1 = promo granted
    user_promo_new_days = Column(BigInteger, nullable=True)
    free_subs_given = Column(Integer, nullable=False, default=0) # сколько бесплатных подписок подарил юзер
    
    subscription_server_id_1 = Column(Integer, nullable=True)
    subscription_autopay_id_1 = Column(Integer, nullable=False, default=0)
    subscription_stop_id_1 = Column(BigInteger, nullable=True)

    subscription_server_id_2 = Column(Integer, nullable=True)
    subscription_autopay_id_2 = Column(Integer, nullable=False, default=0)
    subscription_stop_id_2 = Column(BigInteger, nullable=True)

    subscription_server_id_3 = Column(Integer, nullable=True)
    subscription_autopay_id_3 = Column(Integer, nullable=False, default=0) 
    subscription_stop_id_3 = Column(BigInteger, nullable=True)

    subscription_server_id_4 = Column(Integer, nullable=True)
    subscription_autopay_id_4 = Column(Integer, nullable=False, default=0)
    subscription_stop_id_4 = Column(BigInteger, nullable=True)

    subscription_server_id_5 = Column(Integer, nullable=True)
    subscription_autopay_id_5 = Column(Integer, nullable=False, default=0)
    subscription_stop_id_5 = Column(BigInteger, nullable=True)

    subscription_server_next_id_1 = Column(Integer, default=0)
    subscription_server_next_id_2 = Column(Integer, default=0)
    subscription_server_next_id_3 = Column(Integer, default=0)
    subscription_server_next_id_4 = Column(Integer, default=0)
    subscription_server_next_id_5 = Column(Integer, default=0)

    subscription_server_pending_1 = Column(Boolean, default=False)
    subscription_server_pending_2 = Column(Boolean, default=False)
    subscription_server_pending_3 = Column(Boolean, default=False)
    subscription_server_pending_4 = Column(Boolean, default=False)
    subscription_server_pending_5 = Column(Boolean, default=False)


    subscription_settings_string_1 = Column(String, nullable=True)
    subscription_settings_string_2 = Column(String, nullable=True)
    subscription_settings_string_3 = Column(String, nullable=True)
    subscription_settings_string_4 = Column(String, nullable=True)
    subscription_settings_string_5 = Column(String, nullable=True)

    subscription_qr_path_1 = Column(String, nullable=True)
    subscription_qr_path_2 = Column(String, nullable=True)
    subscription_qr_path_3 = Column(String, nullable=True)
    subscription_qr_path_4 = Column(String, nullable=True)
    subscription_qr_path_5 = Column(String, nullable=True)

    quantity_guests = Column(Integer, nullable=False, default=0)
    quantity_guests_paid = Column(Integer, nullable=False, default=0)
    quantity_guests_paid_potent = Column(Integer, nullable=False, default=0)

    balance_earner = Column(BigInteger, nullable=False, default=0)
    balance_earner_fact = Column(BigInteger, nullable=False, default=0)
    
    total_earned = Column(BigInteger, nullable=False, default=0)
    total_paid = Column(BigInteger, nullable=False, default=0)
    partner_wallet = Column(String(255), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)

    invited_users = relationship("AllUsers", remote_side=[user_id], backref="inviter", lazy="selectin")

class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    slot_number = Column(Integer, nullable=False)  # 1-5
    server_country_id = Column(Integer, nullable=True)
    server_id = Column(Integer, nullable=True)
    autopay_id = Column(Integer, nullable=False, default=0)
    stop_time = Column(BigInteger, nullable=True)  # timestamp in ms
    next_server_id = Column(Integer, default=0)
    pending = Column(Boolean, default=False)
    settings_string = Column(String, nullable=True)
    qr_path = Column(String, nullable=True)

    user = relationship("AllUsers", backref="subscriptions", lazy="selectin")

# db/models.py

class ServerClientDeletion(Base):
    __tablename__ = "server_client_deletions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    slot_number = Column(Integer, nullable=False)

    server_id = Column(Integer, nullable=False)
    client_email = Column(String, nullable=False)

    delete_not_before_ts = Column(BigInteger, nullable=False)  # old stop_time
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class UserNotifications(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, index=True, nullable=False)

    invoice_id = Column(String, index=True, nullable=True)
    subscription_id = Column(Integer, nullable=True)

    reason = Column(String(32), nullable=False)
    payload = Column(JSON, nullable=True)

    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # retry / DLQ
    attempt_count = Column(Integer, default=0, nullable=False)
    next_attempt_at = Column(TIMESTAMP(timezone=True), nullable=True)
    failed_permanently = Column(Boolean, default=False, nullable=False)
    last_error = Column(String(512), nullable=True)


class SecretToken(Base):
    __tablename__ = "secret_tokens"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    owner_user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    purpose = Column(String(32), nullable=False)  # e.g. "payfor"
    created_at = Column(TIMESTAMP(timezone=True), default=now_ts, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    metadata_ = Column(JSON, nullable=True)

    owner = relationship("AllUsers", backref="secret_tokens")


class FriendlyAccount(Base):
    __tablename__ = "friendly_accounts"

    id = Column(Integer, primary_key=True)
    owner_user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    friend_user_id = Column(BigInteger, nullable=False)
    friend_username = Column(String(64), nullable=True)
    friend_fullname = Column(String(128), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=now_ts, nullable=False)

    owner = relationship("AllUsers", backref="friendly_accounts")

class AllInvoices(Base):
    __tablename__ = "all_invoices"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    username = Column(String(255), nullable=True)
    user_full_name = Column(String(255), nullable=True)
    
    invoice_curency = Column(String(50), nullable=False)
    invoice_status = Column(String(50), nullable=False, default="created")
    invoice_ammount = Column(BigInteger, nullable=False, default=0)
    invoice_ammount_fact = Column(BigInteger, nullable=False, default=0)
    accounts_ammount = Column(Integer, nullable=True)
    invoice_target = Column(String(100), nullable=True)
    invoice_source = Column(String(100), nullable=True)
    promo = Column(Integer, nullable=True)
    quantity_guests_paid = Column(Integer, nullable=True, default=0)
    invoice_created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    invoice_updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)

    processing_status = Column(String(50), nullable=False, default="pending")  # created, pending, completed, error

    invoice_url = Column(String(255), nullable=True)
    subscription_tx_id = Column(BigInteger, ForeignKey("subscription_transaction.id"), nullable=True, index=True)

    user = relationship("AllUsers", backref="invoices", lazy="selectin")
    subscription_tx = relationship("SubscriptionTransaction", back_populates="invoice", lazy="selectin")
    items = relationship("InvoiceItems", back_populates="invoice", lazy="selectin")

class InvoiceItems(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, autoincrement=True)

    invoice_id = Column(String, ForeignKey("all_invoices.invoice_id"), nullable=False)

    acc_number = Column(Integer, nullable=False)
    server_country_id = Column(Integer, nullable=False)
    server_id = Column(Integer, nullable=True)

    is_free = Column(Boolean, nullable=False)

    discount_percent = Column(Integer, nullable=False)
    discount_amount = Column(Numeric(10, 2), nullable=False)

    price = Column(Numeric(10, 2), nullable=False)
    final_price = Column(Numeric(10, 2), nullable=False)

    provisioned = Column(Boolean, default=False)
    provisioned_at = Column(TIMESTAMP(timezone=True), nullable=True)

    invoice = relationship("AllInvoices", back_populates="items")

class InvoiceTopupTargets(Base):
    __tablename__ = "invoice_topup_targets"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(String, index=True)
    target_type = Column(String(16))  # "self" or "friend"
    friend_user_id = Column(BigInteger, nullable=True)


class AllTransactions(Base):
    __tablename__ = "all_transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    trans_time = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    # trans_time = Column(BigInteger, nullable=False)
    trans_ammount = Column(BigInteger, nullable=False)
    trans_target = Column(String(100), nullable=True)
    accounts_ammount = Column(Integer, nullable=True)
    quantity_guests_paid = Column(Integer, nullable=True)
    promo = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)

    user = relationship("AllUsers", backref="transactions", lazy="selectin")


class PartnerTransactions(Base):
    __tablename__ = "partner_transactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    trans_time = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    # trans_time = Column(BigInteger, nullable=False)
    trans_ammount = Column(BigInteger, nullable=False)
    trans_target = Column(String(100), nullable=True)
    total_earned = Column(BigInteger, nullable=True, default=0)
    total_paid = Column(BigInteger, nullable=True, default=0)
    balance_earner = Column(BigInteger, nullable=True, default=0)
    balance_earner_fact = Column(BigInteger, nullable=True, default=0)
    partner_wallet = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)

    user = relationship("AllUsers", backref="partner_transactions", lazy="selectin")


class SubscriptionTransaction(Base):
    __tablename__ = "subscription_transaction"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("all_users.user_id"), nullable=False)
    source = Column(String(50), nullable=False)            # e.g., "promo", "manual"
    subs_id = Column(Integer, nullable=False, default=1)
    requested_end_ts = Column(BigInteger, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    provider_invoice_id = Column(String(255), nullable=True, unique=True, index=True)
    amount = Column(BigInteger, nullable=True, default=0)
    frozen_amount = Column(BigInteger, nullable=True, default=0)
    partner_share = Column(BigInteger, nullable=True, default=0)
    admin_share = Column(BigInteger, nullable=True, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    next_run_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    payload_meta = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=now_ts)
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    # completed_at = Column(BigInteger, nullable=True)

    user = relationship("AllUsers", backref="subscription_transactions", lazy="selectin")
    invoice = relationship("AllInvoices", back_populates="subscription_tx", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("provider_invoice_id", name="ux_subscription_transaction_provider_invoice_id"),
        Index("ix_subscription_transaction_status_next_run", "status", "next_run_at"),
    )

class AllServers(Base):
    __tablename__ = "all_servers"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Unique server identifier used everywhere in provisioning
    server_id = Column(Integer, unique=True, nullable=False)

    # Country grouping for capacity-aware selection
    country_id = Column(Integer, nullable=False)

    # Current number of active subscriptions on this server
    all_subscriptions = Column(Integer, default=0, nullable=False)

    # Maximum allowed subscriptions before this server is skipped
    max_subscriptions = Column(Integer, default=0, nullable=False)

    # Optional metadata
    server_name = Column(String, nullable=True)
    server_ip = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))
    
    is_online = Column(Boolean, default=False)
    last_check = Column(BigInteger, nullable=True)

    load = Column(Float, default=0.0)
    active_users = Column(Integer, default=0)
    

class Workers(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    # operational metrics
    queue_size = Column(Integer, default=0)
    last_heartbeat = Column(DateTime(timezone=True))
    last_error = Column(String)

    # status flags
    is_healthy = Column(Boolean, default=True)
    debug_mode = Column(Boolean, default=False)

    # optional metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    
# logs models
# from sqlalchemy import Column, Integer, String, DateTime, JSON
# from sqlalchemy.orm import declarative_base

# Base = declarative_base()

class ProvisioningLog(Base):
    __tablename__ = "provisioning_logs"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer)
    server_id = Column(Integer)
    status = Column(String)
    message = Column(String)
    created_at = Column(DateTime)

    def summary(self):
        return f"sub {self.subscription_id}, server {self.server_id}, {self.status}"

    def details(self):
        return self.message


class RenewalLog(Base):
    __tablename__ = "renewal_logs"

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer)
    user_id = Column(Integer)
    status = Column(String)
    created_at = Column(DateTime)

    def summary(self):
        return f"sub {self.subscription_id}, {self.status}"

    def details(self):
        return f"subscription_id={self.subscription_id}, user_id={self.user_id}, status={self.status}"


class PaymentLog(Base):
    __tablename__ = "payment_logs"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer)
    user_id = Column(Integer)
    status = Column(String)
    created_at = Column(DateTime)

    def summary(self):
        return f"invoice {self.invoice_id}, {self.status}"

    def details(self):
        return f"invoice_id={self.invoice_id}, user_id={self.user_id}, status={self.status}"


class WorkerErrorLog(Base):
    __tablename__ = "worker_error_logs"

    id = Column(Integer, primary_key=True)
    worker_name = Column(String)
    error = Column(String)
    created_at = Column(DateTime)

    def summary(self):
        return f"{self.worker_name}: error"

    def details(self):
        return self.error


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer)
    action = Column(String)
    target_type = Column(String)
    target_id = Column(Integer)
    before = Column(JSON)
    after = Column(JSON)
    reason = Column(String)
    created_at = Column(DateTime)

    def summary(self):
        return f"{self.action} on {self.target_type} {self.target_id}"

    def details(self):
        return f"before={self.before}\nafter={self.after}\nreason={self.reason}"
    
class Settings(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

