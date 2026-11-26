"""Análise preliminar: a moratória desacoplou soja e desmatamento na Amazônia?
(1) Trajetórias agregadas de área de soja e de desmatamento primário: Amazônia vs. Cerrado (municípios sojicultores pré-2006).
(2) Event study (Poisson, EF de município e de UF x ano) do desmatamento primário: Amazônia vs. Cerrado, base 2005.
(3) Dentro dos municípios da divisa: parte amazônica vs. parte de cerrado do MESMO município (EF município x ano e
    município x bioma), base 2005.
(4) Área de soja: Amazônia vs. Cerrado (log, EF de município e UF x ano).
Uso (dentro de moratoria_soja/): python 02_analise_preliminar.py"""
import json, warnings, numpy as np, pandas as pd, pyfixest as pf, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from pathlib import Path
warnings.filterwarnings('ignore')
B = Path(__file__).resolve().parent; PR = B / 'dados/processados'; RS = B / 'resultados'; RS.mkdir(exist_ok=True)
A = pd.read_csv(PR / 'painel_municipio_ano.csv'); P = pd.read_csv(PR / 'painel_municipio_bioma_ano.csv')
A = A[A.ano.between(1998, 2020)]; P = P[P.ano.between(1998, 2020)]
S = A[(A.sojicultor_pre == 1) & A.grupo_bioma.isin(['Amazônia', 'Cerrado'])].copy()
out = {'n': S.drop_duplicates('cod_ibge').grupo_bioma.value_counts().to_dict(), 'n_divisa': int(P.cod_ibge.nunique())}

# (1) trajetórias agregadas (índice 2005 = 100)
agg = S.groupby(['grupo_bioma', 'ano'])[['soja_plantada_ha', 'desmat_prim_ha', 'soja_producao_t']].sum()
idx = agg / agg.xs(2005, level='ano') * 100
out['trajetoria'] = {g: idx.loc[g].round(1).reset_index().values.tolist() for g in ['Amazônia', 'Cerrado']}
pre, pos = S.ano.between(2001, 2005), S.ano.between(2009, 2013)
tab = {}
for g in ['Amazônia', 'Cerrado']:
    s = S[S.grupo_bioma == g]
    tab[g] = {v: [s[pre & (s.grupo_bioma == g)].groupby('ano')[v].sum().mean(), s[pos & (s.grupo_bioma == g)].groupby('ano')[v].sum().mean()]
              for v in ['soja_plantada_ha', 'soja_producao_t', 'desmat_prim_ha']}
out['medias_2001_05_vs_2009_13'] = tab

# (2) event study: Amazônia vs. Cerrado, Poisson do desmatamento primário
S['amz'] = S.amazonia
for y in range(1998, 2021): S[f'e{y}'] = S.amz * (S.ano == y)
ev = ' + '.join(f'e{y}' for y in range(1998, 2021) if y != 2005)
res = {}
def es(name, fml, data, pois=True, vc='cod_ibge'):
    m = (pf.fepois if pois else pf.feols)(fml, data=data, vcov={'CRV1': vc}); t = m.tidy()
    res[name] = {int(k[1:]): [r['Estimate'], r['Std. Error'], r['2.5%'], r['97.5%'], r['Pr(>|t|)']] for k, r in t.iterrows() if k.startswith('e')}
    return m
def did(name, fml, data, coef, pois=True, vc='cod_ibge'):
    m = (pf.fepois if pois else pf.feols)(fml, data=data, vcov={'CRV1': vc}); t = m.tidy().loc[coef]
    out.setdefault('did', {})[name] = dict(coef=t['Estimate'], se=t['Std. Error'], p=t['Pr(>|t|)'], n=int(m._N))
S['amz_pos'] = S.amz * S.pos_2006
es('Desmatamento primário: Amazônia vs. Cerrado', f'desmat_prim_ha ~ {ev} | cod_ibge + uf^ano', S)
did('Desmatamento primário (Poisson), EF UF×ano', 'desmat_prim_ha ~ amz_pos | cod_ibge + uf^ano', S, 'amz_pos')
did('Desmatamento primário (Poisson), EF ano', 'desmat_prim_ha ~ amz_pos | cod_ibge + ano', S, 'amz_pos')
S['log_soja'] = np.log1p(S.soja_plantada_ha)
es('Área de soja (log): Amazônia vs. Cerrado', f'log_soja ~ {ev} | cod_ibge + uf^ano', S, pois=False)
did('Área de soja (log), EF UF×ano', 'log_soja ~ amz_pos | cod_ibge + uf^ano', S, 'amz_pos', pois=False)

# (3) divisa: parte amazônica vs. parte de cerrado do mesmo município
P['mb'] = P.cod_ibge.astype(str) + '_' + P.bioma; P['mt'] = P.cod_ibge.astype(str) + '_' + P.ano.astype(str)
for y in range(1998, 2021): P[f'e{y}'] = P.parte_amazonia * (P.ano == y)
P['amz_pos'] = P.parte_amazonia * P.pos_2006
es('Divisa: parte amazônica vs. parte de cerrado', f'desmat_prim_ha ~ {ev} | mb + mt', P)
did('Divisa (Poisson), EF município×bioma e município×ano', 'desmat_prim_ha ~ amz_pos | mb + mt', P, 'amz_pos')
Ps = P[P.sojicultor_pre == 1]
did('Divisa, só sojicultores pré-2006', 'desmat_prim_ha ~ amz_pos | mb + mt', Ps, 'amz_pos')
# mecanismo: soja, pastagem e vegetação natural em cada parte do município (Poisson em hectares)
for v, lab in [('soja_ha', 'soja'), ('pastagem_ha', 'pastagem'), ('natural_ha', 'vegetação natural')]:
    did(f'Divisa: área de {lab}', f'{v} ~ amz_pos | mb + mt', P, 'amz_pos')
    es(f'Divisa: área de {lab}', f'{v} ~ {ev} | mb + mt', P)
# conversão: participação da pastagem e da soja na área da parte (pontos percentuais, MQO)
did('Divisa: soja (% da área da parte)', 'soja_pct ~ amz_pos | mb + mt', P, 'amz_pos', pois=False)
did('Divisa: pastagem (% da área da parte)', 'pastagem_pct ~ amz_pos | mb + mt', P, 'amz_pos', pois=False)
out['event'] = res
json.dump(out, open(RS / 'resultados_preliminares.json', 'w'), indent=1, default=float)

# figuras
BL, OR, T2, G = '#257de0', '#f47230', '#666666', '#e6e6e6'
plt.rcParams.update({'font.size': 10, 'axes.edgecolor': '#999999', 'xtick.color': T2, 'ytick.color': T2})
def style(ax):
    ax.spines[['top', 'right']].set_visible(False); ax.grid(axis='y', color=G, lw=.8); ax.set_axisbelow(True)
    ax.axvline(2006, color='#999999', ls='--', lw=1); ax.text(2006.2, ax.get_ylim()[1] * .97, 'Moratória (2006)', color=T2, fontsize=8, va='top')
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, (v, ttl) in zip(axs, [('soja_plantada_ha', 'Área plantada de soja (2005 = 100)'), ('desmat_prim_ha', 'Desmatamento primário (2005 = 100)')]):
    for g, c in [('Amazônia', OR), ('Cerrado', BL)]:
        s = idx.loc[g][v]; ax.plot(s.index, s.values, color=c, lw=2, marker='o', ms=3, label=g)
    ax.set_title(ttl, fontsize=10); style(ax)
axs[0].legend(frameon=False, loc='upper left'); fig.tight_layout(); fig.savefig(RS / 'fig_trajetorias.png', dpi=200); plt.close()
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, (k, ttl, c) in zip(axs, [('Desmatamento primário: Amazônia vs. Cerrado', 'Municípios sojicultores:\nAmazônia vs. Cerrado', OR),
                                ('Divisa: parte amazônica vs. parte de cerrado', 'Municípios da divisa:\nparte amazônica vs. parte de cerrado', BL)]):
    e = res[k]; ys = sorted(list(e) + [2005]); g = lambda i: [0 if y == 2005 else e[y][i] for y in ys]
    ax.axhline(0, color='#191919', lw=.8); ax.vlines(ys, g(2), g(3), color=c, lw=1.8); ax.plot(ys, g(0), 'o', color=c, ms=4, mec='white', mew=1)
    ax.set_title(ttl, fontsize=10); style(ax)
axs[0].set_ylabel('Coeficiente Poisson (log), IC 95%\nbase = 2005'); fig.tight_layout(); fig.savefig(RS / 'fig_event_study.png', dpi=200); plt.close()
fig, axs = plt.subplots(1, 3, figsize=(12, 3.6))
for ax, (k, ttl, c) in zip(axs, [('Divisa: área de soja', 'Área de soja', OR), ('Divisa: área de pastagem', 'Área de pastagem', BL), ('Divisa: área de vegetação natural', 'Vegetação natural', '#00b894')]):
    e = res[k]; ys = sorted(list(e) + [2005]); g = lambda i: [0 if y == 2005 else e[y][i] for y in ys]
    ax.axhline(0, color='#191919', lw=.8); ax.vlines(ys, g(2), g(3), color=c, lw=1.8); ax.plot(ys, g(0), 'o', color=c, ms=4, mec='white', mew=1)
    ax.set_title(f'Divisa – parte amazônica vs. cerrado:\n{ttl}', fontsize=9.5); style(ax)
axs[0].set_ylabel('Coeficiente Poisson (log), IC 95%'); fig.tight_layout(); fig.savefig(RS / 'fig_mecanismo_divisa.png', dpi=200); plt.close()
pd.set_option('display.width', 200)
print('N:', out['n'], '| divisa:', out['n_divisa'])
print(pd.DataFrame(out['did']).T.round(4))
for g in tab: print(g, {k: [round(x) for x in v] for k, v in tab[g].items()})
for k in res: print(k, {y: round(v[0], 2) for y, v in res[k].items()})
