import json, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, matplotlib.dates as mdates
B, O, T2, G = '#257de0', '#f47230', '#666666', '#e6e6e6'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#999999', 'xtick.color': T2, 'ytick.color': T2})
# --- Figura: registros mensais (SINARM, categoria Cidadão)
m = pd.read_csv('dados_intermediarios/sinarm_mensal_brasil.csv')
m = m[m.categoria == 'Cidadão'].groupby(['ano', 'mes']).registros.sum().reset_index()
m['data'] = pd.to_datetime(dict(year=m.ano, month=m.mes, day=1)); m = m[(m.data >= '2015-01-01') & (m.data <= '2026-06-01')].sort_values('data')
fig, ax = plt.subplots(figsize=(9, 4), dpi=200)
ax.plot(m.data, m.registros / 1000, color=B, lw=2)
eventos = [('2019-01-15', 'Dec. 9.685\n(jan/2019)'), ('2019-05-07', 'Dec. 9.785\n(mai/2019)'), ('2021-02-12', 'Decs. 10.627–630\n(fev/2021)'),
           ('2023-01-01', 'Dec. 11.366\n(jan/2023)'), ('2023-07-21', 'Dec. 11.615\n(jul/2023)')]
lado = {0: 'right', 1: 'left', 2: 'left', 3: 'right', 4: 'left'}; alt = {0: 17.6, 1: 17.6, 2: 17.6, 3: 16.0, 4: 8.6}
for i, (d, l) in enumerate(eventos):
    x = pd.Timestamp(d); ax.axvline(x, color='#999999', ls='--', lw=1)
    dx = pd.Timedelta(days=25) if lado[i] == 'left' else -pd.Timedelta(days=25)
    ax.text(x + dx, alt[i], l, color=T2, fontsize=7.5, va='top', ha=lado[i])
ax.set_ylim(0, 18); ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color=G, lw=.8); ax.set_axisbelow(True)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax.set_ylabel('Novos registros de armas por civis\n(milhares por mês) — SINARM/PF')
fig.tight_layout(); fig.savefig('fig_registros_mensais.png'); plt.close()
# --- Figura: SDID (trajetórias)
R = json.load(open('resultados_sdid.json')); S = json.load(open('resultados_soja.json'))['sdid']
paineis = [(R['C2'], 'Coorte 2019 vs. nunca tratados\n(municípios ≥ 20 mil hab.)'), (R['B'], 'Quartil superior vs. inferior de registros\n(municípios ≥ 20 mil hab.)'),
           (S['SDID vs. soja consolidada'], 'Fronteira da soja vs.\nsoja consolidada')]
fig, axs = plt.subplots(1, 3, figsize=(11, 3.8), dpi=200, sharey=False)
for ax, (r, ttl) in zip(axs, paineis):
    anos = r['anos']; e = r['sdid']
    ax.plot(anos, e['y1'], color=O, lw=2, marker='o', ms=4, label='Tratados')
    ax.plot(anos, e['synth'], color=B, lw=2, ls='--', marker='o', ms=4, label='Controle sintético (SDID)')
    lam = e['lam']; ax.bar([a for a in anos if a <= 2018], [l * 3 for l in lam], bottom=ax.get_ylim()[0] if False else 0, color='#cccccc', width=.6, label='Pesos de tempo λ (×3)')
    ax.axvline(2018.5, color='#999999', ls='--', lw=1)
    ax.set_title(f"{ttl}\nSDID = {e['tau']:.2f} (EP {e['se']:.2f})".replace(f"{e['tau']:.2f}", f"{e['tau']:.2f}".replace('.', ',')).replace(f"{e['se']:.2f}", f"{e['se']:.2f}".replace('.', ',')), fontsize=8.5)
    ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color=G, lw=.8); ax.set_axisbelow(True); ax.set_xticks(anos[::2]); ax.tick_params(labelsize=8)
axs[0].set_ylabel('Homicídios por arma de fogo / 100 mil'); axs[0].legend(frameon=False, fontsize=7.5, loc='lower left', bbox_to_anchor=(0, 0.08))
fig.tight_layout(); fig.savefig('fig_sdid.png'); plt.close()
