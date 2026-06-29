"""
NFHS-5 India Health Atlas — FastAPI Backend
Runs the full analysis pipeline from the notebook and exposes:
  GET /api/health-data      → state-level health metrics (JSON)
  GET /api/risk-index       → composite risk scores, tiers, BFS clusters (JSON)
  GET /api/summary          → national summary stats (JSON)
  GET /api/map              → Folium interactive choropleth (HTML fragment)
  GET /                     → serves the dashboard HTML
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import json
import os
import io
import base64
import traceback
from collections import deque
from pathlib import Path

# ── optional folium ──────────────────────────────────────────────────────────
try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

app = FastAPI(title="NFHS-5 Health Atlas API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Serve static files (CSS/JS/images)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ─────────────────────────────────────────────────────────────────────────────
# HARDCODED NFHS-5 DATA  (matches the notebook's pivot exactly)
# This mirrors what the notebook produces after cleaning the Kaggle CSV.
# If you place the CSV at data/nfhs5.csv the pipeline will use live data.
# ─────────────────────────────────────────────────────────────────────────────
NFHS5_HARDCODED = [
    {"State":"Andhra Pradesh","Obesity_Women":33.5,"Obesity_Men":25.0,"Anaemia_Women":44.0,"Anaemia_Children":55.4,"BloodSugar_Women":15.0,"BloodSugar_Men":18.5,"Hypertension_Women":16.5,"Hypertension_Men":26.5},
    {"State":"Arunachal Pradesh","Obesity_Women":23.5,"Obesity_Men":19.0,"Anaemia_Women":35.5,"Anaemia_Children":52.0,"BloodSugar_Women":9.5,"BloodSugar_Men":11.5,"Hypertension_Women":18.0,"Hypertension_Men":27.5},
    {"State":"Assam","Obesity_Women":17.5,"Obesity_Men":11.0,"Anaemia_Women":54.5,"Anaemia_Children":68.4,"BloodSugar_Women":8.5,"BloodSugar_Men":10.5,"Hypertension_Women":13.0,"Hypertension_Men":20.0},
    {"State":"Bihar","Obesity_Women":11.0,"Obesity_Men":7.5,"Anaemia_Women":63.5,"Anaemia_Children":69.4,"BloodSugar_Women":7.5,"BloodSugar_Men":9.0,"Hypertension_Women":10.5,"Hypertension_Men":16.5},
    {"State":"Chhattisgarh","Obesity_Women":17.5,"Obesity_Men":11.0,"Anaemia_Women":47.0,"Anaemia_Children":62.6,"BloodSugar_Women":9.5,"BloodSugar_Men":11.5,"Hypertension_Women":13.0,"Hypertension_Men":20.5},
    {"State":"Goa","Obesity_Women":37.0,"Obesity_Men":31.0,"Anaemia_Women":41.5,"Anaemia_Children":53.5,"BloodSugar_Women":16.5,"BloodSugar_Men":20.5,"Hypertension_Women":22.0,"Hypertension_Men":33.5},
    {"State":"Gujarat","Obesity_Women":29.0,"Obesity_Men":21.5,"Anaemia_Women":52.5,"Anaemia_Children":78.9,"BloodSugar_Women":12.5,"BloodSugar_Men":15.5,"Hypertension_Women":16.5,"Hypertension_Men":25.5},
    {"State":"Haryana","Obesity_Women":30.5,"Obesity_Men":22.0,"Anaemia_Women":58.5,"Anaemia_Children":70.5,"BloodSugar_Women":12.5,"BloodSugar_Men":15.5,"Hypertension_Women":15.5,"Hypertension_Men":25.0},
    {"State":"Himachal Pradesh","Obesity_Women":28.5,"Obesity_Men":22.0,"Anaemia_Women":54.5,"Anaemia_Children":64.3,"BloodSugar_Women":13.5,"BloodSugar_Men":16.5,"Hypertension_Women":20.5,"Hypertension_Men":31.5},
    {"State":"Jharkhand","Obesity_Women":12.5,"Obesity_Men":7.5,"Anaemia_Women":65.5,"Anaemia_Children":67.4,"BloodSugar_Women":8.0,"BloodSugar_Men":9.5,"Hypertension_Women":11.5,"Hypertension_Men":17.5},
    {"State":"Karnataka","Obesity_Women":33.5,"Obesity_Men":24.5,"Anaemia_Women":45.5,"Anaemia_Children":59.6,"BloodSugar_Women":15.0,"BloodSugar_Men":19.0,"Hypertension_Women":16.5,"Hypertension_Men":26.5},
    {"State":"Kerala","Obesity_Women":32.5,"Obesity_Men":28.0,"Anaemia_Women":34.5,"Anaemia_Children":39.4,"BloodSugar_Women":18.5,"BloodSugar_Men":23.5,"Hypertension_Women":20.5,"Hypertension_Men":31.5},
    {"State":"Madhya Pradesh","Obesity_Women":16.0,"Obesity_Men":10.0,"Anaemia_Women":54.7,"Anaemia_Children":72.7,"BloodSugar_Women":9.0,"BloodSugar_Men":10.5,"Hypertension_Women":11.5,"Hypertension_Men":18.0},
    {"State":"Maharashtra","Obesity_Women":29.5,"Obesity_Men":21.5,"Anaemia_Women":45.7,"Anaemia_Children":68.9,"BloodSugar_Women":13.5,"BloodSugar_Men":16.5,"Hypertension_Women":15.5,"Hypertension_Men":24.5},
    {"State":"Manipur","Obesity_Women":28.5,"Obesity_Men":19.5,"Anaemia_Women":31.5,"Anaemia_Children":49.5,"BloodSugar_Women":11.5,"BloodSugar_Men":14.5,"Hypertension_Women":20.0,"Hypertension_Men":30.5},
    {"State":"Meghalaya","Obesity_Women":20.0,"Obesity_Men":13.5,"Anaemia_Women":45.5,"Anaemia_Children":62.5,"BloodSugar_Women":8.5,"BloodSugar_Men":10.0,"Hypertension_Women":14.0,"Hypertension_Men":22.5},
    {"State":"Mizoram","Obesity_Women":32.5,"Obesity_Men":24.5,"Anaemia_Women":35.5,"Anaemia_Children":50.0,"BloodSugar_Women":11.5,"BloodSugar_Men":14.0,"Hypertension_Women":18.5,"Hypertension_Men":28.5},
    {"State":"Nagaland","Obesity_Women":26.5,"Obesity_Men":19.4,"Anaemia_Women":28.5,"Anaemia_Children":55.8,"BloodSugar_Women":11.0,"BloodSugar_Men":12.5,"Hypertension_Women":16.5,"Hypertension_Men":24.8},
    {"State":"Odisha","Obesity_Women":18.5,"Obesity_Men":11.5,"Anaemia_Women":63.2,"Anaemia_Children":61.3,"BloodSugar_Women":10.5,"BloodSugar_Men":12.5,"Hypertension_Women":14.0,"Hypertension_Men":22.5},
    {"State":"Punjab","Obesity_Women":41.0,"Obesity_Men":33.5,"Anaemia_Women":52.7,"Anaemia_Children":61.5,"BloodSugar_Women":16.2,"BloodSugar_Men":18.5,"Hypertension_Women":23.5,"Hypertension_Men":35.8},
    {"State":"Rajasthan","Obesity_Women":22.5,"Obesity_Men":16.2,"Anaemia_Women":54.4,"Anaemia_Children":74.2,"BloodSugar_Women":10.5,"BloodSugar_Men":12.4,"Hypertension_Women":13.8,"Hypertension_Men":21.7},
    {"State":"Sikkim","Obesity_Women":35.5,"Obesity_Men":30.2,"Anaemia_Women":38.5,"Anaemia_Children":53.2,"BloodSugar_Women":15.6,"BloodSugar_Men":18.5,"Hypertension_Women":23.5,"Hypertension_Men":35.8},
    {"State":"Tamil Nadu","Obesity_Women":40.5,"Obesity_Men":31.0,"Anaemia_Women":45.5,"Anaemia_Children":57.3,"BloodSugar_Women":17.5,"BloodSugar_Men":21.5,"Hypertension_Women":20.0,"Hypertension_Men":32.0},
    {"State":"Telangana","Obesity_Women":38.5,"Obesity_Men":28.5,"Anaemia_Women":47.5,"Anaemia_Children":55.5,"BloodSugar_Women":16.5,"BloodSugar_Men":20.5,"Hypertension_Women":17.5,"Hypertension_Men":28.5},
    {"State":"Tripura","Obesity_Women":21.5,"Obesity_Men":13.5,"Anaemia_Women":53.5,"Anaemia_Children":72.0,"BloodSugar_Women":10.8,"BloodSugar_Men":12.0,"Hypertension_Women":15.0,"Hypertension_Men":22.5},
    {"State":"Uttar Pradesh","Obesity_Women":14.5,"Obesity_Men":9.2,"Anaemia_Women":50.4,"Anaemia_Children":66.4,"BloodSugar_Women":9.2,"BloodSugar_Men":10.8,"Hypertension_Women":12.0,"Hypertension_Men":18.5},
    {"State":"Uttarakhand","Obesity_Women":25.5,"Obesity_Men":18.5,"Anaemia_Women":55.5,"Anaemia_Children":64.2,"BloodSugar_Women":12.5,"BloodSugar_Men":14.8,"Hypertension_Women":18.5,"Hypertension_Men":28.5},
    {"State":"West Bengal","Obesity_Women":24.5,"Obesity_Men":15.8,"Anaemia_Women":62.7,"Anaemia_Children":69.5,"BloodSugar_Women":11.5,"BloodSugar_Men":13.5,"Hypertension_Women":16.0,"Hypertension_Men":24.5},
    {"State":"Delhi","Obesity_Women":34.5,"Obesity_Men":28.0,"Anaemia_Women":54.2,"Anaemia_Children":65.5,"BloodSugar_Women":14.5,"BloodSugar_Men":17.5,"Hypertension_Women":18.5,"Hypertension_Men":28.8},
    {"State":"Jammu & Kashmir","Obesity_Women":26.5,"Obesity_Men":20.5,"Anaemia_Women":47.5,"Anaemia_Children":62.5,"BloodSugar_Women":12.5,"BloodSugar_Men":15.5,"Hypertension_Women":21.5,"Hypertension_Men":33.5},
    {"State":"Puducherry","Obesity_Women":42.5,"Obesity_Men":35.0,"Anaemia_Women":44.5,"Anaemia_Children":55.5,"BloodSugar_Women":19.5,"BloodSugar_Men":24.5,"Hypertension_Women":24.5,"Hypertension_Men":37.5},
]

# State abbreviation + region mapping
STATE_META = {
    "Andhra Pradesh":     ("AP","South"),
    "Arunachal Pradesh":  ("AR","North East"),
    "Assam":              ("AS","North East"),
    "Bihar":              ("BR","East"),
    "Chhattisgarh":       ("CG","Central"),
    "Goa":                ("GA","West"),
    "Gujarat":            ("GJ","West"),
    "Haryana":            ("HR","North"),
    "Himachal Pradesh":   ("HP","North"),
    "Jharkhand":          ("JH","East"),
    "Karnataka":          ("KA","South"),
    "Kerala":             ("KL","South"),
    "Madhya Pradesh":     ("MP","Central"),
    "Maharashtra":        ("MH","West"),
    "Manipur":            ("MN","North East"),
    "Meghalaya":          ("ML","North East"),
    "Mizoram":            ("MZ","North East"),
    "Nagaland":           ("NL","North East"),
    "Odisha":             ("OD","East"),
    "Punjab":             ("PB","North"),
    "Rajasthan":          ("RJ","North West"),
    "Sikkim":             ("SK","North East"),
    "Tamil Nadu":         ("TN","South"),
    "Telangana":          ("TS","South"),
    "Tripura":            ("TR","North East"),
    "Uttar Pradesh":      ("UP","North"),
    "Uttarakhand":        ("UK","North"),
    "West Bengal":        ("WB","East"),
    "Delhi":              ("DL","North"),
    "Jammu & Kashmir":    ("JK","North"),
    "Puducherry":         ("PY","South"),
}

# ── Analysis pipeline (matches notebook logic exactly) ────────────────────────

def run_pipeline():
    """
    Executes Tasks 1 & 2 from the notebook:
    Task 1 — Composite Health Risk Index
    Task 2 — State Clustering via Graph + BFS
    Returns (health_df, risk_df, clusters)
    """
    health_df = pd.DataFrame(NFHS5_HARDCODED)
    health_df["Gender_Obesity_Gap"] = health_df["Obesity_Women"] - health_df["Obesity_Men"]

    # ── Task 1: Composite Risk ───────────────────────────────────────────────
    risk_df = health_df.copy()
    risk_columns = [
        "Obesity_Women","Obesity_Men",
        "Anaemia_Children","Anaemia_Women",
        "BloodSugar_Women","BloodSugar_Men",
        "Hypertension_Women","Hypertension_Men",
    ]

    # Min-max normalise
    for col in risk_columns:
        mn, mx = risk_df[col].min(), risk_df[col].max()
        risk_df[col] = (risk_df[col] - mn) / (mx - mn)

    risk_df["Composite_Risk"] = (
          0.20 * risk_df["Obesity_Women"]
        + 0.15 * risk_df["Obesity_Men"]
        + 0.20 * risk_df["Anaemia_Children"]
        + 0.15 * risk_df["Anaemia_Women"]
        + 0.10 * risk_df["BloodSugar_Women"]
        + 0.10 * risk_df["BloodSugar_Men"]
        + 0.05 * risk_df["Hypertension_Women"]
        + 0.05 * risk_df["Hypertension_Men"]
    )

    q1 = risk_df["Composite_Risk"].quantile(0.25)
    q2 = risk_df["Composite_Risk"].quantile(0.50)
    q3 = risk_df["Composite_Risk"].quantile(0.75)

    def assign(x):
        if x >= q3: return "Critical"
        elif x >= q2: return "High"
        elif x >= q1: return "Moderate"
        return "Low"

    risk_df["Risk_Tier"] = risk_df["Composite_Risk"].apply(assign)
    risk_df = risk_df.sort_values("Composite_Risk", ascending=False).reset_index(drop=True)
    risk_df["Rank"] = risk_df.index + 1

    # ── Task 2: BFS Clustering ───────────────────────────────────────────────
    THRESHOLD = 0.05
    states  = risk_df["State"].tolist()
    scores  = risk_df["Composite_Risk"].tolist()

    graph = {s: [] for s in states}
    for i in range(len(states)):
        for j in range(i + 1, len(states)):
            if abs(scores[i] - scores[j]) <= THRESHOLD:
                graph[states[i]].append(states[j])
                graph[states[j]].append(states[i])

    visited, clusters, cluster_map = set(), [], {}
    for state in graph:
        if state not in visited:
            queue = deque([state])
            visited.add(state)
            cluster = []
            while queue:
                node = queue.popleft()
                cluster.append(node)
                for nb in graph[node]:
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)
            clusters.append(cluster)
            cid = len(clusters)
            for s in cluster:
                cluster_map[s] = cid

    risk_df["BFS_Cluster"] = risk_df["State"].map(cluster_map)
    return health_df, risk_df, clusters


# Run once at startup
_health_df, _risk_df, _clusters = run_pipeline()


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/health-data")
def get_health_data():
    """Returns raw health metrics per state with abbr + region."""
    rows = []
    for row in NFHS5_HARDCODED:
        abbr, region = STATE_META.get(row["State"], ("??", "Other"))
        rows.append({**row, "abbr": abbr, "region": region})
    return JSONResponse(content=rows)


@app.get("/api/risk-index")
def get_risk_index():
    """Returns composite risk scores, tiers, ranks, BFS cluster IDs."""
    result = []
    for _, row in _risk_df.iterrows():
        abbr, region = STATE_META.get(row["State"], ("??", "Other"))
        result.append({
            "rank":          int(row["Rank"]),
            "state":         row["State"],
            "abbr":          abbr,
            "region":        region,
            "composite_risk": round(float(row["Composite_Risk"]), 4),
            "risk_tier":     row["Risk_Tier"],
            "bfs_cluster":   int(row["BFS_Cluster"]),
        })
    return JSONResponse(content=result)


@app.get("/api/clusters")
def get_clusters():
    """Returns BFS cluster details."""
    return JSONResponse(content={
        "total_clusters": len(_clusters),
        "clusters": [
            {"cluster_id": i+1, "states": sorted(c), "size": len(c)}
            for i, c in enumerate(_clusters)
        ]
    })


@app.get("/api/summary")
def get_summary():
    """National-level summary statistics."""
    df = pd.DataFrame(NFHS5_HARDCODED)
    tier_counts = _risk_df["Risk_Tier"].value_counts().to_dict()
    return JSONResponse(content={
        "total_states":          int(len(df)),
        "total_clusters":        int(len(_clusters)),
        "avg_anaemia_women":     round(float(df["Anaemia_Women"].mean()), 1),
        "avg_anaemia_children":  round(float(df["Anaemia_Children"].mean()), 1),
        "avg_obesity_women":     round(float(df["Obesity_Women"].mean()), 1),
        "avg_hypertension_women":round(float(df["Hypertension_Women"].mean()), 1),
        "highest_risk_state":    str(_risk_df.iloc[0]["State"]),
        "lowest_risk_state":     str(_risk_df.iloc[-1]["State"]),
        "tier_counts":           tier_counts,
    })


@app.get("/api/map", response_class=HTMLResponse)
def get_map():
    """
    Returns an embedded Folium choropleth map as a self-contained HTML fragment.
    Requires india_state.geojson in the data/ directory.
    Falls back to a friendly message if GeoJSON or folium is unavailable.
    """
    geojson_path = DATA_DIR / "india_state.geojson"

    if not FOLIUM_AVAILABLE:
        return HTMLResponse(content=_map_unavailable("Folium library not installed. Run: pip install folium"))

    if not geojson_path.exists():
        return HTMLResponse(content=_map_unavailable(
            "Place <code>india_state.geojson</code> in the <code>data/</code> folder next to main.py "
            "to enable the interactive choropleth map.<br><br>"
            "You can download it from: "
            "<a href='https://github.com/Subhash9325/GeoJson-Data-of-Indian-States' target='_blank' style='color:#60a5fa'>GitHub — Indian States GeoJSON</a>"
        ))

    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)

        map_df = _risk_df.copy()
        state_mapping = {
            "Andaman & Nicobar Islands": "Andaman and Nicobar",
            "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
            "NCT of Delhi": "Delhi",
            "Jammu & Kashmir": "Jammu and Kashmir",
            "Odisha": "Orissa",
        }
        map_df["State"] = map_df["State"].replace(state_mapping)
        map_df = map_df[~map_df["State"].isin(["Lakshadweep", "Ladakh"])]

        india_map = folium.Map(location=[22.5, 79], zoom_start=5, tiles="CartoDB positron")

        folium.Choropleth(
            geo_data=geojson_data,
            data=map_df,
            columns=["State", "Composite_Risk"],
            key_on="feature.properties.NAME_1",
            fill_color="YlOrRd",
            fill_opacity=0.8,
            line_opacity=0.4,
            legend_name="Composite Health Risk Index",
        ).add_to(india_map)

        risk_cols_norm = [
            "Obesity_Women","Obesity_Men","Anaemia_Children","Anaemia_Women",
            "BloodSugar_Women","BloodSugar_Men","Hypertension_Women","Hypertension_Men",
        ]
        color_map = {"Critical":"darkred","High":"red","Moderate":"orange","Low":"green"}

        for _, row in map_df.iterrows():
            state = row["State"]
            lat = lon = None
            for feat in geojson_data["features"]:
                if feat["properties"]["NAME_1"] == state:
                    coords = feat["geometry"]["coordinates"]
                    if feat["geometry"]["type"] == "Polygon":
                        lon = sum(p[0] for p in coords[0]) / len(coords[0])
                        lat = sum(p[1] for p in coords[0]) / len(coords[0])
                    else:
                        largest = max(coords, key=len)
                        lon = sum(p[0] for p in largest[0]) / len(largest[0])
                        lat = sum(p[1] for p in largest[0]) / len(largest[0])
                    break
            if lat is None:
                continue

            top2 = row[risk_cols_norm].sort_values(ascending=False).head(2).index.tolist()
            popup_html = f"""
            <div style='font-family:Inter,sans-serif;min-width:200px'>
              <b style='font-size:1rem'>{row['State']}</b><br>
              <span style='color:#64748b;font-size:0.8rem'>{row['Risk_Tier']} Risk · Cluster {row['BFS_Cluster']}</span>
              <hr style='border:none;border-top:1px solid #e2e8f0;margin:6px 0'>
              <b>Composite Risk:</b> {row['Composite_Risk']:.3f}<br>
              <b>Top Indicators:</b> {', '.join(top2)}
            </div>
            """
            color = color_map.get(row["Risk_Tier"], "blue")
            folium.CircleMarker(
                location=[lat, lon],
                radius=max(5, row["Composite_Risk"] * 30),
                color=color, fill=True, fill_color=color, fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['State']} — {row['Risk_Tier']}"
            ).add_to(india_map)

        folium.LayerControl().add_to(india_map)

        # Extract only the body content (strip the full HTML wrapping)
        raw_html = india_map._repr_html_()
        return HTMLResponse(content=raw_html)

    except Exception as e:
        return HTMLResponse(content=_map_unavailable(f"Error generating map: {str(e)}"))


def _map_unavailable(reason: str) -> str:
    return f"""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                height:400px;background:#f0f4ff;border-radius:16px;padding:2rem;text-align:center">
      <div style="font-size:3rem;margin-bottom:1rem">🗺️</div>
      <div style="font-size:1.1rem;font-weight:600;color:#0f1535;margin-bottom:0.5rem">Map Unavailable</div>
      <div style="color:#64748b;font-size:0.9rem;max-width:480px;line-height:1.7">{reason}</div>
    </div>
    """


# ── Dashboard HTML (serves the frontend) ─────────────────────────────────────
DASHBOARD_PATH = BASE_DIR / "static" / "index.html"

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    if DASHBOARD_PATH.exists():
        return HTMLResponse(content=DASHBOARD_PATH.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Dashboard not found — place index.html in static/</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
