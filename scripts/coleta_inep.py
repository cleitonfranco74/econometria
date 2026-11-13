"""INEP: matrículas técnicas (Censo Escolar 2024) e superiores presenciais (Censo da Educação
Superior 2024) por município, e a variável Campus.

Download (o servidor do INEP não envia o certificado intermediário; a cadeia é completada com o
certificado "RNP ICPEdu GR46 OV TLS CA 2025", publicado pela GlobalSign no endereço AIA do próprio
certificado do INEP, mantendo a verificação TLS):
  https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_2024.zip
  https://download.inep.gov.br/microdados/microdados_censo_da_educacao_superior_2024.zip
Entrada: data/raw/inep/*.zip   Saída: data/raw/inep_municipal.csv
"""
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INEP = ROOT / "data" / "raw" / "inep"
UFS = {"50", "51", "52"}


def ler(zpath, sufixo, cols):
    z = zipfile.ZipFile(zpath)
    nome = next(n for n in z.namelist() if n.upper().endswith(sufixo.upper()))
    with z.open(nome) as f:
        df = pd.read_csv(f, sep=";", encoding="latin-1", usecols=lambda c: c in cols, dtype=str, low_memory=False)
    return df, nome


# ---------------------------------------------------------------- Censo Escolar: matrículas técnicas
esc, n1 = ler(INEP / "censo_escolar_2024.zip", "microdados_ed_basica_2024.csv",
              {"CO_MUNICIPIO", "QT_MAT_PROF_TEC"})
esc = esc[esc.CO_MUNICIPIO.str[:2].isin(UFS)]
esc["QT_MAT_PROF_TEC"] = pd.to_numeric(esc.QT_MAT_PROF_TEC, errors="coerce").fillna(0)
tec = esc.groupby("CO_MUNICIPIO").QT_MAT_PROF_TEC.sum().rename("mat_tecnicas_2024")
print(n1, "->", len(tec), "municípios com escolas")

# ---------------------------------------------------------------- Censo Superior: cursos presenciais
cur, n2 = ler(INEP / "censo_superior_2024.zip", "MICRODADOS_CADASTRO_CURSOS_2024.CSV",
              {"CO_MUNICIPIO", "TP_MODALIDADE_ENSINO", "QT_MAT", "CO_IES", "CO_CURSO", "TP_REDE",
               "TP_ORGANIZACAO_ACADEMICA", "TP_CATEGORIA_ADMINISTRATIVA", "NO_IES"})
cur = cur[cur.CO_MUNICIPIO.notna() & cur.CO_MUNICIPIO.str[:2].isin(UFS) & (cur.TP_MODALIDADE_ENSINO == "1")]
cur["QT_MAT"] = pd.to_numeric(cur.QT_MAT, errors="coerce").fillna(0)
sup = cur.groupby("CO_MUNICIPIO").agg(
    mat_superior_presencial_2024=("QT_MAT", "sum"),
    n_cursos_presenciais_2024=("CO_CURSO", "nunique"),
    n_ies_presenciais_2024=("CO_IES", "nunique"),
    n_ies_publicas_2024=("CO_IES", lambda s: s[cur.loc[s.index, "TP_REDE"] == "1"].nunique()))
print(n2, "->", len(sup), "municípios com cursos presenciais")

# Tipos de presença (cursos presenciais com matrícula):
#   TP_ORGANIZACAO_ACADEMICA 1 = universidade, 4 = instituto federal, 5 = CEFET
#   TP_CATEGORIA_ADMINISTRATIVA 1 = federal, 2 = estadual
cm = cur[cur.QT_MAT > 0]
org, cat = cm.TP_ORGANIZACAO_ACADEMICA, cm.TP_CATEGORIA_ADMINISTRATIVA
tipos = pd.DataFrame({
    "campus_univ_publica": (org == "1") & cat.isin(["1", "2"]),
    "campus_univ_federal": (org == "1") & (cat == "1"),
    "campus_if": org.isin(["4", "5"]),
    "campus_universidade": org == "1"}).groupby(cm.CO_MUNICIPIO).max().astype(int)
out = pd.concat([tec, sup, tipos], axis=1).fillna(0)
out.index.name = "cod_ibge"
# Qualquer curso superior presencial com matrícula (sem variação na amostra: 32 de 33 municípios)
out["campus_qualquer"] = (out.mat_superior_presencial_2024 > 0).astype(int)
out["campus_publico"] = (out.n_ies_publicas_2024 > 0).astype(int)
# Variável Campus do modelo: campus de universidade federal com curso presencial (13 dos 33 municípios)
out["campus"] = out.campus_univ_federal
out.reset_index().to_csv(ROOT / "data" / "raw" / "inep_municipal.csv", index=False)
print(out.describe().T.round(1))
