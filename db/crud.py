# db/crud.py
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db.async_db import SessionLocal
from db.models import AllUsers, SubscriptionTransaction
from datetime import datetime, timezone, timedelta
from config import FIRST_USER_IN_DB


# для тестов добавил админу 10 долларов, чтобы не создавать транзакцию вручную для тестов
async def create_admin():
    async with SessionLocal() as session:
        async with session.begin():
            user_in_db = await session.execute(select(AllUsers).where(AllUsers.user_id == FIRST_USER_IN_DB))
            user_in_db = user_in_db.scalar_one_or_none()
            if not user_in_db:
                datetime_now = datetime.now(timezone.utc)
                datetime_now = int(str(datetime_now.timestamp()*1000)[:13])
                db_user = AllUsers(user_id=FIRST_USER_IN_DB, username="@K_Danilevsky", user_full_name="Admin",user_id_who_invited=FIRST_USER_IN_DB, user_balance=1000)
                session.add(db_user)

async def get_or_create_user_with_promo(
    tg_id: int,
    username: str | None = None,
    full_name: str | None = None,
    user_id_who_invited: int | None = None,
    session: AsyncSession | None = None
) -> tuple[AllUsers, SubscriptionTransaction | None]:
    """
    Returns (user, tx) where tx is a created SubscriptionTransaction or None.
    All DB writes happen inside this function and are committed before returning.
    External provisioning must be executed AFTER this function returns.
    """
    own_session = False
    if session is None:
        session = SessionLocal()
        own_session = True

    tx = None
    try:
        # find or create user
        result = await session.execute(select(AllUsers).where(AllUsers.user_id == tg_id))
        user = result.scalar_one_or_none()

        user_is_new = False

        if user is None:
            inviter = None
            if user_id_who_invited:
                result = await session.execute(select(AllUsers).where(AllUsers.user_id == user_id_who_invited))
                inviter = result.scalar_one_or_none()
            if inviter and inviter.user_blocked != 1:
                user_is_new = True

                user = AllUsers(
                    user_id=tg_id,
                    username=username,
                    user_full_name=full_name,
                    user_id_who_invited=user_id_who_invited if user_id_who_invited else None,
                    user_promo_new=0
                )

                inviter.quantity_guests = (inviter.quantity_guests or 0) + 1
                
                session.add(user)
                session.add(inviter)
                try:
                    await session.commit()
                except IntegrityError:
                    # concurrent create: rollback and re-fetch existing row
                    await session.rollback()
                    result = await session.execute(select(AllUsers).where(AllUsers.user_id == tg_id))
                    user = result.scalar_one()
                else:
                    await session.refresh(user)
        else:
            # update names if changed (optional)
            changed = False
            if username and user.username != username:
                user.username = username; changed = True
            if full_name and user.user_full_name != full_name:
                user.user_full_name = full_name; changed = True
            if changed:
                session.add(user)
                await session.commit()
                await session.refresh(user)

        # Promo logic: only if inviter provided and promo not already granted
        if user_is_new and user_id_who_invited and user.user_promo_new != 1:
            # verify inviter exists and not blocked
            # result = await session.execute(select(AllUsers).where(AllUsers.user_id == user.user_id))
            # inviter = result.scalar_one_or_none()
            if user and user.user_blocked != 1:
                # compute timestamps
                now = datetime.now(timezone.utc)
                requested_end_ts = int(str((now + timedelta(days=5)).timestamp() * 1000)[:13])
                previous_end_ts = None  # if you track previous subscription end, fetch it here

                # mark promo fields on user immediately
                # user.user_id_who_invited = user_id_who_invited
                user.user_promo_new = 1
                user.user_promo_new_days = requested_end_ts
                session.add(user)

                subs_id = 1
                # create subscription transaction row for provisioning
                tx = SubscriptionTransaction(
                    user_id=tg_id,
                    source="promo",
                    subs_id=subs_id,
                    status="pending",
                    requested_end_ts=requested_end_ts,
                    previous_end_ts=previous_end_ts,
                    payload={"user_id_who_invited": user_id_who_invited, "user_id": tg_id, "promo": "new_user_promo"}
                )
                session.add(tx)
                await session.commit()
                await session.refresh(tx)
                await session.refresh(user)
            # else inviter invalid or blocked -> do nothing

        return user, tx
    finally:
        if own_session:
            await session.close()
