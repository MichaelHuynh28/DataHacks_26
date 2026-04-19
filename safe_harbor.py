import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    # ── CELL 1: Load index CSV ────────────────────────────────────────────────────
    import pandas as pd
    import marimo as mo
    import os

    index_file = 'EasyOneArgoTSLite_index.csv'
    index_df = pd.read_csv(index_file, comment='#')
    index_df.columns = index_df.columns.str.strip()

    mo.vstack([
        mo.md(f"## 🛠️ Index Loaded"),
        mo.md(f"**Columns:** `{list(index_df.columns)}`"),
        mo.md(f"**Rows:** `{len(index_df):,}`"),
        mo.ui.table(index_df.head(5))
    ])
    return index_df, mo, os, pd


@app.cell
def _(index_df, mo):
    # ── CELL 2: Filter San Diego profiles ────────────────────────────────────────
    lat_min, lat_max =  32.0,  34.0
    lon_min, lon_max = -119.0, -117.0

    sd_box = index_df[
        (index_df['profile_latitude'].between(lat_min, lat_max)) &
        (index_df['profile_longitude'].between(lon_min, lon_max))
    ].copy()

    mo.vstack([
        mo.md(f"## 🎯 {len(sd_box)} profiles near San Diego"),
        mo.ui.table(sd_box.head(10))
    ])
    return (sd_box,)


@app.cell
def _():
    def _():
        import tarfile
        import os

        tar_path     = r'C:\Users\Mikey\Desktop\DataHacks_26\code\dataset\127234.tar.gz'
        extract_path = r'C:\Users\Mikey\Desktop\DataHacks_26\code\dataset\EasyOneArgoTSLite_20260316T043037Z\data'

        with tarfile.open(tar_path, 'r:gz') as tar:
            members = [m for m in tar.getmembers() if '5906182' in m.name]
            print(f"Found {len(members)} members for 5906182")
            for m in members[:5]:
                print(" ", m.name)
        
            if members:
                tar.extractall(path=extract_path, members=members)
                print("✅ Extracted!")
            else:
                print("❌ 5906182 not in tar at all")
    _()
    return


@app.cell
def _(mo, os, pd, sd_box):

    DATASET_ROOT_A = r'C:\Users\Mikey\Desktop\DataHacks_26\code\dataset\EasyOneArgoTSLite_20260316T043037Z\data'
    DATASET_ROOT_B = r'C:\Users\Mikey\Desktop\DataHacks_26\code\dataset\EasyOneArgoTSLite_20260316T043037Z\data\EasyOneArgoTSLite_20260316T043037Z\data'

    def parse_argo_csv(filepath: str) -> dict:
        meta = {}
        header_lines = 0
        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    header_lines += 1
                    parts = line[1:].strip().split(None, 1)
                    if len(parts) == 2:
                        meta[parts[0]] = parts[1].strip()
                else:
                    break
        df = pd.read_csv(filepath, skiprows=header_lines)
        df.columns = ['pressure', 'temperature', 'salinity',
                      'pressure_error', 'temperature_error', 'salinity_error']
        df = df.dropna(subset=['temperature'])
        if df.empty:
            raise ValueError("No valid temperature readings in file")
        surface = df.loc[df['pressure'].idxmin()]
        return {
            'PLATFORM':  meta.get('platform_number', '?'),
            'CYCLE':     meta.get('cycle_number', '?'),
            'LAT':       float(meta.get('profile_latitude', 'nan')),
            'LON':       float(meta.get('profile_longitude', 'nan')),
            'DATE':      meta.get('profile_date', '?'),
            'SST_degC':  round(float(surface['temperature']), 4),
            'PRES_dbar': round(float(surface['pressure']), 2),
            'FILE':      os.path.basename(filepath),
        }

    def run_physics_extraction(sd_box, root_a, root_b):
        results, errors = [], []
        for _, row_data in sd_box.iterrows():
            p_id  = str(int(float(row_data['platform_number'])))
            c_id  = str(int(float(row_data['cycle_number']))).zfill(3)
            fname = f"{p_id}_{c_id}_EasyTSLite.csv"
            fpath = os.path.join(root_a, p_id, fname)
            if not os.path.exists(fpath):
                fpath = os.path.join(root_b, p_id, fname)
            if not os.path.exists(fpath):
                errors.append({'platform': p_id, 'cycle': c_id,
                               'file': fname, 'reason': 'NOT FOUND in either root'})
                continue
            try:
                results.append(parse_argo_csv(fpath))
            except Exception as exc:
                errors.append({'platform': p_id, 'cycle': c_id,
                               'file': fname, 'reason': str(exc)})
        return (
            pd.DataFrame(results),
            pd.DataFrame(errors) if errors else
            pd.DataFrame(columns=['platform', 'cycle', 'file', 'reason']),
        )

    # ── Module-scope: downstream cells can see these ──────────────────────
    physics_df, error_df = run_physics_extraction(sd_box, DATASET_ROOT_A, DATASET_ROOT_B)

    mo.vstack([
        mo.md(f"## 🌡️ SST Extraction"),
        mo.md(f"✅ **{len(physics_df)} profiles extracted** | ❌ **{len(error_df)} failures**"),
        mo.md("### physics_df"),
        mo.ui.table(physics_df) if len(physics_df) > 0 else mo.md("_Empty — check error log_"),
        mo.md("### ⚠️ Error log") if len(error_df) > 0 else mo.md(""),
        mo.ui.table(error_df)   if len(error_df) > 0 else mo.md(""),
    ])
    return (physics_df,)


@app.cell
def _(physics_df):
    print(repr(physics_df.columns.tolist()))
    print(physics_df.shape)
    return


@app.cell
def _(physics_df):
    import numpy as np
    from scipy.interpolate import griddata
    _lons = physics_df['LON'].values
    _lats = physics_df['LAT'].values
    _sst  = physics_df['SST_degC'].values
    _mask = ~np.isnan(_sst)
    _lons, _lats, _sst = _lons[_mask], _lats[_mask], _sst[_mask]

    lon_g, lat_g = np.meshgrid(
        np.linspace(_lons.min(), _lons.max(), 200),
        np.linspace(_lats.min(), _lats.max(), 200),
    )
    sst_g = griddata(
        np.column_stack([_lons, _lats]), _sst,
        (lon_g, lat_g), method='cubic',
    )
    _dT_dy, _dT_dx = np.gradient(sst_g)
    grad_mag = np.sqrt(_dT_dx**2 + _dT_dy**2)
    return grad_mag, lat_g, lon_g, np, sst_g


@app.cell
def _(mo, np, os, pd, physics_df):


    SIGHTINGS_FILE = 'sightings.csv'

    def load_and_join_sightings(sightings_file, physics_df):
        sightings = pd.read_csv(sightings_file)
        def nearest_sst(slat, slon):
            dists = np.sqrt(
                (physics_df['LAT'].values - slat)**2 +
                (physics_df['LON'].values - slon)**2
            )
            idx = int(np.argmin(dists))
            return {
                'nearest_platform': physics_df.iloc[idx]['PLATFORM'],
                'nearest_dist_deg': round(float(dists[idx]), 4),
                'nearest_SST':      physics_df.iloc[idx]['SST_degC'],
            }
        nearest = sightings.apply(
            lambda r: pd.Series(nearest_sst(r['latitude'], r['longitude'])),
            axis=1
        )
        return pd.concat([sightings, nearest], axis=1)

    if os.path.exists(SIGHTINGS_FILE):
        sightings_df = load_and_join_sightings(SIGHTINGS_FILE, physics_df)
        mo.vstack([
            mo.md("## 🐋 Sightings Loaded & Joined"),
            mo.md(f"**{len(sightings_df)} sightings** joined to nearest Argo profile"),
            mo.ui.table(sightings_df.head(10)),
        ])
    else:
        sightings_df = pd.DataFrame()
        mo.md(f"## 🐋 Sightings\n⚠️ `{SIGHTINGS_FILE}` not found — update path")
    return (sightings_df,)


@app.cell
def _(grad_mag, lat_g, lon_g, mo, np, physics_df, sightings_df, sst_g):
    import io
    import matplotlib.pyplot as plt
    def render_map(lon_g, lat_g, sst_g, grad_mag, physics_df, sightings_df):
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('#0a0a1a')
        ax.set_facecolor('#0a0a1a')

        sst_plot = ax.pcolormesh(
            lon_g, lat_g, sst_g,
            cmap='RdYlBu_r', shading='auto',
            vmin=np.nanmin(sst_g), vmax=np.nanmax(sst_g)
        )
        cbar = fig.colorbar(sst_plot, ax=ax, pad=0.01, fraction=0.03)
        cbar.set_label('SST (°C)', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')

        ax.contour(
            lon_g, lat_g, grad_mag,
            levels=8, colors='white', alpha=0.4, linewidths=0.8
        )
        ax.scatter(
            physics_df['LON'], physics_df['LAT'],
            c='cyan', s=60, zorder=5, label='Argo profiles',
            edgecolors='white', linewidths=0.5
        )
        if not sightings_df.empty and 'longitude' in sightings_df.columns:
            ax.scatter(
                sightings_df['longitude'], sightings_df['latitude'],
                c='yellow', marker='*', s=180, zorder=6,
                label='Mammal sightings', edgecolors='black', linewidths=0.4
            )

        ax.set_xlabel('Longitude', color='white')
        ax.set_ylabel('Latitude',  color='white')
        ax.set_title('San Diego SST · Thermal Gradient · Marine Mammal Sightings',
                     color='white', fontsize=13)
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
        ax.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=9)
        plt.tight_layout()
        return fig

    fig = render_map(lon_g, lat_g, sst_g, grad_mag, physics_df, sightings_df)
    mo.mpl.interactive(fig)
    return (plt,)


@app.cell
def _(pd):
    # Cell 6
    GARIBALDI_URL = 'https://raw.githubusercontent.com/MichaelHuynh28/DataHacks_26/main/DataHacks_26/garibaldi_clean.csv.csv'
    LEOPARD_URL   = 'https://raw.githubusercontent.com/MichaelHuynh28/DataHacks_26/main/DataHacks_26/leopard_shark_clean.csv.csv'

    garibaldi_raw = pd.read_csv(GARIBALDI_URL)
    leopard_raw = pd.read_csv(LEOPARD_URL) 
    def prep_species(df, species_name):
        out = df[['observed_on', 'latitude', 'longitude', 'common_name', 'place_guess']].copy()
        out['observed_on'] = pd.to_datetime(out['observed_on'], errors='coerce')
        out = out.dropna(subset=['observed_on', 'latitude', 'longitude'])
        out['species']    = species_name
        out['year']       = out['observed_on'].dt.year
        out['month']      = out['observed_on'].dt.month
        out['year_frac']  = out['year'] + (out['month'] - 1) / 12
        return out

    garibaldi   = prep_species(garibaldi_raw,  'Garibaldi')
    leopard     = prep_species(leopard_raw,    'Leopard Shark')
    sightings   = pd.concat([garibaldi, leopard], ignore_index=True)

    print(f"Garibaldi:     {len(garibaldi)} sightings  {garibaldi['observed_on'].min().date()} → {garibaldi['observed_on'].max().date()}")
    print(f"Leopard Shark: {len(leopard)} sightings  {leopard['observed_on'].min().date()} → {leopard['observed_on'].max().date()}")
    return garibaldi, leopard


@app.cell
def _(garibaldi, lat_g, leopard, lon_g, np):
    from scipy.stats import gaussian_kde, linregress

    def build_kde(df, lon_g, lat_g):
        pts    = df[['longitude', 'latitude']].dropna().values.T
        kde    = gaussian_kde(pts, bw_method=0.08)
        coords = np.vstack([lon_g.ravel(), lat_g.ravel()])
        return kde(coords).reshape(lon_g.shape)

    def temporal_trend(df):
        monthly      = df.groupby(['year', 'month']).size().reset_index(name='count')
        monthly['t'] = monthly['year'] + (monthly['month'] - 1) / 12
        slope, _, _, p, _ = linregress(monthly['t'], monthly['count'])
        return slope, p, monthly

    gar_kde              = build_kde(garibaldi, lon_g, lat_g)
    leo_kde              = build_kde(leopard,   lon_g, lat_g)
    gar_slope, gar_p, gar_monthly = temporal_trend(garibaldi)
    leo_slope, leo_p, leo_monthly = temporal_trend(leopard)

    print(f"Garibaldi trend:     {gar_slope:+.3f} sightings/month  (p={gar_p:.3f})")
    print(f"Leopard Shark trend: {leo_slope:+.3f} sightings/month  (p={leo_p:.3f})")
    return gar_kde, gar_p, gar_slope, leo_kde, leo_p, leo_slope


@app.cell
def _(
    gar_kde,
    gar_p,
    gar_slope,
    garibaldi,
    grad_mag,
    lat_g,
    leo_kde,
    leo_p,
    leo_slope,
    leopard,
    lon_g,
    mo,
    np,
    physics_df,
    plt,
    sst_g,
):
    fig9, axes = plt.subplots(1, 2, figsize=(18, 8))
    fig9.patch.set_facecolor('#0a0a1a')

    SPECIES = [
        ('Garibaldi',     garibaldi, gar_kde, gar_slope, gar_p, '#FF6B35', 'Oranges'),
        ('Leopard Shark', leopard,   leo_kde, leo_slope, leo_p, '#00F5FF', 'Blues'),
    ]

    for ax, (name, df, kde, slope, p, color, cmap) in zip(axes, SPECIES):
        ax.set_facecolor('#0a0a1a')

        ax.pcolormesh(lon_g, lat_g, sst_g, cmap='RdYlBu_r',
                      shading='auto', alpha=0.6,
                      vmin=np.nanmin(sst_g), vmax=np.nanmax(sst_g))

        ax.contour(lon_g, lat_g, grad_mag,
                   levels=6, colors='white', alpha=0.25, linewidths=0.6)

        ax.contourf(lon_g, lat_g, kde, levels=10, cmap=cmap, alpha=0.55)
        ax.contour(lon_g, lat_g, kde, levels=6, colors=color, alpha=0.8, linewidths=0.8)

        ax.scatter(df['longitude'], df['latitude'],
                   c=color, s=12, alpha=0.4, zorder=5,
                   edgecolors='none', label='Sightings')

        ax.scatter(physics_df['LON'], physics_df['LAT'],
                   c='cyan', s=40, zorder=6,
                   edgecolors='white', linewidths=0.4, label='Argo')

        direction = '↑ Increasing' if slope > 0 else '↓ Decreasing'
        sig       = '★ significant' if p < 0.05 else 'not significant'
        ax.set_title(f'{name}\n{direction} trend  ({sig})', color='white', fontsize=12)
        ax.set_xlabel('Longitude', color='white')
        ax.set_ylabel('Latitude',  color='white')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
        ax.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=8)

    fig9.suptitle('San Diego · Species Hotspots vs SST Thermal Structure',
                  color='white', fontsize=14, y=1.01)
    plt.tight_layout()
    mo.mpl.interactive(fig9)
    return


if __name__ == "__main__":
    app.run()
