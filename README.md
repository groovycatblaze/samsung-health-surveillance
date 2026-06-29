# NFHS-5 Health Risk Analysis

An exploratory data analysis project based on the **National Family Health Survey (NFHS-5) 2019–21** dataset. The project examines state-wise health indicators, develops a composite health risk index, identifies similarities between states using graph traversal, and visualizes the results through statistical plots and choropleth maps.

---

## Dataset

**Source:** National Family Health Survey (NFHS-5), 2019–21

The analysis includes the following indicators:

- Women's obesity
- Men's obesity
- Women's anaemia
- Childhood anaemia
- Childhood stunting
- Childhood wasting

---

## Objectives

- Clean and preprocess NFHS-5 data
- Explore relationships between major health indicators
- Compare health outcomes across Indian states
- Compute a composite health risk score
- Identify groups of states with similar health profiles
- Visualize results geographically

---

## Methodology

### Data Preparation

- Imported the NFHS-5 dataset
- Selected relevant health indicators
- Removed missing and inconsistent values
- Standardized state names
- Normalized variables for comparison

### Exploratory Data Analysis

The notebook includes:

- Summary statistics
- Distribution analysis
- Correlation matrix
- State-wise comparisons
- Ranked visualizations

### Composite Health Risk Index

A composite score is calculated by combining normalized health indicators to compare the overall health risk of each state.

### Graph-Based State Clustering

States are represented as nodes in a graph. Edges connect states with similar health profiles based on a predefined similarity threshold. Breadth-First Search (BFS) is then used to identify connected groups of similar states.

### Geographic Visualization

Health indicators and composite scores are displayed using choropleth maps generated from GeoJSON state boundaries. Interactive visualizations are created with Folium.

---

## Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib
- Folium

---

## Repository Structure

```text
.
├── NFHS-5.ipynb
├── india_states.geojson
├── README.md
```

---

## Results

The project produces:

- State-wise comparison of health indicators
- Composite Health Risk Index
- Graph-based clustering of states
- Choropleth maps
- Interactive geographic visualizations

---

## Future Work

- District-level analysis
- Comparison across multiple NFHS survey rounds
- Inclusion of additional demographic and socioeconomic indicators
- Interactive dashboard deployment

---

## Author

**Team 7 — NumPies**

SRM Institute of Science and Technology
