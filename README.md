# nfhs-5 health risk surveillance

state-level health risk analysis across india using nfhs-5 (2019–21) data. computes a composite risk index, clusters states via bfs graph traversal, and serves everything through a fastapi backend with an interactive choropleth dashboard.

---

## what it does

takes health indicators such as women's obesity, men's obesity, women's anaemia, childhood anaemia, childhood stunting, and childhood wasting, across 31 indian states and runs them through:

1. **min-max normalisation** across all indicators
2. **weighted composite scoring** to produce a single composite health risk index (chri) per state
3. **bfs graph clustering** — states within 0.05 chri of each other get connected as nodes; bfs finds the connected components
4. **quartile-based tier labelling** — low / moderate / high / critical
5. a **fastapi backend** serving all of this as json, plus a folium choropleth map as an html fragment

---

## stack

- python 3, fastapi, uvicorn
- pandas, numpy
- folium
- geojson for india state boundaries

---

## quickstart

```bash
git clone https://github.com/groovycatblaze/samsung-health-surveillance
cd samsung-health-surveillance
pip install -r requirements.txt
uvicorn main:app --reload
```

open `http://localhost:8000`. the dashboard is served from `static/index.html`.

for the interactive map, drop `india_state.geojson` into the `data/` folder. you can grab it from [this repo](https://github.com/Subhash9325/GeoJson-Data-of-Indian-States). without it, the `/api/map` endpoint returns a friendly fallback message instead of crashing.

---

## api endpoints

| endpoint | returns |
|---|---|
| `GET /api/health-data` | raw state metrics + region labels |
| `GET /api/risk-index` | chri scores, risk tiers, bfs cluster ids |
| `GET /api/clusters` | all bfs clusters as grouped state lists |
| `GET /api/summary` | national averages + tier distribution |
| `GET /api/map` | folium choropleth as embeddable html |

---

## repo structure

```
├── main.py                        # fastapi app + full analysis pipeline
├── NFHS-5.ipynb                   # original analysis notebook
├── cleaned_nfhs5.csv              # preprocessed dataset
├── Composite_Health_Risk_Index.csv
├── data/
│   └── india_state.geojson        # (add manually — see quickstart)
├── static/
│   └── index.html                 # dashboard frontend
└── requirements.txt
```

---

## key findings

- **punjab and puducherry** rank critical; high obesity and hypertension co-occurring
- **bihar, jharkhand, mp** score poorly on anaemia despite lower obesity, a separate health burden entirely
- **manipur and nagaland** are the only two states in the low tier
- bfs clustering groups most northern states together and isolates a high-obesity southern cluster

---

## dataset

national family health survey (nfhs-5), 2019–21. the app ships with the cleaned data hardcoded in `main.py` so it runs without any external files. point it at a live csv by placing `nfhs5.csv` in `data/` and the pipeline picks it up automatically.
