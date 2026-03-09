# CLAUDE.md — cianogym / lab_v2_gym

## COMPORTAMIENTO OBLIGATORIO

- Antes de crear, modificar o borrar cualquier fichero, explica qué vas a hacer y espera confirmación explícita ("sí", "adelante", "ok").
- Antes de ejecutar cualquier comando en terminal, explica qué hace y espera confirmación.
- Trabaja un paso a la vez. No encadenes múltiples acciones sin confirmación entre ellas.
- Si tienes dudas sobre cómo implementar algo, pregunta antes de escribir código.
- No instales dependencias sin confirmación explícita.
- No hagas commits ni toques Git sin que se te pida explícitamente.
- Si algo falla, explica el error en lenguaje claro antes de proponer solución.
- Nunca modifiques ficheros dentro de `data/` — son datos de entrada, solo lectura.

---

## DESCRIPCIÓN DEL PROYECTO

Dashboard de análisis de entrenamientos personales construido con Streamlit. Los datos provienen de la app Hevy, exportados como CSV. El objetivo es visualizar el progreso de entrenamientos de fuerza y cardio a lo largo del tiempo, con múltiples dimensiones de análisis.

---

## STACK

- **Python 3.11+**
- **Streamlit** — framework del dashboard
- **Pandas** — manipulación y transformación de datos
- **NumPy** — cálculos numéricos
- **Plotly** — visualizaciones interactivas
- **Entorno virtual** — `venv` local en la raíz del proyecto

---

## ESTRUCTURA DE CARPETAS

```
lab_v2_gym/
│
├── data/
│   ├── workouts.csv                  # CSV exportado de Hevy — NO MODIFICAR
│   └── mappings/
│       ├── ejercicios_mapping.csv    # ejercicio → músculo principal, patrón
│       └── musculos_secundarios.csv  # ejercicio → músculos secundarios
│
├── src/
│   ├── loader.py        # carga y limpieza del CSV
│   ├── metrics.py       # cálculos: RMs, volumen, fatiga
│   ├── mappings.py      # carga y aplicación de mappings
│   └── filters.py       # lógica de filtros temporales
│
├── pages/
│   ├── 01_ejercicio.py
│   ├── 02_musculo.py
│   ├── 03_patron.py
│   ├── 04_sesion.py
│   ├── 05_fatiga.py
│   ├── 06_mesociclo.py
│   └── 07_cardio.py
│
├── app.py               # entrada principal de Streamlit
├── CLAUDE.md            # este fichero
├── requirements.txt     # dependencias del proyecto
└── README.md
```

---

## DATOS — ESTRUCTURA DEL CSV

Fichero: `data/workouts.csv`
Exportado de: Hevy (app de registro de entrenamientos)
Cada fila es una **serie** dentro de un ejercicio dentro de una sesión.

### Columnas

| columna | tipo | descripción |
|---|---|---|
| `title` | string | Nombre de la sesión (ej: "Upper w4", "Run 🏃🏾") |
| `start_time` | string | Fecha y hora de inicio (ej: "6 Mar 2026, 11:01") |
| `end_time` | string | Fecha y hora de fin |
| `description` | string | Notas generales (casi siempre vacío) |
| `exercise_title` | string | Nombre del ejercicio en inglés |
| `superset_id` | float | ID de superset (siempre vacío, ignorar) |
| `exercise_notes` | string | Notas del ejercicio (casi siempre vacío) |
| `set_index` | int | Índice de la serie — **empieza en 0** |
| `set_type` | string | Tipo: `normal`, `warmup`, `dropset` |
| `weight_kg` | float | Peso en kg (vacío en cardio) |
| `reps` | float | Repeticiones (vacío en cardio) |
| `distance_km` | float | Distancia en km (solo cardio) |
| `duration_seconds` | float | Duración en segundos |
| `rpe` | float | Esfuerzo percibido 1-10 (muy poco registrado) |

### Reglas importantes
- Una **sesión** se identifica por `start_time` único (fecha + hora)
- Nunca hay dos sesiones con el mismo `start_time`
- Las series de tipo `warmup` se excluyen de los cálculos de progreso y volumen
- Las semanas se identifican por el patrón `wN` en el título (ej: "Upper w4" = semana 4 del Meso 1)
- Los mesociclos se identifican así:
  - Meso 1: títulos con solo `wN` sin sufijo de meso (ej: "Upper w3", "Lower w1")
  - Meso 2+: títulos con `wNmM` donde N=semana y M=número de meso (ej: "Upper w1m2" = semana 1 del Meso 2)
  - Si no hay patrón `wN` ni `wNmM`, la sesión no pertenece a ningún mesociclo estructurado
- Sesiones de cardio puro: `title` contiene "Run" o emojis de correr
- Cardio dentro de fuerza: ejercicios como Treadmill, Elliptical Trainer dentro de sesiones de fuerza

---

## MAPPINGS

### ejercicios_mapping.csv
Columnas: `exercise_title`, `nombre_es`, `musculo_principal`, `patron`

Patrones definidos:
- Empuje horizontal
- Empuje vertical arriba
- Empuje vertical abajo
- Tirón vertical
- Tirón horizontal
- Bisagra de cadera
- Pierna
- Curl
- Core
- Cardio
- Movilidad

### musculos_secundarios.csv
Columnas: `exercise_title`, `musculo_secundario`
Un ejercicio puede tener múltiples músculos secundarios (una fila por músculo secundario).

---

## DIMENSIONES DEL DASHBOARD

### 1. Ejercicio
- KPIs: 1RM estimado, peso máximo, volumen por serie (peso × reps), volumen por sesión
- Variación de KPIs adaptada al periodo temporal seleccionado: si filtro = 1 semana → variación vs semana anterior; 1 mes → vs mes anterior; Todo → vs inicio
- Fórmula Epley para RMs: `peso × (1 + reps / 30)` — se calculan 1RM a 10RM
- Gráfico de línea con peso máximo, volumen por serie y 1RM — seleccionables individualmente — vinculado al filtro temporal
- Filtro de ejercicio con ejercicios agrupados y ordenados por músculo principal (optgroup)
- Ventanas temporales: Todo, 1 año, YTD, 6 meses, 3 meses, 1 mes, 2 semanas, 1 semana
- Gráfico de barras inferior: comparativa de todos los ejercicios mostrando el valor total del KPI seleccionado (1RM / peso máx / vol/serie) — vinculado al filtro temporal activo

### 2. Músculo
- KPIs: series efectivas/semana (directas × 1.0 + indirectas × 0.5), volumen/semana (kg), ejercicios distintos, sesiones — todos referidos al periodo temporal seleccionado, con delta vs periodo anterior
- Series/volumen incluyen ejercicios donde el músculo es principal Y secundario (factor ×0.5 solo para contar series, volumen a valor completo en ambos casos)
- Filtros: músculo individual, ventanas temporales idénticas a Ejercicio
- Gráfico de progreso: barras (volumen semanal, eje izq) + línea (series efectivas/semana, eje der), agrupado por semana ISO
- Gráfico comparativo inferior: barras horizontales con todos los músculos por volumen semanal medio en el periodo, músculo seleccionado en azul — aislado con @st.fragment

### 3. Sesión
- Unidad de análisis: semana ISO (no sesiones individuales)
- KPIs (4 tarjetas): sesiones totales en el periodo, duración semanal media (min), volumen semanal medio (kg), series semanales medias — todos con delta vs periodo anterior
- 5 gráficos de línea apilados verticalmente (ancho completo), vinculados al filtro temporal:
  1. Duration / week (min)
  2. Sets / week
  3. Volume / week (kg)
  4. Reps / week
  5. Distinct exercises / week
- Cada gráfico incluye media móvil de 4 semanas (línea punteada, misma paleta, opacidad 0.45)
- Eje X compartido: fecha del lunes de cada semana, formato DD MMM YY
- Sets/volumen/reps calculados solo sobre series normales+dropset (warmup excluido); sesiones y duración sobre todas las sesiones
- Filtro temporal idéntico al resto de páginas (key: ses_window)


### 4. Mesociclo
- Comparativa entre mesociclos (no dentro del mesociclo)
- Métricas por ejercicio y mesociclo: máximo de peso, volumen por serie y 1RM estimado
- Detección automática de mesociclos:
  - Meso 1: sesiones con patrón `wN` sin sufijo de meso (ej: "Upper w3", "Lower w1")
  - Meso 2+: sesiones con patrón `wNmM` (ej: "Upper w1m2" = semana 1 del Meso 2)
  - Sesiones sin este patrón no se asignan a ningún mesociclo
- Si ninguna sesión del fichero contiene el patrón `wN` o `wNmM`, la pestaña Mesociclo mostrará un mensaje informativo y no generará ningún gráfico ni tabla.

### 5. Cardio
- Separado completamente de fuerza
- Los ejercicios se llaman Run y un emoji en el fichero workouts
- Progreso en pace (min/km)
- Distancia acumulada por mes
- Ventanas temporales: Todo, 1 año, YTD, 6 meses, 3 meses, 1 mes, 2 semanas, 1 semana

---

## CONVENCIONES DE CÓDIGO

- Nombres de variables y funciones en **snake_case**
- Nombres de ficheros en **snake_case**
- Comentarios en **inglés**
- Docstrings en todas las funciones de `src/`
- Las series de tipo `warmup` se filtran antes de cualquier cálculo de progreso
- Las fechas se parsean con `pd.to_datetime` con el formato `%d %b %Y, %H:%M`

---

## COMANDOS ÚTILES

```bash
# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Arrancar el dashboard
streamlit run app.py

# Ver logs de Streamlit
streamlit run app.py --logger.level=debug
```

---

## ORDEN DE DESARROLLO SUGERIDO

1. Crear entorno virtual e instalar dependencias
2. Implementar `src/loader.py` — carga y limpieza del CSV
3. Implementar `src/mappings.py` — carga de mappings
4. Implementar `src/metrics.py` — cálculos de RMs y volumen
5. Implementar `src/filters.py` — filtros temporales
6. Construir `app.py` — estructura base de Streamlit
7. Construir páginas en orden: 01_ejercicio → 02_musculo → 03_patron → 04_sesion → 05_fatiga → 06_mesociclo → 07_cardio

---

## LO QUE NO DEBES HACER

- No modificar ficheros en `data/`
- No hacer commits sin que se pida explícitamente
- No instalar paquetes fuera de los definidos en `requirements.txt` sin confirmación
- No encadenar más de una acción sin confirmación
- No asumir que algo funciona sin ejecutarlo y verificar el output
