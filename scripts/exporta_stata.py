"""Exporta a base municipal para o Stata (stata/idf_mp.dta), com rótulos."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAP = {"5103403", "5002704", "5208707"}
ENT = {"5200258", "5212501", "5221858", "5217609", "5215231", "5205497", "5219753", "5208004", "5206206"}
b = pd.read_csv(ROOT / "data/processed/base_municipal_CO.csv", dtype={"cod_ibge": str})
d = b[(b.pop_2024 >= 50000) & (b.pop_2024 <= 600000) & ~b.cod_ibge.isin(CAP)].copy()
d["amostra_artigo"] = (~d.cod_ibge.isin(ENT)).astype(np.int8)
r = pd.read_csv(ROOT / "resultados/artigo/idf_ranking.csv", dtype={"cod_ibge": str})[["cod_ibge", "IDF"]]
d = d.merge(r.rename(columns={"IDF": "idf_python"}), on="cod_ibge", how="left")
IND = [f"I{i:02d}" for i in range(1, 17)]
CAMPUS = ["campus", "campus_univ_publica", "campus_if", "campus_universidade", "campus_qualquer"]
cols = (["cod_ibge", "municipio", "uf", "amostra_artigo", "pop_2024", "pop_2021", "domicilios_2022"] + IND +
        ["I16_censo2022", "idhm_2010", "ln_pop", "pib_pc_2021", "ln_pib_pc", "agro_va_pct"] + CAMPUS +
        ["mat_tecnicas_2024", "mat_superior_presencial_2024", "empresas_ativas", "idf_python"])
d = d[cols].sort_values(["uf", "municipio"]).reset_index(drop=True)
d.columns = [c.lower() for c in d.columns]
d["cod_ibge"] = d.cod_ibge.astype("int64")
for c in CAMPUS:
    d[c] = d[c].astype(np.int8)
lab = {
    "cod_ibge": "Código IBGE (7 dígitos)", "municipio": "Município", "uf": "Unidade federativa",
    "amostra_artigo": "1 = amostra do artigo (n=33; exclui entorno DF)",
    "pop_2024": "População estimada 2024 (IBGE)", "pop_2021": "População estimada 2021 (IBGE)",
    "domicilios_2022": "Domicílios ocupados, Censo 2022",
    "i01": "I01 Acessos BL fixa por 100 domicílios (Anatel dez/2024)",
    "i02": "I02 Cobertura 4G, % moradores (Anatel dez/2024)", "i03": "I03 Cobertura 5G, % moradores (Anatel dez/2024)",
    "i04": "I04 Backhaul de fibra (constante = 1)", "i05": "I05 Pontos de atendimento financeiro por 10 mil hab (BCB)",
    "i06": "I06 Postos de cooperativas (PAC) por 10 mil hab (BCB)",
    "i07": "I07 Transações Pix recebidas PJ por empresa ativa, média mensal 2024",
    "i08": "I08 % empresas recebedoras de Pix, média mensal 2024",
    "i09": "I09 Crédito (Estban verbete 160) por empresa ativa, R$ mil",
    "i10": "I10 Empresas ativas por mil hab (Receita)", "i11": "I11 % optantes do Simples Nacional",
    "i12": "I12 Taxa de abertura 2024 (%)", "i13": "I13 Taxa de encerramento 2024 (%) (-)",
    "i14": "I14 Idade média das empresas ativas (anos)", "i15": "I15 % 25+ com ensino médio completo ou mais (Censo 2022)",
    "i16": "I16 Matrículas técnicas + superiores presenciais por mil hab (INEP 2024)",
    "i16_censo2022": "Proxy antiga de I16: frequência a ensino superior por mil hab (Censo 2022)",
    "idhm_2010": "IDHM 2010 (Atlas Brasil/Ipeadata)", "ln_pop": "ln(população 2024)",
    "pib_pc_2021": "PIB per capita 2021 (R$)", "ln_pib_pc": "ln(PIB per capita 2021)",
    "agro_va_pct": "Agropecuária no VA 2021 (%)",
    "campus": "Campus de universidade federal com curso presencial (INEP 2024)",
    "campus_univ_publica": "Campus de universidade pública (federal/estadual) presencial",
    "campus_if": "Campus de instituto federal/CEFET presencial",
    "campus_universidade": "Campus de qualquer universidade presencial",
    "campus_qualquer": "Qualquer curso superior presencial com matrícula",
    "mat_tecnicas_2024": "Matrículas em cursos técnicos (Censo Escolar 2024)",
    "mat_superior_presencial_2024": "Matrículas em cursos superiores presenciais (Censo Superior 2024)",
    "empresas_ativas": "Estabelecimentos ativos (Receita, jan/2025)",
    "idf_python": "IDF-MP calculado em Python (conferência)"}
d.to_stata(ROOT / "stata/idf_mp.dta", write_index=False, version=118, variable_labels=lab,
           data_label="IDF-MP: municipios 50-600 mil hab MT/MS/GO, 2024")
print(d.shape, int(d.amostra_artigo.sum()), "campus na amostra:", int(d.loc[d.amostra_artigo == 1, "campus"].sum()))
