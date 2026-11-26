"""Monta os painéis do projeto Moratória da Soja.
(A) município-ano 1995-2024: soja (IBGE/PAM: área plantada, colhida, produção), desmatamento (MapBiomas Col. 11: total e
    vegetação primária, por bioma) e cobertura (MapBiomas: soja, pastagem, vegetação natural), com a classificação do município
    em Amazônia, Cerrado ou divisa pela área de cada bioma (>= 95% em um bioma; divisa = >= 5% em cada).
(B) município-bioma-ano 1995-2024, só para municípios na divisa Amazônia-Cerrado: desmatamento em cada parte do município.
Uso (dentro de moratoria_soja/): python 01_painel.py"""
import json, numpy as np, pandas as pd, openpyxl
from pathlib import Path
B = Path(__file__).resolve().parent; BR = B / 'dados/brutos'; PR = B / 'dados/processados'; PR.mkdir(parents=True, exist_ok=True)
ANOS = range(1995, 2025)

# ---------- municípios e área
m = json.load(open(BR / 'ibge_municipios.json'))
def uf(x):
    try: return x['microrregiao']['mesorregiao']['UF']['sigla']
    except Exception: return x['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
mun = pd.DataFrame([{'cod_ibge': x['id'], 'municipio': x['nome'], 'uf': uf(x)} for x in m])
a = json.load(open(BR / 'area_municipios.json')); a = pd.DataFrame(a[1:])
mun = mun.merge(pd.DataFrame({'cod_ibge': a.D1C.astype(int), 'area_km2': pd.to_numeric(a.V, errors='coerce')}), on='cod_ibge', how='left')

# ---------- PAM soja
rows = []
for y in ANOS:
    d = json.load(open(BR / f'pam_soja_{y}.json')); d = pd.DataFrame(d[1:])
    d['v'] = pd.to_numeric(d.V.replace({'-': '0'}), errors='coerce')            # '-' = zero; '..'/'...' = sem dado
    p = d.pivot_table(index='D1C', columns='D2C', values='v', aggfunc='first').rename(columns={'8331': 'soja_plantada_ha', '216': 'soja_colhida_ha', '214': 'soja_producao_t'})
    p['ano'] = y; p.index = p.index.astype(int); rows.append(p.reset_index().rename(columns={'D1C': 'cod_ibge'}))
pam = pd.concat(rows)

# ---------- MapBiomas: desmatamento por município, bioma e ano
wb = openpyxl.load_workbook(BR / 'mapbiomas_desmatamento_municipio.xlsx', read_only=True); ws = wb['ANNUAL_DEFORESTATION']
it = ws.iter_rows(values_only=True); h = next(it); ix = {k: i for i, k in enumerate(h)}
anos_mb = [int(k[1:]) for k in h if isinstance(k, str) and k.startswith('y') and k[1:].isdigit()]
acc = {}
for r in it:
    if r[ix['GEOCODE']] is None: continue
    g, b, prim = int(r[ix['GEOCODE']]), r[ix['BIOME']], 'Primária' in str(r[ix['TRANSITION_CLASS_NAME']])
    for y in anos_mb:
        v = r[ix[f'y{y}']] or 0
        if v == 0: continue
        e = acc.setdefault((g, b, y), [0.0, 0.0]); e[0] += v; e[1] += v if prim else 0
mb = pd.DataFrame([(k[0], k[1], k[2], v[0], v[1]) for k, v in acc.items()], columns=['cod_ibge', 'bioma', 'ano', 'desmat_ha', 'desmat_prim_ha'])

# cobertura do MapBiomas por município, bioma e ano (gerada por 01a_cobertura.py)
cob = pd.read_csv(PR / 'cobertura_municipio_bioma_ano.csv')
# composição de biomas do município: participação de cada bioma na ÁREA do município (cobertura de 2020)
comp = cob[cob.ano == 2020].pivot_table(index='cod_ibge', columns='bioma', values='area_total_ha', aggfunc='sum').fillna(0)
comp = comp.div(comp.sum(axis=1), axis=0)
for b in ['Amazônia', 'Cerrado']:
    if b not in comp: comp[b] = 0.0
cls = pd.Series('Outro', index=comp.index)
cls[comp['Amazônia'] >= .95] = 'Amazônia'; cls[comp['Cerrado'] >= .95] = 'Cerrado'
cls[(comp['Amazônia'] >= .05) & (comp['Cerrado'] >= .05)] = 'Divisa'
bioma_info = pd.DataFrame({'grupo_bioma': cls, 'share_amazonia': comp['Amazônia'], 'share_cerrado': comp['Cerrado']})

# ---------- Painel A: município-ano
base = pd.MultiIndex.from_product([mun.cod_ibge, ANOS], names=['cod_ibge', 'ano']).to_frame(index=False).merge(mun, on='cod_ibge')
tot = mb.groupby(['cod_ibge', 'ano'])[['desmat_ha', 'desmat_prim_ha']].sum().reset_index()
porb = mb[mb.bioma.isin(['Amazônia', 'Cerrado'])].pivot_table(index=['cod_ibge', 'ano'], columns='bioma', values='desmat_prim_ha', aggfunc='sum')
porb.columns = ['desmat_prim_ha_amazonia' if c == 'Amazônia' else 'desmat_prim_ha_cerrado' for c in porb.columns]
A = base.merge(pam, on=['cod_ibge', 'ano'], how='left').merge(tot, on=['cod_ibge', 'ano'], how='left').merge(porb.reset_index(), on=['cod_ibge', 'ano'], how='left')
for c in ['desmat_ha', 'desmat_prim_ha', 'desmat_prim_ha_amazonia', 'desmat_prim_ha_cerrado']: A[c] = A[c].fillna(0)
A = A.merge(bioma_info, left_on='cod_ibge', right_index=True, how='left'); A['grupo_bioma'] = A.grupo_bioma.fillna('Outro')
cobm = cob.groupby(['cod_ibge', 'ano'])[['soja_ha', 'pastagem_ha', 'natural_ha', 'agropecuaria_ha']].sum().add_prefix('mb_').reset_index()
A = A.merge(cobm, on=['cod_ibge', 'ano'], how='left')
A['desmat_prim_pct'] = A.desmat_prim_ha / (A.area_km2 * 100) * 100
A['soja_pct_area'] = A.soja_plantada_ha / (A.area_km2 * 100) * 100
A['produtividade_t_ha'] = A.soja_producao_t / A.soja_colhida_ha.replace(0, np.nan)
pre = A[A.ano.between(2001, 2005)].groupby('cod_ibge').soja_plantada_ha.mean()
A['soja_media_2001_2005'] = A.cod_ibge.map(pre).fillna(0)
A['sojicultor_pre'] = (A.soja_media_2001_2005 >= 1000).astype(int)        # município sojicultor antes da moratória
A['amazonia'] = (A.grupo_bioma == 'Amazônia').astype(int)
A['pos_2006'] = (A.ano >= 2006).astype(int)
A.to_csv(PR / 'painel_municipio_ano.csv', index=False)

# ---------- Painel B: município-bioma-ano (municípios da divisa)
div = bioma_info[bioma_info.grupo_bioma == 'Divisa'].index
Bp = pd.MultiIndex.from_product([div, ['Amazônia', 'Cerrado'], ANOS], names=['cod_ibge', 'bioma', 'ano']).to_frame(index=False)
Bp = Bp.merge(mb, on=['cod_ibge', 'bioma', 'ano'], how='left').fillna({'desmat_ha': 0, 'desmat_prim_ha': 0}).merge(mun, on='cod_ibge')
Bp = Bp.merge(cob[['cod_ibge', 'bioma', 'ano', 'area_total_ha', 'soja_ha', 'pastagem_ha', 'natural_ha', 'floresta_ha', 'agropecuaria_ha']],
              on=['cod_ibge', 'bioma', 'ano'], how='left')
Bp['area_parte_ha'] = Bp.groupby(['cod_ibge', 'bioma']).area_total_ha.transform('max')
for c in ['soja_ha', 'pastagem_ha', 'natural_ha', 'floresta_ha', 'agropecuaria_ha']: Bp[c] = Bp[c].fillna(0)
Bp['desmat_prim_pct'] = Bp.desmat_prim_ha / Bp.area_parte_ha * 100
Bp['soja_pct'] = Bp.soja_ha / Bp.area_parte_ha * 100; Bp['pastagem_pct'] = Bp.pastagem_ha / Bp.area_parte_ha * 100
Bp['parte_amazonia'] = (Bp.bioma == 'Amazônia').astype(int); Bp['pos_2006'] = (Bp.ano >= 2006).astype(int)
Bp = Bp.merge(A[['cod_ibge', 'ano', 'soja_plantada_ha', 'sojicultor_pre']], on=['cod_ibge', 'ano'], how='left')
soja_pre_parte = Bp[Bp.ano.between(2001, 2005)].groupby(['cod_ibge', 'bioma']).soja_ha.mean().rename('soja_parte_2001_2005')
Bp = Bp.merge(soja_pre_parte.reset_index(), on=['cod_ibge', 'bioma'], how='left')
Bp.to_csv(PR / 'painel_municipio_bioma_ano.csv', index=False)

u = A.drop_duplicates('cod_ibge')
print('Painel A:', A.shape, '| Painel B:', Bp.shape)
print(pd.crosstab(u.grupo_bioma, u.sojicultor_pre, margins=True))
print(u[(u.sojicultor_pre == 1) & u.grupo_bioma.isin(['Amazônia', 'Cerrado', 'Divisa'])].groupby('grupo_bioma').uf.value_counts().unstack(fill_value=0).T)
