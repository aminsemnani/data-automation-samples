CREATE TABLE invoices (
    invoice_id TEXT PRIMARY KEY,
    customer TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    invoice_amount REAL NOT NULL CHECK(invoice_amount >= 0)
);

CREATE TABLE payments (
    payment_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL CHECK(amount >= 0)
);

CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
