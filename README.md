# cianogym

Personal training analytics dashboard built with Streamlit. Visualises workout history exported from the training app "Hevy", providing insights on exercise progression, muscle volume, weekly load, mesocycles and cardio.

## Pages

### 📈 Exercise
Track progression for any individual exercise over time. Filter by muscle group and exercise using the two dropdowns. Four KPI cards show estimated 1RM, max weight lifted, volume per set and volume per session. Below the cards, three line charts display the evolution of each metric session by session. At the bottom, a bar chart compares all exercises in the selected muscle group side by side so you can see which movements you are strongest in.

### 💪 Muscle
Analyse training volume by muscle group. Select a muscle from the dropdown to see four KPIs: average weekly sets, average weekly volume, number of distinct exercises and total sessions. The main chart overlays weekly volume (bars) and effective sets (line) over time. Two horizontal bar charts below compare all muscle groups: one for direct sets per week and one for effective sets per week (which accounts for indirect stimulus from compound movements).

### 📅 Sessions
Overview of weekly training load across the full history. Four KPI cards show total sessions, average weekly duration, average weekly volume and average weekly sets. Five stacked line charts — one per metric — display the week-by-week evolution of duration, sets, volume, reps and distinct exercises. Each chart includes a 4-week moving average trend line to smooth out noise.

### 🏆 Mesocycle
Compare training blocks against each other. The page auto-detects mesocycles from session titles: sessions following the pattern `wN` (e.g. "Upper w3") are assigned to Meso 1, and sessions following `wNmM` (e.g. "Upper w1m2") are assigned to the corresponding meso. Select a muscle group, exercise and metric (Est. 1RM / Max weight / Volume per set) to see a line chart with one line per mesocycle showing how that metric evolved week by week within each block. A summary table shows the peak value per exercise per mesocycle and overall progression from first to latest meso.

### 🏃 Cardio
Dedicated view for running and cardio sessions, fully separated from strength data. Four KPI cards show total runs, total distance, best pace and average pace. Three charts are displayed: a dual-axis line chart with distance and pace per session (pace axis is inverted — lower is better) including a 4-session moving average for pace, a bar chart with distance per session, and a bar chart with total distance per calendar month.

## Requirements

- Python 3.9+
- Dependencies listed in `requirements.txt`

## Setup

```bash
# Clone the repo
git clone https://github.com/markciano/cyanogym.git
cd cyanogym

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Data

The app expects two CSV files placed in the project root:

| File | Description | Place |
|------|-------------|-------|
| `workouts.csv` | Raw export from your training app — one row per set | root/data |
| `ejercicios_mapping.csv` | Exercise → muscle group and movement pattern mapping | root/data/mappings |
| `musculos_secundarios.csv` | Affected muscles when principal muscle is exercised | root/data/mappings |

workouts.csv is not included in the repo.

## Running the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Claude Code

This project was built with [Claude Code](https://claude.ai/code). The `.claude/` folder contains project context and custom commands used during development. It is intentionally included in the repo so the full development context is available when resuming work from any machine.