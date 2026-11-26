"""Synthetic Difference-in-Differences (Arkhangelsky, Athey, Hirshberg, Imbens & Wager, 2021, AER).
Implementação do algoritmo do pacote synthdid (R) para muitas unidades tratadas com adoção em bloco (2019):
pesos de unidades (omega) e de tempo (lambda) por Frank-Wolfe no simplex com intercepto e penalização ridge,
EP por bootstrap de unidades (Arkhangelsky et al., 2021, Alg. 2). Compara SDID, DiD e Controle Sintético (SC).
Uso: python 08_sdid.py AV2_painel_municipal_Brasil.csv resultados_sdid.json
"""
import sys, json, numpy as np, pandas as pd

def fw_simplex(A, b, zeta2, intercept=True, max_iter=10000, tol=1e-8):
    """min_{w in simplex} ||A w - b||^2 + zeta2 ||w||^2, com intercepto (centraliza linhas). Frank-Wolfe com passo exato."""
    if intercept:
        A = A - A.mean(axis=0, keepdims=True); b = b - b.mean()
    n = A.shape[1]; w = np.full(n, 1.0 / n); Aw = A @ w
    for _ in range(max_iter):
        g = 2 * (A.T @ (Aw - b)) + 2 * zeta2 * w           # gradiente
        i = int(np.argmin(g)); d = -w.copy(); d[i] += 1.0  # direção para o vértice e_i
        Ad = A[:, i] - Aw
        den = Ad @ Ad + zeta2 * (d @ d)
        if den <= 0: break
        step = -(((Aw - b) @ Ad) + zeta2 * (w @ d)) / den
        step = min(max(step, 0.0), 1.0)
        if step * np.abs(d).max() < tol: break
        w = w + step * d; Aw = Aw + step * Ad
    return w

def estimate(Y0, Y1, T0, method='sdid', w1=None):
    """Y0: N0 x T (controles), Y1: N1 x T (tratados). T0 períodos pré. Retorna tau e pesos."""
    N0, T = Y0.shape; N1 = Y1.shape[0]; Tpost = T - T0
    y1 = Y1.mean(axis=0) if w1 is None else (w1 @ Y1) / w1.sum()   # média dos tratados (opcional: ponderada pela população)
    if method == 'did':
        w = np.full(N0, 1 / N0); lam = np.full(T0, 1 / T0)
    else:
        sig = np.std(np.diff(Y0[:, :T0], axis=1), ddof=1)
        zeta_w = (N1 * Tpost) ** 0.25 * sig if method == 'sdid' else 0.0
        w = fw_simplex(Y0[:, :T0].T, y1[:T0], zeta_w ** 2 * T0, intercept=(method == 'sdid'))
        if method == 'sdid':
            lam = fw_simplex(Y0[:, :T0], Y0[:, T0:].mean(axis=1), (1e-6 * sig) ** 2 * N0, intercept=True)
        else:
            lam = np.zeros(T0)                              # SC: sem pesos de tempo
    ctrl = w @ Y0                                          # trajetória ponderada dos controles (T)
    if method == 'sc':
        tau_t = y1[T0:] - ctrl[T0:]
        pre_gap = y1[:T0] - ctrl[:T0]
    else:
        ref = lam @ (y1[:T0] - ctrl[:T0])                  # diferença de nível no período de referência
        tau_t = y1[T0:] - ctrl[T0:] - ref
        pre_gap = y1[:T0] - ctrl[:T0] - ref
    return dict(tau=float(tau_t.mean()), tau_t=tau_t.tolist(), pre_gap=pre_gap.tolist(), w=w, lam=lam,
                y1=y1.tolist(), synth=(ctrl + (0 if method == 'sc' else lam @ (y1[:T0] - ctrl[:T0]))).tolist())

def bootstrap_se(Y0, Y1, T0, method, B=200, seed=42, w1=None):
    rng = np.random.default_rng(seed); N0, N1 = len(Y0), len(Y1); taus = []
    Y = np.vstack([Y0, Y1]); tr = np.r_[np.zeros(N0, bool), np.ones(N1, bool)]
    W1 = np.r_[np.zeros(N0), w1 if w1 is not None else np.ones(N1)]
    while len(taus) < B:
        idx = rng.integers(0, N0 + N1, N0 + N1); t = tr[idx]
        if t.all() or (~t).all(): continue
        taus.append(estimate(Y[idx][~t], Y[idx][t], T0, method, None if w1 is None else W1[idx][t])['tau'])
    return float(np.std(taus, ddof=1))

def run(df, y, treat_mask, ctrl_mask, label, B=200, pond=False):
    W = df.pivot(index='cod_ibge', columns='ano', values=y)
    anos = list(W.columns); T0 = sum(a <= 2018 for a in anos)
    tr_ids = df.loc[treat_mask, 'cod_ibge'].unique(); ct_ids = df.loc[ctrl_mask, 'cod_ibge'].unique()
    Y1 = W.loc[tr_ids].values; Y0 = W.loc[ct_ids].values
    w1 = df.drop_duplicates('cod_ibge').set_index('cod_ibge').loc[tr_ids, 'pop2018'].values if pond else None
    out = dict(label=label, y=y, ponderado=pond, N1=int(len(Y1)), N0=int(len(Y0)), anos=anos)
    for m in ('sdid', 'did', 'sc'):
        e = estimate(Y0, Y1, T0, m, w1); se = bootstrap_se(Y0, Y1, T0, m, B=B, w1=w1)
        z = e['tau'] / se if se > 0 else np.nan
        from scipy.stats import norm
        out[m] = dict(tau=e['tau'], se=se, p=float(2 * (1 - norm.cdf(abs(z)))), tau_t=e['tau_t'], pre_gap=e['pre_gap'],
                      y1=e['y1'], synth=e['synth'], lam=e['lam'].tolist(), n_w_pos=int((e['w'] > 1e-6).sum()),
                      w_max=float(e['w'].max()))
        print(f"{label:55s} {m:5s} tau={e['tau']:8.3f} se={se:6.3f} p={out[m]['p']:.4f}  N1={len(Y1)} N0={len(Y0)}", flush=True)
    return out

if __name__ == '__main__':
    df = pd.read_csv(sys.argv[1])
    p18 = df[df.ano == 2018].set_index('cod_ibge')['pop']; df['pop2018'] = df.cod_ibge.map(p18)
    q = df.drop_duplicates('cod_ibge').delta_reg_pc.quantile([.25, .75])
    Q4 = df.delta_reg_pc >= q[.75]; Q1 = df.delta_reg_pc <= q[.25]; big = df.pop2018 >= 20000
    res = {}
    res['A'] = run(df, 'taxa_homic_af', Q4, Q1, 'A. Q4 vs Q1 – todos os municípios')
    res['A2'] = run(df, 'taxa_homic_af', Q4, Q1, 'A2. Q4 vs Q1 – tratados ponderados pela população', pond=True)
    res['B'] = run(df, 'taxa_homic_af', Q4 & big, Q1 & big, 'B. Q4 vs Q1 – municípios ≥ 20 mil hab.')
    res['B2'] = run(df, 'taxa_homic_af', Q4 & big, Q1 & big, 'B2. Q4 vs Q1 – ≥ 20 mil hab., tratados ponderados', pond=True)
    res['C'] = run(df, 'taxa_homic_af', df.ano_primeiro_salto == 2019, df.ano_primeiro_salto == 0, 'C. Coorte 2019 vs nunca tratados')
    res['C2'] = run(df, 'taxa_homic_af', (df.ano_primeiro_salto == 2019) & big, (df.ano_primeiro_salto == 0) & big, 'C2. Coorte 2019 vs nunca tratados – ≥ 20 mil hab.')
    res['D'] = run(df, 'taxa_homic_ab', Q4 & big, Q1 & big, 'D. Placebo: arma branca – ≥ 20 mil hab.')
    res['E'] = run(df, 'taxa_obitos_transito', Q4 & big, Q1 & big, 'E. Placebo: trânsito – ≥ 20 mil hab.')
    json.dump(res, open(sys.argv[2], 'w'), indent=1)
