"""Database models for Strawberry Supply Chain App"""
import os
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import bcrypt
import enum

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "strawberry.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Role(str, enum.Enum):
    OWNER = "owner"
    DRIVER = "driver"
    SORTER = "sorter"
    SALES = "sales"
    ADMIN = "admin"

class PickupStatus(str, enum.Enum):
    PENDING = "pending"
    RECEIVED = "received"
    CANCELLED = "cancelled"

class SaleStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class ShippingMethod(str, enum.Enum):
    GO_SEND = "GO SEND"
    PAXEL = "Paxel"
    KURIR_SENDIRI = "Kurir Sendiri"
    MOBIL_BOX = "Mobil Box Sewa"

class MovementType(str, enum.Enum):
    IN_SORTING = "in_sorting"
    OUT_SALE = "out_sale"
    ADJUSTMENT = "adjustment"
    IN_RETURN = "in_return"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default=Role.DRIVER.value)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    pickups = relationship("Pickup", back_populates="driver")
    sales = relationship("Sale", back_populates="created_by_user")

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    color = Column(String(20), default="#e11d48")
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    sorting_details = relationship("SortingDetail", back_populates="category")
    recipe_items = relationship("ProductRecipe", back_populates="category")
    movements = relationship("InventoryMovement", back_populates="category")

class Pickup(Base):
    __tablename__ = "pickups"
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    farm_name = Column(String(150), nullable=False)
    farm_location = Column(String(200))
    pickup_date = Column(Date, nullable=False, default=date.today)
    tray_count = Column(Integer, nullable=False)
    photo_path = Column(String(300))
    sj_number = Column(String(50), unique=True, nullable=False)
    notes = Column(Text)
    status = Column(String(20), default=PickupStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    driver = relationship("User", back_populates="pickups")
    receiving = relationship("Receiving", back_populates="pickup", uselist=False)

class Receiving(Base):
    __tablename__ = "receivings"
    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickups.id"), unique=True, nullable=False)
    total_kg = Column(Float, nullable=False)
    checked_by = Column(String(100))
    check_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    is_balanced = Column(Boolean, default=False)
    photo_path = Column(String(300))
    created_at = Column(DateTime, default=datetime.utcnow)
    pickup = relationship("Pickup", back_populates="receiving")
    sorting_details = relationship("SortingDetail", back_populates="receiving", cascade="all, delete-orphan")

class SortingDetail(Base):
    __tablename__ = "sorting_details"
    id = Column(Integer, primary_key=True, index=True)
    receiving_id = Column(Integer, ForeignKey("receivings.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    kg = Column(Float, nullable=False)
    percentage = Column(Float)
    receiving = relationship("Receiving", back_populates="sorting_details")
    category = relationship("Category", back_populates="sorting_details")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    movement_type = Column(String(20), nullable=False)
    qty_kg = Column(Float, nullable=False)
    ref_type = Column(String(30))
    ref_id = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100))
    category = relationship("Category", back_populates="movements")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    product_type = Column(String(20), default="pure")
    base_price = Column(Float, nullable=False, default=0.0)
    description = Column(Text)
    image_path = Column(String(300))
    approval_status = Column(String(20), default="approved")  # pending | approved | rejected
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    recipes = relationship("ProductRecipe", back_populates="product", cascade="all, delete-orphan")
    sale_items = relationship("SaleItem", back_populates="product")

class ProductRecipe(Base):
    __tablename__ = "product_recipes"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    ratio = Column(Float, nullable=False)
    product = relationship("Product", back_populates="recipes")
    category = relationship("Category", back_populates="recipe_items")

class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(30))
    address = Column(Text)
    notes = Column(Text)
    default_discount_pct = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sales = relationship("Sale", back_populates="customer")

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    sale_date = Column(Date, nullable=False, default=date.today)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    discount_pct = Column(Float, default=0.0)
    shipping_method = Column(String(50))
    shipping_cost = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default=SaleStatus.DRAFT.value)
    notes = Column(Text)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    shipped_at = Column(DateTime)
    customer = relationship("Customer", back_populates="sales")
    created_by_user = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")

class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    qty_kg = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    expense_date = Column(Date, nullable=False, default=date.today)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text)
    related_sale_id = Column(Integer, ForeignKey("sales.id"), nullable=True)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    key = Column(String(50), primary_key=True)
    value = Column(Text)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50))
    user_name = Column(String(100))
    role = Column(String(20))
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(Integer)
    summary = Column(Text, nullable=False)
    detail = Column(Text)

class ChangeRequest(Base):
    __tablename__ = "change_requests"
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    request_type = Column(String(30), nullable=False)
    payload = Column(Text)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="pending")
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    requested_by_name = Column(String(100))
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_by_name = Column(String(100))
    review_note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)

def get_db() -> Session:
    return SessionLocal()


def write_log(db: Session, user: dict, action: str, summary: str,
              entity_type: str = None, entity_id: int = None, detail: str = None):
    db.add(ActivityLog(
        user_id=(user or {}).get("id"),
        username=(user or {}).get("username"),
        user_name=(user or {}).get("name"),
        role=(user or {}).get("role"),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        detail=detail,
    ))

def verify_password(plain: str, hashed: str) -> bool:
    try:
        if not plain or not hashed:
            return False
        hashed_bytes = hashed.encode("utf-8") if isinstance(hashed, str) else hashed
        return bcrypt.checkpw(plain.encode("utf-8"), hashed_bytes)
    except Exception:
        return False

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

FARMS = ["RED HARVEST 1", "RED HARVEST 2"]
FARM_CODES = {
    "RED HARVEST 1": "RH1",
    "RED HARVEST 2": "RH2",
}

def farm_code(farm_name: str) -> str:
    return FARM_CODES.get(farm_name, "XX")

def make_sj_number(pickup_date: date, farm_name: str, seq: int = 1) -> str:
    """No. SJ = DD + MM + YYYY + KodeKebun (+ seq jika >1)."""
    base = f"{pickup_date.day:02d}{pickup_date.month:02d}{pickup_date.year}{farm_code(farm_name)}"
    return base if seq <= 1 else f"{base}-{seq:02d}"


def format_rp(amount) -> str:
    """Display: Rp. 37.000"""
    try:
        n = int(round(float(amount or 0)))
    except (TypeError, ValueError):
        n = 0
    return f"Rp. {n:,}".replace(",", ".")


def parse_rp(text) -> int:
    """Parse '37000' / '37.000' / 'Rp. 37.000' -> int."""
    if text is None:
        return 0
    s = str(text).strip().upper().replace("RP.", "").replace("RP", "").replace(" ", "")
    s = s.replace(".", "").replace(",", "")
    if not s:
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _migrate_sqlite_columns():
    """Add missing columns on existing SQLite tables."""
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    if "products" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("products")}
    alters = []
    if "image_path" not in existing:
        alters.append("ALTER TABLE products ADD COLUMN image_path VARCHAR(300)")
    if "approval_status" not in existing:
        alters.append("ALTER TABLE products ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'")
    if "created_by" not in existing:
        alters.append("ALTER TABLE products ADD COLUMN created_by VARCHAR(100)")
    if alters:
        with engine.begin() as conn:
            for sql in alters:
                conn.execute(text(sql))
            conn.execute(text(
                "UPDATE products SET approval_status = 'approved' "
                "WHERE approval_status IS NULL OR approval_status = ''"
            ))


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_columns()
    db = SessionLocal()
    try:
        if db.query(Category).count() == 0:
            cats = [
                Category(name="JUMBO", description="Ukuran jumbo premium", color="#e11d48", sort_order=1),
                Category(name="B", description="Ukuran B / medium bagus", color="#f59e0b", sort_order=2),
                Category(name="AB MIX", description="Campuran AB / grade lebih kecil", color="#10b981", sort_order=3),
            ]
            db.add_all(cats)
            db.commit()
        demo_users = [
            ("Owner Utama", "owner", "owner123", Role.OWNER.value),
            ("Driver 1", "driver1", "driver123", Role.DRIVER.value),
            ("Sorter 1", "sorter1", "sorter123", Role.SORTER.value),
            ("Sales 1", "sales1", "sales123", Role.SALES.value),
        ]
        if db.query(User).count() == 0:
            users = [
                User(name=name, username=username, password_hash=hash_password(password), role=role)
                for name, username, password, role in demo_users
            ]
            db.add_all(users)
            db.commit()
        else:
            for name, username, password, role in demo_users:
                user = db.query(User).filter(User.username == username).first()
                if user and not verify_password(password, user.password_hash):
                    user.password_hash = hash_password(password)
            db.commit()
        if db.query(Product).count() == 0:
            cats = db.query(Category).all()
            for c in cats:
                price = 45000.0 if c.name == "JUMBO" else (38000.0 if c.name == "B" else 32000.0)
                p = Product(name=f"Strawberry {c.name}", product_type="pure", base_price=price)
                db.add(p)
                db.flush()
                db.add(ProductRecipe(product_id=p.id, category_id=c.id, ratio=1.0))
            jumbo = db.query(Category).filter_by(name="JUMBO").first()
            ab = db.query(Category).filter_by(name="AB MIX").first()
            b = db.query(Category).filter_by(name="B").first()
            if jumbo and ab:
                p_mix = Product(name="Mix Jumbo 50% + AB 50%", product_type="mixed", base_price=38000.0)
                db.add(p_mix)
                db.flush()
                db.add(ProductRecipe(product_id=p_mix.id, category_id=jumbo.id, ratio=0.5))
                db.add(ProductRecipe(product_id=p_mix.id, category_id=ab.id, ratio=0.5))
            if jumbo and b and ab:
                p_mix2 = Product(name="Mix 1/3 Jumbo + 1/3 B + 1/3 AB", product_type="mixed", base_price=37000.0)
                db.add(p_mix2)
                db.flush()
                for cat, r in [(jumbo, 1/3), (b, 1/3), (ab, 1/3)]:
                    db.add(ProductRecipe(product_id=p_mix2.id, category_id=cat.id, ratio=r))
            db.commit()
        if db.query(Setting).count() == 0:
            db.add(Setting(key="company_name", value="Strawberry Fresh Supply"))
            db.add(Setting(key="tolerance_kg", value="0.15"))
            db.commit()
        if db.query(Pickup).count() == 0:
            driver = db.query(User).filter(User.username == "driver1").first()
            if driver:
                demo_pickups = [
                    ("RED HARVEST 1", date(2026, 7, 26), 24),
                    ("RED HARVEST 2", date(2026, 7, 27), 18),
                    ("RED HARVEST 1", date(2026, 7, 28), 30),
                    ("RED HARVEST 2", date(2026, 7, 29), 22),
                ]
                for farm, pdate, trays in demo_pickups:
                    sj = make_sj_number(pdate, farm, seq=1)
                    if db.query(Pickup).filter(Pickup.sj_number == sj).first():
                        continue
                    db.add(Pickup(
                        driver_id=driver.id,
                        farm_name=farm,
                        farm_location=None,
                        pickup_date=pdate,
                        tray_count=trays,
                        sj_number=sj,
                        notes="Data demo",
                        status=PickupStatus.PENDING.value,
                    ))
                db.commit()
    finally:
        db.close()

def get_current_stock(db: Session, category_id: int = None):
    q = db.query(InventoryMovement.category_id, func.sum(InventoryMovement.qty_kg).label("stock")).group_by(InventoryMovement.category_id)
    if category_id:
        q = q.filter(InventoryMovement.category_id == category_id)
    rows = q.all()
    result = {r.category_id: round(float(r.stock or 0), 2) for r in rows}
    if category_id:
        return result.get(category_id, 0.0)
    cats = db.query(Category).filter_by(is_active=True).all()
    return {c.id: result.get(c.id, 0.0) for c in cats}

def get_stock_by_name(db: Session) -> dict:
    stocks = get_current_stock(db)
    cats = {c.id: c.name for c in db.query(Category).all()}
    return {cats.get(cid, str(cid)): kg for cid, kg in stocks.items()}
