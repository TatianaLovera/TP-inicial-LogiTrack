import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

print("🤖 Iniciando entrenamiento de Machine Learning para LogiTrack...\n")

# 1. CREAR DATASET DE ENTRENAMIENTO (Simulado)
# ---------------------------------------------------------
np.random.seed(42)
cantidad_datos = 500

# Inventamos datos históricos
distancias_km = np.random.randint(10, 2000, cantidad_datos)
pesos_kg = np.random.uniform(0.5, 50.0, cantidad_datos)
es_express = np.random.choice([0, 1], cantidad_datos, p=[0.7, 0.3]) # 1 si es express, 0 si no

# Lógica de negocio simulada para la etiqueta (Target)
# Si es express o va muy lejos y pesa poco, es prioridad ALTA
prioridades = []
for i in range(cantidad_datos):
    if es_express[i] == 1:
        prioridades.append("Alta")
    elif distancias_km[i] > 1000 and pesos_kg[i] < 5:
        prioridades.append("Media")
    else:
        prioridades.append("Normal")

# Armamos el DataFrame (Tabla)
df = pd.DataFrame({
    'distancia_km': distancias_km,
    'peso_kg': pesos_kg,
    'es_express': es_express,
    'prioridad': prioridades
})

print(f"✅ Dataset generado con {cantidad_datos} registros históricos.")

# 2. SEPARAR DATOS Y ENTRENAR EL MODELO
# ---------------------------------------------------------
# X son las características, y es lo que queremos predecir
X = df[['distancia_km', 'peso_kg', 'es_express']]
y = df['prioridad']

# Separamos: 80% para entrenar la IA, 20% para tomarle examen (test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Elegimos el "Cerebro" (Random Forest Classifier)
modelo = RandomForestClassifier(n_estimators=100, random_state=42)

print("⏳ Entrenando el modelo RandomForest...")
modelo.fit(X_train, y_train)

# 3. TOMARLE EXAMEN A LA IA Y SACAR MÉTRICAS
# ---------------------------------------------------------
predicciones = modelo.predict(X_test)

precision_general = accuracy_score(y_test, predicciones)
print("\n📊 RESULTADOS Y MÉTRICAS DE PRECISIÓN:")
print("========================================")
print(f"🎯 Exactitud general (Accuracy): {precision_general * 100:.2f}%")
print("\nDesglose detallado (Classification Report):")
print(classification_report(y_test, predicciones))

# 4. GUARDAR EL CEREBRO PARA USARLO EN LA APP WEB
# ---------------------------------------------------------
if not os.path.exists('models'):
    os.makedirs('models')

joblib.dump(modelo, 'models/modelo_prioridad.pkl')
print("💾 Modelo guardado exitosamente en 'models/modelo_prioridad.pkl'.")
print("¡El modelo ya está listo para conectarse a app.py!")