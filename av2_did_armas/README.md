# AV2 PROFNIT – Flexibilização do acesso a armas e homicídios (DiD municipal, 2015–2024)

Projeto empírico de Diferenças em Diferenças (UNEMAT/PROFNIT, disciplina STATS). Este projeto
substitui a base simulada da proposta original por dados municipais reais de todos os 5.570 municípios.

## Desenho
- **Resultado:** homicídios por arma de fogo por 100 mil hab. (SIM/DATASUS, CID-10 X93–X95, município de residência).
  Homicídios por arma branca (X99) entram na tripla diferença e óbitos no trânsito (V01–V89) servem de placebo.
- **Tratamento (contínuo):** `delta_reg_pc` = novos registros de armas por civis (SINARM/PF) em 2019–2022 por mil hab. × Pós-2019.
  Coortes para Callaway & Sant'Anna: 1º ano (2019–2021) com taxa de registros ≥ 2× a média 2015–18.
- **Heterogeneidade:** fronteira agrícola ativa = desmatamento 2015–18 (MapBiomas Col. 11) acima da mediana.
- CACs (SIGMA/Exército) não têm dado público por município; o SINARM é a medida municipal disponível.

## Principais resultados
| Especificação | Efeito | p |
|---|---|---|
| TWFE com controles, por +1 registro/mil hab. | +0,225 homicídios/100 mil | 0,014 |
| Callaway & Sant'Anna (ATT) | +1,62 homicídios/100 mil | < 0,01 |
| DDD arma de fogo vs. arma branca | +0,19 | 0,03 |
| Interação com fronteira agrícola | −0,10 | 0,47 |

Ressalvas: o teste conjunto de pré-tendências do event study TWFE dá p = 0,04, e o placebo de trânsito é positivo no TWFE
(mas nulo no C&S). Ver Seções 7–8 do artigo.

## Arquivos
- `AV2_PROFNIT_Artigo_Revisado_Dados_Municipais.docx` – artigo completo revisado.
- `AV2_PROFNIT_Resultados_Municipais.docx` – relatório técnico dos resultados.
- `AV2_painel_municipal_Brasil.csv` / `.xlsx` – painel 5.570 × 10 (o .xlsx traz o dicionário de variáveis).
- `resultados_municipal.json`, `cs_resultados.json`, `fronteira_tratamento.json`, `fig*.png` – saídas.
- `AV2_SCRIPT_municipal.R` – replicação em R (fixest + did).
- `proposta_original/` – proposta inicial e a base **simulada** que ela usava (mantidas só para referência).

## Como reproduzir (rodar de dentro de `av2_did_armas/`)
```bash
pip install pandas numpy openpyxl pyfixest differences python-docx matplotlib scipy
./00_baixar_dados.sh                                   # IBGE/SIDRA e MapBiomas -> dados_intermediarios/
# opcional (já incluídos em dados_intermediarios/):
#   python 00a_sim_agregar.py dados_intermediarios/sim                      # SIM/DATASUS (OpenDataSUS)
#   python 00b_sinarm_agregar.py <pasta_SINARM> dados_intermediarios/sinarm_mun_raw.csv
python 01_painel_municipal.py dados_intermediarios AV2_painel_municipal_Brasil.csv
python 02_estima_municipal.py AV2_painel_municipal_Brasil.csv resultados_municipal.json
python 03_callaway_santanna.py AV2_painel_municipal_Brasil.csv cs_resultados.json
python 04_figuras.py
python 06_artigo_completo.py proposta_original/AV2_PROFNIT_Projeto_DiD.docx AV2_PROFNIT_Artigo_Revisado_Dados_Municipais.docx
```
`fronteira_tratamento.json` vem da especificação com a fronteira como grupo tratado, descrita na Seção 6 do artigo.

## Fontes
SINARM/Polícia Federal (dados abertos `REGISTROS_com_categoria`; servidor acessível só do Brasil, por isso foram usadas cópias
públicas idênticas no GitHub: `yurilq/IBMEC_DESENVOLVIMENTO_AGENTE_2026` e `AdrielCout/DadosPorteDeArmasBrasil`, validadas contra
o Anuário FBSP 2023, correlação de 0,89 por UF); SIM/DATASUS (OpenDataSUS); IBGE/SIDRA (6579, 4714, 5938, 1737);
MapBiomas Coleção 11; Fórum Brasileiro de Segurança Pública (Anuários 2022–2023).
