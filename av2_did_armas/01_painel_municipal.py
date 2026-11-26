"""Painel municipal NACIONAL 2015-2024 com tratamento MUNICIPAL real.
Tratamento: registros novos de armas de fogo por civis ("Cidadão") no SINARM/Polícia Federal, por município e ano
  (CSVs oficiais da PF - servicos.dpf.gov.br/dadosabertos/SINARM_CSV/REGISTROS - obtidos de cópia pública no GitHub:
   github.com/yurilq/IBMEC_DESENVOLVIMENTO_AGENTE_2026, pasta DADOS_SINARM/REGISTROS).
Resultados: SIM/DATASUS. Controles: IBGE/SIDRA. Fronteira: MapBiomas Col. 11 (desmatamento)."""
import json, re, sys, unicodedata, difflib, numpy as np, pandas as pd, openpyxl
S, OUT = sys.argv[1], sys.argv[2]
def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().replace('-', ' ').replace("'", ' ')
    return ' '.join(re.sub(r'[^A-Z ]', '', s).split())
def sidra(f):
    d = json.load(open(f)); return pd.DataFrame(d[1:]).rename(columns=d[0])
# ---------- IBGE municípios
m = json.load(open(f'{S}/ibge_mun.json'))
def uf(x):
    try: return x['microrregiao']['mesorregiao']['UF']['sigla']
    except Exception: return x['regiao-imediata']['regiao-intermediaria']['UF']['sigla']
ib = pd.DataFrame([{'cod_ibge': x['id'], 'municipio': x['nome'], 'uf': uf(x)} for x in m]); ib['k'] = ib.uf + '|' + ib.municipio.map(norm)
# ---------- SINARM: casar nomes (exato; depois aproximado dentro da UF)
g = pd.read_csv(f'{S}/sinarm_mun_raw.csv').drop(columns='cod_ibge')
kmap = dict(zip(ib.k, ib.cod_ibge))
manual = {'RS|SANTANA DO LIVRAMENTO': 'RS|SANT ANA DO LIVRAMENTO', 'PA|SANTA ISABEL DO PARA': 'PA|SANTA IZABEL DO PARA', 'RN|ACU': 'RN|ASSU',
          'SC|PICARRAS': 'SC|BALNEARIO PICARRAS', 'TO|SAO VALERIO DA NATIVIDADE': 'TO|SAO VALERIO', 'RN|BOA SAUDE': 'RN|JANUARIO CICCO',
          'PR|VILA ALTA': 'PR|ALTO PARAISO', 'SE|AMPARO DE SAO FRANCISCO': 'SE|AMPARO DO SAO FRANCISCO', 'PB|SERIDO': 'PB|SAO VICENTE DO SERIDO',
          'RN|ESPIRITO SANTO DO OESTE': 'RN|PARAU', 'SP|SAO MIGUEL PAULISTA': 'SP|SAO PAULO'}
def match(k):
    if k in kmap: return kmap[k]
    if k in manual and manual[k] in kmap: return kmap[manual[k]]
    u = k.split('|')[0]; c = difflib.get_close_matches(k, [x for x in kmap if x.startswith(u + '|')], n=1, cutoff=0.85)
    return kmap[c[0]] if c else np.nan
km = {k: match(k) for k in g.k.unique()}; g['cod_ibge'] = g.k.map(km)
print('SINARM: registros sem município IBGE:', g[g.cod_ibge.isna()].TOTAL.sum(), 'de', g.TOTAL.sum())
g = g.dropna(subset=['cod_ibge']); g['cod_ibge'] = g.cod_ibge.astype(int)
reg = g.pivot_table(index=['cod_ibge', 'ano'], columns='CATEGORIA', values='TOTAL', aggfunc='sum').fillna(0)
reg = reg.rename(columns={'Cidadão': 'reg_cidadao', 'Caçador de Subsistência': 'reg_cacador_subs', 'Servidor Público(Porte por prerrogativa de função)': 'reg_servidor'})
reg = reg[[c for c in ['reg_cidadao', 'reg_cacador_subs', 'reg_servidor'] if c in reg]].reset_index()
# ---------- População
pops = []
for y in [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2024]:
    p = sidra(f'{S}/pop_{y}.json'); pops.append(pd.DataFrame({'cod_ibge': p['Município (Código)'].astype(int), 'ano': y, 'pop': pd.to_numeric(p['Valor'], errors='coerce')}))
c = sidra(f'{S}/c22all.json'); c['cod_ibge'] = c['Município (Código)'].astype(int); c['V'] = pd.to_numeric(c['Valor'], errors='coerce')
c22 = c.pivot_table(index='cod_ibge', columns='Variável', values='V')
pops.append(pd.DataFrame({'cod_ibge': c22.index, 'ano': 2022, 'pop': c22['População residente'].values}))
w = pd.concat(pops).pivot(index='cod_ibge', columns='ano', values='pop'); w[2023] = np.sqrt(w[2022] * w[2024])
pop = w.stack().rename('pop').reset_index()
area = c22['Área da unidade territorial'].rename('area_km2')
# ---------- VAB agro (IPCA dez/2022)
ip = sidra(f'{S}/ipca.json'); ip['ano'] = ip['Mês'].str[-4:].astype(int); defl = ip.set_index('ano')['Valor'].astype(float); defl = defl.loc[2022] / defl
vs = []
for y in range(2015, 2024):
    v = sidra(f'{S}/pib_{y}.json'); v = v[v['Ano'] == str(y)]
    vs.append(pd.DataFrame({'cod_ibge': v['Município (Código)'].astype(int), 'ano': y, 'vab_agro': pd.to_numeric(v['Valor'], errors='coerce') * 1000}))
vab = pd.concat(vs)
# ---------- MapBiomas: desmatamento 2015-2018 (ha) -> % da área
wb = openpyxl.load_workbook(f'{S}/mb_def.xlsx', read_only=True); ws = wb['ANNUAL_DEFORESTATION']
rows = ws.iter_rows(values_only=True); h = next(rows); ix = {k: i for i, k in enumerate(h)}
acc = {}
for r in rows:
    if r[ix['GEOCODE']] is None: continue
    gcode = int(r[ix['GEOCODE']]); acc[gcode] = acc.get(gcode, 0) + sum((r[ix[f'y{y}']] or 0) for y in (2015, 2016, 2017, 2018))
mb = pd.Series(acc, name='desmat_ha_2015_2018')
# ---------- SIM
sim = pd.read_csv(f'{S}/sim/sim_mun.csv', dtype={'mun6': str})
# ---------- Painel
base = pd.MultiIndex.from_product([ib.cod_ibge, range(2015, 2025)], names=['cod_ibge', 'ano']).to_frame(index=False)
df = base.merge(ib[['cod_ibge', 'municipio', 'uf']], on='cod_ibge').merge(pop, on=['cod_ibge', 'ano'], how='left')
df['mun6'] = df.cod_ibge.astype(str).str[:6]
df = df.merge(sim, on=['mun6', 'ano'], how='left').merge(reg, on=['cod_ibge', 'ano'], how='left').merge(vab, on=['cod_ibge', 'ano'], how='left')
for v in ['af', 'ab', 'outros', 'transito', 'covid', 'reg_cidadao', 'reg_cacador_subs', 'reg_servidor']: df[v] = df[v].fillna(0)
df = df.merge(area, left_on='cod_ibge', right_index=True, how='left').merge(mb, left_on='cod_ibge', right_index=True, how='left')
df = df.sort_values(['cod_ibge', 'ano'])
df['vab_agro_imputado'] = df.vab_agro.isna().astype(int); df['vab_agro'] = df.groupby('cod_ibge').vab_agro.ffill()
df['log_vab_agro_pc'] = np.log((df.vab_agro * df.ano.clip(upper=2023).map(defl)).clip(lower=1) / df['pop'])
df['log_densidade_pop'] = np.log(df['pop'] / df.area_km2)
for v, n in [('af', 'taxa_homic_af'), ('ab', 'taxa_homic_ab'), ('outros', 'taxa_homic_outros'), ('transito', 'taxa_obitos_transito'), ('covid', 'taxa_mortalidade_covid')]:
    df[n] = df[v] / df['pop'] * 1e5
df['reg_cidadao_1000'] = df.reg_cidadao / df['pop'] * 1000
df['pos_2019'] = (df.ano >= 2019).astype(int); df['pos_2023'] = (df.ano >= 2023).astype(int)
# ---------- Tratamento (fixo no tempo)
P = df.pivot(index='cod_ibge', columns='ano', values='pop'); R = df.pivot(index='cod_ibge', columns='ano', values='reg_cidadao')
t = pd.DataFrame(index=P.index)
t['reg_cid_2015_2018'] = R[[2015, 2016, 2017, 2018]].sum(1); t['reg_cid_2019_2022'] = R[[2019, 2020, 2021, 2022]].sum(1)
t['delta_reg_pc'] = t.reg_cid_2019_2022 / P[2018] * 1000                  # novos registros 2019-22 por mil hab. (pop. 2018)
t['pre_reg_pc'] = t.reg_cid_2015_2018 / P[2015] * 1000                    # idem 2015-18 (linha de base)
t['excesso_reg_pc'] = t.delta_reg_pc - t.pre_reg_pc                       # aceleração atribuível aos decretos
lo, hi = t.delta_reg_pc.quantile([.01, .99]); dw = t.delta_reg_pc.clip(lo, hi)
t['intens_reg'] = (dw - dw.min()) / (dw.max() - dw.min())                 # Min-Max [0,1] após winsorizar p1-p99
t['tratamento_quartil_sup'] = (t.delta_reg_pc >= t.delta_reg_pc.quantile(.75)).astype(int)
# Coorte (Callaway & Sant'Anna): 1º ano 2019-2021 em que a taxa anual >= 2x a média 2015-18 (e >= 3 registros)
pre_mean = R[[2015, 2016, 2017, 2018]].mean(1) / P[2015] * 1000
coh = pd.Series(0, index=R.index)
for y in (2021, 2020, 2019):
    hit = (R[y] / P[y] * 1000 >= 2 * pre_mean.clip(lower=1e-9)) & (R[y] >= 3); coh[hit] = y
t['ano_primeiro_salto'] = coh
dm = mb.reindex(t.index) / (area.reindex(t.index) * 100) * 100             # % da área desmatada 2015-18
t['taxa_desmat_2015_2018'] = dm.fillna(0)
t['fronteira_ativa'] = (t.taxa_desmat_2015_2018 > t.taxa_desmat_2015_2018.median()).astype(int)
amz = ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO', 'MT', 'MA']
df = df.merge(t, left_on='cod_ibge', right_index=True)
df['amazonia_legal_uf'] = df.uf.isin(amz).astype(int)
orig = pd.read_csv(f'{S}/muns.csv'); df['amostra_projeto_50'] = df.cod_ibge.isin(orig.cod_ibge).astype(int)
df = df.dropna(subset=['pop'])
keep = ['cod_ibge','municipio','uf','ano','pos_2019','pos_2023','amostra_projeto_50','amazonia_legal_uf','fronteira_ativa','taxa_desmat_2015_2018',
        'reg_cidadao','reg_cacador_subs','reg_servidor','reg_cidadao_1000','reg_cid_2015_2018','reg_cid_2019_2022','pre_reg_pc','delta_reg_pc','excesso_reg_pc',
        'intens_reg','tratamento_quartil_sup','ano_primeiro_salto','pop','af','ab','outros','transito','covid','taxa_homic_af','taxa_homic_ab',
        'taxa_homic_outros','taxa_obitos_transito','taxa_mortalidade_covid','vab_agro','log_vab_agro_pc','vab_agro_imputado','area_km2','log_densidade_pop']
df[keep].to_csv(OUT, index=False)
print(df[keep].shape, df.cod_ibge.nunique())
print(df.drop_duplicates('cod_ibge')[['delta_reg_pc','pre_reg_pc','intens_reg','taxa_desmat_2015_2018']].describe().round(3).to_string())
print(df.drop_duplicates('cod_ibge').ano_primeiro_salto.value_counts())
print(df.groupby('ano')[['reg_cidadao','af','ab','pop']].sum())
