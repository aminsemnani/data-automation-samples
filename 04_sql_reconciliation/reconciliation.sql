WITH payment_totals AS (
    SELECT invoice_id, ROUND(SUM(amount), 2) AS paid_amount, COUNT(*) AS payment_count
    FROM payments
    GROUP BY invoice_id
)
SELECT
    i.invoice_id,
    i.customer,
    i.invoice_amount,
    ROUND(COALESCE(p.paid_amount, 0), 2) AS paid_amount,
    ROUND(COALESCE(p.paid_amount, 0) - i.invoice_amount, 2) AS variance,
    CASE
        WHEN p.invoice_id IS NULL THEN 'unpaid'
        WHEN ABS(p.paid_amount - i.invoice_amount) <= 0.01 THEN 'matched'
        WHEN p.paid_amount < i.invoice_amount THEN 'partial'
        ELSE 'overpaid'
    END AS status
FROM invoices i
LEFT JOIN payment_totals p ON p.invoice_id = i.invoice_id
ORDER BY i.invoice_id;
