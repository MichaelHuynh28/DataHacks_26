# 🌊 Safe Harbor
### Marine Species Habitat Forecast — DataHacks 2026, UC San Diego
**Michael Lam Huynh & Andres Rodriguez · First-Year Data Science Students**

> Predicting where marine species will migrate as ocean temperatures rise off the coast of San Diego.

---

## The Problem
With Climate Change continuing to increase the temperature of the ocean, many marine species shift their ecological ranges.
Policymakers, conservationists, and fishermen all need to know where these species will move to.

---

## Our Solution
Safe Harbor combines real oceanographic buoy data with machine learning to forecast habitat shift for two San Diego coastal species:
- 🟠 **Garibaldi** 
- 🔵 **Leopard Shark**

---

## How It Works
**1. Oceanographic Data Pipeline**
- Processed 18 Argo float profiles from the EasyOneArgoTSLite dataset
- Extracted Sea Surface Temperature from CSV profiles using custom parser
- Computed thermal gradient ∇T via scipy interpolation + numpy gradient

**2. Species Sighting Data**
- Pulled Garibaldi and Leopard Shark sightings from iNaturalist
- Joined each sighting to nearest Argo SST measurement
- Built KDE density maps showing historical habitat hotspots

**3. Machine Learning — Random Forest Classifier**
- Features: latitude, longitude, month, SST
- Labels: Garibaldi / Leopard Shark / neither
- 200 trees, trained on real sightings + random negative samples
- Outputs habitat probability at every coastal point

**4. Climate Projection**
- Linear regression on historical SST to extract warming trend
- Bootstrap resampling (10,000 iterations) for 95% confidence interval
- Projects SST forward 6 months, 1 year, 2 years
- Feeds projected SST into trained RF to forecast habitat shift

---

## 📊 Key Results

| Metric | Value |
|--------|-------|
| Argo profiles processed | 18 |
| Garibaldi sightings | ~1,000+ |
| Leopard Shark sightings | ~1,000+ |
| SST warming trend | +0.002°C/year |
| Model features | lat, lon, month, SST |
| Forecast horizon | Up to 2 years |

---

## Technology Used
- **Python** — pandas, numpy, scipy, scikit-learn, matplotlib
- **Marimo** — reactive notebook environment
- **Cartopy** — geographic map rendering
- **Data Sources** — Argo GDAC (oceanography), iNaturalist (biology)

---

## Running the Project

```bash
git clone https://github.com/MichaelHuynh28/DataHacks_26
cd DataHacks_26
pip install pandas numpy scipy scikit-learn matplotlib marimo cartopy
marimo run safe_harbor.py
```

> **Note:** Argo float data files (~1.5GB) are not included in this repo.
> Download from [Argo GDAC](https://argo.ucsd.edu/data/data-from-gdac/)

---

## Future Work
- [ ] Integrate NOAA satellite SST for full coastal coverage
- [ ] Expand to California Gray Whale and Blue Whale
- [ ] Train/test split with proper accuracy metrics
- [ ] Deploy as interactive web application
- [ ] Extend coverage to full California coastline

---

## 📚 Data Sources
- [Argo Global Data Assembly Centre](https://argo.ucsd.edu/)
- [iNaturalist](https://www.inaturalist.org/)
- [EasyOneArgoTSLite Dataset](https://doi.org/10.17882/42182)

---

*Built in 36 hours at DataHacks 2026 · UC San Diego*
