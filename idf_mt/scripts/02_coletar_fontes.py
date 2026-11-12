"""
02 - Coleta e organiza os indicadores que NÃO vêm do CNPJ.

Fontes (todas públicas):
  IBGE/SIDRA  : população 2024 (tab. 6579), PIB e VA 2021 (tab. 5938),
                Censo 2022 - domicílios (4712), pop. (4709), escolaridade 25+ (10061),
                pessoas 18+ que frequentavam escola (10059)
  Anatel      : Meu Município - acessos de banda larga fixa e cobertura 4G/5G (dez/2024)
  Base dos Dados (espelho GCS): backhaul Anatel; Censo da Educação Superior 2022 (IES)
  BCB         : agências e postos de atendimento (nov/2024), ESTBAN (dez/2024),
                Pix por município (2024, API Olinda)
  Atlas Brasil: IDHM 2010 (PNUD/Ipea/FJP)

Uso: python3 scripts/02_coletar_fontes.py   (rodar a partir da pasta idf_mt)
Saída: dados/processados/fontes_nao_cnpj.csv
"""
import json, os, unicodedata, urllib.parse, urllib.request
import numpy as np
import pandas as pd

BR = "dados/brutos"
os.makedirs("dados/processados", exist_ok=True)

# ---------------------------------------------------------------- amostra
# 33 municípios: 50 mil a 600 mil hab. (estimativa IBGE 2024), sem capitais e,
# em GO, sem os municípios da RIDE-DF (critério que reproduz n=13/6/14 do artigo)
AMOSTRA = {
    # MT
    5108402: "Várzea Grande", 5107602: "Rondonópolis", 5107909: "Sinop", 5107925: "Sorriso",
    5107958: "Tangará da Serra", 5107040: "Primavera do Leste", 5105259: "Lucas do Rio Verde",
    5102504: "Cáceres", 5101803: "Barra do Garças", 5100250: "Alta Floresta",
    5106224: "Nova Mutum", 5106752: "Pontes e Lacerda", 5102637: "Campo Novo do Parecis",
    # MS
    5003702: "Dourados", 5008305: "Três Lagoas", 5003207: "Corumbá", 5006606: "Ponta Porã",
    5005707: "Naviraí", 5006200: "Nova Andradina",
    # GO
    5201405: "Aparecida de Goiânia", 5201108: "Anápolis", 5218805: "Rio Verde",
    5220454: "Senador Canedo", 5221403: "Trindade", 5205109: "Catalão", 5211503: "Itumbiara",
    5211909: "Jataí", 5204508: "Caldas Novas", 5208806: "Goianira", 5208608: "Goianésia",
    5213103: "Mineiros", 5213806: "Morrinhos", 5210000: "Inhumas",
}
UF = {"50": "MS", "51": "MT", "52": "GO"}
COD = list(AMOSTRA)
df = pd.DataFrame({"cod_ibge": COD, "municipio": [AMOSTRA[c] for c in COD]})
df["uf"] = df.cod_ibge.astype(str).str[:2].map(UF)


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return " ".join(s.upper().replace("'", " ").replace("-", " ").split())


def get_json(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def sidra(caminho):
    """Consulta a API do SIDRA e devolve DataFrame com códigos/valores."""
    d = get_json("https://apisidra.ibge.gov.br/values" + caminho)
    t = pd.DataFrame(d[1:])
    t["cod_ibge"] = t.D1C.astype(int)
    t["valor"] = pd.to_numeric(t.V, errors="coerce")
    return t


LISTA = ",".join(map(str, COD))

# ---------------------------------------------------------------- IBGE
pop = sidra(f"/t/6579/n6/{LISTA}/v/9324/p/2021,2024")
df["pop_2024"] = df.cod_ibge.map(pop[pop.D3C == "2024"].set_index("cod_ibge").valor)
pop21 = pop[pop.D3C == "2021"].set_index("cod_ibge").valor

pib = sidra(f"/t/5938/n6/{LISTA}/v/37,498,513/p/2021")
pib = pib.pivot(index="cod_ibge", columns="D2C", values="valor")  # R$ mil
df["pib_2021_mil"] = df.cod_ibge.map(pib["37"])
df["pib_pc_2021"] = df.pib_2021_mil * 1000 / df.cod_ibge.map(pop21)          # R$
df["agro_va_pct"] = df.cod_ibge.map(pib["513"] / pib["498"] * 100)

dom = sidra(f"/t/4712/n6/{LISTA}/v/381/p/2022")
df["domicilios_2022"] = df.cod_ibge.map(dom.set_index("cod_ibge").valor)
pop22 = sidra(f"/t/4709/n6/{LISTA}/v/93/p/2022")
df["pop_2022"] = df.cod_ibge.map(pop22.set_index("cod_ibge").valor)

# I15: % de pessoas 25+ com médio completo ou mais (Censo 2022)
esc = sidra(f"/t/10061/n6/{LISTA}/v/2667/p/2022/c2/6794/c86/95251/c58/108866/c1568/120704,9495,99713")
esc = esc.pivot(index="cod_ibge", columns="D7C", values="valor")
df["I15"] = df.cod_ibge.map((esc["9495"] + esc["99713"]) / esc["120704"] * 100)

# I16 (proxy): pessoas 18+ que frequentavam escola por 1.000 hab. (Censo 2022)
freq = sidra(f"/t/10059/n6/{LISTA}/v/13284/p/2022")
freq = freq[(freq.D4C == "6794") & (freq.D5C == "95253") & (freq.D6C == "95251") & (freq.D7C == "95300")]
df["I16"] = df.cod_ibge.map(freq.set_index("cod_ibge").valor) / df.pop_2022 * 1000

# ---------------------------------------------------------------- Anatel
ac = pd.read_csv(f"{BR}/anatel/Meu_Municipio_Acessos.csv", sep=";", decimal=",", encoding="utf-8-sig")
ac = ac[(ac.Ano == 2024) & (ac["Mês"] == 12) & (ac["Serviço"] == "Banda Larga Fixa")]
df["acessos_blf_dez24"] = df.cod_ibge.map(ac.set_index("Código IBGE").Acessos)
# domicílios de 2024 estimados = domicílios Censo 2022 x crescimento populacional 2022-24
dom24 = df.domicilios_2022 * df.pop_2024 / df.pop_2022
df["I01"] = df.acessos_blf_dez24 / dom24 * 100

cob = pd.read_csv(f"{BR}/anatel/Meu_Municipio_Cobertura.csv", sep=";", decimal=",", encoding="utf-8-sig")
cob = cob[(cob.Ano == 2024) & (cob["Mês"] == 12) & (cob.Operadora == "Todas")]
for tec, ind in [("4G", "I02"), ("5G", "I03")]:
    s = cob[cob.Tecnologia == tec].set_index("Código IBGE")["% moradores cobertos"]
    df[ind] = df.cod_ibge.map(s)

bh = pd.read_csv(f"{BR}/basedosdados/br_anatel_banda_larga_fixa__backhaul.csv.gz")
# Base PGMU/Anatel: todos os municípios da amostra constam com "infraestrutura existente
# antes do Decreto 6.424/2008" (tecnologia não informada) -> presença de backhaul = 1
df["I04"] = df.cod_ibge.isin(bh.id_municipio).astype(int)

# ---------------------------------------------------------------- BCB: pontos de atendimento
def ler_unicad(arq):
    raw = pd.read_excel(arq, header=None)
    lin = raw.index[raw.iloc[:, 0].astype(str).str.strip() == "CNPJ"][0]
    t = pd.read_excel(arq, header=lin)
    t.columns = [str(c).strip().upper() for c in t.columns]
    t = t[pd.to_numeric(t["MUNICIPIO IBGE"], errors="coerce").notna()]
    t["cod_ibge"] = t["MUNICIPIO IBGE"].astype(int)
    t["SEGMENTO"] = t["SEGMENTO"].astype(str).str.strip()
    return t

ag = ler_unicad(f"{BR}/bcb_pontos/202411AGENCIAS.xlsx")
po = ler_unicad(f"{BR}/bcb_pontos/202411POSTOS.xlsx")
coop = po.SEGMENTO.str.contains("Cooperativa", case=False)
df["agencias"] = df.cod_ibge.map(ag.cod_ibge.value_counts()).fillna(0)
df["postos"] = df.cod_ibge.map(po.cod_ibge.value_counts()).fillna(0)
df["postos_coop"] = df.cod_ibge.map(po[coop].cod_ibge.value_counts()).fillna(0)
df["I05"] = (df.agencias + df.postos) / df.pop_2024 * 10000
df["I06"] = df.postos_coop / df.pop_2024 * 10000

# ---------------------------------------------------------------- BCB: ESTBAN (crédito)
est = pd.read_csv(f"{BR}/estban/202412_ESTBAN.CSV", sep=";", skiprows=2, encoding="latin-1")
est["chave"] = est.UF + "|" + est.MUNICIPIO.map(norm)
cred = est.groupby("chave")["VERBETE_160_OPERACOES_DE_CREDITO"].sum()
df["credito_dez24"] = (df.uf + "|" + df.municipio.map(norm)).map(cred)   # R$

# ---------------------------------------------------------------- BCB: Pix (2024)
pix = []
for uf_ibge in (50, 51, 52):
    filtro = f"Estado_Ibge eq {uf_ibge} and AnoMes ge 202401 and AnoMes le 202412"
    q = "&".join(f"{k}={urllib.parse.quote(str(v), safe=',')}" for k, v in
                 {"@DataBase": "'202401'", "$filter": filtro, "$format": "json", "$top": 100000,
                  "$select": "AnoMes,Municipio_Ibge,QT_RecebedorPJ,QT_PES_RecebedorPJ"}.items())
    url = ("https://olinda.bcb.gov.br/olinda/servico/Pix_DadosAbertos/versao/v1/odata/"
           "TransacoesPixPorMunicipio(DataBase=@DataBase)?" + q)
    pix += get_json(url)["value"]
pix = pd.DataFrame(pix)
pix.to_csv(f"{BR}/pix_2024_mt_ms_go.csv", index=False)
pix = pix[pix.Municipio_Ibge.isin(COD)]
# mediana mensal de 2024 (robusta a meses com registros anômalos)
med = pix.groupby("Municipio_Ibge")[["QT_RecebedorPJ", "QT_PES_RecebedorPJ"]].median()
df["pix_trans_receb_pj_mes"] = df.cod_ibge.map(med.QT_RecebedorPJ)
df["pix_pj_recebedoras_mes"] = df.cod_ibge.map(med.QT_PES_RecebedorPJ)
df["pix_meses"] = df.cod_ibge.map(pix.groupby("Municipio_Ibge").size())

# ---------------------------------------------------------------- Educação superior: Campus
ies = pd.read_csv(f"{BR}/basedosdados/br_inep_censo_educacao_superior__ies.csv.gz",
                  usecols=["ano", "id_municipio", "tipo_organizacao_academica", "sigla"])
ies = ies[(ies.ano == 2022) & ies.tipo_organizacao_academica.isin([1, 2])]  # univ. ou centro univ.
df["campus"] = df.cod_ibge.isin(ies.id_municipio).astype(int)

# ---------------------------------------------------------------- IDHM (Atlas Brasil)
atl = pd.read_excel(f"{BR}/atlas/censo_total_1991_2010.xlsx", sheet_name="MUN 91-00-10",
                    usecols=["ANO", "Codmun7", "IDHM", "GINI", "THEIL"])
atl = atl[atl.ANO == 2010].set_index("Codmun7")
df["idhm_2010"] = df.cod_ibge.map(atl.IDHM)
# Índice de Gini da renda domiciliar per capita (Censo 2010, Atlas Brasil).
# Obs.: os microdados públicos do Censo 2022 não identificam o município, e o IBGE
# não publicou Gini municipal de 2022 no SIDRA até a data da coleta.
df["gini_2010"] = df.cod_ibge.map(atl.GINI)
df["theil_2010"] = df.cod_ibge.map(atl.THEIL)

df.to_csv("dados/processados/fontes_nao_cnpj.csv", index=False)
print(df.to_string())
print("\nFaltantes:\n", df.isna().sum()[df.isna().sum() > 0])
