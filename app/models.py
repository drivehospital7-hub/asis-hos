"""Modelos SQLAlchemy para notas técnicas."""

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class EpsContratado(Base):
    """EPS contratadas para servicios."""
    __tablename__ = "eps_contratado"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cod_contrato = Column(String, unique=True, nullable=False)
    eps = Column(String, nullable=False)
    regimen = Column(String, nullable=False, default="SUBSIDIADO")
    
    # Relationships
    eps_notas = relationship("EpsNota", back_populates="eps_contratado")
    
    def to_dict(self):
        return {
            "id": self.id,
            "cod_contrato": self.cod_contrato,
            "eps": self.eps,
            "regimen": self.regimen
        }


class Procedimiento(Base):
    """Catálogo de procedimientos CUPs."""
    __tablename__ = "procedimiento"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cups = Column(String, unique=True, nullable=False)
    procedimiento = Column(String, nullable=False)
    
    # Relationships
    notas_tecnicas = relationship("NotasTecnicas", back_populates="procedimiento")
    
    def to_dict(self):
        return {
            "id": self.id,
            "cups": self.cups,
            "procedimiento": self.procedimiento
        }


class NotaHoja(Base):
    """Catálogo de notas técnicas (hojas)."""
    __tablename__ = "nota_hoja"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nota = Column(String, nullable=False)
    
    # Relationships
    notas_tecnicas = relationship("NotasTecnicas", back_populates="nota_hoja")
    eps_notas = relationship("EpsNota", back_populates="nota_hoja")
    
    def to_dict(self):
        return {
            "id": self.id,
            "nota": self.nota
        }


class NotasTecnicas(Base):
    """Notas técnicas con tarifas por procedimiento y hoja."""
    __tablename__ = "notas_tecnicas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_procedimiento = Column(Integer, ForeignKey("procedimiento.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False)
    id_nota_hoja = Column(Integer, ForeignKey("nota_hoja.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False)
    tarifa = Column(Numeric(12, 2), nullable=False)
    
    # Relationships
    procedimiento = relationship("Procedimiento", back_populates="notas_tecnicas")
    nota_hoja = relationship("NotaHoja", back_populates="notas_tecnicas")
    
    def to_dict(self):
        return {
            "id": self.id,
            "id_procedimiento": self.id_procedimiento,
            "id_nota_hoja": self.id_nota_hoja,
            "tarifa": float(self.tarifa)
        }


class EpsNota(Base):
    """Relación muchos a muchos entre EPS y Notas."""
    __tablename__ = "eps_nota"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_nota_hoja = Column(Integer, ForeignKey("nota_hoja.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False)
    id_eps_contratado = Column(Integer, ForeignKey("eps_contratado.id", ondelete="NO ACTION", onupdate="NO ACTION"), nullable=False)
    
    # Relationships
    nota_hoja = relationship("NotaHoja", back_populates="eps_notas")
    eps_contratado = relationship("EpsContratado", back_populates="eps_notas")
    
    def to_dict(self):
        return {
            "id": self.id,
            "id_nota_hoja": self.id_nota_hoja,
            "id_eps_contratado": self.id_eps_contratado
        }
