"""Figuras do paper em português (pt) e inglês (en). Salva em paper/figs/<nome>_<lang>.pdf.
Uso (dentro de av2_did_armas/paper/): python figuras.py"""
import json, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.dates as mdates
from pathlib import Path
B = Path(__file__).resolve().parent.parent; OUT = Path(__file__).resolve().parent / 'figs'; OUT.mkdir(exist_ok=True)
J = lambda f: json.load(open(B / f, encoding='utf-8'))
R = J('resultados_municipal.json'); CS = J('cs_resultados.json'); SD = J('resultados_sdid.json'); SJ = J('resultados_soja.json')
BL, OR, T2, G = '#257de0', '#f47230', '#666666', '#e6e6e6'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#999999', 'xtick.color': T2, 'ytick.color': T2, 'font.family': 'serif'})
TXT = {
 'pt': dict(dec=',', reg_m='Novos registros de armas por civis\n(milhares por mês)', reg_y='Novos registros de armas\npor mil habitantes',
            cons='Municípios consolidados', front='Fronteira agrícola ativa', q1='Quartil inferior de expansão dos registros', q4='Quartil superior de expansão dos registros',
            af='Homicídios por arma de fogo\npor 100 mil habitantes', af1='Homicídios por arma de fogo', tr='Placebo: óbitos no trânsito',
            es_y='Coeficiente por registro adicional\npor mil hab. (IC 95%)', wald='Teste conjunto pré-2019: F = {F}; p = {p}',
            cs_x='Anos em relação ao primeiro salto de registros', cs_y='ATT (óbitos por 100 mil), IC 95%', cs_af='Homicídios por arma de fogo', cs_tr='Placebo: óbitos no trânsito',
            dec19='Decretos de 2019', dec23='Decreto 11.615/2023', treat='Tratados', synth='Controle sintético (SDID)', lam='Pesos de tempo λ (×3)',
            sd1='Coorte 2019 vs. nunca tratados\n(municípios ≥ 20 mil hab.)', sd2='Quartil superior vs. inferior\n(municípios ≥ 20 mil hab.)', sd3='Fronteira da soja vs.\nsoja consolidada'),
 'en': dict(dec='.', reg_m='New civilian firearm registrations\n(thousands per month)', reg_y='New firearm registrations\nper 1,000 inhabitants',
            cons='Consolidated municipalities', front='Active agricultural frontier', q1='Bottom quartile of registration growth', q4='Top quartile of registration growth',
            af='Firearm homicides\nper 100,000 inhabitants', af1='Firearm homicides', tr='Placebo: traffic deaths',
            es_y='Coefficient per additional registration\nper 1,000 inh. (95% CI)', wald='Joint pre-2019 test: F = {F}; p = {p}',
            cs_x='Years relative to first registration surge', cs_y='ATT (deaths per 100,000), 95% CI', cs_af='Firearm homicides', cs_tr='Placebo: traffic deaths',
            dec19='2019 decrees', dec23='Decree 11,615/2023', treat='Treated', synth='Synthetic control (SDID)', lam='Time weights λ (×3)',
            sd1='2019 cohort vs. never treated\n(municipalities ≥ 20,000 inh.)', sd2='Top vs. bottom quartile\n(municipalities ≥ 20,000 inh.)', sd3='Soy frontier vs.\nconsolidated soy')}
def num(x, d, L): return f'{x:.{d}f}'.replace('.', TXT[L]['dec'])
def style(ax):
    ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color=G, lw=.8); ax.set_axisbelow(True)
def vlines(ax, L, top):
    for x, k in [(2018.5, 'dec19'), (2022.5, 'dec23')]:
        ax.axvline(x, color='#999999', ls='--', lw=1); ax.text(x + .08, top, TXT[L][k], color=T2, fontsize=8, va='top')
for L in ('pt', 'en'):
    t = TXT[L]
    # 1. registros mensais
    m = pd.read_csv(B / 'dados_intermediarios/sinarm_mensal_brasil.csv'); m = m[m.categoria == 'Cidadão'].groupby(['ano', 'mes']).registros.sum().reset_index()
    m['data'] = pd.to_datetime(dict(year=m.ano, month=m.mes, day=1)); m = m[(m.data >= '2015-01-01') & (m.data <= '2026-06-01')].sort_values('data')
    fig, ax = plt.subplots(figsize=(9, 3.8)); ax.plot(m.data, m.registros / 1000, color=BL, lw=2)
    ev = [('2019-01-15', 'Dec. 9.685' if L == 'pt' else 'Dec. 9,685', 'right', 17.6), ('2019-05-07', 'Dec. 9.785' if L == 'pt' else 'Dec. 9,785', 'left', 17.6),
          ('2021-02-12', 'Decs. 10.627–630' if L == 'pt' else 'Decs. 10,627–630', 'left', 17.6), ('2023-01-01', 'Dec. 11.366' if L == 'pt' else 'Dec. 11,366', 'right', 16.0),
          ('2023-07-21', 'Dec. 11.615' if L == 'pt' else 'Dec. 11,615', 'left', 8.6)]
    for d, lab, ha, y in ev:
        x = pd.Timestamp(d); ax.axvline(x, color='#999999', ls='--', lw=1)
        ax.text(x + (pd.Timedelta(days=25) if ha == 'left' else -pd.Timedelta(days=25)), y, lab, color=T2, fontsize=8, va='top', ha=ha)
    ax.set_ylim(0, 18); style(ax); ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y')); ax.set_ylabel(t['reg_m'])
    fig.tight_layout(); fig.savefig(OUT / f'registros_mensais_{L}.pdf'); plt.close()
    # 2. registros por grupo
    rg = R['regs']; anos = [int(x[0]) for x in rg]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.plot(anos, [x[1] for x in rg], color=BL, lw=2, marker='o', ms=4, label=t['cons']); ax.plot(anos, [x[2] for x in rg], color=OR, lw=2, marker='o', ms=4, label=t['front'])
    ax.set_ylim(0, 1.0); style(ax); vlines(ax, L, 0.98); ax.set_xticks(anos); ax.set_ylabel(t['reg_y']); ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0, 0.9))
    fig.tight_layout(); fig.savefig(OUT / f'registros_grupos_{L}.pdf'); plt.close()
    # 3. homicídios por quartil
    tq = R['tend']; anos = [int(x[0]) for x in tq]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.plot(anos, [float(x[1]) for x in tq], color=BL, lw=2, marker='o', ms=4, label=t['q1']); ax.plot(anos, [float(x[4]) for x in tq], color=OR, lw=2, marker='o', ms=4, label=t['q4'])
    ax.set_ylim(0, 22); style(ax); vlines(ax, L, 21.5); ax.set_xticks(anos); ax.set_ylabel(t['af']); ax.legend(frameon=False, loc='lower left')
    fig.tight_layout(); fig.savefig(OUT / f'homicidios_quartis_{L}.pdf'); plt.close()
    # 4. event study TWFE
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, (k, ttl, c) in zip(axs, [('taxa_homic_af', t['af1'], BL), ('taxa_obitos_transito', t['tr'], OR)]):
        co = R['es'][k]['coefs']; ys = sorted([int(y) for y in co] + [2018]); g = lambda i: [0 if y == 2018 else co[str(y)][i] for y in ys]
        ax.axhline(0, color='#191919', lw=.8); ax.vlines(ys, g(2), g(3), color=c, lw=2); ax.plot(ys, g(0), 'o', color=c, ms=5, mec='white', mew=1.2)
        ax.set_title(ttl + '\n' + t['wald'].format(F=num(R['es'][k]['F'], 2, L), p=num(R['es'][k]['p'], 3, L)), fontsize=9)
        ax.axvline(2018.5, color='#999999', ls='--', lw=1); ax.set_xticks(ys); ax.tick_params(axis='x', labelsize=8); ax.set_ylim(-0.4, 0.8); style(ax)
    axs[0].set_ylabel(t['es_y']); fig.tight_layout(); fig.savefig(OUT / f'event_study_{L}.pdf'); plt.close()
    # 5. Callaway & Sant'Anna
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    for k, c, lab, dx in [('taxa_homic_af|not_yet_treated', BL, t['cs_af'], -0.08), ('taxa_obitos_transito|not_yet_treated', OR, t['cs_tr'], 0.08)]:
        ev = CS[k]['event']; e = [int(float(x[0])) for x in ev]; b = [float(x[1]) for x in ev]; lo = [float(x[3]) for x in ev]; hi = [float(x[4]) for x in ev]
        xs = [v + dx for v in e]; ax.vlines(xs, lo, hi, color=c, lw=2); ax.plot(xs, b, 'o', color=c, ms=5, mec='white', mew=1.2, label=lab)
    ax.axhline(0, color='#191919', lw=.8); ax.axvline(-0.5, color='#999999', ls='--', lw=1); style(ax)
    ax.set_xticks(range(-5, 6)); ax.set_xlabel(t['cs_x']); ax.set_ylabel(t['cs_y']); ax.legend(frameon=False, loc='upper left')
    fig.tight_layout(); fig.savefig(OUT / f'callaway_santanna_{L}.pdf'); plt.close()
    # 6. SDID
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, (rr, ttl) in zip(axs, [(SD['C2'], t['sd1']), (SD['B'], t['sd2']), (SJ['sdid']['SDID vs. soja consolidada'], t['sd3'])]):
        anos = rr['anos']; e = rr['sdid']
        ax.plot(anos, e['y1'], color=OR, lw=2, marker='o', ms=3.5, label=t['treat']); ax.plot(anos, e['synth'], color=BL, lw=2, ls='--', marker='o', ms=3.5, label=t['synth'])
        ax.bar([a for a in anos if a <= 2018], [x * 3 for x in e['lam']], color='#cccccc', width=.6, label=t['lam'])
        ax.axvline(2018.5, color='#999999', ls='--', lw=1)
        ax.set_title(f"{ttl}\nSDID = {num(e['tau'], 2, L)} ({'EP' if L == 'pt' else 'SE'} {num(e['se'], 2, L)})", fontsize=8.5)
        style(ax); ax.set_xticks(anos[::2]); ax.tick_params(labelsize=8)
    axs[0].set_ylabel(t['af']); axs[0].legend(frameon=False, fontsize=7.5, loc='lower left', bbox_to_anchor=(0, 0.08))
    fig.tight_layout(); fig.savefig(OUT / f'sdid_{L}.pdf'); plt.close()
print(sorted(p.name for p in OUT.iterdir()))
