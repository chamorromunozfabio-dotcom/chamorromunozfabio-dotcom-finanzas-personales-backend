from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import engine, get_db
import modelos
import analitica
import hashlib

# 1. PRIMERO SE CREA LA INSTANCIA DE FASTAPI
app = FastAPI(title="API Finanzas Personales")

# 2. SE CONFIGURA EL CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. CREAR LAS TABLAS EN LA BASE DE DATOS SI NO EXISTEN
modelos.Base.metadata.create_all(bind=engine)


# --- RUTAS DE AUTENTICACIÓN ---

@app.post("/api/registro")
def registrar_usuario(user: modelos.UsuarioRegister, db: Session = Depends(get_db)):
    # Verificar si el email ya existe
    existente = db.query(modelos.Usuario).filter(modelos.Usuario.email == user.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    # Cifrar contraseña de forma segura con SHA-256 nativo
    pass_hash = hashlib.sha256(user.password.encode()).hexdigest()
    
    nuevo_usuario = modelos.Usuario(
        nombre=user.nombre,
        email=user.email,
        password_hash=pass_hash
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return {"mensaje": "Usuario registrado exitosamente", "id_usuario": nuevo_usuario.id}

@app.post("/api/login")
def login_usuario(user: modelos.UsuarioLogin, db: Session = Depends(get_db)):
    pass_hash = hashlib.sha256(user.password.encode()).hexdigest()
    
    db_user = db.query(modelos.Usuario).filter(
        modelos.Usuario.email == user.email,
        modelos.Usuario.password_hash == pass_hash
    ).first()
    
    if not db_user:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
    return {"mensaje": "Login exitoso", "id_usuario": db_user.id, "nombre": db_user.nombre}


# --- RUTAS DE MOVIMIENTOS Y ANALÍTICA ---

@app.post("/api/movimientos")
def crear_movimiento(mov: modelos.MovimientoCreate, db: Session = Depends(get_db)):
    nuevo = modelos.Movimiento(**mov.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"mensaje": "Movimiento registrado", "id": nuevo.id}

@app.get("/api/movimientos")
def listar_movimientos(id_usuario: int, db: Session = Depends(get_db)):
    movimientos = db.query(modelos.Movimiento).filter(modelos.Movimiento.id_usuario == id_usuario).all()
    return movimientos

@app.get("/api/resumen")
def obtener_resumen(id_usuario: int, db: Session = Depends(get_db)):
    ingresos = db.query(func.sum(modelos.Movimiento.monto)).filter(
        modelos.Movimiento.id_usuario == id_usuario, 
        modelos.Movimiento.tipo == "ingreso"
    ).scalar() or 0

    gastos = db.query(func.sum(modelos.Movimiento.monto)).filter(
        modelos.Movimiento.id_usuario == id_usuario, 
        modelos.Movimiento.tipo == "gasto"
    ).scalar() or 0

    return {
        "total_ingresos": float(ingresos),
        "total_gastos": float(gastos),
        "balance": float(ingresos - gastos)
    }

@app.get("/api/analitica/prediccion")
def obtener_prediccion(id_usuario: int):
    df = analitica.cargar_datos(engine, id_usuario)
    if df.empty:
        return {"prediccion_proximo_mes": 0, "mensaje": "Sin datos"}
    
    prediccion = analitica.predecir_gasto(df)
    metodo = "promedio_simple" if len(df['mes'].unique()) < 3 else "regresion_lineal"
    
    return {
        "id_usuario": id_usuario,
        "prediccion_proximo_mes": prediccion,
        "metodo": metodo
    }

@app.get("/api/analitica/anomalias")
def obtener_anomalias(id_usuario: int):
    df = analitica.cargar_datos(engine, id_usuario)
    anomalias = analitica.detectar_anomalias(df)
    return {"id_usuario": id_usuario, "anomalias_detectadas": anomalias}

@app.delete("/api/movimientos/{id_movimiento}")
def eliminar_movimiento(id_movimiento: int, db: Session = Depends(get_db)):
    movimiento = db.query(modelos.Movimiento).filter(modelos.Movimiento.id == id_movimiento).first()
    
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        
    db.delete(movimiento)
    db.commit()
    return {"mensaje": "Movimiento eliminado exitosamente"}

@app.put("/api/movimientos/{id_movimiento}")
def editar_movimiento(id_movimiento: int, mov_actualizado: modelos.MovimientoUpdate, db: Session = Depends(get_db)):
    movimiento = db.query(modelos.Movimiento).filter(modelos.Movimiento.id == id_movimiento).first()
    
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    datos_nuevos = mov_actualizado.dict(exclude_unset=True)
    for clave, valor in datos_nuevos.items():
        setattr(movimiento, clave, valor)
        
    db.commit()
    db.refresh(movimiento)
    return {"mensaje": "Movimiento actualizado"}

@app.get("/api/analitica/tendencia")
def obtener_tendencia_api(id_usuario: int):
    df = analitica.cargar_datos(engine, id_usuario)
    tendencia = analitica.obtener_tendencia(df)
    return tendencia