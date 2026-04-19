import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    # Cell 1
    import pandas as pd
    import marimo as mo
    import os

    index_file = 'EasyOneArgoTSLite_index.csv'
    index_df = pd.read_csv(index_file, comment='#')
    index_df.columns = index_df.columns.str.strip()

    mo.vstack([
        mo.md(f"## 🗂️ Index Loaded"),
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
    # ── CELL 3 
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
    # ── CELL 4
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
def _():
    return


@app.cell
def _(physics_df):
    print(repr(physics_df.columns.tolist()))
    print(physics_df.shape)
    return


@app.cell
def _(physics_df):
    # ── CELL 5 
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
    # ── CELL 6
    SIGHTINGS_FILE = 'sightings.csv'

    def load_and_join_sightings(sightings_file, physics_df):
        sightings = pd.read_csv(sightings_file)
        def nearest_sst(slat, slon):
            # no idea m8 :/
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
    # Cell 7
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    def render_map_geo(lon_g, lat_g, sst_g, grad_mag, physics_df, sightings_df):
        fig, ax = plt.subplots(figsize=(10, 8),
                               subplot_kw={'projection': ccrs.PlateCarree()})
        fig.patch.set_facecolor('#0a0a1a')
        ax.set_facecolor('#0a0a1a')
        ax.set_extent([-120.5, -116.5, 31.0, 34.0], crs=ccrs.PlateCarree())

        sst_plot = ax.pcolormesh(lon_g, lat_g, sst_g, cmap='RdYlBu_r',
                                  shading='auto', transform=ccrs.PlateCarree(),
                                  vmin=np.nanmin(sst_g), vmax=np.nanmax(sst_g))
        cbar = fig.colorbar(sst_plot, ax=ax, pad=0.01, fraction=0.03)
        cbar.set_label('SST (°C)', color='white')
        cbar.ax.yaxis.set_tick_params(color='white')
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')

        ax.contour(lon_g, lat_g, grad_mag, levels=8,
                   colors='white', alpha=0.4, linewidths=0.8,
                   transform=ccrs.PlateCarree())

        ax.add_feature(cfeature.COASTLINE, color='white', linewidth=1.2, zorder=4)
        ax.add_feature(cfeature.LAND, facecolor='#1a1a2e', zorder=3)
        ax.add_feature(cfeature.STATES, edgecolor='gray', linewidth=0.5, zorder=4)

        ax.scatter(physics_df['LON'], physics_df['LAT'],
                   c='cyan', s=60, zorder=5, label='Argo profiles',
                   edgecolors='white', linewidths=0.5,
                   transform=ccrs.PlateCarree())

        if not sightings_df.empty and 'longitude' in sightings_df.columns:
            ax.scatter(sightings_df['longitude'], sightings_df['latitude'],
                       c='yellow', marker='*', s=180, zorder=6,
                       label='Mammal sightings', edgecolors='black', linewidths=0.4,
                       transform=ccrs.PlateCarree())

        ax.set_title('San Diego SST · Thermal Gradient · Marine Mammal Sightings',
                     color='white', fontsize=13)
        ax.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=9)
        ax.text(-117.1573, 32.7157, 'San Diego', color='white', fontsize=10,
            fontweight='bold', transform=ccrs.PlateCarree(),
            ha='left', va='bottom')
        plt.tight_layout()
        return fig

    fig = render_map_geo(lon_g, lat_g, sst_g, grad_mag, physics_df, sightings_df)
    mo.mpl.interactive(fig)
    return ccrs, cfeature, plt


@app.cell
def _(pd):
    # Cell 8
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
def _(garibaldi, leopard, np, pd, physics_df):
    # Cell 9
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder

    def get_nearest_sst(slat, slon):
        dists = np.sqrt((physics_df['LAT'].values - slat)**2 +
                        (physics_df['LON'].values - slon)**2)
        return physics_df.iloc[int(np.argmin(dists))]['SST_degC']

    garibaldi['SST'] = garibaldi.apply(
        lambda r: get_nearest_sst(r['latitude'], r['longitude']), axis=1)
    leopard['SST'] = leopard.apply(
        lambda r: get_nearest_sst(r['latitude'], r['longitude']), axis=1)

    garibaldi['label'] = 'Garibaldi'
    leopard['label']   = 'Leopard Shark'

    positives = pd.concat([
        garibaldi[['latitude', 'longitude', 'month', 'SST', 'label']],
        leopard[['latitude',   'longitude', 'month', 'SST', 'label']],
    ], ignore_index=True)

    rng_rf  = np.random.default_rng(42)
    n_neg   = len(positives)
    neg_lats   = rng_rf.uniform(32.0, 34.0, n_neg)
    neg_lons   = rng_rf.uniform(-119.0, -117.0, n_neg)
    neg_months = rng_rf.integers(1, 13, n_neg)
    neg_sst    = np.array([get_nearest_sst(la, lo)
                           for la, lo in zip(neg_lats, neg_lons)])

    negatives = pd.DataFrame({
        'latitude':  neg_lats,
        'longitude': neg_lons,
        'month':     neg_months,
        'SST':       neg_sst,
        'label':     'neither',
    })

    training = pd.concat([positives, negatives], ignore_index=True)
    X = training[['latitude', 'longitude', 'month', 'SST']].values
    le = LabelEncoder()
    y  = le.fit_transform(training['label'])

    rf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    rf.fit(X, y)

    print(f"Classes: {le.classes_}")
    print("Feature importances:")
    for feat, imp in zip(['lat', 'lon', 'month', 'SST'], rf.feature_importances_):
        print(f"  {feat}: {imp:.3f}")
    return le, rf


@app.cell
def _(garibaldi, lat_g, leopard, lon_g, np):
    # ── CELL 10
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
    return gar_kde, gar_p, gar_slope, leo_kde, leo_p, leo_slope, linregress


@app.cell
def _(
    ccrs,
    cfeature,
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
    # Cell 11
    def render_species_map():
        fig9, axes9 = plt.subplots(1, 2, figsize=(18, 8),
                                   subplot_kw={'projection': ccrs.PlateCarree()})
        fig9.patch.set_facecolor('#0a0a1a')
        SPECIES = [
            ('Garibaldi',     garibaldi, gar_kde, gar_slope, gar_p, '#FF6B35', 'Oranges'),
            ('Leopard Shark', leopard,   leo_kde, leo_slope, leo_p, '#00F5FF', 'Blues'),
        ]
        for ax9, (name, df, kde, slope, p, color, cmap) in zip(axes9, SPECIES):
            ax9.set_facecolor('#0a0a1a')
            ax9.set_extent([-120.5, -116.5, 31.0, 34.0], crs=ccrs.PlateCarree())

            ax9.pcolormesh(lon_g, lat_g, sst_g, cmap='RdYlBu_r',
                           shading='auto', alpha=0.6, transform=ccrs.PlateCarree(),
                           vmin=np.nanmin(sst_g), vmax=np.nanmax(sst_g))
            ax9.contour(lon_g, lat_g, grad_mag,
                        levels=6, colors='white', alpha=0.25, linewidths=0.6,
                        transform=ccrs.PlateCarree())
            ax9.contourf(lon_g, lat_g, kde, levels=10, cmap=cmap, alpha=0.55,
                         transform=ccrs.PlateCarree())
            ax9.contour(lon_g, lat_g, kde, levels=6, colors=color, alpha=0.8,
                        linewidths=0.8, transform=ccrs.PlateCarree())
            ax9.scatter(df['longitude'], df['latitude'],
                        c=color, s=12, alpha=0.4, zorder=5,
                        edgecolors='none', label='Sightings',
                        transform=ccrs.PlateCarree())
            ax9.scatter(physics_df['LON'], physics_df['LAT'],
                        c='cyan', s=40, zorder=6,
                        edgecolors='white', linewidths=0.4, label='Argo',
                        transform=ccrs.PlateCarree())

            ax9.add_feature(cfeature.COASTLINE, color='white', linewidth=1.2, zorder=4)
            ax9.add_feature(cfeature.LAND, facecolor='#1a1a2e', zorder=3)
            ax9.add_feature(cfeature.STATES, edgecolor='gray', linewidth=0.5, zorder=4)
            ax9.text(-117.1573, 32.7157, 'San Diego', color='white', fontsize=9,
                     fontweight='bold', transform=ccrs.PlateCarree(),
                     ha='left', va='bottom')

            direction = '↑ Increasing' if slope > 0 else '↓ Decreasing'
            sig       = '★ significant' if p < 0.05 else 'not significant'
            ax9.set_title(f'{name}\n{direction} trend  ({sig})', color='white', fontsize=12)
            ax9.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=8)

        fig9.suptitle('San Diego · Species Hotspots vs SST Thermal Structure',
                      color='white', fontsize=14, y=1.01)
        plt.tight_layout()
        return fig9

    fig9 = render_species_map()
    mo.mpl.interactive(fig9)
    return


@app.cell
def _(linregress, np, pd, physics_df):
    # Cell 12
    # ── Extract SST + date from physics_df ───────────────────────────────
    sst_trend_df = physics_df[['DATE', 'SST_degC']].copy()
    sst_trend_df['DATE'] = pd.to_datetime(sst_trend_df['DATE'], errors='coerce')
    sst_trend_df = sst_trend_df.dropna()
    sst_trend_df['year_frac'] = (sst_trend_df['DATE'].dt.year +
                                  (sst_trend_df['DATE'].dt.month - 1) / 12)

    t   = sst_trend_df['year_frac'].values
    sst = sst_trend_df['SST_degC'].values

    # ── Observed trend ────────────────────────────────────────────────────
    obs_slope, obs_intercept, _, _, _ = linregress(t, sst)

    # ── Bootstrap CI on slope ─────────────────────────────────────────────
    rng        = np.random.default_rng(42)
    n_boot     = 10_000
    boot_slopes = np.array([
        linregress(
            t[idx := rng.integers(0, len(t), len(t))],
            sst[idx]
        ).slope
        for _ in range(n_boot)
    ])

    ci_low, ci_high = np.percentile(boot_slopes, [2.5, 97.5])

    print(f"Observed SST trend: {obs_slope:+.4f} °C/year")
    print(f"95% CI:             [{ci_low:+.4f}, {ci_high:+.4f}] °C/year")
    print(f"Current mean SST:   {sst.mean():.2f} °C")
    return ci_high, ci_low, obs_slope


@app.cell
def _(ci_high, ci_low, np, obs_slope, sst_g):
    # Cell 13 Predict New Surface Sea Temp
    current_year_frac = 2026 + (4 - 1) / 12  # April 2026

    horizons = {
        'Today':     0,
        '+6 months': 0.5,
        '+1 year':   1.0,
        '+2 years':  2.0,
    }

    sst_futures = {}
    for label, delta in horizons.items():
        sst_futures[label] = {
            'mid':  sst_g + obs_slope * delta,
            'low':  sst_g + ci_low   * delta,
            'high': sst_g + ci_high  * delta,
        }

    print("Projected mean SST in SD box:")
    for label, delta in horizons.items():
        mid = np.nanmean(sst_futures[label]['mid'])
        lo  = np.nanmean(sst_futures[label]['low'])
        hi  = np.nanmean(sst_futures[label]['high'])
        print(f"  {label:12s}: {mid:.2f}°C  (95% CI: {lo:.2f}–{hi:.2f}°C)")
    return (sst_futures,)


@app.cell
def _(
    ccrs,
    cfeature,
    ci_high,
    ci_low,
    grad_mag,
    lat_g,
    le,
    lon_g,
    mo,
    np,
    obs_slope,
    physics_df,
    plt,
    rf,
    sst_futures,
):
    # Cell 14
    def build_and_render_forecast():
        def predict_habitat(sst_grid, month):
            grid_lats   = lat_g.ravel()
            grid_lons   = lon_g.ravel()
            grid_sst    = sst_grid.ravel()
            grid_months = np.full_like(grid_lats, month)
            valid       = ~np.isnan(grid_sst)
            X_grid      = np.column_stack([grid_lats[valid], grid_lons[valid],
                                           grid_months[valid], grid_sst[valid]])
            probs   = rf.predict_proba(X_grid)
            gar_idx = list(le.classes_).index('Garibaldi')
            leo_idx = list(le.classes_).index('Leopard Shark')
            def to_grid(col):
                arr        = np.full(grid_lats.shape, np.nan)
                arr[valid] = probs[:, col]
                return arr.reshape(lon_g.shape)
            return to_grid(gar_idx), to_grid(leo_idx)

        h_labels = ['Today', '+6 months', '+1 year', '+2 years']
        h_months = [4, 10, 4, 4]
        gar_maps, leo_maps, sst_maps = [], [], []
        for lbl, month in zip(h_labels, h_months):
            g, l = predict_habitat(sst_futures[lbl]['mid'], month)
            gar_maps.append(g)
            leo_maps.append(l)
            sst_maps.append(sst_futures[lbl]['mid'])

        fig_pred, axes14 = plt.subplots(2, 4, figsize=(24, 10),
                                        subplot_kw={'projection': ccrs.PlateCarree()})
        fig_pred.patch.set_facecolor('#0a0a1a')

        ROWS = [
            ('Garibaldi',     gar_maps, '#FF6B35', 'Oranges'),
            ('Leopard Shark', leo_maps, '#00F5FF', 'Blues'),
        ]

        for row_idx, (species, maps, clr, cm) in enumerate(ROWS):
            for col_idx, (lbl, prob_g, sst_future) in enumerate(
                    zip(h_labels, maps, sst_maps)):
                ax14 = axes14[row_idx, col_idx]
                ax14.set_facecolor('#0a0a1a')
                ax14.set_extent([-120.5, -116.5, 31.0, 34.0], crs=ccrs.PlateCarree())

                # SST base
                ax14.pcolormesh(lon_g, lat_g, sst_future,
                                cmap='RdYlBu_r', shading='auto', alpha=0.55,
                                transform=ccrs.PlateCarree(), vmin=10, vmax=26)

                # Thermal fronts
                ax14.contour(lon_g, lat_g, grad_mag,
                             levels=4, colors='white', alpha=0.2, linewidths=0.5,
                             transform=ccrs.PlateCarree())

                # Habitat probability surface
                ax14.contourf(lon_g, lat_g, prob_g,
                              levels=10, cmap=cm, alpha=0.6, vmin=0, vmax=1,
                              transform=ccrs.PlateCarree())
                ax14.contour(lon_g, lat_g, prob_g,
                             levels=[0.4, 0.6, 0.8], colors=clr,
                             alpha=0.9, linewidths=1.0,
                             transform=ccrs.PlateCarree())

                # Argo floats
                ax14.scatter(physics_df['LON'], physics_df['LAT'],
                             c='cyan', s=20, zorder=6,
                             edgecolors='white', linewidths=0.3,
                             transform=ccrs.PlateCarree())

                # ── Predicted sighting locations ──────────────────────────
                n_pred     = 15
                valid_prob = prob_g.copy()
                valid_prob[np.isnan(valid_prob)] = 0
                candidates = np.where(valid_prob.ravel() > 0.2)[0]
                if len(candidates) >= n_pred:
                    flat_idx = np.random.default_rng(col_idx + row_idx).choice(
                        candidates, size=n_pred, replace=False)
                else:
                    flat_idx = np.argsort(valid_prob.ravel())[-n_pred:]
                pred_lats  = lat_g.ravel()[flat_idx]
                pred_lons  = lon_g.ravel()[flat_idx]
                pred_probs = valid_prob.ravel()[flat_idx]

                ax14.scatter(pred_lons, pred_lats,
                             c=pred_probs, cmap=cm,
                             marker='*', s=120, zorder=8,
                             edgecolors=clr, linewidths=0.6,
                             vmin=0, vmax=1,
                             transform=ccrs.PlateCarree(),
                             label='Predicted sightings')

                # Coastline + land
                ax14.add_feature(cfeature.COASTLINE, color='white', linewidth=1.0, zorder=4)
                ax14.add_feature(cfeature.LAND, facecolor='#1a1a2e', zorder=3)
                ax14.add_feature(cfeature.STATES, edgecolor='gray', linewidth=0.4, zorder=4)

                # San Diego label
                ax14.text(-117.1573, 32.7157, 'San Diego', color='white', fontsize=7,
                          fontweight='bold', transform=ccrs.PlateCarree(),
                          ha='left', va='bottom')

                # Title
                ax14.set_title(f'{lbl}\n{np.nanmean(sst_future):.1f}°C mean SST',
                               color='white', fontsize=9)
                ax14.tick_params(colors='white', labelsize=6)

                # Species label on left
                if col_idx == 0:
                    ax14.text(-0.08, 0.5, species, color=clr, fontsize=11,
                              fontweight='bold', transform=ax14.transAxes,
                              rotation=90, ha='center', va='center')

                # Legend on first panel only
                if col_idx == 0 and row_idx == 0:
                    ax14.legend(facecolor='#1a1a2e', labelcolor='white',
                                fontsize=7, loc='lower left')

        fig_pred.suptitle(
            f'San Diego · RF Habitat Shift Forecast  |  '
            f'SST trend: {obs_slope:+.4f}°C/year  (95% CI: {ci_low:+.4f}–{ci_high:+.4f})',
            color='white', fontsize=12, y=1.01
        )
        plt.tight_layout()
        return fig_pred

    fig_pred = build_and_render_forecast()
    mo.mpl.interactive(fig_pred)
    return


if __name__ == "__main__":
    app.run()
