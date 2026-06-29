from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)          # 'manager' | 'operator' | 'system'
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    routings = relationship("Routing", back_populates="product")
    work_orders = relationship("WorkOrder", back_populates="product")


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    sequence = Column(Integer, nullable=False)

    routings = relationship("Routing", back_populates="station")
    operations = relationship("Operation", back_populates="station")


class Routing(Base):
    __tablename__ = "routings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    sequence = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("product_id", "station_id"),
        UniqueConstraint("product_id", "sequence"),
    )

    product = relationship("Product", back_populates="routings")
    station = relationship("Station", back_populates="routings")


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(50), unique=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    qty_planned = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="planned")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    product = relationship("Product", back_populates="work_orders")
    operations = relationship("Operation", back_populates="work_order")
    production_logs = relationship("ProductionLog", back_populates="work_order")


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    started_by = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)

    __table_args__ = (UniqueConstraint("work_order_id", "station_id"),)

    work_order = relationship("WorkOrder", back_populates="operations")
    station = relationship("Station", back_populates="operations")
    production_logs = relationship("ProductionLog", back_populates="operation")


class ProductionLog(Base):
    __tablename__ = "production_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(Integer, ForeignKey("operations.id"), nullable=False)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False, default=1)
    qty_good = Column(Integer, nullable=False)
    qty_scrap = Column(Integer, nullable=False)
    logged_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source = Column(String(10), nullable=False)        # 'mqtt' | 'manual'
    is_anomaly = Column(Boolean, nullable=False, default=False)

    operation = relationship("Operation", back_populates="production_logs")
    work_order = relationship("WorkOrder", back_populates="production_logs")
