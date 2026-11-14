"""Deterministic synthetic data generator. ALL DATA IS SYNTHETIC.

Two kinds of records are written to SQLite:
  * background store activity (customers, orders, shipments, refunds, a few closed disputes)
  * one open dispute per scenario spec, with its order records built to match the spec

The generator does NOT write labels. Ground truth is derived afterwards from the stored
records by evals/labeling/labeler.py, so a bug in a scenario spec shows up as a mismatch
between scenario intent and derived label (checked in tests), not as a wrong label.

Narrative text (support messages, issuer messages) is template-based. Templates have
several phrasings so the agent has to read the text, not match a fixed string.
"""
from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.backend.db import init_db
from src.config import decision_config
from src.knowledge.rules import codes_for, lookup

AS_OF = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
SEED = 20261109


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- catalog
PRODUCTS = [
    # (title, description, price)
    ("Cotton tote bag", "Natural canvas tote, 15 x 16 in, single interior pocket.", 9.99),
    ("Enamel camp mug", "12 oz white enamel mug with blue rim. Not microwave safe.", 14.50),
    ("Merino crew socks (3-pack)", "Mid-weight merino blend, sizes S-XL, charcoal/grey/navy.", 22.00),
    ("Beeswax candle", "Hand-poured 8 oz candle, unscented, approx. 40 h burn time.", 18.00),
    ("Linen napkins (set of 4)", "Stonewashed linen, 18 x 18 in, color: sage.", 34.00),
    ("Ceramic pour-over dripper", "Size 02 dripper, matte black glaze, fits standard filters.", 42.00),
    ("Leather card holder", "Vegetable-tanned leather, 4 slots, color: tan.", 48.00),
    ("Waxed canvas cap", "Six-panel cap, adjustable strap, color: olive.", 39.00),
    ("Insulated water bottle", "750 ml double-wall steel bottle, keeps cold 24 h.", 36.00),
    ("Wool throw blanket", "50 x 60 in lambswool throw, herringbone, color: oatmeal.", 129.00),
    ("Rain shell jacket", "Packable 2.5-layer shell, waterproof 10k/10k, color: navy, unisex sizing.", 168.00),
    ("Hiking daypack 22L", "22 L pack with laptop sleeve and hip belt, color: rust.", 112.00),
    ("Cast iron skillet 10in", "Pre-seasoned 10 in skillet, 5.2 lb.", 64.00),
    ("Stoneware dinner set (4)", "4 plates, 4 bowls, reactive glaze, color: speckled white.", 145.00),
    ("Down vest", "650-fill down vest, color: black, sizes XS-XXL.", 189.00),
    ("Chef knife 8in", "8 in chef knife, VG-10 steel core, walnut handle.", 155.00),
    ("Bluetooth speaker", "Portable speaker, 12 h battery, IPX5, color: grey.", 89.00),
    ("Leather weekender bag", "Full-grain leather weekender, 45 L, brass hardware, color: cognac.", 345.00),
    ("Wool overcoat", "Single-breasted wool-blend overcoat, color: camel, regular fit.", 395.00),
    ("Noise-cancelling headphones", "Over-ear ANC headphones, 30 h battery, color: black.", 279.00),
    ("Standing desk converter", "Desktop riser, 32 in wide, 11-level height adjustment.", 229.00),
    ("Mechanical keyboard", "75% layout, hot-swap switches, tactile, color: white.", 189.00),
    ("Air purifier", "HEPA H13 purifier for rooms up to 400 sq ft.", 249.00),
    ("Ergonomic office chair", "Mesh back chair, adjustable lumbar and arms, color: graphite.", 549.00),
    ("Smartwatch", "GPS smartwatch, 1.4 in AMOLED, 7-day battery, color: slate.", 329.00),
    ("Espresso machine", "15-bar semi-automatic espresso machine with steam wand, stainless.", 899.00),
    ("Road bike helmet + lights kit", "MIPS road helmet with front and rear USB lights.", 249.00),
    ("Robot vacuum", "LiDAR robot vacuum with auto-empty base.", 799.00),
    ("Carbon road bike wheelset", "Carbon clincher wheelset, 45 mm depth, rim brake.", 1290.00),
    ("Laptop 14in", "14 in laptop, 16 GB RAM, 512 GB SSD, color: silver.", 1199.00),
    ("Mirrorless camera body", "24 MP mirrorless camera body, no lens included.", 1549.00),
]

BANDS = {
    "low": (9.0, 23.0),
    "normal": (85.0, 700.0),
    "upper_mid": (345.0, 700.0),
    "high": (780.0, 1600.0),
}

FIRST = ["Avery", "Jordan", "Riley", "Casey", "Morgan", "Quinn", "Rowan", "Sage", "Taylor", "Emerson",
         "Hayden", "Parker", "Reese", "Skyler", "Dakota", "Finley", "Harper", "Jules", "Kai", "Logan"]
LAST = ["Testwood", "Sampleton", "Mockford", "Placeholder", "Fakeley", "Synthbury", "Demoreaux",
        "Examplar", "Notreal", "Fictor", "Stubbs", "Dummond", "Proto", "Cassidy-Mock", "Lorem"]
STREETS = ["Maple", "Cedar", "Harbor", "Juniper", "Willow", "Granite", "Orchard", "Sycamore", "Linden", "Birch"]
CITIES = [("Springfield", "ST"), ("Riverton", "RV"), ("Lakeside", "LK"), ("Fairview", "FV"), ("Hillcrest", "HC")]
CARRIERS = [("UPS", "Ground", "SYN1Z"), ("FedEx", "Home Delivery", "SYNFX"), ("USPS", "Priority Mail", "SYN94")]
BRANDS = {"visa": "visa", "mastercard": "mastercard", "amex": "amex"}
PROCESSOR_CATEGORY = {
    "item_not_received": "product_not_received",
    "fraud": "fraudulent",
    "not_as_described": "product_unacceptable",
}

# ---------------------------------------------------------------------- text templates
ISSUER_MSG = {
    "item_not_received": [
        "Cardholder states merchandise was never received.",
        "CH advises order not delivered; contacted merchant without resolution.",
        "Cardholder claims package did not arrive at shipping address.",
        "Goods not received per cardholder. Expected delivery date has passed.",
    ],
    "fraud": [
        "Cardholder does not recognize this transaction.",
        "CH states card was used without authorization for an online purchase.",
        "Cardholder denies participating in this card-not-present transaction.",
        "Unauthorized transaction reported. Cardholder still in possession of card.",
    ],
    "not_as_described": [
        "Cardholder states item received was not as described on the website.",
        "CH reports merchandise arrived damaged and merchant refused to help.",
        "Item received is defective per cardholder.",
        "Cardholder says product differs materially from listing (color/size).",
    ],
}

MSG = {
    "where_is_order": [
        "Hi, my tracking hasn't updated in a few days. Can you check where my order is?",
        "Hello - I ordered over a week ago and nothing has shown up. Any update?",
        "Is my order still coming? The tracking page just says in transit.",
    ],
    "where_is_order_early": [
        "Is my order still coming? The tracking page just says in transit.",
        "Any idea when my package will arrive? I need it by the weekend.",
    ],
    "where_is_order_reply": [
        "Thanks for reaching out. Carriers can be delayed this time of year; please allow a few more business days.",
        "Sorry for the wait! I've asked the carrier for an update and will follow up.",
    ],
    "customer_ack_receipt": [
        "Hi, the package arrived yesterday. Quick question - can I exchange for a different size?",
        "Got my order today, thanks. Do you have care instructions for it?",
        "Received the box this afternoon. Is there a gift receipt I could print?",
    ],
    "not_received_complaint": [
        "Tracking says delivered but there is nothing at my door. Can you help?",
        "I never got this package even though it shows delivered.",
    ],
    "merchant_ack_nondelivery": [
        "I'm sorry about this. I checked with the carrier and it looks like the package was left at the wrong address. We'll look into a reship.",
        "Apologies - the carrier confirmed a misdelivery on their side. Let me see what we can do about a replacement.",
    ],
    "nad_complaint": [
        "The item I received doesn't look like the photos at all. The color is completely different.",
        "This arrived with a broken part and doesn't work properly.",
        "The size is nothing like what the listing said. Very disappointed.",
        "Material feels cheap and it's not what was described.",
    ],
    "merchant_offered_remedy": [
        "We're sorry it isn't what you expected. You can return it within 30 days for a full refund using the prepaid label below, or we can send a replacement.",
        "Sorry to hear that! I can send a replacement right away, or you can return it for a refund - just reply and let me know which you'd prefer.",
        "Thanks for letting us know. Please send it back with the attached return label and we'll refund you as soon as it arrives.",
    ],
    "merchant_admitted_defect": [
        "You're right - this batch had a known manufacturing defect and we've pulled it from sale. We're sorry.",
        "I've confirmed with our warehouse that the units from this shipment were mislabeled and do not match the listing. Apologies.",
    ],
    "general_question": [
        "Do you ship to PO boxes?",
        "Can I change the email on my account?",
    ],
}


# ------------------------------------------------------------------------- scenario spec
@dataclass
class Spec:
    """Everything needed to build one dispute's records. Defaults = strong, clean case."""
    case_id: str
    category: str
    scenario: str
    source: str = "generated"          # generated | handwritten
    network: str | None = None
    reason_code: str | None = None
    amount_band: str = "normal"
    fixed_amount: float | None = None  # exact order total (handwritten boundary cases)
    deadline: str = "normal"           # normal | near | passed | exact_hours
    hours_remaining: float | None = None
    refund: str | None = None          # None | partial_mismatch | partial_consistent | full
    refund_fraction: float | None = None
    prior_disputes: int = 0
    issuer_message: bool | None = None
    # shipping
    tracked: bool = True
    ship_status: str = "delivered"     # delivered | in_transit | lost | returned_to_sender
    address_match: bool | None = True  # None = carrier reported no address data
    signature: bool = False
    photo: bool = False
    dispatch_photo: bool = False
    # payment / identity
    avs_cvv: bool = True
    ship_to_billing: bool = True
    priors_in_window: int = 0
    device_match: bool = False
    account_age_days: int = 400
    # listing / policy / returns
    listing: bool = True
    policy: bool = True
    return_status: str | None = None   # None | requested | received
    # support messages
    customer_ack: bool = False
    merchant_ack_nondelivery: bool = False
    nad_complaint: bool = False
    remedy: bool = False
    admitted_defect: bool = False
    where_is_order: bool = False
    note: str = ""


def _strong_base(rng: random.Random, case_id: str, category: str, scenario: str) -> Spec:
    s = Spec(case_id=case_id, category=category, scenario=scenario)
    s.signature = rng.random() < 0.35
    s.photo = (not s.signature) and rng.random() < 0.4
    s.dispatch_photo = rng.random() < 0.4
    s.account_age_days = rng.randint(30, 1500)
    s.priors_in_window = rng.choice([0, 0, 1, 2, 3])
    s.device_match = s.priors_in_window > 0 and rng.random() < 0.6
    s.ship_to_billing = rng.random() < 0.75
    if category == "item_not_received":
        s.customer_ack = rng.random() < 0.35
        s.where_is_order = (not s.customer_ack) and rng.random() < 0.3
    elif category == "fraud":
        s.ship_to_billing = True
    elif category == "not_as_described":
        s.nad_complaint = True
        s.remedy = True
        s.return_status = None if rng.random() < 0.7 else "requested"
    return s


def _weak(rng: random.Random, s: Spec) -> Spec:
    """Remove some required evidence without creating a conflict or merchant fault."""
    if s.category == "item_not_received":
        variant = rng.choice(["untracked", "stuck", "no_address_data"])
        s.note = variant
        s.customer_ack = False
        s.signature = s.photo = False
        if variant == "untracked":
            s.tracked, s.ship_status, s.address_match = False, "in_transit", None
        elif variant == "stuck":
            s.ship_status, s.address_match = "in_transit", None
            s.where_is_order = True
        else:
            s.address_match = None
    elif s.category == "fraud":
        drop = rng.sample(["avs_cvv", "billing", "delivery"], k=rng.randint(1, 3))
        s.note = "+".join(sorted(drop))
        if "avs_cvv" in drop:
            s.avs_cvv = False
            s.priors_in_window, s.device_match = 0, False  # otherwise it is a conflict
            s.account_age_days = rng.randint(1, 60)
        if "billing" in drop:
            s.ship_to_billing = False
        if "delivery" in drop:
            s.ship_status, s.address_match = "in_transit", None
            s.signature = s.photo = False
    else:
        drop = rng.sample(["listing", "policy", "remedy"], k=rng.randint(1, 3))
        s.note = "+".join(sorted(drop))
        s.listing = "listing" not in drop
        s.policy = "policy" not in drop
        s.remedy = "remedy" not in drop
    return s


def _conflict(rng: random.Random, s: Spec, variant: int) -> Spec:
    s.amount_band = "upper_mid"
    if s.category == "item_not_received":
        if variant % 2 == 0:
            s.address_match = False
            s.note = "delivered_to_other_address"
        else:
            s.nad_complaint = False
            s.customer_ack = False
            s.merchant_ack_nondelivery = True
            s.note = "agent_admitted_misdelivery"
    elif s.category == "fraud":
        s.avs_cvv = False
        s.priors_in_window = rng.randint(2, 3)
        s.device_match = True
        s.account_age_days = max(s.account_age_days, 500)
        s.note = "avs_fail_but_device_history"
    else:
        s.admitted_defect = True
        s.note = "agent_admitted_defect"
    return s


def scenario_specs(seed: int = SEED) -> list[Spec]:
    rng = random.Random(seed)
    specs: list[Spec] = []
    n = 0

    def new(cat: str, scen: str) -> Spec:
        nonlocal n
        n += 1
        return _strong_base(rng, f"GEN-{n:03d}", cat, scen)

    plan = {
        "item_not_received": dict(strong=12, weak=12, conflicting=8, deadline_near=2, deadline_passed=1,
                                  partial_refund_mismatch=2, partial_refund_consistent=1, full_refund=2,
                                  high_value=3, repeat_disputer=2, low_amount=2, merchant_fault=3),
        "fraud": dict(strong=12, weak=12, conflicting=8, deadline_near=2, deadline_passed=1,
                      partial_refund_mismatch=2, partial_refund_consistent=1, full_refund=2,
                      high_value=3, repeat_disputer=3, low_amount=2),
        "not_as_described": dict(strong=12, weak=12, conflicting=8, deadline_near=2, deadline_passed=1,
                                 partial_refund_mismatch=2, partial_refund_consistent=1, full_refund=2,
                                 high_value=3, repeat_disputer=2, low_amount=2, merchant_fault=2),
    }
    for cat, counts in plan.items():
        for scen, k in counts.items():
            for i in range(k):
                s = new(cat, scen)
                if scen == "weak":
                    _weak(rng, s)
                elif scen == "conflicting":
                    _conflict(rng, s, i)
                elif scen == "deadline_near":
                    s.deadline = "near"
                elif scen == "deadline_passed":
                    s.deadline = "passed"
                elif scen == "partial_refund_mismatch":
                    s.refund, s.amount_band = "partial_mismatch", "upper_mid"
                elif scen == "partial_refund_consistent":
                    s.refund, s.amount_band = "partial_consistent", "upper_mid"
                elif scen == "full_refund":
                    s.refund = "full"
                elif scen == "high_value":
                    s.amount_band = "high"
                elif scen == "repeat_disputer":
                    s.prior_disputes = rng.randint(2, 3)
                elif scen == "low_amount":
                    s.amount_band = "low"
                elif scen == "merchant_fault":
                    if cat == "item_not_received":
                        s.ship_status = ["lost", "returned_to_sender", "lost"][i % 3]
                        s.address_match = None
                        s.signature = s.photo = s.customer_ack = False
                        s.where_is_order = True
                        s.note = s.ship_status
                    else:
                        s.return_status = "received"
                        s.note = "return_received_no_refund"
                specs.append(s)
    return specs


# ---------------------------------------------------------------------------- builder
@dataclass
class Ids:
    counters: dict = field(default_factory=dict)

    def next(self, prefix: str, width: int = 6, start: int = 100000) -> str:
        v = self.counters.get(prefix, start) + 1
        self.counters[prefix] = v
        return f"{prefix}-{v:0{width}d}"


class Builder:
    def __init__(self, conn: sqlite3.Connection, seed: int = SEED):
        self.conn = conn
        self.rng = random.Random(seed)
        self.ids = Ids()
        self.product_ids: list[tuple[str, float]] = []

    # ---- helpers
    def address(self) -> str:
        city, st = self.rng.choice(CITIES)
        return f"{self.rng.randint(10, 9899)} {self.rng.choice(STREETS)} St, {city}, {st} 0{self.rng.randint(1000, 9999)}"

    def ip(self) -> str:
        net = self.rng.choice(["192.0.2", "198.51.100", "203.0.113"])
        return f"{net}.{self.rng.randint(1, 254)}"

    def device(self) -> str:
        return "dev_" + "".join(self.rng.choice("0123456789abcdef") for _ in range(12))

    def insert(self, table: str, **cols):
        keys = ",".join(cols)
        qs = ",".join("?" for _ in cols)
        self.conn.execute(f"INSERT INTO {table} ({keys}) VALUES ({qs})", tuple(cols.values()))

    # ---- catalog
    def build_catalog(self):
        for i, (title, desc, price) in enumerate(PRODUCTS, start=1):
            pid = f"PRD-{i:04d}"
            self.insert("products", product_id=pid, title=title, description=desc, price=price, active=1)
            self.product_ids.append((pid, price))

    def pick_product(self, band: str) -> tuple[str, float]:
        lo, hi = BANDS[band]
        options = [p for p in self.product_ids if lo <= p[1] <= hi]
        return self.rng.choice(options)

    # ---- entities
    def customer(self, created_at: datetime) -> str:
        cid = self.ids.next("CUS")
        name = f"{self.rng.choice(FIRST)} {self.rng.choice(LAST)}"
        email = f"{name.lower().replace(' ', '.').replace('-', '')}.{cid[-4:]}@example.com"
        self.insert("customers", customer_id=cid, name=name, email=email, created_at=iso(created_at))
        return cid

    def order(self, customer_id: str, created_at: datetime, *, band: str = "normal",
              fixed_amount: float | None = None, billing: str | None = None,
              ship_to_billing: bool = True, avs_cvv: bool = True, ip: str | None = None,
              device: str | None = None, policy: bool = True, listing: bool = True,
              network: str = "visa", last4: str | None = None) -> tuple[str, float]:
        oid = self.ids.next("ORD")
        if fixed_amount is None:
            pid, price = self.pick_product(band)
        else:  # closest catalog item, sold at the fixed price (handwritten boundary cases)
            pid = min(self.product_ids, key=lambda p: abs(p[1] - fixed_amount))[0]
            price = fixed_amount
        qty = 1
        subtotal = round(price * qty, 2)
        shipping_fee = 0.0 if (subtotal >= 75 or fixed_amount is not None) else 6.95
        total = round(subtotal + shipping_fee, 2)
        billing = billing or self.address()
        shipping = billing if ship_to_billing else self.address()
        if avs_cvv:
            avs, cvv = "Y", "M"
        else:
            avs, cvv = self.rng.choice([("N", "M"), ("N", "N"), ("U", "N"), ("N", "U")])
        self.insert(
            "orders", order_id=oid, customer_id=customer_id, created_at=iso(created_at),
            subtotal=subtotal, shipping_fee=shipping_fee, total=total, currency="USD",
            billing_address=billing, shipping_address=shipping, card_brand=BRANDS[network],
            card_last4=last4 or f"{self.rng.randint(0, 9999):04d}", avs_result=avs, cvv_result=cvv,
            ip_address=ip or self.ip(), device_id=device or self.device(),
            policy_version_accepted="returns-v3 (2025-01-01)" if policy else None,
        )
        snap = None
        if listing:
            snap = self.ids.next("LST")
            title, desc = self.conn.execute(
                "SELECT title, description FROM products WHERE product_id=?", (pid,)).fetchone()
            self.insert("listing_snapshots", snapshot_id=snap, product_id=pid, title=title,
                        description=desc, captured_at=iso(created_at))
        self.insert("order_items", order_id=oid, product_id=pid, qty=qty, unit_price=subtotal,
                    listing_snapshot_id=snap)
        return oid, total

    def _city_of(self, order_id: str) -> tuple[str, str] | None:
        row = self.conn.execute("SELECT shipping_address FROM orders WHERE order_id=?", (order_id,)).fetchone()
        if row is None:
            return None
        for c in CITIES:
            if f", {c[0]}, {c[1]} " in row[0]:
                return c
        return None

    def shipment(self, order_id: str, order_at: datetime, *, tracked=True, status="delivered",
                 address_match: bool | None = True, signature=False, photo=False,
                 dispatch_photo=False) -> datetime | None:
        sid = self.ids.next("SHP")
        shipped = order_at + timedelta(hours=self.rng.randint(18, 52))
        if tracked:
            carrier, service, prefix = self.rng.choice(CARRIERS)
            tn = prefix + "".join(self.rng.choice("0123456789") for _ in range(12))
        else:
            carrier, service, tn = "USPS", "First-Class (untracked)", None
        delivered_at = None
        events: list[tuple[datetime, str, str, str]] = []
        if tracked:
            city, st = self.rng.choice(CITIES)  # drawn as before, so every other generated value is unchanged
            # Destination scans must agree with the carrier's address-match flag (bug found in human grading,
            # 2026-11-14: 112 of 131 "matched" deliveries were scanned in another city).
            ship_city = self._city_of(order_id)
            if ship_city and status == "delivered" and address_match is True:
                city, st = ship_city
            elif ship_city and status == "delivered" and address_match is False and (city, st) == ship_city:
                city, st = CITIES[(CITIES.index(ship_city) + 1) % len(CITIES)]
            events.append((shipped, "label_created", "Origin facility, NV", "Shipping label created"))
            t1 = shipped + timedelta(hours=self.rng.randint(8, 20))
            events.append((t1, "in_transit", "Regional hub, UT", "Departed facility"))
            t2 = t1 + timedelta(hours=self.rng.randint(20, 40))
            events.append((t2, "in_transit", f"{city}, {st}", "Arrived at destination facility"))
            if status == "delivered":
                t3 = t2 + timedelta(hours=self.rng.randint(6, 14))
                events.append((t3, "out_for_delivery", f"{city}, {st}", "Out for delivery"))
                delivered_at = t3 + timedelta(hours=self.rng.randint(1, 8))
                detail = "Delivered"
                if signature:
                    detail += ", signed by recipient"
                elif photo:
                    detail += ", photo taken at front door"
                else:
                    detail += ", left at front door"
                events.append((delivered_at, "delivered", f"{city}, {st}", detail))
            elif status == "lost":
                events.append((t2 + timedelta(days=9), "exception", f"{city}, {st}",
                               "Package could not be located. Claim opened by carrier."))
            elif status == "returned_to_sender":
                events.append((t2 + timedelta(days=2), "exception", f"{city}, {st}",
                               "Address not deliverable"))
                events.append((t2 + timedelta(days=7), "returned_to_sender", "Origin facility, NV",
                               "Returned to sender"))
        self.insert(
            "shipments", shipment_id=sid, order_id=order_id, carrier=carrier, service=service,
            tracking_number=tn, shipped_at=iso(shipped),
            status=status if tracked else "shipped",
            delivered_at=iso(delivered_at) if delivered_at else None,
            delivered_address_match=(None if (status != "delivered" or address_match is None or not tracked)
                                     else int(address_match)),
            signature_on_file=int(bool(signature and status == "delivered" and tracked)),
            photo_on_file=int(bool(photo and status == "delivered" and tracked)),
            dispatch_photo_on_file=int(dispatch_photo),
        )
        for ts, st_, loc, det in events:
            self.insert("tracking_events", shipment_id=sid, ts=iso(ts), status=st_, location=loc, detail=det)
        return delivered_at

    def message(self, order_id: str, ts: datetime, sender: str, kind: str, tag: str | None = None,
                channel: str | None = None):
        mid = self.ids.next("MSG", width=7, start=1000000)
        body = self.rng.choice(MSG[kind]) if kind in MSG else kind
        self.insert("support_messages", message_id=mid, order_id=order_id, ts=iso(ts),
                    channel=channel or self.rng.choice(["email", "chat"]), sender=sender, body=body)
        if tag:
            self.insert("_gen_message_labels", message_id=mid, tag=tag)

    def system_messages(self, order_id: str, order_at: datetime, total: float):
        self.message(order_id, order_at + timedelta(minutes=1), "system",
                     f"Order confirmation sent for {order_id} (total ${total:.2f}).", channel="email")
        self.message(order_id, order_at + timedelta(hours=30), "system",
                     f"Shipping notification sent for {order_id}.", channel="email")

    # ---- background activity
    def build_background(self, n_customers: int = 300):
        for _ in range(n_customers):
            created = AS_OF - timedelta(days=self.rng.randint(30, 900))
            cid = self.customer(created)
            for _ in range(self.rng.randint(0, 5)):
                age = self.rng.randint(5, max(6, (AS_OF - created).days - 1))
                at = AS_OF - timedelta(days=age, hours=self.rng.randint(0, 23))
                oid, total = self.order(cid, at, band=self.rng.choice(["low", "normal", "normal"]),
                                        network=self.rng.choice(["visa", "mastercard", "amex"]))
                self.shipment(oid, at, dispatch_photo=self.rng.random() < 0.3,
                              signature=self.rng.random() < 0.2)
                self.system_messages(oid, at, total)
                if self.rng.random() < 0.06:
                    self.insert("refunds", refund_id=self.ids.next("RFD"), order_id=oid,
                                ts=iso(at + timedelta(days=10)), amount=total, reason="customer_return")
                if self.rng.random() < 0.02 and age > 60:
                    self._closed_dispute(oid, cid, at, total)

    def _closed_dispute(self, order_id: str, customer_id: str, order_at: datetime, total: float):
        network = self.rng.choice(["visa", "mastercard", "amex"])
        cat = self.rng.choice(["item_not_received", "fraud", "not_as_described"])
        code = self.rng.choice(codes_for(network, cat))
        recv = order_at + timedelta(days=self.rng.randint(15, 40))
        self.insert(
            "disputes", dispute_id=self.ids.next("DSP"), order_id=order_id, customer_id=customer_id,
            network=network, reason_code=code,
            reason_category="general" if (network == "mastercard" and code == "4853") else PROCESSOR_CATEGORY[cat],
            amount=total, currency="USD", received_at=iso(recv), response_due_at=iso(recv + timedelta(days=13)),
            issuer_message=self.rng.choice(ISSUER_MSG[cat]), status=self.rng.choice(["won", "lost", "accepted"]),
            closed_at=iso(recv + timedelta(days=40)),
        )

    # ---- one dispute case
    def build_case(self, spec: Spec) -> dict:
        rng = self.rng
        network = spec.network or rng.choices(["visa", "mastercard", "amex"], weights=[5, 3, 2])[0]
        code = spec.reason_code or rng.choice(codes_for(network, spec.category))
        rule = lookup(network, code, spec.category)

        order_at = AS_OF - timedelta(days=rng.randint(14, 50), hours=rng.randint(0, 23))
        # customer account must predate every prior order
        oldest_prior_days = 0
        if spec.priors_in_window:
            oldest_prior_days = 365
        if spec.prior_disputes:
            oldest_prior_days = max(oldest_prior_days, 400)
        account_age = max(spec.account_age_days, oldest_prior_days + 10)
        cid = self.customer(order_at - timedelta(days=account_age))

        billing = self.address()
        ip, dev = self.ip(), self.device()

        # prior undisputed orders inside the 120-365 day window
        prior_ages = sorted(rng.sample(range(125, 360), spec.priors_in_window), reverse=True)
        for i, age in enumerate(prior_ages):
            at = order_at - timedelta(days=age)
            same = spec.device_match and i == len(prior_ages) - 1 or (spec.device_match and rng.random() < 0.5)
            poid, ptotal = self.order(cid, at, billing=billing, ip=ip if same else None,
                                      device=dev if same else None, network=network)
            self.shipment(poid, at)
            self.system_messages(poid, at, ptotal)
        if spec.device_match and not spec.priors_in_window:
            at = order_at - timedelta(days=rng.randint(30, 100))
            poid, ptotal = self.order(cid, at, billing=billing, ip=ip, device=dev, network=network)
            self.shipment(poid, at)
            self.system_messages(poid, at, ptotal)
        # prior disputed orders (repeat disputer)
        for _ in range(spec.prior_disputes):
            at = order_at - timedelta(days=rng.randint(60, 300))
            poid, ptotal = self.order(cid, at, billing=billing, network=network)
            self.shipment(poid, at)
            self.system_messages(poid, at, ptotal)
            self._closed_dispute(poid, cid, at, ptotal)

        oid, total = self.order(
            cid, order_at, band=spec.amount_band, fixed_amount=spec.fixed_amount, billing=billing,
            ship_to_billing=spec.ship_to_billing, avs_cvv=spec.avs_cvv, ip=ip, device=dev,
            policy=spec.policy, listing=spec.listing, network=network,
        )
        if not spec.listing:
            self.conn.execute(
                "UPDATE products SET active=0 WHERE product_id=(SELECT product_id FROM order_items WHERE order_id=?)",
                (oid,))
        delivered_at = self.shipment(
            oid, order_at, tracked=spec.tracked, status=spec.ship_status, address_match=spec.address_match,
            signature=spec.signature, photo=spec.photo, dispatch_photo=spec.dispatch_photo)
        self.system_messages(oid, order_at, total)

        # dispute timing
        window_days = rule.response_deadline_days - decision_config()["processor"]["processor_buffer_days"]
        if spec.deadline == "normal":
            received = AS_OF - timedelta(days=rng.randint(1, 5), hours=rng.randint(0, 20))
            due = received + timedelta(days=window_days)
        elif spec.deadline == "near":
            due = AS_OF + timedelta(hours=rng.randint(18, 60))
            received = due - timedelta(days=window_days)
        elif spec.deadline == "passed":
            due = AS_OF - timedelta(hours=rng.randint(2, 30))
            received = due - timedelta(days=window_days)
        else:  # exact_hours
            due = AS_OF + timedelta(hours=spec.hours_remaining)
            received = due - timedelta(days=window_days)
        received = max(received, order_at + timedelta(days=8))

        # support messages, all before the dispute arrived
        base = (delivered_at or order_at + timedelta(days=6))
        t = lambda d: min(base + timedelta(hours=d), received - timedelta(hours=1))  # noqa: E731
        if spec.where_is_order:
            if delivered_at:  # asked while still in transit, before the delivery scan
                ask = delivered_at - timedelta(hours=10)
                self.message(oid, ask, "customer", "where_is_order_early")
            else:
                ask = order_at + timedelta(days=7)
                self.message(oid, ask, "customer", "where_is_order")
            self.message(oid, ask + timedelta(hours=3), "agent", "where_is_order_reply")
        if spec.customer_ack:
            self.message(oid, t(20), "customer", "customer_ack_receipt", tag="customer_ack_receipt")
        if spec.merchant_ack_nondelivery:
            self.message(oid, t(24), "customer", "not_received_complaint")
            self.message(oid, t(28), "agent", "merchant_ack_nondelivery", tag="merchant_ack_nondelivery")
        if spec.nad_complaint:
            self.message(oid, t(30), "customer", "nad_complaint")
        if spec.admitted_defect:
            self.message(oid, t(34), "agent", "merchant_admitted_defect", tag="merchant_admitted_defect")
        if spec.remedy:
            self.message(oid, t(36), "agent", "merchant_offered_remedy", tag="merchant_offered_remedy")
        if rng.random() < 0.15:
            self.message(oid, t(2), "customer", "general_question")

        if spec.return_status:
            req = t(48)
            self.insert("returns", return_id=self.ids.next("RET"), order_id=oid, requested_at=iso(req),
                        status="received" if spec.return_status == "received" else "label_sent",
                        received_at=iso(req + timedelta(days=6)) if spec.return_status == "received" else None)

        amount = total
        if spec.refund:
            frac = spec.refund_fraction or (1.0 if spec.refund == "full" else round(rng.uniform(0.2, 0.5), 2))
            r_amt = round(total * frac, 2)
            self.insert("refunds", refund_id=self.ids.next("RFD"), order_id=oid,
                        ts=iso(received - timedelta(days=rng.randint(2, 6))), amount=r_amt,
                        reason="full refund" if spec.refund == "full" else "partial refund - goodwill credit")
            if spec.refund == "partial_consistent":
                amount = round(total - r_amt, 2)

        has_msg = spec.issuer_message if spec.issuer_message is not None else rng.random() < 0.65
        needs_msg = network == "mastercard" and code == "4853"
        issuer_message = rng.choice(ISSUER_MSG[spec.category]) if (has_msg or needs_msg) else ""
        did = self.ids.next("DSP")
        dispute = dict(
            dispute_id=did, order_id=oid, customer_id=cid, network=network, reason_code=code,
            reason_category="general" if needs_msg else PROCESSOR_CATEGORY[spec.category],
            amount=amount, currency="USD", received_at=iso(received), response_due_at=iso(due),
            issuer_message=issuer_message, status="needs_response", closed_at=None,
        )
        self.insert("disputes", **dispute)
        webhook = {k: dispute[k] for k in ("dispute_id", "network", "reason_code", "reason_category", "order_id",
                                           "amount", "currency", "received_at", "response_due_at",
                                           "issuer_message")}
        return webhook


def build(db_path: Path | str, specs: list[Spec], seed: int = SEED,
          n_background: int = 300) -> list[tuple[Spec, dict]]:
    conn = init_db(db_path)
    b = Builder(conn, seed)
    b.build_catalog()
    b.build_background(n_background)
    out = [(spec, b.build_case(spec)) for spec in specs]
    conn.commit()
    conn.close()
    return out


def with_overrides(spec: Spec, **kw) -> Spec:
    return replace(spec, **kw)
