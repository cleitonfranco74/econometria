"""Agrega a cobertura do MapBiomas Col. 11 por município, bioma e ano (área total, soja, pastagem, floresta, vegetação
natural e agropecuária). Entrada: dados/brutos/mapbiomas_cobertura_municipio_bioma.xlsx (aba COVERAGE_11).
Saída: dados/processados/cobertura_municipio_bioma_ano.csv"""
import openpyxl, pandas as pd
from pathlib import Path
B = Path(__file__).resolve().parent
wb = openpyxl.load_workbook(B / 'dados/brutos/mapbiomas_cobertura_municipio_bioma.xlsx', read_only=True); ws = wb['COVERAGE_11']
it = ws.iter_rows(values_only=True); h = next(it); ix = {k: i for i, k in enumerate(h)}
anos = [int(k[1:]) for k in h if isinstance(k, str) and k.startswith('y') and k[1:].isdigit()]
acc = {}
for r in it:
    if r[ix['geocode']] is None: continue
    g, b, cl = int(r[ix['geocode']]), r[ix['biome']], int(r[ix['class']])
    l0, l1 = str(r[ix['class_level_0']]), str(r[ix['class_level_1']])
    cols = ['area_total_ha']
    if cl == 39: cols.append('soja_ha')
    if cl == 15: cols.append('pastagem_ha')
    if l1.startswith('1.'): cols.append('floresta_ha')
    if l0 == 'Natural': cols.append('natural_ha')
    if l1.startswith('3.'): cols.append('agropecuaria_ha')
    for y in anos:
        v = r[ix[f'y{y}']] or 0
        if not v: continue
        e = acc.setdefault((g, b, y), {})
        for c in cols: e[c] = e.get(c, 0) + v
out = pd.DataFrame([{'cod_ibge': k[0], 'bioma': k[1], 'ano': k[2], **v} for k, v in acc.items()]).fillna(0)
out.to_csv(B / 'dados/processados/cobertura_municipio_bioma_ano.csv', index=False)
print(out.shape, out.ano.min(), out.ano.max()); print(out.groupby('ano')[['soja_ha', 'pastagem_ha']].sum().loc[[1985, 2005, 2024]] / 1e6)
