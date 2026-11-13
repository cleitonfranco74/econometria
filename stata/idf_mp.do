*==============================================================================*
* IDF-MP — Índice de Inclusão Digital-Financeira dos Pequenos Negócios
* Construção do índice, robustez e estimações do artigo
*
* Base   : idf_mp.dta (42 municípios de 50-600 mil hab. de MT/MS/GO, sem capitais;
*          amostra_artigo == 1 identifica os 33 do artigo, sem o entorno do DF)
* Fontes : IBGE/SIDRA, BCB (Pix, agências/postos, Estban), Anatel, Receita Federal,
*          Ipeadata (IDHM 2010). Ano-base 2024.
* Stata  : 15 ou superior. Pacote opcional: spost13 (teste de Brant).
*
* Para rodar com os 42 municípios, troque o valor do local AMOSTRA abaixo.
*==============================================================================*

version 15
clear all
set more off
capture log close
log using "idf_mp_resultados.log", replace text

use "idf_mp.dta", clear

local AMOSTRA "artigo"          // "artigo" (n = 33) ou "todos" (n = 42)
if "`AMOSTRA'" == "artigo" keep if amostra_artigo == 1
count
local N = r(N)

encode uf, gen(uf_n)            // GO = 1 (base), MS = 2, MT = 3
label var uf_n "Unidade federativa"

*------------------------------------------------------------------------------*
* 1. Normalização: winsorização P1/P99 + min-max (I13 invertido)
*    Percentis por interpolação linear (mesma regra do pandas: posição (n-1)p)
*------------------------------------------------------------------------------*
capture program drop pct_lin
program define pct_lin, rclass
    args var p
    preserve
    quietly keep if !missing(`var')
    sort `var'
    local n = _N
    local h = (`n' - 1) * `p' + 1
    local lo = floor(`h')
    local hi = min(`lo' + 1, `n')
    local v = `var'[`lo'] + (`h' - `lo') * (`var'[`hi'] - `var'[`lo'])
    restore
    return scalar q = `v'
end

foreach v of varlist i01-i16 {
    quietly summarize `v'
    if r(sd) == 0 {
        display as text "`v' é constante: fora da normalização"
        continue
    }
    pct_lin `v' 0.01
    local p1 = r(q)
    pct_lin `v' 0.99
    local p99 = r(q)
    quietly gen double w_`v' = min(max(`v', `p1'), `p99')
    quietly summarize w_`v'
    quietly gen double n_`v' = (w_`v' - r(min)) / (r(max) - r(min))
    quietly gen double z_`v' = (w_`v' - r(mean)) / r(sd)
    if "`v'" == "i13" {
        quietly replace n_`v' = 1 - n_`v'
        quietly replace z_`v' = -z_`v'
    }
}

*------------------------------------------------------------------------------*
* 2. Subíndices (média simples) e IDF-MP (média geométrica ponderada, pesos Delphi)
*------------------------------------------------------------------------------*
egen double S_D1 = rowmean(n_i01 n_i02 n_i03)            // I04 constante
egen double S_D2 = rowmean(n_i05 n_i06)
egen double S_D3 = rowmean(n_i07 n_i08 n_i09)
egen double S_D4 = rowmean(n_i10 n_i11 n_i12 n_i13 n_i14)
egen double S_D5 = rowmean(n_i15 n_i16)
label var S_D1 "D1 Infraestrutura Digital"
label var S_D2 "D2 Acesso Financeiro"
label var S_D3 "D3 Uso Digital-Financeiro"
label var S_D4 "D4 Ambiente Empresarial"
label var S_D5 "D5 Capital Humano"

local w1 = .25
local w2 = .20
local w3 = .25
local w4 = .15
local w5 = .15

* subíndice igual a zero é truncado em 1e-6 na média geométrica
gen double idf = 100 * exp(`w1'*ln(max(S_D1,1e-6)) + `w2'*ln(max(S_D2,1e-6)) + ///
    `w3'*ln(max(S_D3,1e-6)) + `w4'*ln(max(S_D4,1e-6)) + `w5'*ln(max(S_D5,1e-6)))
label var idf "IDF-MP (0-100)"

* conferência com o cálculo em Python (amostra do artigo)
if "`AMOSTRA'" == "artigo" {
    gen double dif = abs(idf - idf_python)
    summarize dif
    assert dif < 1e-6
    drop dif
}

xtile faixa = idf, nq(4)
label define faixa 1 "Baixa" 2 "Média-baixa" 3 "Média-alta" 4 "Alta"
label values faixa faixa
quietly summarize idf, detail
gen byte alta = idf > r(p50)
label var alta "1 = IDF-MP acima da mediana"

*------------------------------------------------------------------------------*
* 3. Quadro 4 — Descritivas do IDF-MP, subíndices e indicadores; alfa de Cronbach
*------------------------------------------------------------------------------*
tabstat idf S_D1-S_D5, statistics(mean sd min max) columns(statistics) format(%9.3f)
tabstat i01-i16, statistics(mean sd min max cv) columns(statistics) format(%9.2f)

alpha n_i01 n_i02 n_i03, asis
alpha n_i05 n_i06, asis
alpha n_i07 n_i08 n_i09, asis
alpha n_i10 n_i11 n_i12 n_i13 n_i14, asis
alpha n_i15 n_i16, asis

* ranking e médias por UF e por faixa
gsort -idf
list municipio uf idf faixa, noobs sep(8)
tabstat idf idhm_2010 pop_2024 pib_pc_2021 S_D1-S_D5, by(uf) statistics(mean) format(%9.3f)
tabstat idf idhm_2010 pop_2024 pib_pc_2021 S_D1-S_D5, by(faixa) statistics(mean) format(%9.3f)

*------------------------------------------------------------------------------*
* 4. Quadro 6 — Robustez do ranking (Spearman e variação média de posições)
*------------------------------------------------------------------------------*
* (a) pesos iguais
gen double idf_iguais = 100 * exp(.2*(ln(max(S_D1,1e-6)) + ln(max(S_D2,1e-6)) + ///
    ln(max(S_D3,1e-6)) + ln(max(S_D4,1e-6)) + ln(max(S_D5,1e-6))))

* (b) pesos por PCA: quadrado das cargas do 1º componente (matriz de correlação)
pca S_D1-S_D5, components(1)
matrix L = e(L)
scalar soma = 0
forvalues k = 1/5 {
    scalar soma = soma + L[`k',1]^2
}
forvalues k = 1/5 {
    scalar pw`k' = L[`k',1]^2 / soma
    display "peso PCA D`k' = " %5.3f pw`k'
}
gen double idf_pca = 100 * exp(pw1*ln(max(S_D1,1e-6)) + pw2*ln(max(S_D2,1e-6)) + ///
    pw3*ln(max(S_D3,1e-6)) + pw4*ln(max(S_D4,1e-6)) + pw5*ln(max(S_D5,1e-6)))

* (c) pesos Delphi, agregação aritmética
gen double idf_arit = 100 * (`w1'*S_D1 + `w2'*S_D2 + `w3'*S_D3 + `w4'*S_D4 + `w5'*S_D5)

* (d) normalização por escore z, agregação aritmética
egen double Z_D1 = rowmean(z_i01 z_i02 z_i03)
egen double Z_D2 = rowmean(z_i05 z_i06)
egen double Z_D3 = rowmean(z_i07 z_i08 z_i09)
egen double Z_D4 = rowmean(z_i10 z_i11 z_i12 z_i13 z_i14)
egen double Z_D5 = rowmean(z_i15 z_i16)
gen double idf_z = 100 * (`w1'*Z_D1 + `w2'*Z_D2 + `w3'*Z_D3 + `w4'*Z_D4 + `w5'*Z_D5)

egen rk = rank(-idf)
foreach a in iguais pca arit z {
    spearman idf idf_`a'
    egen rk_`a' = rank(-idf_`a')
    gen absdif_`a' = abs(rk - rk_`a')
    quietly summarize absdif_`a'
    display "Variação média de posições (`a'): " %5.2f r(mean)
}

*------------------------------------------------------------------------------*
* 5. Quadro 7 — Variáveis explicativas
*------------------------------------------------------------------------------*
gen double pop_mil = pop_2024 / 1000
gen double pib_pc_mil = pib_pc_2021 / 1000
tabstat idhm_2010 pop_mil pib_pc_mil agro_va_pct, statistics(mean sd min max) columns(statistics) format(%9.3f)
pwcorr idf idhm_2010 pop_mil pib_pc_mil agro_va_pct

*------------------------------------------------------------------------------*
* 6. Quadro 8 — MQO com erros-padrão HC3 (M3 exige a variável Campus, não incluída)
*------------------------------------------------------------------------------*
regress idf idhm_2010 ln_pop, vce(hc3)
estimates store M1
estat vif
estat ic
display "Efeito de +0,01 no IDHM: " %6.2f _b[idhm_2010]/100 " pontos"
display "Efeito de dobrar a população: " %6.2f ln(2)*_b[ln_pop] " pontos"

regress idf idhm_2010 ln_pop ln_pib_pc, vce(hc3)
estimates store M2
estat vif
estat ic

regress idf idhm_2010 ln_pop ln_pib_pc agro_va_pct, vce(hc3)
estimates store M4
estat vif
estat ic

regress idf idhm_2010 ln_pop ln_pib_pc agro_va_pct i.uf_n, vce(hc3)
estimates store M5
estat vif
estat ic

estimates table M1 M2 M4 M5, b(%9.2f) se(%9.2f) star(.1 .05 .01) stats(N r2_a aic bic)

*------------------------------------------------------------------------------*
* 7. Diagnósticos do M1 (estimado por MQO comum)
*------------------------------------------------------------------------------*
quietly regress idf idhm_2010 ln_pop
estat hettest, rhs iid                       // Breusch-Pagan (versão de Koenker)
predict double yhat, xb
gen double yhat2 = yhat^2
quietly regress idf idhm_2010 ln_pop yhat2   // RESET de Ramsey com yhat^2
test yhat2
quietly regress idf idhm_2010 ln_pop
predict double resid_m1, residuals
predict double cook, cooksd
swilk resid_m1
list municipio uf cook if cook > 4/`N', noobs
gsort -resid_m1
list municipio uf idf resid_m1 in 1/5, noobs
gsort resid_m1
list municipio uf idf resid_m1 in 1/5, noobs

*------------------------------------------------------------------------------*
* 8. Quadro 9 — M1 por dimensão (subíndice x 100)
*------------------------------------------------------------------------------*
forvalues k = 1/5 {
    gen double D`k'x100 = S_D`k' * 100
    regress D`k'x100 idhm_2010 ln_pop, vce(hc3)
    estimates store Dim`k'
}
estimates table Dim1 Dim2 Dim3 Dim4 Dim5, b(%9.2f) se(%9.2f) star(.1 .05 .01) stats(N r2_a)

*------------------------------------------------------------------------------*
* 9. Quadro 10 — Robustez com variável dependente discreta (especificação M1)
*------------------------------------------------------------------------------*
* Probit: efeitos marginais médios
probit alta idhm_2010 ln_pop, vce(robust)
margins, dydx(idhm_2010 ln_pop)
estat classification

* Modelo de probabilidade linear
regress alta idhm_2010 ln_pop, vce(hc3)

* Logit ordenado nas quatro faixas (razões de chance)
ologit faixa idhm_2010 ln_pop
lincom 0.01*idhm_2010, or                    // razão de chance para +0,01 no IDHM
lincom ln_pop, or
capture noisily brant                        // requer spost13: ssc install spost13_ado

*------------------------------------------------------------------------------*
* 10. Quadro 11 — Robustez adicional do M1
*------------------------------------------------------------------------------*
foreach a in iguais pca arit z {
    regress idf_`a' idhm_2010 ln_pop, vce(hc3)
}
regress idf idhm_2010 ln_pop if cook <= 4/`N', vce(hc3)
qreg idf idhm_2010 ln_pop, quantile(.5)

*------------------------------------------------------------------------------*
* 11. Salva a base com o índice calculado
*------------------------------------------------------------------------------*
gsort -idf
keep cod_ibge municipio uf amostra_artigo pop_2024 i01-i16 S_D1-S_D5 idf faixa alta ///
    idf_iguais idf_pca idf_arit idf_z idhm_2010 ln_pop pib_pc_2021 ln_pib_pc agro_va_pct ///
    resid_m1 cook
save "idf_mp_calculado_`AMOSTRA'.dta", replace

log close
