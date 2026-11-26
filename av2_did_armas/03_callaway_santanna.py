import sys, json, numpy as np, pandas as pd, warnings
warnings.filterwarnings('ignore')
from differences import ATTgt
df = pd.read_csv(sys.argv[1])
dd = df[['cod_ibge', 'ano', 'taxa_homic_af', 'taxa_obitos_transito', 'ano_primeiro_salto', 'pop']].copy()
dd['coorte'] = dd.ano_primeiro_salto.replace(0, np.nan)
dd = dd.set_index(['cod_ibge', 'ano'])
out = {}
for y in ['taxa_homic_af', 'taxa_obitos_transito']:
    for cg in ['not_yet_treated', 'never_treated']:
        a = ATTgt(data=dd, cohort_column='coorte', base_period='varying')
        a.fit(formula=y, control_group=cg, weights_column='pop', progress_bar=False)
        s = a.aggregate('simple'); e = a.aggregate('event')
        out[f'{y}|{cg}'] = dict(simple=s.reset_index().astype(str).values.tolist(), cols=[str(c) for c in s.reset_index().columns],
                               event=e.reset_index().astype(str).values.tolist(), ecols=[str(c) for c in e.reset_index().columns])
        print('==', y, cg); print(s.to_string()); print(e.to_string())
json.dump(out, open(sys.argv[2], 'w'), indent=1)
