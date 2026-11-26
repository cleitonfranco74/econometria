"""Agrega os CSVs oficiais do SINARM/PF (REGISTROS_com_categoria_*.csv) por UF, município, ano e categoria.
Uso: python 00b_sinarm_agregar.py <pasta_com_os_csv_do_SINARM> dados_intermediarios/sinarm_mun_raw.csv
Fonte oficial: https://servicos.dpf.gov.br/dadosabertos/SINARM_CSV/REGISTROS/ (acessível do Brasil).
Cópia pública idêntica: github.com/yurilq/IBMEC_DESENVOLVIMENTO_AGENTE_2026 (pasta DADOS_SINARM/REGISTROS)."""
import sys, re, unicodedata, pandas as pd
src, out = sys.argv[1], sys.argv[2]
fs = ['REGISTROS_com_categoria_2015-2019.csv', 'REGISTROS_com_categoria_2020-2022.csv', 'REGISTROS_com_categoria_2023.csv',
      'REGISTROS_com_categoria_2024.csv', 'REGISTROS_com_categoria_2025.csv']
d = pd.concat([pd.read_csv(f'{src}/{f}', encoding='latin1', dtype=str, sep=None, engine='python').apply(lambda s: s.str.strip()) for f in fs])
d['TOTAL'] = d.TOTAL.astype(int); d['ano'] = d.ANO_EMISSAO.astype(int)
def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().replace('-', ' ').replace("'", ' ')
    return ' '.join(re.sub(r'[^A-Z ]', '', s).split())
d['k'] = d.UF + '|' + d.MUNICIPIO.map(norm)
g = d.groupby(['k', 'UF', 'MUNICIPIO', 'ano', 'CATEGORIA'], as_index=False).TOTAL.sum(); g['cod_ibge'] = None
g.to_csv(out, index=False); print(g.shape, g.TOTAL.sum())
