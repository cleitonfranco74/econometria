"""DiD com a fronteira agrícola ativa como grupo tratado (fronteira_ativa x Pós-2019) e primeiro estágio em registros.
Uso: python 13_fronteira_tratamento.py AV2_painel_municipal_Brasil.csv fronteira_tratamento.json"""
import sys, json, warnings, pandas as pd, numpy as np, pyfixest as pf
warnings.filterwarnings('ignore')
df = pd.read_csv(sys.argv[1]); df['fp'] = df.fronteira_ativa * df.pos_2019
C = 'log_vab_agro_pc + log_densidade_pop + taxa_mortalidade_covid'; out = {}
for nm, fml, w in [('fronteira_pond', f'taxa_homic_af ~ fp + {C} | cod_ibge + ano', 'pop'), ('fronteira_sem_pond', f'taxa_homic_af ~ fp + {C} | cod_ibge + ano', None),
                   ('fronteira_registros', 'reg_cidadao_1000 ~ fp | cod_ibge + ano', 'pop')]:
    t = pf.feols(fml, data=df, vcov={'CRV1': 'cod_ibge'}, weights=w).tidy().loc['fp']; out[nm] = [t['Estimate'], t['Std. Error'], t['Pr(>|t|)']]; print(nm, np.round(out[nm], 4))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
