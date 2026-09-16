#!/usr/bin/env python3

# script to clean up orphan QR codes that are not linked to any active subscription in the database
# This is needed because sometimes QR codes can be generated but not properly linked to a subscription, or subscriptions can be deleted without removing the QR code file. This script will scan the QR code directory and delete any files that are not associated with an active subscription in the database.
# Usage: python cleanup_orphan_qrs.py
# Make sure to run this script periodically (e.g. via cron) to keep the QR code directory clean and prevent clutter from orphan files.

# Edit your crontab to run at 3:30 AM every day:
# crontab -e
# 30 3 * * * /usr/bin/python3 /path/to/scripts/cleanup_orphan_qrs.py >> /var/log/cleanup_orphan_qrs_cron.log 2>&1

import os
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from sqlalchemy import select

from db.async_db import SessionLocal
from db.models import UserSubscription

QRS_BASE_DIR = "qrs/subs_qrs"
LOG_FILE = "logs/cleanup_orphan_qrs.log"


def setup_logging():
    os.makedirs("logs", exist_ok=True)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[handler, logging.StreamHandler()]
    )


async def cleanup_orphan_qrs():
    logger = logging.getLogger("cleanup_orphan_qrs")

    logger.info("=== QR Cleanup Started ===")

    # Load valid QR paths from DB
    async with SessionLocal() as session:
        async with session.begin():
            r = await session.execute(select(UserSubscription.qr_path))
            valid_paths = {row[0] for row in r.fetchall() if row[0]}

    logger.info(f"Loaded {len(valid_paths)} valid QR paths from DB")

    scanned = 0
    deleted = 0

    # Walk filesystem
    for root, dirs, files in os.walk(QRS_BASE_DIR):
        for f in files:
            if not f.endswith(".png"):
                continue

            scanned += 1
            full_path = os.path.join(root, f)

            if full_path not in valid_paths:
                logger.info(f"Deleting orphan QR: {full_path}")
                try:
                    os.remove(full_path)
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {full_path}: {e}")

    logger.info(
        f"QR Cleanup Completed — scanned={scanned}, deleted={deleted}, valid={len(valid_paths)}"
    )
    logger.info("=== QR Cleanup Finished ===")


if __name__ == "__main__":
    setup_logging()
    asyncio.run(cleanup_orphan_qrs())
