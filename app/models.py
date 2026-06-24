"""Modelos SQLAlchemy para notas técnicas y motor de reglas de auditoría."""

from sqlalchemy import (
    Column, Integer, String, Numeric, Text, Boolean,
    ForeignKey, UniqueConstraint, Table,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
    ide = Column(Integer, nullable=True)  # ID externo para vinculación
    
    # Relationships
    notas_tecnicas = relationship("NotasTecnicas", back_populates="procedimiento")
    
    def to_dict(self):
        return {
            "id": self.id,
            "cups": self.cups,
            "procedimiento": self.procedimiento,
            "ide": self.ide,
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
    tariff = Column("tariff", Numeric(12, 2), nullable=False)
    
    # Relationships
    procedimiento = relationship("Procedimiento", back_populates="notas_tecnicas")
    nota_hoja = relationship("NotaHoja", back_populates="notas_tecnicas")
    
    def to_dict(self):
        return {
            "id": self.id,
            "id_procedimiento": self.id_procedimiento,
            "id_nota_hoja": self.id_nota_hoja,
            "tariff": float(self.tariff)
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


# ═══════════════════════════════════════════════════════════════════════════
# Motor de Reglas de Auditoría — DB-Backed Rule Engine
# ═══════════════════════════════════════════════════════════════════════════


class Regla(Base):
    """Regla de auditoría versionada, parametric y domain-scoped.

    States: draft → active → deprecated → retired.
    Version grouping via rule_base_id: updates create a new version row
    sharing the same rule_base_id, linked by (nombre, version) uniqueness.
    """
    __tablename__ = "reglas"

    __table_args__ = (
        UniqueConstraint('nombre', 'version', name='uq_regla_nombre_version'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_base_id = Column(Integer, nullable=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text, nullable=True)
    dominio = Column(String(50), nullable=False)
    estado = Column(String(20), nullable=False, default="draft")
    version = Column(Integer, nullable=False, default=1)
    prioridad = Column(Integer, nullable=False, default=100)
    parametros = Column(JSONB, nullable=True)
    parametros_default = Column(JSONB, nullable=True)
    severidad = Column(String(20), nullable=False, default="error")
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    actualizado_en = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    # Relationships
    condiciones = relationship("Condicion", back_populates="regla")
    excepciones = relationship("Excepcion", back_populates="regla")
    evidencias = relationship("Evidencia", back_populates="regla")
    resultados = relationship("ResultadoAuditoria", back_populates="regla")

    def to_dict(self):
        return {
            "id": self.id,
            "rule_base_id": self.rule_base_id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "dominio": self.dominio,
            "estado": self.estado,
            "version": self.version,
            "prioridad": self.prioridad,
            "parametros": self.parametros,
            "parametros_default": self.parametros_default,
            "severidad": self.severidad,
            "activo": self.activo,
            "creado_en": str(self.creado_en) if self.creado_en else None,
            "actualizado_en": str(self.actualizado_en) if self.actualizado_en else None,
        }


class Condicion(Base):
    """Condición atómica o compuesta en un árbol de evaluación.

    Self-referencing tree: padre_id → NULL for root, FK to another condition.
    tipo: 'composite' (AND/OR/NOT) or 'atomic' (eq, gt, lt, etc.)
    """
    __tablename__ = "condiciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    regla_id = Column(Integer, ForeignKey("reglas.id"), nullable=False)
    padre_id = Column(Integer, ForeignKey("condiciones.id"), nullable=True)
    tipo = Column(String(10), nullable=False)
    operador = Column(String(20), nullable=True)
    fuente_datos = Column(String(100), nullable=True)
    valor_esperado = Column(JSONB, nullable=True)
    orden = Column(Integer, nullable=False, default=0)

    # Relationships
    regla = relationship("Regla", back_populates="condiciones")
    padre = relationship("Condicion", remote_side=[id], backref="hijos")

    def to_dict(self):
        return {
            "id": self.id,
            "regla_id": self.regla_id,
            "padre_id": self.padre_id,
            "tipo": self.tipo,
            "operador": self.operador,
            "fuente_datos": self.fuente_datos,
            "valor_esperado": self.valor_esperado,
            "orden": self.orden,
        }


class Excepcion(Base):
    """Excepción que suspende o modifica una regla para un scope específico.

    tipo_efecto: 'skip' (suspende), 'downgrade' (baja severidad), 'override' (modifica params).
    """
    __tablename__ = "excepciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    regla_id = Column(Integer, ForeignKey("reglas.id"), nullable=False)
    tipo_efecto = Column(String(20), nullable=False)
    condicion_json = Column(JSONB, nullable=False)
    parametros_override = Column(JSONB, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())
    expira_en = Column(TIMESTAMP(timezone=False), nullable=True)

    # Relationships
    regla = relationship("Regla", back_populates="excepciones")

    def to_dict(self):
        return {
            "id": self.id,
            "regla_id": self.regla_id,
            "tipo_efecto": self.tipo_efecto,
            "condicion_json": self.condicion_json,
            "parametros_override": self.parametros_override,
            "activo": self.activo,
            "creado_en": str(self.creado_en) if self.creado_en else None,
            "expira_en": str(self.expira_en) if self.expira_en else None,
        }


class ResultadoAuditoria(Base):
    """Resultado individual de la evaluación de una regla sobre una factura.

    Links to evidence snapshot via evidencia_id.
    """
    __tablename__ = "resultados_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evidencia_id = Column(Integer, ForeignKey("evidencias.id"), nullable=False)
    regla_id = Column(Integer, ForeignKey("reglas.id"), nullable=False)
    regla_version = Column(Integer, nullable=False)
    factura = Column(String(50), nullable=False)
    param_config_id = Column(Integer, nullable=True)
    resultado = Column(String(10), nullable=False)
    severidad = Column(String(20), nullable=False)
    mensaje = Column(Text, nullable=True)
    detalles = Column(JSONB, nullable=True)
    creado_en = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    # Relationships
    evidencia = relationship("Evidencia", back_populates="resultados")
    regla = relationship("Regla", back_populates="resultados")

    def to_dict(self):
        return {
            "id": self.id,
            "evidencia_id": self.evidencia_id,
            "regla_id": self.regla_id,
            "regla_version": self.regla_version,
            "factura": self.factura,
            "param_config_id": self.param_config_id,
            "resultado": self.resultado,
            "severidad": self.severidad,
            "mensaje": self.mensaje,
            "detalles": self.detalles,
            "creado_en": str(self.creado_en) if self.creado_en else None,
        }


class Evidencia(Base):
    """Evidencia inmutable de la evaluación de una regla sobre una fila.

    INSERT-ONLY: application-level guard against UPDATE/DELETE.
    """
    __tablename__ = "evidencias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    regla_id = Column(Integer, ForeignKey("reglas.id"), nullable=False)
    regla_version = Column(Integer, nullable=False)
    dominio = Column(String(50), nullable=False)
    factura = Column(String(50), nullable=False)
    param_config_id = Column(Integer, nullable=True)
    outcome = Column(String(10), nullable=False)
    arbol_evaluado = Column(JSONB, nullable=False)
    snapshot_fila = Column(JSONB, nullable=False)
    snapshot_referencia = Column(JSONB, nullable=True)
    error_mensaje = Column(Text, nullable=True)
    creado_en = Column(TIMESTAMP(timezone=False), nullable=False, server_default=func.now())

    # Relationships
    regla = relationship("Regla", back_populates="evidencias")
    resultados = relationship("ResultadoAuditoria", back_populates="evidencia")

    def to_dict(self):
        return {
            "id": self.id,
            "regla_id": self.regla_id,
            "regla_version": self.regla_version,
            "dominio": self.dominio,
            "factura": self.factura,
            "param_config_id": self.param_config_id,
            "outcome": self.outcome,
            "arbol_evaluado": self.arbol_evaluado,
            "snapshot_fila": self.snapshot_fila,
            "snapshot_referencia": self.snapshot_referencia,
            "error_mensaje": self.error_mensaje,
            "creado_en": str(self.creado_en) if self.creado_en else None,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Immutability Guards — Evidencia records are INSERT-ONLY
# ═══════════════════════════════════════════════════════════════════════════

from sqlalchemy import event


@event.listens_for(Evidencia, "before_update")
def _block_evidencia_update(mapper, connection, target):
    raise RuntimeError("Evidencia records are immutable. UPDATE is forbidden.")


@event.listens_for(Evidencia, "before_delete")
def _block_evidencia_delete(mapper, connection, target):
    raise RuntimeError("Evidencia records are immutable. DELETE is forbidden.")
