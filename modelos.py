from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from database import Base
from pydantic import BaseModel
from typing import Optional
from datetime import date

# --- Modelos de Base de Datos (SQLAlchemy) ---
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)

class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    tipo = Column(String(20), nullable=False)

class Movimiento(Base):
    __tablename__ = "movimientos"
    id = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"))
    id_categoria = Column(Integer, ForeignKey("categorias.id"))
    tipo = Column(String(20), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    fecha = Column(Date, nullable=False)
    descripcion = Column(String)

# --- Esquemas de Validación (Pydantic) ---
class MovimientoCreate(BaseModel):
    id_usuario: int
    id_categoria: int
    tipo: str
    monto: float
    fecha: date
    descripcion: Optional[str] = None
    
# Agregar esto al final de modelos.py
class MovimientoUpdate(BaseModel):
    id_categoria: Optional[int] = None
    tipo: Optional[str] = None
    monto: Optional[float] = None
    fecha: Optional[date] = None
    descripcion: Optional[str] = None
    
    # Agregar al final de modelos.py
class UsuarioRegister(BaseModel):
    nombre: str
    email: str
    password: str

class UsuarioLogin(BaseModel):
    email: str
    password: str