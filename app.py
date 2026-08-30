from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import engine, get_db
import modelos
import analitica

# Crear las tablas en la base de datos si no existen
modelos.Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Finanzas Personales")

# Configurar CORS (Crucial para que Vercel pueda hablar con Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiar por la URL de Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Agregar esto al final de app.py

@app.delete("/api/movimientos/{id_movimiento}")
def eliminar_movimiento(id_movimiento: int, db: Session = Depends(get_db)):
    # Buscar el movimiento en la base de datos
    movimiento = db.query(modelos.Movimiento).filter(modelos.Movimiento.id == id_movimiento).first()
    
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        
    db.delete(movimiento) # Eliminarlo
    db.commit() # Guardar cambios
    return {"mensaje": "Movimiento eliminado exitosamente"}

@app.put("/api/movimientos/{id_movimiento}")
def editar_movimiento(id_movimiento: int, mov_actualizado: modelos.MovimientoUpdate, db: Session = Depends(get_db)):
    movimiento = db.query(modelos.Movimiento).filter(modelos.Movimiento.id == id_movimiento).first()
    
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    # Actualizar solo los campos que el frontend nos haya enviado
    datos_nuevos = mov_actualizado.dict(exclude_unset=True)
    for clave, valor in datos_nuevos.items():
        setattr(movimiento, clave, valor)
        
    db.commit()
    db.refresh(movimiento)
    return {"mensaje": "Movimiento actualizado"}

@app.get("/api/analitica/tendencia")
def obtener_tendencia_api(id_usuario: int):
    # Usamos nuestra capa analítica para extraer y agrupar
    df = analitica.cargar_datos(engine, id_usuario)
    tendencia = analitica.obtener_tendencia(df)
    return tendencia