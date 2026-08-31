import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np

def cargar_datos(engine, id_usuario: int):
    # Extraemos los datos directamente a un DataFrame de Pandas
    query = f"""
        SELECT fecha, tipo, monto, id_categoria 
        FROM movimientos 
        WHERE id_usuario = {id_usuario}
    """
    df = pd.read_sql(query, engine)
    if df.empty:
        return df
    
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['mes'] = df['fecha'].dt.to_period('M')
    # Convertir decimales a float para cálculos
    df['monto'] = df['monto'].astype(float) 
    return df

def predecir_gasto(df):
    if df.empty:
        return 0.0

    gastos = df[df['tipo'] == 'gasto'].copy()
    if gastos.empty:
        return 0.0

    # Agrupar por mes
    resumen = gastos.groupby('mes')['monto'].sum().reset_index()
    
    # Manejo de excepción: Si hay menos de 3 meses, usar promedio simple
    if len(resumen) < 3:
        return round(resumen['monto'].mean(), 2)

    # Si hay 3 meses o más, usamos Regresión Lineal
    resumen['n_mes'] = range(len(resumen))
    X = resumen[['n_mes']]
    y = resumen['monto']

    modelo = LinearRegression()
    modelo.fit(X, y)

    # Predecir el mes siguiente (el índice actual + 1)
    siguiente_mes = pd.DataFrame({'n_mes': [len(resumen)]})
    prediccion = modelo.predict(siguiente_mes)[0]
    
    # Evitar predicciones negativas por fluctuaciones extrañas
    return round(max(0, prediccion), 2)

def detectar_anomalias(df, umbral_z=2):
    if df.empty:
        return []

    gastos = df[df['tipo'] == 'gasto'].copy()
    if gastos.empty:
        return []

    # Calcular media y desviación estándar por categoría
    stats = gastos.groupby('id_categoria')['monto'].agg(['mean', 'std']).reset_index()
    stats['std'] = stats['std'].fillna(0)
    
    gastos = gastos.merge(stats, on='id_categoria')
    
    anomalias_lista = []
    for _, row in gastos.iterrows():
        media = row['mean']
        monto = row['monto']
        std = row['std']
        
        # 1. Cálculo por Z-score tradicional
        es_anomalia_z = False
        if std > 0:
            z_score = abs((monto - media) / std)
            if z_score > umbral_z:
                es_anomalia_z = True
                
        # 2. Regla de respaldo infalible: Si el gasto supera el 250% del promedio de su categoría
        es_anomalia_proporcion = monto > (media * 2.5) and media > 0

        if es_anomalia_z or es_anomalia_proporcion:
            anomalias_lista.append({
                "fecha": row['fecha'].strftime('%Y-%m-%d'),
                "monto": float(monto),
                "id_categoria": int(row['id_categoria']),
                "z_score": float((monto - media) / std) if std > 0 else 5.0
            })
            
    return anomalias_lista

# Agregar esto al final de analitica.py
def obtener_tendencia(df):
    if df.empty:
        return {"meses": [], "ingresos": [], "gastos": []}
    
    # Agrupar por mes y tipo, sumando los montos
    tendencia = df.groupby(['mes', 'tipo'])['monto'].sum().unstack(fill_value=0).reset_index()
    
    # Asegurarnos de que existan las columnas de ingreso y gasto aunque un mes no tenga de ambos
    if 'ingreso' not in tendencia.columns: tendencia['ingreso'] = 0
    if 'gasto' not in tendencia.columns: tendencia['gasto'] = 0
    
    # Convertir a listas simples para que el frontend (Chart.js) las entienda fácil
    return {
        "meses": [str(mes) for mes in tendencia['mes']],
        "ingresos": tendencia['ingreso'].tolist(),
        "gastos": tendencia['gasto'].tolist()
    }