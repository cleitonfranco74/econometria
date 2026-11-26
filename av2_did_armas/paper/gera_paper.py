"""Gera paper_pt.tex e paper_en.tex (working paper para o SSRN) a partir dos resultados em ../*.json e do painel.
Uso (dentro de av2_did_armas/paper/):  python gera_paper.py pt|en && latexmk -pdf paper_pt.tex"""
import json, re, sys, numpy as np, pandas as pd
LANG = sys.argv[1] if len(sys.argv) > 1 else 'pt'
EN = LANG == 'en'
def T(pt, en): return en if EN else pt
from scipy.stats import norm
from pathlib import Path
B = Path(__file__).resolve().parent.parent
J = lambda f: json.load(open(B / f, encoding='utf-8'))
R = J('resultados_municipal.json'); r = R['res']; I = R['info']; ES = R['es']
CS = J('cs_resultados.json'); SD = J('resultados_sdid.json'); SJ = J('resultados_soja.json'); CSJ = J('resultados_cs_soja.json'); FT = J('fronteira_tratamento.json')
df = pd.read_csv(B / 'AV2_painel_municipal_Brasil.csv')

def n(x, d=2):
    s = f'{abs(x):,.{d}f}' if EN else f'{abs(x):,.{d}f}'.replace(',', 'X').replace('.', '{,}').replace('X', '.')
    if EN: s = s.replace(',', '{,}')
    return ('$-$' if x < 0 and round(abs(x), d) > 0 else '') + s
def st(p): return '$^{***}$' if p < .01 else '$^{**}$' if p < .05 else '$^{*}$' if p < .10 else ''
def pv(p): return ('$<$0.001' if EN else '$<$0{,}001') if p < .001 else n(p, 3)
def cs_simple(k):
    x = [float(v) for v in CS[k]['simple'][0][1:5]]; p = 2 * (1 - norm.cdf(abs(x[0] / x[1]))); return x + [p]
V = {}
b2 = r['(2) TWFE c/ controles, ponderado pop']; csn = cs_simple('taxa_homic_af|not_yet_treated'); csv_ = cs_simple('taxa_homic_af|never_treated')
cst = cs_simple('taxa_obitos_transito|not_yet_treated'); cse = CSJ['Escalonado (salto de registros) – controle ainda não tratados']
V.update(b2=n(b2['coef'], 3), b2se=n(b2['se'], 3), b2p=pv(b2['p']), iqr=n(b2['coef'] * (I['p75'] - I['p25'])), p25=n(I['p25']), p75=n(I['p75']),
         meanaf=n(I['mean_af']), pctiqr=n(100 * b2['coef'] * (I['p75'] - I['p25']) / I['mean_af'], 1), sdd=n(I['sd_delta']), sdeff=n(b2['coef'] * I['sd_delta']),
         cs=n(csn[0]), csse=n(csn[1]), cslo=n(csn[2]), cshi=n(csn[3]), csnev=n(csv_[0]), csnevse=n(csv_[1]), cspct=n(100 * csn[0] / I['mean_af'], 0),
         cstr=n(cst[0]), cstrse=n(cst[1]), soycs=n(cse['att']), soycsse=n(cse['se']), soycsp=pv(cse['p']),
         ddd=n(r['R1 DDD: AF vs arma branca']['coef'], 3), dddp=pv(r['R1 DDD: AF vs arma branca']['p']),
         ab=n(r['R5 Homicídios arma branca']['coef'], 3), abp=pv(r['R5 Homicídios arma branca']['p']),
         pois=n(100 * r['(5) Poisson (contagem, offset pop)']['coef']), poisp=pv(r['(5) Poisson (contagem, offset pop)']['p']),
         mm=n(r['(6) Intensidade Min-Max [0,1]']['coef']), mmp=pv(r['(6) Intensidade Min-Max [0,1]']['p']),
         fint=n(r['(3) Fronteira: ΔREG×Pós×Fronteira']['coef'], 3), fintp=pv(r['(3) Fronteira: ΔREG×Pós×Fronteira']['p']),
         rev=n(r['(4) Reversão: ΔREG×Pós2023']['coef'], 3), revp=pv(r['(4) Reversão: ΔREG×Pós2023']['p']),
         wF=n(ES['taxa_homic_af']['F']), wp=n(ES['taxa_homic_af']['p'], 3), tr=n(r['R2 Placebo: óbitos no trânsito']['coef'], 3), trp=pv(r['R2 Placebo: óbitos no trânsito']['p']),
         p17=n(r['R3 Placebo temporal (2017)']['coef'], 3), p17p=pv(r['R3 Placebo temporal (2017)']['p']),
         ufano=n(r['(9) EF UF×ano']['coef']), q4=n(r['R4 Tratamento binário (Q4)']['coef']), s50=n(r['(11) Só os 50 municípios do projeto']['coef'], 3), s50p=pv(r['(11) Só os 50 municípios do projeto']['p']),
         c2=n(SD['C2']['sdid']['tau']), c2se=n(SD['C2']['sdid']['se']), sdb=n(SD['B']['sdid']['tau']), sdbse=n(SD['B']['sdid']['se']),
         sda2=n(SD['A2']['sdid']['tau']), sda2se=n(SD['A2']['sdid']['se']),
         ftreg=n(FT['fronteira_registros'][0], 3), ftaf=n(FT['fronteira_pond'][0]), ftafp=pv(FT['fronteira_pond'][2]),
         nsoja=f"{SJ['n']['Fronteira da soja']}", ncons=f"{SJ['n']['Soja consolidada']:,}".replace(',', ',' if EN else '.'), nsem=f"{SJ['n']['Sem soja']:,}".replace(',', ',' if EN else '.'),
         soysd=n(SJ['sdid']['SDID vs. soja consolidada']['sdid']['tau']), soysdse=n(SJ['sdid']['SDID vs. soja consolidada']['sdid']['se']),
         soyddd=n(SJ['res']['DDD: ΔREG × Pós × Fronteira da soja (todos)']['coef']), soydddp=pv(SJ['res']['DDD: ΔREG × Pós × Fronteira da soja (todos)']['p']),
         soydid=n(SJ['res']['DiD homic. AF vs. sem soja']['coef']), soyesp=n(SJ['res']['Event study vs. sem soja']['p'], 3),
         c19=f"{I['coortes']['2019']:,}".replace(',', ',' if EN else '.'), c20=f"{I['coortes']['2020']:,}".replace(',', ',' if EN else '.'), c21=f"{I['coortes']['2021']}", c0=f"{I['coortes']['0']:,}".replace(',', ',' if EN else '.'))
cc = CSJ['coortes_escalonado']; V.update(sc19=str(cc['2019.0']), sc20=str(cc['2020.0']), sc21=str(cc['2021.0']))
DF = J('resultados_desmatamento.json'); pn = DF['painel']; bi = DF['bioma']; tc = DF['tercil']; esc = DF['escala']
V.update(soyratio=n(cse['att'] / csn[0], 1), soyesp2=n(SJ['res']['Event study vs. soja consolidada']['p'], 3),
         dp1=n(pn['EF município e UF × ano']['coef'], 3), dp1p=pv(pn['EF município e UF × ano']['p']),
         dplag=n(pn['Desmatamento defasado (t−1)']['coef'], 3), dplagp=pv(pn['Desmatamento defasado (t−1)']['p']),
         dpprim=n(pn['Só vegetação primária']['coef'], 3), dpprimp=pv(pn['Só vegetação primária']['p']),
         dpsd=n(100 * pn['EF município e UF × ano']['coef'] * esc['sd_within'] / esc['media_reg'], 1),
         dball=n(bi['Todos']['coef'], 3), dballp=pv(bi['Todos']['p']), dbce=n(bi['Cerrado']['coef'], 3), dbcep=pv(bi['Cerrado']['p']),
         dbam=n(bi['Amazônia']['coef'], 3), dbamp=pv(bi['Amazônia']['p']),
         t3r0=n(tc['Alto|0']['reg']), t3r1=n(tc['Alto|1']['reg']), t1r0=n(tc['Baixo|0']['reg']), t1r1=n(tc['Baixo|1']['reg']),
         t3pct=n(100 * (tc['Alto|1']['reg'] / tc['Alto|0']['reg'] - 1), 0), t3a0=n(tc['Alto|0']['af'], 1), t3a1=n(tc['Alto|1']['af'], 1),
         t1a0=n(tc['Baixo|0']['af'], 1), t1a1=n(tc['Baixo|1']['af'], 1))


# ------------------------------------------------------------------ tabelas
def row(*c): return ' & '.join(c) + r' \\'
def coef(k, d=3): x = r[k]; return n(x['coef'], d) + st(x['p']), '(' + n(x['se'], d) + ')'
# Tabela 1: descritivas
specs = [(T('Intensidade $\\Delta REG_i$ (registros por mil hab.)', 'Intensity $\\Delta REG_i$ (registrations per 1,000)'), 'delta_reg_pc'),
         (T('Novos registros por mil hab. por ano', 'New registrations per 1,000 per year'), 'reg_cidadao_1000'),
         (T('Homicídios por arma de fogo (por 100 mil)', 'Firearm homicides (per 100,000)'), 'taxa_homic_af'),
         (T('Homicídios por arma branca (por 100 mil)', 'Knife homicides (per 100,000)'), 'taxa_homic_ab'),
         (T('Óbitos no trânsito (por 100 mil)', 'Traffic deaths (per 100,000)'), 'taxa_obitos_transito')]
t1 = []
for lab, v in specs:
    cells = []
    for fa in (0, 1):
        for per in (0, 1):
            s_ = df[(df.fronteira_ativa == fa) & (df.pos_2019 == per)][v]; cells.append(f'{n(s_.mean())} ({n(s_.std())})')
    t1.append(row(lab, *cells))
agg = lambda fa, per, c: df[(df.fronteira_ativa == fa) & (df.pos_2019 == per)].pipe(lambda s: s[c].sum() / s['pop'].sum())
t1.append(row(T('Homicídios por arma de fogo, taxa agregada', 'Firearm homicides, aggregate rate'), *[n(agg(fa, per, 'af') * 1e5) for fa in (0, 1) for per in (0, 1)]))
t1.append(row(T('Municípios', 'Municipalities'), *([T('2.785', '2,785')] * 4)))
V['tab1'] = '\n'.join(t1)
# Tabela 2: principais
k = ['(1) TWFE s/ controles, ponderado pop', '(2) TWFE c/ controles, ponderado pop', '(3) Fronteira: ΔREG×Pós', '(4) Reversão: ΔREG×Pós2019', '(5) Poisson (contagem, offset pop)']
cA = [coef(x) for x in k]
t2 = [row(T('$\\Delta REG_i \\times Pos_t$', '$\\Delta REG_i \\times Post_t$'), *[c[0] for c in cA], n(csn[0]) + st(csn[4])), row('', *[c[1] for c in cA], '(' + n(csn[1]) + ')'),
      row(T('$\\Delta REG_i \\times Pos_t \\times Fronteira_i$', '$\\Delta REG_i \\times Post_t \\times Frontier_i$'), '', '', coef('(3) Fronteira: ΔREG×Pós×Fronteira')[0], '', '', ''),
      row('', '', '', coef('(3) Fronteira: ΔREG×Pós×Fronteira')[1], '', '', ''),
      row(T('$\\Delta REG_i \\times Pos2023_t$', '$\\Delta REG_i \\times Post2023_t$'), '', '', '', coef('(4) Reversão: ΔREG×Pós2023')[0], '', ''),
      row('', '', '', '', coef('(4) Reversão: ΔREG×Pós2023')[1], '', ''), r'\midrule',
      row(T('Controles', 'Controls'), *[T(a, b) for a, b in [('Não', 'No'), ('Sim', 'Yes'), ('Sim', 'Yes'), ('Sim', 'Yes'), ('Sim', 'Yes'), ('Não', 'No')]]), row(T('EF de município e ano', 'Municipality and year FE'), *[T('Sim', 'Yes')] * 5, '--'),
      row(T('Ponderação', 'Weights'), 'Pop.', 'Pop.', 'Pop.', 'Pop.', 'Offset', 'Pop.'),
      row(T('Observações', 'Observations'), *[T('55.700', '55,700')] * 4, f"{r['(5) Poisson (contagem, offset pop)']['n']:,}".replace(',', ',' if EN else '.'), T('55.700', '55,700'))]
V['tab2'] = '\n'.join(t2)
# Tabela 3: event study
cse_ev = {int(float(x[0])): [float(v) for v in x[1:5]] for x in CS['taxa_homic_af|not_yet_treated']['event']}
t3 = []
for y in range(2015, 2025):
    kk = y - 2019; csc = n(cse_ev[kk][0]) + f" ({n(cse_ev[kk][1])})" if kk in cse_ev else '--'
    if y == 2018: t3.append(row(T('2018 (ref.)', '2018 (ref.)'), '$k=-1$', '0', '--', '0', '--', csc)); continue
    a = ES['taxa_homic_af']['coefs'][str(y)]; t = ES['taxa_obitos_transito']['coefs'][str(y)]
    t3.append(row(str(y), f'$k={kk:+d}$', n(a[0], 3) + st(a[4]), '(' + n(a[1], 3) + ')', n(t[0], 3) + st(t[4]), '(' + n(t[1], 3) + ')', csc))
t3.append(r'\midrule'); t3.append(row(T('Teste conjunto pré (2015--17)', 'Joint pre-test (2015--17)'), '', 'F = ' + n(ES['taxa_homic_af']['F']), 'p = ' + n(ES['taxa_homic_af']['p'], 3),
                                      'F = ' + n(ES['taxa_obitos_transito']['F']), 'p = ' + n(ES['taxa_obitos_transito']['p'], 3), ''))
V['tab3'] = '\n'.join(t3)
# Tabela 4: robustez
rk = [('R1 DDD: AF vs arma branca', T('Tripla diferença: arma de fogo vs. arma branca', 'Triple difference: firearm vs. knife')),
      ('R2 Placebo: óbitos no trânsito', T('Placebo de resultado: óbitos no trânsito', 'Outcome placebo: traffic deaths')),
      ('R3 Placebo temporal (2017)', T('Placebo temporal: choque fictício em 2017', 'Timing placebo: fake shock in 2017')),
      ('R4 Tratamento binário (Q4)', T('Tratamento binário: quartil superior', 'Binary treatment: top quartile')),
      ('R5 Homicídios arma branca', T('Homicídios por arma branca', 'Knife homicides')), ('R6 Homicídios outros meios', T('Homicídios por outros meios', 'Homicides by other means')),
      ('(8) Tendência por linha de base (pre_reg×ano)', T('Tendências por linha de base de registros', 'Baseline-registration trends')),
      ('(9) EF UF×ano', T('EF de UF $\\times$ ano', 'State $\\times$ year FE')), ('(10) Excesso sobre 2015-18', T('Intensidade em excesso sobre 2015--18', 'Intensity in excess of 2015--18')),
      ('(7) Sem ponderação', T('Sem ponderação', 'Unweighted')), ('(12) Municípios ≥ 20 mil hab.', T('Municípios com 20 mil hab. ou mais', 'Municipalities with 20,000+ inhabitants')),
      ('R7 Subamostra fronteira', T('Subamostra: fronteira agrícola', 'Subsample: agricultural frontier')), ('R8 Subamostra consolidados', T('Subamostra: consolidados', 'Subsample: consolidated')),
      ('(11) Só os 50 municípios do projeto', T('Amostra de 50 municípios', 'Original 50-municipality sample'))]
V['tab4'] = '\n'.join(row(lab, n(r[k]['coef'], 3) + st(r[k]['p']), '(' + n(r[k]['se'], 3) + ')', pv(r[k]['p']), f"{r[k]['n']:,}".replace(',', ',' if EN else '.')) for k, lab in rk)
# Tabela 5: SDID
def sdr(lab, k):
    x = SD[k]; c = [lab]
    for m in ('sdid', 'did', 'sc'): c += [n(x[m]['tau']) + st(x[m]['p']), '(' + n(x[m]['se']) + ')']
    return row(*c, f"{x['N1']}/{x['N0']}")
V['tab5'] = '\n'.join([sdr(T('Q4 vs. Q1, todos', 'Q4 vs. Q1, all'), 'A'), sdr(T('Q4 vs. Q1, tratados pond. pela pop.', 'Q4 vs. Q1, pop.-weighted treated'), 'A2'),
                       sdr(T('Q4 vs. Q1, $\\geq$ 20 mil hab.', 'Q4 vs. Q1, $\\geq$ 20,000 inh.'), 'B'), sdr(T('Q4 vs. Q1, $\\geq$ 20 mil, pond.', 'Q4 vs. Q1, $\\geq$ 20,000, weighted'), 'B2'),
                       sdr(T('Coorte 2019 vs. nunca tratados', '2019 cohort vs. never treated'), 'C'), sdr(T('Coorte 2019 vs. nunca, $\\geq$ 20 mil', '2019 cohort vs. never, $\\geq$ 20,000'), 'C2'),
                       r'\midrule', sdr(T('Placebo arma branca ($\\geq$ 20 mil)', 'Placebo: knife homicides ($\\geq$ 20,000)'), 'D'), sdr(T('Placebo trânsito ($\\geq$ 20 mil)', 'Placebo: traffic deaths ($\\geq$ 20,000)'), 'E')])
# Tabela 6: fronteira da soja
sr = SJ['res']; ss = SJ['sdid']
def l(k): x = sr[k]; return [n(x['coef'], 3) + st(x['p']), '(' + n(x['se'], 3) + ')']
def lsd(k): x = ss[k]['sdid']; return [n(x['tau']) + st(x['p']), '(' + n(x['se']) + ')']
def lcs(k): x = CSJ[k]; return [n(x['att']) + st(x['p']), '(' + n(x['se']) + ')']
t6 = [row(T('Registros por mil hab. (1º estágio)', 'Registrations per 1,000 (1st stage)'), *l('1º estágio: registros/mil hab. vs. sem soja'), *l('1º estágio: registros/mil hab. vs. soja consolidada')),
      row(T('DiD TWFE (ponderado pela pop.)', 'TWFE DiD (pop.-weighted)'), *l('DiD homic. AF vs. sem soja'), *l('DiD homic. AF vs. soja consolidada')),
      row(T('DiD TWFE (sem ponderação)', 'TWFE DiD (unweighted)'), *l('DiD homic. AF vs. sem soja (sem ponderação)'), *l('DiD homic. AF vs. soja consolidada (sem ponderação)')),
      row(T('Event study: p do teste conjunto pré', 'Event study: joint pre-test p'), n(sr['Event study vs. sem soja']['p'], 3), '', n(sr['Event study vs. soja consolidada']['p'], 3), ''),
      row('SDID', *lsd('SDID vs. sem soja'), *lsd('SDID vs. soja consolidada')),
      row(T('SDID, tratados ponderados pela pop.', 'SDID, pop.-weighted treated'), *lsd('SDID vs. sem soja (tratados ponderados)'), *lsd('SDID vs. soja consolidada (tratados ponderados)')),
      row(T('C\\&S, bloco 2019', 'C\\&S, 2019 block'), *lcs('Bloco 2019 vs. sem soja'), *lcs('Bloco 2019 vs. soja consolidada')),
      row(T('C\\&S, bloco 2019, ponderado', 'C\\&S, 2019 block, weighted'), *lcs('Bloco 2019 vs. sem soja – ponderado pop.'), *lcs('Bloco 2019 vs. soja consolidada – ponderado pop.')),
      row(T('C\\&S, escalonado pelo salto de registros', 'C\\&S, staggered by registration surge'), '--', '', *lcs('Escalonado (salto de registros) – controle ainda não tratados')),
      row(T('C\\&S, escalonado, ponderado', 'C\\&S, staggered, weighted'), '--', '', *lcs('Escalonado (salto de registros) – controle ainda não tratados, pond.')),
      r'\midrule',
      row(T('Placebo arma branca: DiD TWFE', 'Knife-homicide placebo: TWFE DiD'), *l('Placebo arma branca vs. sem soja'), *l('Placebo arma branca vs. soja consolidada')),
      row(T('Placebo arma branca: C\\&S bloco', 'Knife-homicide placebo: C\\&S block'), *lcs('Placebo arma branca: bloco 2019 vs. sem soja'), *lcs('Placebo arma branca: bloco 2019 vs. soja consolidada')),
      r'\midrule', row(T('Municípios tratados / controle', 'Treated / control municipalities'), f"{SJ['n']['Fronteira da soja']} / {V['nsem']}", '', f"{SJ['n']['Fronteira da soja']} / {V['ncons']}", '')]
V['tab6'] = '\n'.join(t6)

t7 = [row(T('\\textit{Painel A: dentro do município (2015--2024)}', '\\textit{Panel A: within municipality (2015--2024)}'), '', '', '', '')]
for k, lab in [('EF município e ano', T('Desmatamento no ano, EF de município e ano', 'Deforestation in year, municipality and year FE')),
               ('EF município e UF × ano', T('Desmatamento no ano, EF de município e UF $\\times$ ano', 'Deforestation in year, municipality and state $\\times$ year FE')),
               ('Desmatamento defasado (t−1)', T('Desmatamento no ano anterior', 'Deforestation in previous year')),
               ('Só vegetação primária', T('Só perda de vegetação primária', 'Primary vegetation loss only'))]:
    x = pn[k]; t7.append(row(lab, n(x['coef'], 3) + st(x['p']), '(' + n(x['se'], 3) + ')', pv(x['p']), f"{x['n']:,}".replace(',', ',' if EN else '.')))
t7 += [r'\midrule', row(T('\\textit{Painel B: entre municípios, por bioma}', '\\textit{Panel B: across municipalities, by biome}'), '', '', '', '')]
for b, lab in [('Todos', T('Todos os municípios', 'All municipalities')), ('Amazônia', T('Amazônia', 'Amazon')), ('Cerrado', 'Cerrado'),
               ('Mata Atlântica', T('Mata Atlântica', 'Atlantic Forest')), ('Caatinga', 'Caatinga'), ('Pampa', 'Pampa')]:
    x = bi[b]; t7.append(row(lab, n(x['coef'], 3) + st(x['p']), '(' + n(x['se'], 3) + ')', pv(x['p']), f"{x['n']:,}".replace(',', ',' if EN else '.')))
V['tab7'] = '\n'.join(t7)
tex = open(Path(__file__).with_name(f'paper_modelo_{LANG}.tex'), encoding='utf-8').read()
for k_, v in V.items(): tex = tex.replace('@@' + k_ + '@@', v)
left = re.findall(r'@@\w+@@', tex)
assert not left, left
open(Path(__file__).with_name(f'paper_{LANG}.tex'), 'w', encoding='utf-8').write(tex); print(f'paper_{LANG}.tex gerado')
