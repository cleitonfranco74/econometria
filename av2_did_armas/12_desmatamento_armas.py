"""Associação entre desmatamento (MapBiomas Col. 11) e registros de armas por civis (SINARM).
(1) painel 2015-2024 com EF de município e ano: desmatamento do ano (e do ano anterior) -> registros por mil hab.;
(2) entre municípios, por bioma: desmatamento 2015-18 -> novos registros 2019-22 por mil hab.;
(3) taxas agregadas por tercil de desmatamento 2015-18.
Uso: python 12_desmatamento_armas.py AV2_painel_municipal_Brasil.csv resultados_desmatamento.json"""
import sys, json, warnings, numpy as np, pandas as pd, pyfixest as pf
warnings.filterwarnings('ignore')
d = pd.read_csv(sys.argv[1]).sort_values(['cod_ibge', 'ano'])
d['desm_lag'] = d.groupby('cod_ibge').desmat_pct.shift(1)
out = {'painel': {}, 'bioma': {}, 'tercil': {}}
for k, f in [('EF município e ano', 'reg_cidadao_1000 ~ desmat_pct | cod_ibge + ano'),
             ('EF município e UF × ano', 'reg_cidadao_1000 ~ desmat_pct | cod_ibge + uf^ano'),
             ('Desmatamento defasado (t−1)', 'reg_cidadao_1000 ~ desm_lag | cod_ibge + uf^ano'),
             ('Só vegetação primária', 'reg_cidadao_1000 ~ desmat_prim_pct | cod_ibge + uf^ano')]:
    m = pf.feols(f, data=d, vcov={'CRV1': 'cod_ibge'}, weights='pop'); t = m.tidy().iloc[0]
    out['painel'][k] = dict(coef=t['Estimate'], se=t['Std. Error'], p=t['Pr(>|t|)'], n=int(m._N))
u = d.drop_duplicates('cod_ibge').set_index('cod_ibge').copy()
u['d1518'] = d[d.ano <= 2018].groupby('cod_ibge').desmat_pct.sum(); u['log_pop'] = np.log(u['pop'])
f = 'delta_reg_pc ~ d1518 + log_vab_agro_pc + log_densidade_pop + log_pop + pre_reg_pc | uf'
for b in ['Todos', 'Amazônia', 'Cerrado', 'Mata Atlântica', 'Caatinga', 'Pampa']:
    s = u if b == 'Todos' else u[u.bioma == b]
    m = pf.feols(f, data=s.reset_index(), vcov='hetero'); t = m.tidy().loc['d1518']
    out['bioma'][b] = dict(coef=t['Estimate'], se=t['Std. Error'], p=t['Pr(>|t|)'], n=int(m._N))
u['terc'] = pd.qcut(u.d1518, 3, labels=['Baixo', 'Médio', 'Alto']); d = d.merge(u.terc, left_on='cod_ibge', right_index=True)
for (tc, pos), g in d.groupby(['terc', 'pos_2019']):
    out['tercil'][f'{tc}|{pos}'] = dict(reg=g.reg_cidadao.sum() / g['pop'].sum() * 1000, af=g.af.sum() / g['pop'].sum() * 1e5)
dm = d.desmat_pct - d.groupby('cod_ibge').desmat_pct.transform('mean')
out['escala'] = dict(sd_within=float(dm.std()), media_reg=float(d.reg_cidadao_1000.mean()), media_delta=float(u.delta_reg_pc.mean()), sd_d1518=float(u.d1518.std()))
json.dump(out, open(sys.argv[2], 'w'), indent=1, default=float)
for k in ('painel', 'bioma'): print(pd.DataFrame(out[k]).T.round(4))
print(pd.DataFrame(out['tercil']).T.round(3)); print(out['escala'])
