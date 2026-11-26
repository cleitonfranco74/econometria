"""DiD e SDID com a FRONTEIRA DA SOJA como grupo tratado (pedido do docente).
Fronteira da soja = município com >= 1.000 ha de soja em 2018 (IBGE/PAM, Tab. 5457), área de soja crescendo >= 50% entre
2010 e 2018 e desmatamento 2015-18 acima da mediana nacional (MapBiomas). Controles: (a) municípios sem soja relevante
(< 1.000 ha em 2018); (b) soja consolidada (>= 1.000 ha, mas sem expansão ou sem desmatamento).
Uso: python 09_fronteira_soja.py AV2_painel_municipal_Brasil.csv dados_intermediarios/soja_pam.json resultados_soja.json"""
import sys, json, warnings, importlib.util, numpy as np, pandas as pd, pyfixest as pf
from scipy import stats
warnings.filterwarnings('ignore')
df = pd.read_csv(sys.argv[1]); raw = json.load(open(sys.argv[2]))
s = pd.DataFrame(raw[1:]); s['cod_ibge'] = s.D1C.astype(int); s['ano'] = s.D3N.astype(int)
s['ha'] = pd.to_numeric(s.V.replace({'-': '0', '..': None, '...': None, 'X': None}), errors='coerce').fillna(0)
s = s.pivot(index='cod_ibge', columns='ano', values='ha').add_prefix('soja_ha_')
df = df.merge(s, left_on='cod_ibge', right_index=True, how='left').fillna({c: 0 for c in s.columns})
u = df.drop_duplicates('cod_ibge').set_index('cod_ibge')
prod = u.soja_ha_2018 >= 1000
expande = (u.soja_ha_2018 >= 1.5 * u.soja_ha_2010)
front_soja = prod & expande & (u.fronteira_ativa == 1)
grp = pd.Series('Sem soja', index=u.index); grp[prod] = 'Soja consolidada'; grp[front_soja] = 'Fronteira da soja'
df['grupo_soja'] = df.cod_ibge.map(grp); df['fronteira_soja'] = (df.grupo_soja == 'Fronteira da soja').astype(int)
print(grp.value_counts()); print(df[df.fronteira_soja == 1].drop_duplicates('cod_ibge').uf.value_counts().head(12).to_dict())
C = 'log_vab_agro_pc + log_densidade_pop + taxa_mortalidade_covid'
df['fp'] = df.fronteira_soja * df.pos_2019; df['did'] = df.delta_reg_pc * df.pos_2019; df['ddd'] = df.did * df.fronteira_soja
for y in range(2015, 2025): df[f'f{y}'] = df.fronteira_soja * (df.ano == y)
res = {}
def fit(name, fml, data, coef, **kw):
    m = pf.feols(fml, data=data, vcov={'CRV1': 'cod_ibge'}, **kw); t = m.tidy().loc[coef]
    res[name] = dict(coef=t['Estimate'], se=t['Std. Error'], p=t['Pr(>|t|)'], n=int(m._N)); return m
for ctrl, lab in [('Sem soja', 'vs. sem soja'), ('Soja consolidada', 'vs. soja consolidada')]:
    d = df[df.grupo_soja.isin(['Fronteira da soja', ctrl])]
    fit(f'1º estágio: registros/mil hab. {lab}', 'reg_cidadao_1000 ~ fp | cod_ibge + ano', d, 'fp', weights='pop')
    fit(f'DiD homic. AF {lab}', f'taxa_homic_af ~ fp + {C} | cod_ibge + ano', d, 'fp', weights='pop')
    fit(f'DiD homic. AF {lab} (sem ponderação)', f'taxa_homic_af ~ fp + {C} | cod_ibge + ano', d, 'fp')
    fit(f'Placebo arma branca {lab}', f'taxa_homic_ab ~ fp + {C} | cod_ibge + ano', d, 'fp', weights='pop')
    m = pf.feols('taxa_homic_af ~ ' + ' + '.join(f'f{y}' for y in range(2015, 2025) if y != 2018) + f' + {C} | cod_ibge + ano', data=d, vcov={'CRV1': 'cod_ibge'}, weights='pop')
    t = m.tidy(); R = np.array([[1 if c == f'f{y}' else 0 for c in t.index] for y in (2015, 2016, 2017)]); w = m.wald_test(R=R)
    res[f'Event study {lab}'] = dict(coefs={k: [r['Estimate'], r['Std. Error'], r['Pr(>|t|)']] for k, r in t.iterrows() if k.startswith('f2')},
                                     F=float(w.f_statistic), p=float(1 - stats.f.cdf(w.f_statistic, w.df1, w.df2)))
fit('DDD: ΔREG × Pós × Fronteira da soja (todos)', f'taxa_homic_af ~ did + ddd + {C} | cod_ibge + ano', df, 'ddd', weights='pop')
# SDID
spec = importlib.util.spec_from_file_location('sd', '08_sdid.py'); sd = importlib.util.module_from_spec(spec); spec.loader.exec_module(sd)
p18 = df[df.ano == 2018].set_index('cod_ibge')['pop']; df['pop2018'] = df.cod_ibge.map(p18)
sdid = {}
for ctrl, lab in [('Sem soja', 'vs. sem soja'), ('Soja consolidada', 'vs. soja consolidada')]:
    for pond in (False, True):
        k = f'SDID {lab}' + (' (tratados ponderados)' if pond else '')
        sdid[k] = sd.run(df, 'taxa_homic_af', df.grupo_soja == 'Fronteira da soja', df.grupo_soja == ctrl, k, pond=pond)
n = grp.value_counts().to_dict()
json.dump(dict(res=res, sdid=sdid, n=n, ufs=df[df.fronteira_soja == 1].drop_duplicates('cod_ibge').uf.value_counts().to_dict()), open(sys.argv[3], 'w'), indent=1, default=float)
pd.set_option('display.width', 200)
print(pd.DataFrame({k: v for k, v in res.items() if 'coef' in v}).T.round(4).to_string())
for k, v in res.items():
    if 'F' in v: print(k, 'Wald pré F=%.2f p=%.3f' % (v['F'], v['p']), {a: round(b[0], 2) for a, b in v['coefs'].items()})
