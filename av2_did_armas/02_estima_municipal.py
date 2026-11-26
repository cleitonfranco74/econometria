import sys, json, warnings, numpy as np, pandas as pd, pyfixest as pf
from scipy import stats
warnings.filterwarnings('ignore')
df = pd.read_csv(sys.argv[1]); OUT = sys.argv[2]
df['log_pop'] = np.log(df['pop'])
df['did'] = df.delta_reg_pc * df.pos_2019          # efeito por +1 registro novo /1.000 hab. (2019-22)
df['did_int'] = df.intens_reg * df.pos_2019         # versão Min-Max [0,1] (como no projeto)
df['did_23'] = df.delta_reg_pc * df.pos_2023
df['did_front'] = df.did * df.fronteira_ativa
df['did_bin'] = df.tratamento_quartil_sup * df.pos_2019
df['did_exc'] = df.excesso_reg_pc * df.pos_2019
for y in range(2015, 2025): df[f'ev{y}'] = df.delta_reg_pc * (df.ano == y)
C = 'log_vab_agro_pc + log_densidade_pop + taxa_mortalidade_covid'
res = {}
def fit(name, fml, coef='did', data=df, pois=False, **kw):
    f = pf.fepois if pois else pf.feols
    m = f(fml, data=data, vcov={'CRV1': 'cod_ibge'}, **kw); t = m.tidy().loc[coef]
    res[name] = dict(coef=t['Estimate'], se=t['Std. Error'], p=t['Pr(>|t|)'], n=int(m._N), lo=t['2.5%'], hi=t['97.5%'])
    return m
W = dict(weights='pop')
fit('(1) TWFE s/ controles, ponderado pop', 'taxa_homic_af ~ did | cod_ibge + ano', **W)
fit('(2) TWFE c/ controles, ponderado pop', f'taxa_homic_af ~ did + {C} | cod_ibge + ano', **W)
fit('(3) Fronteira: ΔREG×Pós', f'taxa_homic_af ~ did + did_front + {C} | cod_ibge + ano', **W)
fit('(3) Fronteira: ΔREG×Pós×Fronteira', f'taxa_homic_af ~ did + did_front + {C} | cod_ibge + ano', coef='did_front', **W)
fit('(4) Reversão: ΔREG×Pós2019', f'taxa_homic_af ~ did + did_23 + {C} | cod_ibge + ano', **W)
fit('(4) Reversão: ΔREG×Pós2023', f'taxa_homic_af ~ did + did_23 + {C} | cod_ibge + ano', coef='did_23', **W)
fit('(5) Poisson (contagem, offset pop)', f'af ~ did + {C} | cod_ibge + ano', pois=True, offset='log_pop')
fit('(6) Intensidade Min-Max [0,1]', f'taxa_homic_af ~ did_int + {C} | cod_ibge + ano', coef='did_int', **W)
fit('(7) Sem ponderação', f'taxa_homic_af ~ did + {C} | cod_ibge + ano')
fit('(8) Tendência por linha de base (pre_reg×ano)', f'taxa_homic_af ~ did + {C} + i(ano, pre_reg_pc, ref=2018) | cod_ibge + ano', **W)
fit('(9) EF UF×ano', f'taxa_homic_af ~ did + {C} | cod_ibge + uf^ano', **W)
fit('(10) Excesso sobre 2015-18', f'taxa_homic_af ~ did_exc + {C} | cod_ibge + ano', coef='did_exc', **W)
s50 = df[df.amostra_projeto_50 == 1]
fit('(11) Só os 50 municípios do projeto', f'taxa_homic_af ~ did + {C} | cod_ibge + ano', data=s50)
fit('(12) Municípios ≥ 20 mil hab.', f'taxa_homic_af ~ did + {C} | cod_ibge + ano', data=df[df.groupby('cod_ibge')['pop'].transform('min') >= 20000])
# Robustez
d = df.melt(id_vars=['cod_ibge', 'ano', 'delta_reg_pc', 'pos_2019', 'pop'], value_vars=['taxa_homic_af', 'taxa_homic_ab'], var_name='meio', value_name='y')
d['af'] = (d.meio == 'taxa_homic_af').astype(int); d['ddd'] = d.delta_reg_pc * d.af * d.pos_2019
fit('R1 DDD: AF vs arma branca', 'y ~ ddd | cod_ibge^af + ano^af + cod_ibge^ano', coef='ddd', data=d, weights='pop')
fit('R2 Placebo: óbitos no trânsito', f'taxa_obitos_transito ~ did + {C} | cod_ibge + ano', **W)
pre = df[df.ano <= 2018].copy(); pre['did_p'] = pre.delta_reg_pc * (pre.ano >= 2017)
fit('R3 Placebo temporal (2017)', 'taxa_homic_af ~ did_p + log_vab_agro_pc + log_densidade_pop | cod_ibge + ano', coef='did_p', data=pre, weights='pop')
fit('R4 Tratamento binário (Q4)', f'taxa_homic_af ~ did_bin + {C} | cod_ibge + ano', coef='did_bin', **W)
fit('R5 Homicídios arma branca', f'taxa_homic_ab ~ did + {C} | cod_ibge + ano', **W)
fit('R6 Homicídios outros meios', f'taxa_homic_outros ~ did + {C} | cod_ibge + ano', **W)
fit('R7 Subamostra fronteira', f'taxa_homic_af ~ did + {C} | cod_ibge + ano', data=df[df.fronteira_ativa == 1], weights='pop')
fit('R8 Subamostra consolidados', f'taxa_homic_af ~ did + {C} | cod_ibge + ano', data=df[df.fronteira_ativa == 0], weights='pop')
# Event study
ev = ' + '.join(f'ev{y}' for y in range(2015, 2025) if y != 2018)
es = {}
for yv in ['taxa_homic_af', 'taxa_homic_ab', 'taxa_obitos_transito']:
    m = pf.feols(f'{yv} ~ {ev} + {C} | cod_ibge + ano', data=df, vcov={'CRV1': 'cod_ibge'}, weights='pop'); t = m.tidy()
    R = np.array([[1 if c == f'ev{y}' else 0 for c in t.index] for y in (2015, 2016, 2017)]); w = m.wald_test(R=R)
    es[yv] = dict(coefs={int(k[2:]): [r['Estimate'], r['Std. Error'], r['2.5%'], r['97.5%'], r['Pr(>|t|)']] for k, r in t.iterrows() if k.startswith('ev')},
                  F=float(w.f_statistic), p=float(1 - stats.f.cdf(w.f_statistic, w.df1, w.df2)))
# Callaway & Sant'Anna (2021) - coortes 2019/2020/2021, controle not-yet-treated (e never-treated)
cs = {}
try:
    from differences import ATTgt
    dd = df[['cod_ibge', 'ano', 'taxa_homic_af', 'ano_primeiro_salto', 'pop']].copy()
    dd['coorte'] = dd.ano_primeiro_salto.replace(0, np.nan)
    dd = dd.set_index(['cod_ibge', 'ano'])
    for cg in ['not_yet_treated', 'never_treated']:
        a = ATTgt(data=dd, cohort_name='coorte', base_period='varying')
        a.fit(formula='taxa_homic_af', control_group=cg, weights_name='pop', n_jobs=1, progress_bar=False)
        s = a.aggregate('simple'); cs[cg] = s.iloc[0].tolist(); cs[cg + '_cols'] = [str(c) for c in s.columns]
        ev_ = a.aggregate('event'); cs[cg + '_event'] = ev_.reset_index().astype(str).values.tolist()
except Exception as e:
    cs['erro'] = repr(e)
u = df.drop_duplicates('cod_ibge')
info = dict(mean_af=float(np.average(df.taxa_homic_af, weights=df['pop'])), sd_delta=float(u.delta_reg_pc.std()), p75=float(u.delta_reg_pc.quantile(.75)),
            p25=float(u.delta_reg_pc.quantile(.25)), n_mun=int(u.shape[0]), coortes=u.ano_primeiro_salto.value_counts().to_dict())
tend = df.assign(q=pd.qcut(df.delta_reg_pc.rank(method='first'), 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])).groupby(['ano', 'q']).apply(lambda g: g.af.sum() / g['pop'].sum() * 1e5).unstack().round(2)
regs = df.groupby(['ano', 'fronteira_ativa']).apply(lambda g: g.reg_cidadao.sum() / g['pop'].sum() * 1000).unstack().round(3)
desc = df.assign(per=np.where(df.pos_2019 == 1, 'Pós', 'Pré')).groupby(['fronteira_ativa', 'per']).apply(
    lambda g: pd.Series({'municipios': g.cod_ibge.nunique(), 'pop_media': g['pop'].mean(), 'reg_cid_1000': g.reg_cidadao.sum() / g['pop'].sum() * 1000,
                         'delta_reg_pc': g.drop_duplicates('cod_ibge').delta_reg_pc.mean(), 'homic_af': g.af.sum() / g['pop'].sum() * 1e5,
                         'homic_ab': g.ab.sum() / g['pop'].sum() * 1e5, 'transito': g.transito.sum() / g['pop'].sum() * 1e5})).round(3)
json.dump(dict(res=res, es=es, cs=cs, info=info, tend=tend.reset_index().astype(str).values.tolist(), regs=regs.reset_index().values.tolist(), desc=desc.reset_index().values.tolist()),
          open(OUT, 'w'), default=str, indent=1)
pd.set_option('display.width', 220)
print(pd.DataFrame(res).T.round(4).to_string())
for k, v in es.items(): print(k, 'Wald pré F=%.3f p=%.4f' % (v['F'], v['p'])); print(pd.DataFrame(v['coefs'], index=['b', 'se', 'lo', 'hi', 'p']).T.round(4).to_string())
print(json.dumps(cs, default=str)[:3000]); print(info); print(tend.to_string()); print(regs.to_string()); print(desc.to_string())
