#!/usr/bin/env bash
# Baixa os insumos públicos (IBGE/SIDRA, MapBiomas) para dados_intermediarios/. Rodar de dentro de av2_did_armas/.
set -e; D=dados_intermediarios; mkdir -p $D
curl -s https://servicodados.ibge.gov.br/api/v1/localidades/municipios -o $D/ibge_mun.json
for y in 2015 2016 2017 2018 2019 2020 2021 2024; do curl -s "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/$y" -o $D/pop_$y.json; done
curl -s "https://apisidra.ibge.gov.br/values/t/4714/n6/all/v/93,6318/p/2022" -o $D/c22all.json
for y in 2015 2016 2017 2018 2019 2020 2021 2022 2023; do curl -s "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/513/p/$y" -o $D/pib_$y.json; done
curl -s "https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/201512,201612,201712,201812,201912,202012,202112,202212,202312" -o $D/ipca.json
curl -sL "https://brasil.mapbiomas.org/wp-content/uploads/sites/3/2026/10/MAPBIOMAS-BRAZIL-DEFORESTATION-ANNUAL-MUNICIPALITY-COLLECTION_11.xlsx" -o $D/mb_def.xlsx
# SIM/DATASUS (já agregado em dados_intermediarios/sim/sim_mun.csv): python 00a_sim_agregar.py dados_intermediarios/sim
