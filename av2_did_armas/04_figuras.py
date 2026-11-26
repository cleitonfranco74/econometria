import json, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
R = json.load(open('resultados_municipal.json')); CS = json.load(open('cs_resultados.json'))
B, O, T2, G = '#257de0', '#f47230', '#666666', '#e6e6e6'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#999999', 'xtick.color': T2, 'ytick.color': T2})
def base(ax, x1=2018.5, x2=2022.5, top=None):
    ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color=G, lw=.8); ax.set_axisbelow(True)
    for x, l in [(x1, 'Decretos 2019'), (x2, 'Decreto 11.615/2023')]:
        if x is None: continue
        ax.axvline(x, color='#999999', ls='--', lw=1); ax.text(x + .08, top if top is not None else ax.get_ylim()[1] * .97, l, color=T2, fontsize=8, va='top')
# Fig 1: registros novos por mil hab.
r = R['regs']; anos = [int(x[0]) for x in r]
fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=200)
ax.plot(anos, [x[1] for x in r], color=B, lw=2, marker='o', ms=5, label='Consolidados (2.785 mun.)')
ax.plot(anos, [x[2] for x in r], color=O, lw=2, marker='o', ms=5, label='Fronteira agrícola ativa (2.785 mun.)')
ax.set_ylim(0, 1.0); base(ax); ax.set_xticks(anos); ax.set_ylabel('Novos registros de armas (civis)\npor mil hab. — SINARM/PF')
ax.legend(frameon=False, loc='upper left')
fig.tight_layout(); fig.savefig('fig1_registros_sinarm.png'); plt.close()
# Fig 2: event study TWFE
fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), dpi=200, sharey=True)
for ax, (k, ttl, c) in zip(axs, [('taxa_homic_af', 'Homicídios por arma de fogo', B), ('taxa_obitos_transito', 'Placebo: óbitos no trânsito', O)]):
    co = R['es'][k]['coefs']; ys = sorted([int(y) for y in co] + [2018])
    g = lambda i: [0 if y == 2018 else co[str(y)][i] for y in ys]
    ax.axhline(0, color='#191919', lw=.8); ax.vlines(ys, g(2), g(3), color=c, lw=2); ax.plot(ys, g(0), 'o', color=c, ms=6, mec='white', mew=1.5)
    ax.set_title(f"{ttl}\nWald pré (2015–17): F={R['es'][k]['F']:.2f}; p={R['es'][k]['p']:.3f}", fontsize=9)
    ax.set_xticks(ys); ax.tick_params(axis='x', labelsize=8); ax.set_ylim(-0.4, 0.8); base(ax, top=0.78)
axs[0].set_ylabel('δ_t por +1 registro/mil hab.\n(óbitos/100 mil), IC 95%')
fig.tight_layout(); fig.savefig('fig2_event_study_twfe.png'); plt.close()
# Fig 3: C&S event
fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=200)
for k, c, lab, dx in [('taxa_homic_af|not_yet_treated', B, 'Homicídios AF', -0.08), ('taxa_obitos_transito|not_yet_treated', O, 'Placebo: trânsito', 0.08)]:
    ev = CS[k]['event']; e = [int(float(x[0])) for x in ev]; b = [float(x[1]) for x in ev]; lo = [float(x[3]) for x in ev]; hi = [float(x[4]) for x in ev]
    xs = [v + dx for v in e]; ax.vlines(xs, lo, hi, color=c, lw=2); ax.plot(xs, b, 'o', color=c, ms=6, mec='white', mew=1.5, label=lab)
ax.axhline(0, color='#191919', lw=.8); ax.axvline(-0.5, color='#999999', ls='--', lw=1)
ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color=G, lw=.8); ax.set_axisbelow(True)
ax.set_xticks(range(-5, 6)); ax.set_xlabel('Anos relativos ao 1º salto de registros no município'); ax.set_ylabel('ATT (óbitos/100 mil), IC 95%')
ax.legend(frameon=False, loc='upper left'); fig.tight_layout(); fig.savefig('fig3_callaway_santanna.png'); plt.close()
