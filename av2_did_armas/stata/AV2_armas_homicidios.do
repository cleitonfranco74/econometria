/*==============================================================================
  Mais armas, mais homicídios? Flexibilização do acesso a armas de fogo e
  violência letal nos municípios brasileiros e na fronteira da soja (2015-2024)

  Do-file de replicação das Tabelas 1 a 7 do paper.
  Base: AV2_armas_homicidios.dta (5.570 municípios x 2015-2024 = 55.700 obs.)

  Fontes: SINARM/Polícia Federal (registros de armas), SIM/DATASUS (óbitos),
          IBGE (população, área, PIB, PAM-soja) e MapBiomas Col. 11 (desmatamento).

  Pacotes (instalar uma vez):
    ssc install reghdfe, replace
    ssc install ftools, replace
    ssc install ppmlhdfe, replace
    ssc install csdid, replace
    ssc install drdid, replace
    ssc install sdid, replace
    ssc install estout, replace
    ssc install event_plot, replace
==============================================================================*/

version 17
clear all
set more off
set seed 42

* Ajuste o caminho da pasta
* cd "C:/caminho/para/av2_did_armas/stata"

use "AV2_armas_homicidios.dta", clear
xtset cod_ibge ano

* Controles variantes no tempo
global X "log_vab_agro_pc log_densidade_pop taxa_mortalidade_covid"

* Variáveis de tratamento
gen did      = delta_reg_pc * pos_2019              // efeito de +1 registro por mil hab.
gen did_int  = intens_reg   * pos_2019              // versão Min-Max [0,1]
gen did_23   = delta_reg_pc * pos_2023              // reversão (Decreto 11.615/2023)
gen did_fr   = did * fronteira_ativa                // heterogeneidade: fronteira agrícola
gen did_bin  = tratamento_quartil_sup * pos_2019    // tratamento binário (quartil superior)
gen did_exc  = excesso_reg_pc * pos_2019            // intensidade em excesso a 2015-18
label var did     "Delta REG x Pós-2019"
label var did_fr  "Delta REG x Pós-2019 x Fronteira"
label var did_23  "Delta REG x Pós-2023"

/*------------------------------------------------------------------------------
  TABELA 1 - Estatísticas descritivas por grupo territorial e período
------------------------------------------------------------------------------*/
tabstat delta_reg_pc reg_cidadao_1000 taxa_homic_af taxa_homic_ab taxa_obitos_transito if pos_2019 == 0, ///
    by(fronteira_ativa) statistics(mean sd) columns(statistics) format(%9.2f)
tabstat delta_reg_pc reg_cidadao_1000 taxa_homic_af taxa_homic_ab taxa_obitos_transito if pos_2019 == 1, ///
    by(fronteira_ativa) statistics(mean sd) columns(statistics) format(%9.2f)

* Taxa agregada de homicídios por arma de fogo (óbitos totais / população total)
preserve
    collapse (sum) af reg_cidadao pop, by(fronteira_ativa pos_2019)
    gen taxa_af_agregada  = af / pop * 1e5
    gen registros_por_mil = reg_cidadao / pop * 1000
    list fronteira_ativa pos_2019 taxa_af_agregada registros_por_mil, noobs
restore

/*------------------------------------------------------------------------------
  TABELA 2 - Efeito da expansão dos registros sobre homicídios por arma de fogo
------------------------------------------------------------------------------*/
eststo clear
eststo m1: reghdfe taxa_homic_af did              [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
eststo m2: reghdfe taxa_homic_af did $X           [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
eststo m3: reghdfe taxa_homic_af did did_fr $X    [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
eststo m4: reghdfe taxa_homic_af did did_23 $X    [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
* Poisson com efeitos fixos (contagem de óbitos; offset = log da população)
eststo m5: ppmlhdfe af did $X, absorb(cod_ibge ano) exposure(pop) vce(cluster cod_ibge)
* Intensidade na escala Min-Max do projeto original
eststo m6: reghdfe taxa_homic_af did_int $X       [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)

esttab m1 m2 m3 m4 m5 m6 using "tabela2_principal.rtf", replace ///
    keep(did did_fr did_23 did_int) se star(* 0.10 ** 0.05 *** 0.01) b(3) se(3) ///
    mtitles("TWFE" "TWFE" "Fronteira" "Reversão" "Poisson" "Min-Max") ///
    title("Tabela 2 - Homicídios por arma de fogo por 100 mil hab.")

* Callaway & Sant'Anna (2021): coortes 2019/2020/2021 (ano_primeiro_salto = 0: nunca tratado)
* Coluna (6) do paper. Ponderação pela população, como na versão em Python.
csdid taxa_homic_af [iw = pop], ivar(cod_ibge) time(ano) gvar(ano_primeiro_salto) notyet
estat simple
estat event, window(-5 5)
* event_plot, default_look graph_opt(xtitle("Anos em relação ao 1º salto de registros"))

* Mesma estimação com os nunca tratados como controle
csdid taxa_homic_af [iw = pop], ivar(cod_ibge) time(ano) gvar(ano_primeiro_salto)
estat simple

/*------------------------------------------------------------------------------
  TABELA 3 - Event study (ano de referência: 2018)
------------------------------------------------------------------------------*/
forvalues y = 2015/2024 {
    if `y' != 2018 gen ev`y' = delta_reg_pc * (ano == `y')
}
eststo clear
foreach v in taxa_homic_af taxa_homic_ab taxa_obitos_transito {
    eststo es_`v': reghdfe `v' ev2015 ev2016 ev2017 ev2019-ev2024 $X [aw = pop], ///
        absorb(cod_ibge ano) vce(cluster cod_ibge)
    test ev2015 ev2016 ev2017            // teste conjunto pré-tratamento
}
esttab es_taxa_homic_af es_taxa_obitos_transito using "tabela3_event_study.rtf", replace ///
    keep(ev*) se star(* 0.10 ** 0.05 *** 0.01) b(3) se(3) ///
    mtitles("Homic. arma de fogo" "Placebo: trânsito")
* coefplot es_taxa_homic_af, keep(ev*) vertical yline(0)   // requer: ssc install coefplot

/*------------------------------------------------------------------------------
  TABELA 4 - Testes de robustez
------------------------------------------------------------------------------*/
eststo clear
* (1) Tripla diferença: arma de fogo vs. arma branca no mesmo município e ano
preserve
    keep cod_ibge ano pop pos_2019 delta_reg_pc taxa_homic_af taxa_homic_ab
    reshape long taxa_homic_, i(cod_ibge ano) j(meio) string
    gen af  = (meio == "af")
    gen ddd = delta_reg_pc * af * pos_2019
    eststo r1: reghdfe taxa_homic_ ddd [aw = pop], absorb(cod_ibge#af ano#af cod_ibge#ano) vce(cluster cod_ibge)
restore
* (2) Placebo de resultado: óbitos no trânsito
eststo r2: reghdfe taxa_obitos_transito did $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
* (3) Placebo temporal: choque fictício em 2017, amostra 2015-2018
gen did_p = delta_reg_pc * (ano >= 2017)
eststo r3: reghdfe taxa_homic_af did_p log_vab_agro_pc log_densidade_pop [aw = pop] if ano <= 2018, absorb(cod_ibge ano) vce(cluster cod_ibge)
* (4) Tratamento binário: quartil superior
eststo r4: reghdfe taxa_homic_af did_bin $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
* (5)-(6) Homicídios por arma branca e por outros meios
eststo r5: reghdfe taxa_homic_ab     did $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
eststo r6: reghdfe taxa_homic_outros did $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
* (7) Tendências por linha de base de registros (pre_reg_pc x EF de ano)
eststo r7: reghdfe taxa_homic_af did $X c.pre_reg_pc#i.ano [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
* (8) EF de UF x ano
eststo r8: reghdfe taxa_homic_af did $X [aw = pop], absorb(cod_ibge uf_id#ano) vce(cluster cod_ibge)
* (9) Intensidade em excesso a 2015-18
eststo r9: reghdfe taxa_homic_af did_exc $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
* (10) Sem ponderação
eststo r10: reghdfe taxa_homic_af did $X, absorb(cod_ibge ano) vce(cluster cod_ibge)
* (11) Municípios com 20 mil hab. ou mais (pop. mínima no período), sem ponderação
bys cod_ibge: egen pop_min = min(pop)
eststo r11: reghdfe taxa_homic_af did $X if pop_min >= 20000, absorb(cod_ibge ano) vce(cluster cod_ibge)
* (12)-(13) Subamostras: fronteira agrícola e consolidados
eststo r12: reghdfe taxa_homic_af did $X [aw = pop] if fronteira_ativa == 1, absorb(cod_ibge ano) vce(cluster cod_ibge)
eststo r13: reghdfe taxa_homic_af did $X [aw = pop] if fronteira_ativa == 0, absorb(cod_ibge ano) vce(cluster cod_ibge)
* (14) Amostra original de 50 municípios
eststo r14: reghdfe taxa_homic_af did $X if amostra_projeto_50 == 1, absorb(cod_ibge ano) vce(cluster cod_ibge)

esttab r* using "tabela4_robustez.rtf", replace keep(ddd did did_p did_bin did_exc) ///
    se star(* 0.10 ** 0.05 *** 0.01) b(3) se(3) title("Tabela 4 - Robustez")

/*------------------------------------------------------------------------------
  TABELA 5 - Synthetic Difference-in-Differences (Arkhangelsky et al., 2021)
  Observação: o comando sdid não aceita ponderação dos tratados pela população;
  as linhas "tratados ponderados" do paper vêm do script Python 08_sdid.py.
------------------------------------------------------------------------------*/
* Quartis de delta_reg_pc entre municípios
bys cod_ibge (ano): gen byte primeiro = (_n == 1)
xtile q_reg = delta_reg_pc if primeiro, nq(4)
bys cod_ibge (q_reg): replace q_reg = q_reg[1]
gen pop18 = pop2018

* (A) Q4 vs. Q1, todos os municípios
preserve
    keep if inlist(q_reg, 1, 4)
    gen D = (q_reg == 4) * pos_2019
    sdid taxa_homic_af cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(sdid)
    sdid taxa_homic_af cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(did)
    sdid taxa_homic_af cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(sc)
restore
* (B) Q4 vs. Q1, municípios com 20 mil hab. ou mais em 2018
preserve
    keep if inlist(q_reg, 1, 4) & pop18 >= 20000
    gen D = (q_reg == 4) * pos_2019
    sdid taxa_homic_af cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(sdid) graph
restore
* (C) Coorte de 2019 vs. nunca tratados (todos e >= 20 mil hab.)
preserve
    keep if inlist(ano_primeiro_salto, 0, 2019)
    gen D = (ano_primeiro_salto == 2019) * pos_2019
    sdid taxa_homic_af cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(sdid)
    sdid taxa_homic_af cod_ibge ano D if pop18 >= 20000, vce(bootstrap) reps(200) seed(42) method(sdid) graph
restore
* Placebos (>= 20 mil hab., Q4 vs. Q1)
preserve
    keep if inlist(q_reg, 1, 4) & pop18 >= 20000
    gen D = (q_reg == 4) * pos_2019
    sdid taxa_homic_ab        cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(sdid)
    sdid taxa_obitos_transito cod_ibge ano D, vce(bootstrap) reps(200) seed(42) method(sdid)
restore

/*------------------------------------------------------------------------------
  TABELA 6 - Fronteira da soja como grupo tratado
  grupo_soja: 0 = sem soja; 1 = soja consolidada; 2 = fronteira da soja
  Fronteira da soja: Amazônia/Cerrado, >= 1.000 ha de soja em 2018, área +50% desde
  2010 e perda de vegetação primária 2015-18 acima da mediana do bioma.
------------------------------------------------------------------------------*/
gen fp = fronteira_soja * pos_2019
forvalues y = 2015/2024 {
    if `y' != 2018 gen fs`y' = fronteira_soja * (ano == `y')
}
eststo clear
foreach c in 0 1 {     // c = 0: vs. sem soja ; c = 1: vs. soja consolidada
    preserve
        keep if inlist(grupo_soja, 2, `c')
        eststo fs1_`c': reghdfe reg_cidadao_1000 fp [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)   // 1º estágio
        eststo fs2_`c': reghdfe taxa_homic_af fp $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
        eststo fs3_`c': reghdfe taxa_homic_af fp $X,           absorb(cod_ibge ano) vce(cluster cod_ibge)
        eststo fs4_`c': reghdfe taxa_homic_ab fp $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)   // placebo
        reghdfe taxa_homic_af fs2015 fs2016 fs2017 fs2019-fs2024 $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)
        test fs2015 fs2016 fs2017
        * SDID
        sdid taxa_homic_af cod_ibge ano fp, vce(bootstrap) reps(200) seed(42) method(sdid)
        * Callaway & Sant'Anna, tratamento em bloco em 2019
        gen g_bloco = 2019 * fronteira_soja
        csdid taxa_homic_af, ivar(cod_ibge) time(ano) gvar(g_bloco)
        estat simple
        csdid taxa_homic_af [iw = pop], ivar(cod_ibge) time(ano) gvar(g_bloco)
        estat simple
        csdid taxa_homic_ab, ivar(cod_ibge) time(ano) gvar(g_bloco)     // placebo
        estat simple
    restore
}
* Callaway & Sant'Anna escalonado: coorte = 1º salto de registros na fronteira da soja;
* controles = soja consolidada (nunca tratados) e ainda não tratados; fronteira sem salto excluída.
preserve
    keep if grupo_soja == 1 | (grupo_soja == 2 & ano_primeiro_salto > 0)
    gen g_soja = cond(grupo_soja == 2, ano_primeiro_salto, 0)
    csdid taxa_homic_af, ivar(cod_ibge) time(ano) gvar(g_soja) notyet
    estat simple
    estat event, window(-5 5)
    csdid taxa_homic_af [iw = pop], ivar(cod_ibge) time(ano) gvar(g_soja) notyet
    estat simple
restore
* Tripla interação com a intensidade contínua (todos os municípios)
gen ddd_soja = did * fronteira_soja
reghdfe taxa_homic_af did ddd_soja $X [aw = pop], absorb(cod_ibge ano) vce(cluster cod_ibge)

esttab fs* using "tabela6_fronteira_soja.rtf", replace keep(fp) se star(* 0.10 ** 0.05 *** 0.01) b(3) se(3)

/*------------------------------------------------------------------------------
  TABELA 7 - Desmatamento e registros de armas por civis
------------------------------------------------------------------------------*/
eststo clear
* Painel A: dentro do município (2015-2024)
eststo d1: reghdfe reg_cidadao_1000 desmat_pct      [aw = pop], absorb(cod_ibge ano)       vce(cluster cod_ibge)
eststo d2: reghdfe reg_cidadao_1000 desmat_pct      [aw = pop], absorb(cod_ibge uf_id#ano) vce(cluster cod_ibge)
eststo d3: reghdfe reg_cidadao_1000 L.desmat_pct    [aw = pop], absorb(cod_ibge uf_id#ano) vce(cluster cod_ibge)
eststo d4: reghdfe reg_cidadao_1000 desmat_prim_pct [aw = pop], absorb(cod_ibge uf_id#ano) vce(cluster cod_ibge)
* Painel B: entre municípios, por bioma (desmatamento acumulado 2015-18 -> registros 2019-22)
bys cod_ibge: egen d1518 = total(desmat_pct * (ano <= 2018))
preserve
    keep if ano == 2015
    eststo b0: reghdfe delta_reg_pc d1518 log_vab_agro_pc log_densidade_pop log_pop pre_reg_pc, absorb(uf_id) vce(robust)
    foreach b in "Amazônia" "Cerrado" "Mata Atlântica" "Caatinga" "Pampa" {
        reghdfe delta_reg_pc d1518 log_vab_agro_pc log_densidade_pop log_pop pre_reg_pc if bioma == "`b'", absorb(uf_id) vce(robust)
    }
restore
esttab d1 d2 d3 d4 b0 using "tabela7_desmatamento.rtf", replace se star(* 0.10 ** 0.05 *** 0.01) b(3) se(3)

* Fim
