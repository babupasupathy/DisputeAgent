-- Synthetic store + mock processor. ALL DATA IS SYNTHETIC.
CREATE TABLE customers (
  customer_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE products (
  product_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  price REAL NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);
-- Archived copy of the listing as it looked when an order was placed.
CREATE TABLE listing_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(product_id),
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  captured_at TEXT NOT NULL
);
CREATE TABLE orders (
  order_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  created_at TEXT NOT NULL,
  subtotal REAL NOT NULL,
  shipping_fee REAL NOT NULL,
  total REAL NOT NULL,
  currency TEXT NOT NULL,
  billing_address TEXT NOT NULL,
  shipping_address TEXT NOT NULL,
  card_brand TEXT NOT NULL,
  card_last4 TEXT NOT NULL,          -- synthetic; never a full PAN
  avs_result TEXT NOT NULL,          -- Y = match, N = no match, U = unavailable
  cvv_result TEXT NOT NULL,          -- M = match, N = no match, U = unavailable
  ip_address TEXT NOT NULL,          -- documentation ranges only (RFC 5737)
  device_id TEXT NOT NULL,
  policy_version_accepted TEXT       -- NULL = no record of policy acceptance
);
CREATE TABLE order_items (
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  product_id TEXT NOT NULL REFERENCES products(product_id),
  qty INTEGER NOT NULL,
  unit_price REAL NOT NULL,
  listing_snapshot_id TEXT REFERENCES listing_snapshots(snapshot_id)
);
CREATE TABLE shipments (
  shipment_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  carrier TEXT NOT NULL,
  service TEXT NOT NULL,
  tracking_number TEXT,              -- NULL = untracked service
  shipped_at TEXT NOT NULL,
  status TEXT NOT NULL,              -- shipped, in_transit, delivered, lost, returned_to_sender
  delivered_at TEXT,
  delivered_address_match INTEGER,   -- 1/0, NULL if not delivered
  signature_on_file INTEGER NOT NULL DEFAULT 0,
  photo_on_file INTEGER NOT NULL DEFAULT 0,
  dispatch_photo_on_file INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE tracking_events (
  shipment_id TEXT NOT NULL REFERENCES shipments(shipment_id),
  ts TEXT NOT NULL,
  status TEXT NOT NULL,
  location TEXT NOT NULL,
  detail TEXT NOT NULL
);
CREATE TABLE support_messages (
  message_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  ts TEXT NOT NULL,
  channel TEXT NOT NULL,             -- email, chat
  sender TEXT NOT NULL,              -- customer, agent, system
  body TEXT NOT NULL
);
CREATE TABLE refunds (
  refund_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  ts TEXT NOT NULL,
  amount REAL NOT NULL,
  reason TEXT NOT NULL
);
CREATE TABLE returns (
  return_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  requested_at TEXT NOT NULL,
  status TEXT NOT NULL,              -- requested, label_sent, received
  received_at TEXT
);
-- Mock processor: open disputes (eval cases) and closed historical disputes.
CREATE TABLE disputes (
  dispute_id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL REFERENCES orders(order_id),
  customer_id TEXT NOT NULL REFERENCES customers(customer_id),
  network TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  reason_category TEXT NOT NULL,     -- processor's coarse category; may be 'general'
  amount REAL NOT NULL,
  currency TEXT NOT NULL,
  received_at TEXT NOT NULL,
  response_due_at TEXT NOT NULL,
  issuer_message TEXT NOT NULL,
  status TEXT NOT NULL,              -- needs_response, won, lost, accepted
  closed_at TEXT
);
CREATE TABLE escalations (
  escalation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  dispute_id TEXT NOT NULL,
  summary TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE submissions (
  submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
  dispute_id TEXT NOT NULL,
  payload TEXT NOT NULL,
  approved_by TEXT NOT NULL,
  created_at TEXT NOT NULL
);
-- GENERATOR-ONLY metadata used by the ground-truth labeler. Never exposed by
-- src/backend/repository.py or the API (enforced by tests/test_separation.py).
CREATE TABLE _gen_message_labels (
  message_id TEXT NOT NULL REFERENCES support_messages(message_id),
  tag TEXT NOT NULL
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_ship_order ON shipments(order_id);
CREATE INDEX idx_msg_order ON support_messages(order_id);
CREATE INDEX idx_disp_customer ON disputes(customer_id);
