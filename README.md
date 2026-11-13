# IDF-MT — Índice de Inclusão Digital-Financeira dos Pequenos Negócios

Reprodução, com dados públicos baixados por API, do artigo *"Índice de Inclusão Digital-Financeira dos
Pequenos Negócios (IDF-MT): Desenvolvimento e Validação em Municípios Médios do Centro-Oeste Brasileiro"*.

## Como rodar

```bash
pip install pandas numpy scipy statsmodels
python scripts/coleta_apis.py                 # IBGE, BCB, Anatel, Ipeadata  (~2 min)
python scripts/cnpj_download_filter.py Estabelecimentos0 ... Estabelecimentos9   # Receita (~5,5 GB, filtra MT/MS/GO)
python scripts/cnpj_download_filter.py Simples
python scripts/coleta_inep.py                 # INEP: matrículas e Campus (requer os zips em data/raw/inep)
python scripts/build_indicadores.py           # monta data/processed/base_municipal_CO.csv
python scripts/idf_modelo.py artigo           # amostra do artigo (n = 33)
python scripts/idf_modelo.py todos            # variante: todos os 50-600 mil hab. sem capitais (n = 42)
python scripts/exporta_stata.py               # stata/idf_mp.dta
```

`data/raw/` não vai para o Git (arquivos grandes; é regenerado pelos scripts). As bases tratadas
ficam em `data/processed/` e os quadros do artigo em `resultados/<amostra>/`.

## Fontes e APIs

| Ind. | Indicador | Fonte / endpoint | Referência |
|---|---|---|---|
| I01 | Acessos BL fixa por 100 domicílios | Anatel, *Meu Município* (`dadosabertos/paineis_de_dados/meu_municipio/meu_municipio.zip`) ÷ domicílios ocupados Censo 2022 (SIDRA 4712) | dez/2024 |
| I02 | Cobertura 4G (% moradores) | Anatel, *Meu Município – Cobertura*, operadora "Todas", tecnologia 4G | dez/2024 |
| I03 | Cobertura 5G (% moradores) | idem, tecnologia 5G | dez/2024 |
| I04 | Backhaul de fibra | **não localizado em dados abertos**; o artigo reporta valor 1 para todos (DP = 0) → mantido constante e fora da normalização | — |
| I05 | Pontos de atendimento financeiro / 10 mil hab. | BCB Olinda `Informes_Agencias` + `Informes_PostosDeAtendimento` (agências, PAB, PAA, PAT, PAC) | cadastro atual; agências com início ≤ 2024 |
| I06 | Pontos de cooperativas / 10 mil hab. | BCB Olinda `Informes_PostosDeAtendimento` (PAC) | cadastro atual |
| I07 | Transações Pix recebidas por PJ, por empresa ativa (média mensal) | BCB Olinda `Pix_DadosAbertos/TransacoesPixPorMunicipio` (`QT_RecebedorPJ`) | jan–dez/2024 |
| I08 | % de empresas recebedoras de Pix | idem (`QT_PES_RecebedorPJ`, média mensal) ÷ empresas ativas | 2024 |
| I09 | Saldo de crédito por empresa ativa (R$ mil) | BCB ESTBAN municipal, verbete 160 (`/content/estatisticas/estatistica_bancaria_estban/municipio/202412_ESTBAN.csv.zip`) | dez/2024 |
| I10 | Empresas ativas / 1.000 hab. | Receita Federal, CNPJ dados abertos (WebDAV público), estabelecimentos situação 02 | snapshot 2025-01 |
| I11 | % optantes do Simples | Receita, arquivo Simples | snapshot 2025-01 |
| I12 | Taxa de abertura (%) | estabelecimentos com início de atividade em 2024 ÷ ativos | 2024 |
| I13 | Taxa de encerramento (%) (−) | estabelecimentos baixados (situação 08) em 2024 ÷ (ativos + baixados) | 2024 |
| I14 | Idade média das empresas ativas | data de início de atividade, em 31/12/2024 | 2024 |
| I15 | 25+ com médio completo ou mais (%) | IBGE SIDRA 10061 (Censo 2022) | 2022 |
| I16 | Matrículas técnicas e superiores / 1.000 hab. | INEP: Censo Escolar 2024 (`QT_MAT_PROF_TEC`) + Censo da Educação Superior 2024 (cursos presenciais) | 2024 |

Controles do probit: IDHM 2010 (Ipeadata `ADH_IDHM`), ln(população 2024) (SIDRA 6579),
ln(PIB per capita 2021) e % do VA agropecuário 2021 (SIDRA 5938; 2021 é o último ano com VA municipal no SIDRA).

## Diferenças em relação ao artigo (importante)

1. **Amostra.** Regra da versão IDF-MP: 50–600 mil hab., sem capitais e sem o entorno de Brasília.
   Com a **estimativa populacional de 2024** e excluindo os 9 municípios goianos da RIDE-DF acima de 50 mil hab.
   (Águas Lindas, Luziânia, Valparaíso, Planaltina, Novo Gama, Cidade Ocidental, Sto. Antônio do Descoberto,
   Formosa, Cristalina) obtêm-se exatamente **33 municípios (MT 13, MS 6, GO 14)**. Com a população do
   Censo 2022 (como diz o texto do IDF-MP) seriam 31 (Campo Novo do Parecis e Nova Andradina ficam abaixo de 50 mil).
2. **INEP (I16 e Campus).** `download.inep.gov.br` não envia o certificado intermediário; a cadeia é completada
   com o certificado "RNP ICPEdu GR46 OV TLS CA 2025" (GlobalSign, endereço AIA do próprio certificado),
   mantendo a verificação TLS. `scripts/coleta_inep.py` processa os microdados. *Campus* = curso presencial de
   universidade federal (13 dos 33); "qualquer curso superior presencial" não varia (32 dos 33). Definições
   alternativas (universidade pública, instituto federal, qualquer universidade) entram como robustez.
   A validade externa com o IBC (Anatel) e a correlação com o ICI-MP não foram calculadas.
3. **I04 (backhaul)** não entra (constante).
4. Agências e postos vêm do cadastro vigente do BCB (não há série histórica por API); agências abertas
   depois de 2024 foram excluídas, mas encerramentos ocorridos depois de 2024 não podem ser revertidos.
5. A normalização segue o artigo (winsorização P1/P99, min-max, I13 invertido, média aritmética por dimensão,
   média geométrica ponderada com pesos Delphi 25/20/25/15/15). Subíndices iguais a zero são truncados em 1e-6
   na média geométrica (o script informa quantos municípios caem nesse caso).
6. Pesos Delphi: o rascunho IDF-MP deixa os pesos em aberto; usam-se os da versão IDF-MT (25/20/25/15/15).

## Modelos estimados (`scripts/idf_modelo.py`)

- Índice: Quadro 4 (IDF e subíndices + alfa de Cronbach) e Quadro 5 (Spearman e variação média de posições com
  pesos iguais, PCA, agregação aritmética e normalização z).
- Determinantes: MQO com erros HC3, M1 = IDHM + ln(Pop), M2 (+ ln PIB pc), M4* (+ % agro no VA), M5* (+ EF de UF);
  R² ajustado, AIC, BIC, VIF; diagnósticos do M1 (Breusch-Pagan, RESET, Shapiro-Wilk, Cook > 4/n);
  M1 por dimensão (D1–D5).
- Robustez (Quadro 8): probit (efeitos marginais médios), modelo de probabilidade linear (HC3), logit ordenado
  (razões de chance) com teste de Brant aproximado; M1 com índices alternativos, sem observações influentes e
  por regressão quantílica na mediana.

## Resultados principais (amostra do artigo, n = 33)

| | |
|---|---|
| IDF-MP | média 45,5; DP 14,2; mín. 1,9 (Goianira, com subíndice D2 = 0); máx. 68,3 (Lucas do Rio Verde) |
| M1 (MQO, HC3) | IDHM = 516,9*** (EP 87,1); ln(Pop) = −1,58 (EP 2,19); R² aj. = 0,607 |
| Leitura | +0,01 no IDHM ⇒ +5,2 pontos no índice; o porte populacional não é significativo |
| M5* | IDHM segue significativo (496,6***); efeitos fixos de MS (+10,1**) e MT (+8,3*) em relação a GO |
| Robustez | IDHM positivo e significativo a 1% em probit (EMM 12,4), MPL (15,8) e logit ordenado (RC 2,33 por +0,01); ln(Pop) não significativo em nenhum |
| Ranking | Spearman com o Delphi: pesos iguais 0,993; aritmética 0,963; escore z 0,972; PCA 0,801 |

Tabelas completas em `resultados/artigo/` e `resultados/todos/` (`saida_completa.txt` traz todas as saídas).

## Arquivos para o usuário

- `artigo/Artigo_IDF-MP.docx` e `artigo/Artigo_IDF-MP.pdf` — artigo completo com os resultados.
- `stata/idf_mp.dta` — base com os 42 municípios (`amostra_artigo == 1` marca os 33 do artigo), 16 indicadores e controles.
- `stata/idf_mp.do` — reconstrói o índice (winsorização, min-max, subíndices, média geométrica) e roda todas as estimações
  (MQO HC3 M1–M5, diagnósticos, regressões por dimensão, probit, MPL, logit ordenado, regressão quantílica e robustez do ranking).
  Rodar a partir da pasta `stata/`.
