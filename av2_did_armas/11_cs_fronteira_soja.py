"""Callaway & Sant'Anna (2021) com a fronteira da soja como grupo tratado.
(a) Adoção em bloco: fronteira da soja tratada em 2019; controles nunca tratados = soja consolidada ou sem soja.
(b) Adoção escalonada: coorte = 1º ano de salto de registros de armas (2019-2021) nos municípios da fronteira da soja;
    controles = ainda não tratados + soja consolidada (nunca tratados).
Uso: python 11_cs_fronteira_soja.py AV2_painel_municipal_Brasil.csv dados_intermediarios/soja_pam.json resultados_cs_soja.json"""
import sys, json, warnings, numpy as np, pandas as pd
from scipy.stats import norm
from differences import ATTgt
warnings.filterwarnings('ignore')
df = pd.read_csv(sys.argv[1]); raw = json.load(open(sys.argv[2]))
s = pd.DataFrame(raw[1:]); s['cod_ibge'] = s.D1C.astype(int); s['ano'] = s.D3N.astype(int)
s['ha'] = pd.to_numeric(s.V.replace({'-': '0'}), errors='coerce').fillna(0)
s = s.pivot(index='cod_ibge', columns='ano', values='ha')
u = df.drop_duplicates('cod_ibge').set_index('cod_ibge'); s = s.reindex(u.index).fillna(0)
prod = s[2018] >= 1000; front = prod & (s[2018] >= 1.5 * s[2010]) & (u.fronteira_ativa == 1) & u.bioma.isin(['Amazônia', 'Cerrado'])
grp = pd.Series('Sem soja', index=u.index); grp[prod] = 'Soja consolidada'; grp[front] = 'Fronteira da soja'
df['grupo'] = df.cod_ibge.map(grp)
out = {}
def cs(name, d, y='taxa_homic_af', weights=None, cg='never_treated'):
    dd = d[['cod_ibge', 'ano', y, 'coorte', 'pop']].set_index(['cod_ibge', 'ano'])
    a = ATTgt(data=dd, cohort_column='coorte', base_period='varying')
    a.fit(formula=y, control_group=cg, weights_column=weights, progress_bar=False)
    sm = a.aggregate('simple').iloc[0].tolist(); ev = a.aggregate('event')
    att, se = float(sm[0]), float(sm[1]); p = float(2 * (1 - norm.cdf(abs(att / se))))
    evd = {int(k): [float(v[0]), float(v[1]), float(v[2]), float(v[3])] for k, v in zip(ev.index, ev.values.tolist())}
    pre = [k for k in evd if k < 0]
    out[name] = dict(att=att, se=se, p=p, lo=float(sm[2]), hi=float(sm[3]), event=evd,
                     N1=int(d[d.coorte.notna()].cod_ibge.nunique()), N0=int(d[d.coorte.isna()].cod_ibge.nunique()))
    print(f"{name:62s} ATT={att:7.3f} EP={se:6.3f} p={p:.4f} | pré: " + ', '.join(f"{k}:{evd[k][0]:.2f}" for k in sorted(pre)) +
          ' | pós: ' + ', '.join(f"{k}:{evd[k][0]:.2f}" for k in sorted(evd) if k >= 0), flush=True)
# (a) bloco 2019
for ctrl in ['Soja consolidada', 'Sem soja']:
    d = df[df.grupo.isin(['Fronteira da soja', ctrl])].copy(); d['coorte'] = np.where(d.grupo == 'Fronteira da soja', 2019, np.nan)
    cs(f'Bloco 2019 vs. {ctrl.lower()}', d)
    cs(f'Bloco 2019 vs. {ctrl.lower()} – ponderado pop.', d, weights='pop')
    cs(f'Placebo arma branca: bloco 2019 vs. {ctrl.lower()}', d, y='taxa_homic_ab')
# (b) escalonado pelo salto de registros
d = df[df.grupo.isin(['Fronteira da soja', 'Soja consolidada'])].copy()
d['coorte'] = np.where((d.grupo == 'Fronteira da soja') & (d.ano_primeiro_salto > 0), d.ano_primeiro_salto, np.nan)
d = d[~((d.grupo == 'Fronteira da soja') & d.coorte.isna())]   # fronteira sem salto sai da amostra
out['coortes_escalonado'] = d.drop_duplicates('cod_ibge').coorte.value_counts(dropna=False).rename(str).to_dict()
cs('Escalonado (salto de registros) – controle ainda não tratados', d, cg='not_yet_treated')
cs('Escalonado (salto de registros) – controle ainda não tratados, pond.', d, weights='pop', cg='not_yet_treated')
cs('Escalonado (salto de registros) – controle nunca tratados', d, cg='never_treated')
print('coortes:', out['coortes_escalonado'])
json.dump(out, open(sys.argv[3], 'w'), indent=1, default=str)
