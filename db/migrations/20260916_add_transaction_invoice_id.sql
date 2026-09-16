-- Add the invoice reference used by invoice idempotency checks.
-- Run this migration against existing databases before deploying the worker.
ALTER TABLE all_transactions
    ADD COLUMN IF NOT EXISTS invoice_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS ix_all_transactions_invoice_id
    ON all_transactions (invoice_id);

-- Prevent duplicate bookkeeping rows for the same invoice and operation.
CREATE UNIQUE INDEX IF NOT EXISTS ux_all_transactions_invoice_target
    ON all_transactions (invoice_id, trans_target)
    WHERE invoice_id IS NOT NULL AND trans_target IS NOT NULL;
