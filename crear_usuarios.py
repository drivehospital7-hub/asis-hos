"""Crear usuarios de ejemplo - standalone (sin Flask)."""

import sys
sys.path.insert(0, ".")

from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, UserArea, AREAS_VALIDAS
from app.utils.db_config import get_database_config


def crear_usuarios():
    """Crea los usuarios de ejemplo."""
    db_config = get_database_config()
    engine = create_engine(db_config.connection_string)
    
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # 1. Admin (acceso a todas las áreas)
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                rol="admin"
            )
            db.add(admin)
            print("✓ Usuario admin creado (password: admin123, rol: admin)")
        else:
            print("✓ Usuario admin ya existe")
        
        # 2. Usuario de Odontología
        odonto = db.query(User).filter(User.username == "odonto_user").first()
        if not odonto:
            odonto = User(
                username="odonto_user",
                password_hash=generate_password_hash("odonto123"),
                rol="usuario"
            )
            db.add(odonto)
            db.flush()
            
            # Agregar área odontologia
            db.add(UserArea(user_id=odonto.id, area="odontologia"))
            print("✓ Usuario odonto_user creado (password: odonto123, área: odontologia)")
        else:
            print("✓ Usuario odonto_user ya existe")
        
        # 3. Usuario de Urgencias
        urgencias = db.query(User).filter(User.username == "urgencias_user").first()
        if not urgencias:
            urgencias = User(
                username="urgencias_user",
                password_hash=generate_password_hash("urgencias123"),
                rol="usuario"
            )
            db.add(urgencias)
            db.flush()
            
            # Agregar área urgencias
            db.add(UserArea(user_id=urgencias.id, area="urgencias"))
            print("✓ Usuario urgencias_user creado (password: urgencias123, área: urgencias)")
        else:
            print("✓ Usuario urgencias_user ya existe")
        
        db.commit()
        print("\n🎉 Usuarios creados exitosamente!")
        print("\nCredenciales:")
        print("  admin / admin123     → acceso a todas las áreas")
        print("  odonto_user / odonto123   → solo odontologia")
        print("  urgencias_user / urgencias123 → solo urgencias")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("Creando usuarios de ejemplo...\n")
    crear_usuarios()