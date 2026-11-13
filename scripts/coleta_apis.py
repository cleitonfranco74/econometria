"""Coleta via API dos dados públicos do IDF-MT (exceto CNPJ, ver cnpj_download_filter.py).

Fontes:
  IBGE/SIDRA  - população 2024 (6579), domicílios Censo 2022 (4712), PIB/VA municipal (5938),
                escolaridade 25+ (10061), frequência a curso superior 18+ (10059)
  BCB/Olinda  - Pix por município (2024), agências e postos de atendimento (cadastro atual)
  BCB/ESTBAN  - estatística bancária por município, dez/2024
  Anatel      - painel "Meu Município": acessos BL fixa e cobertura 4G/5G (dez/2024)
Saída: data/raw/*.csv
"""
import io
import json
import subprocess
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
UF_COD = "50,51,52"  # MS, MT, GO


def get(url: str, binary=False, tries=5):
    for i in range(tries):
        r = subprocess.run(["curl", "-sS", "-f", "-m", "600", "--compressed", url], capture_output=True)
        if r.returncode == 0:
            return r.stdout if binary else r.stdout.decode("utf-8")
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"falha: {url}\n{r.stderr.decode()}")


# ----------------------------------------------------------------- IBGE / SIDRA
def sidra(path: str) -> pd.DataFrame:
    d = json.loads(get("https://apisidra.ibge.gov.br/values/" + path))
    df = pd.DataFrame(d[1:])
    df["V"] = pd.to_numeric(df["V"], errors="coerce")
    return df


def coleta_ibge():
    mun = f"n6/in%20n3%20{UF_COD}"
    pop = sidra(f"t/6579/{mun}/v/9324/p/2021,2024")
    pop = pop.pivot_table(index=["D1C", "D1N"], columns="D3C", values="V").reset_index()
    pop.columns = ["cod_ibge", "municipio", "pop_2021", "pop_2024"]

    dom = sidra(f"t/4712/{mun}/v/381/p/2022")[["D1C", "V"]].rename(columns={"D1C": "cod_ibge", "V": "domicilios_2022"})

    pib = sidra(f"t/5938/{mun}/v/37,498,513/p/2021")
    pib = pib.pivot_table(index="D1C", columns="D2C", values="V").reset_index()
    pib.columns = ["cod_ibge", "pib_2021_mil", "va_total_2021_mil", "va_agro_2021_mil"]

    # Pessoas 25+ por nível de instrução (Censo 2022)
    edu = sidra(f"t/10061/{mun}/v/2667/p/2022/c2/6794/c86/95251/c58/108866/c1568/120704,9495,99713")
    edu = edu.pivot_table(index="D1C", columns="D7C", values="V").reset_index()
    edu = edu.rename(columns={"D1C": "cod_ibge", "120704": "pop25_total", "9495": "pop25_medio_sup_inc",
                              "99713": "pop25_superior"})

    # Pessoas 18+ que frequentavam curso superior (graduação, especialização, mestrado, doutorado)
    fre = sidra(f"t/10059/{mun}/v/13284/p/2022/c2/6794/c58/95253/c11798/95307,7910,7911,7912/c86/95251")
    fre = fre.groupby("D1C")["V"].sum().reset_index().rename(columns={"D1C": "cod_ibge", "V": "freq_superior_2022"})

    df = pop.merge(dom, on="cod_ibge").merge(pib, on="cod_ibge").merge(edu, on="cod_ibge").merge(fre, on="cod_ibge")
    df["uf"] = df["municipio"].str[-2:]
    df["municipio"] = df["municipio"].str[:-5]
    df.to_csv(RAW / "ibge.csv", index=False)
    print("IBGE:", df.shape)


# ----------------------------------------------------------------- BCB
OLINDA = "https://olinda.bcb.gov.br/olinda/servico"


def olinda_all(url_base: str, top=1_000_000) -> pd.DataFrame:
    # Alguns serviços Olinda recusam $skip: pede-se tudo numa página só.
    sep = "&" if "?" in url_base else "?"
    d = json.loads(get(f"{url_base}{sep}$format=json&$top={top}"))["value"]
    assert len(d) < top, "resultado truncado"
    return pd.DataFrame(d)


def coleta_bcb():
    # DataBase = mês inicial; a API devolve esse mês e os seguintes
    pix = pd.concat([olinda_all(
        f"{OLINDA}/Pix_DadosAbertos/versao/v1/odata/TransacoesPixPorMunicipio(DataBase=@DataBase)"
        f"?@DataBase='202401'&$filter=Estado_Ibge%20eq%20{uf}%20and%20AnoMes%20le%20202412")
        for uf in (50, 51, 52)])
    pix = pix[(pix.AnoMes >= 202401) & (pix.AnoMes <= 202412)]
    pix.to_csv(RAW / "bcb_pix_2024.csv", index=False)
    print("Pix:", pix.shape, sorted(pix.AnoMes.unique()))

    ag = olinda_all(f"{OLINDA}/Informes_Agencias/versao/v1/odata/Agencias")
    ag = ag[ag.UF.isin(["MT", "MS", "GO"])]
    ag.to_csv(RAW / "bcb_agencias.csv", index=False)
    po = olinda_all(f"{OLINDA}/Informes_PostosDeAtendimento/versao/v1/odata/PostosAtendimento")
    po = po[po.UF.isin(["MT", "MS", "GO"])]
    po.to_csv(RAW / "bcb_postos.csv", index=False)
    print("Agências:", ag.shape, "Postos:", po.shape)

    z = zipfile.ZipFile(io.BytesIO(get(
        "https://www.bcb.gov.br/content/estatisticas/estatistica_bancaria_estban/municipio/202412_ESTBAN.csv.zip",
        binary=True)))
    raw = z.read(z.namelist()[0]).decode("latin-1")
    lines = raw.splitlines()
    start = next(i for i, l in enumerate(lines) if l.upper().startswith("#DATA_BASE") or l.upper().startswith("DATA_BASE"))
    est = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=";", decimal=",")
    est.columns = [c.lstrip("#") for c in est.columns]
    est = est[est["UF"].isin(["MT", "MS", "GO"])]
    est.to_csv(RAW / "bcb_estban_202412.csv", index=False)
    print("ESTBAN:", est.shape)


# ----------------------------------------------------------------- Anatel
def coleta_anatel():
    z = zipfile.ZipFile(io.BytesIO(get(
        "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/meu_municipio/meu_municipio.zip", binary=True)))
    ac = pd.read_csv(z.open("Meu_Municipio_Acessos.csv"), sep=";", decimal=",", encoding="utf-8-sig")
    ac = ac[(ac.UF.isin(["MT", "MS", "GO"])) & (ac.Ano == 2024) & (ac["Mês"] == 12)]
    ac.to_csv(RAW / "anatel_acessos_202412.csv", index=False)
    cob = pd.read_csv(z.open("Meu_Municipio_Cobertura.csv"), sep=";", decimal=",", encoding="utf-8-sig")
    cob = cob[(cob.UF.isin(["MT", "MS", "GO"])) & (cob.Ano == 2024) & (cob["Mês"] == 12)
              & (cob.Operadora.str.upper() == "TODAS")]
    cob.to_csv(RAW / "anatel_cobertura_202412.csv", index=False)
    print("Anatel:", ac.shape, cob.shape)


# ----------------------------------------------------------------- Ipeadata (IDHM, Atlas Brasil)
def coleta_ipea():
    d = json.loads(get("https://ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='ADH_IDHM')"))["value"]
    df = pd.DataFrame(d)
    df = df[(df.NIVNOME == "Municípios") & (df.VALDATA.str[:4] == "2010")]
    df = df[df.TERCODIGO.str[:2].isin(UF_COD.split(","))]
    df[["TERCODIGO", "VALVALOR"]].rename(columns={"TERCODIGO": "cod_ibge", "VALVALOR": "idhm_2010"}) \
        .to_csv(RAW / "ipea_idhm_2010.csv", index=False)
    print("IDHM:", df.shape)


if __name__ == "__main__":
    import sys
    etapas = sys.argv[1:] or ["ibge", "bcb", "anatel", "ipea"]
    for e in etapas:
        globals()[f"coleta_{e}"]()
