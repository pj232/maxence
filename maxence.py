# -*- coding: utf-8 -*-
"""
GC Barrage Pro — collecte, analyse et gestion de données d'un projet de barrage
(retenue, crue, évacuateur, stabilité, remblai, fondation, auscultation, sécurité).
Lancement :  streamlit run App.py

Résultats indicatifs (méthodes simplifiées) : à valider par un ingénieur / bureau d'études.
"""
import io
import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="GC Barrage Pro", page_icon="🌊", layout="wide",
                   initial_sidebar_state="expanded")

# ===================== THÈME =====================
ACCENT = "#00B4D8"
ACCENT_CLAIR = "#CAF0F8"
FOND = "#F2FBFD"
NOIR = "#0B2545"
ROUGE = "#D62828"
VERT = "#2A9D4F"
ORANGE = "#F77F00"
BLEU = "#1D4ED8"
GRIS = "#6B7280"
PALETTE = [NOIR, ACCENT, ROUGE, BLEU, VERT, ORANGE, GRIS]

CSS = f"""
<style>
.stApp {{ background: linear-gradient(180deg,#FAFEFF 0%,{FOND} 55%,#E3F6FB 100%); color:{NOIR}; }}
h1,h2,h3,h4,h5 {{ color:{NOIR} !important; font-weight:800 !important; }}
[data-testid="stSidebar"] {{ background:{NOIR}; border-right:5px solid {ACCENT}; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] div, [data-testid="stSidebar"] small {{ color:{ACCENT_CLAIR} !important; }}
.brand {{ background:{ACCENT}; color:{NOIR}; font-weight:900; font-size:1.2rem; padding:12px 14px;
          border-radius:12px; text-align:center; margin-bottom:8px; border:2px solid {ACCENT_CLAIR}; }}
.hero {{ background:linear-gradient(110deg,{ACCENT} 0%,#5CD6EE 60%,{ACCENT_CLAIR} 100%);
         border:3px solid {NOIR}; border-radius:16px 16px 0 0; padding:16px 26px; }}
.hero h1 {{ margin:0; color:{NOIR} !important; font-size:1.9rem; }}
.hero p {{ margin:4px 0 0; color:{NOIR}; font-weight:600; }}
.hazard {{ height:12px; border:3px solid {NOIR}; border-top:0; border-radius:0 0 16px 16px; margin-bottom:18px;
           background:repeating-linear-gradient(45deg,{NOIR} 0 14px,{ORANGE} 14px 28px); background-size:40px 100%;
           animation:slide 1.2s linear infinite; }}
@keyframes slide {{ from {{ background-position:0 0; }} to {{ background-position:40px 0; }} }}
[data-testid="stMetric"] {{ background:#FFFFFF; border:2px solid {NOIR}; border-left:10px solid {ACCENT};
          padding:10px 16px; border-radius:12px; box-shadow:4px 4px 0 {NOIR}22; }}
[data-testid="stMetricValue"] {{ color:{NOIR}; font-weight:800; }}
.stButton>button, .stDownloadButton>button, [data-testid="stFormSubmitButton"]>button {{
    background:{ACCENT}; color:{NOIR}; border:2px solid {NOIR}; font-weight:800; border-radius:10px; }}
.stButton>button:hover, .stDownloadButton>button:hover, [data-testid="stFormSubmitButton"]>button:hover {{
    background:{NOIR}; color:{ACCENT}; border-color:{ACCENT}; }}
.stTabs [data-baseweb="tab-list"] {{ gap:6px; flex-wrap:wrap; }}
.stTabs [data-baseweb="tab"] {{ background:#FFFFFF; border:2px solid {NOIR}; border-radius:10px 10px 0 0;
    padding:8px 16px; font-weight:700; color:{NOIR}; }}
.stTabs [aria-selected="true"] {{ background:{ACCENT}; }}
.note {{ background:{NOIR}; color:{ACCENT_CLAIR}; padding:10px 16px; border-radius:10px; border-left:8px solid {ACCENT};
         margin:8px 0 14px; font-size:0.95rem; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def _wide():
    try:
        v = tuple(int(x) for x in st.__version__.split(".")[:2])
    except Exception:
        v = (0, 0)
    return {"width": "stretch"} if v >= (1, 50) else {"use_container_width": True}


WIDE = _wide()
_PN = [0]


# ===================== OUTILS =====================
def hero(titre, sous=""):
    st.markdown(f"<div class='hero'><h1>{titre}</h1><p>{sous}</p></div><div class='hazard'></div>",
                unsafe_allow_html=True)


def note(txt):
    st.markdown(f"<div class='note'>{txt}</div>", unsafe_allow_html=True)


def fnum(x, default=0.0):
    try:
        v = float(x)
        return default if math.isnan(v) else v
    except Exception:
        return default


def fmt(x, nd=2):
    try:
        return f"{x:,.{nd}f}".replace(",", " ")
    except Exception:
        return str(x)


def num(df, col):
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def verdict(cond, ok_msg, ko_msg):
    (st.success if cond else st.error)(("✅ " + ok_msg) if cond else ("❌ " + ko_msg))


def pplot(fig, height=420):
    _PN[0] += 1
    fig.update_layout(height=height, paper_bgcolor="#FFFFFF", plot_bgcolor="#F7FDFF", font=dict(color=NOIR),
                      colorway=PALETTE, margin=dict(l=20, r=20, t=55, b=20), title_font=dict(size=16, color=NOIR))
    fig.update_xaxes(gridcolor="#CFE8EE", zerolinecolor="#9CC5D0")
    fig.update_yaxes(gridcolor="#CFE8EE", zerolinecolor="#9CC5D0")
    try:
        st.plotly_chart(fig, key=f"pl{_PN[0]}", **WIDE)
    except TypeError:
        st.plotly_chart(fig, key=f"pl{_PN[0]}")


def show_df(df, **kw):
    try:
        st.dataframe(df, hide_index=True, **WIDE, **kw)
    except TypeError:
        st.dataframe(df, hide_index=True, **kw)


# ===================== SCHÉMAS =====================
COLS = {
    "releves": ["Date", "Instrument", "Type", "Valeur", "Unité", "Niveau retenue (m)", "Remarque"],
    "journal": ["Date", "Météo", "Effectif", "Activités", "Observations"],
    "essais": ["Date", "Élément", "Classe", "Âge (j)", "Résistance (MPa)"],
    "compactage": ["Date", "Zone", "Densité sèche (t/m³)", "OPM (t/m³)", "Teneur en eau (%)", "w OPM (%)"],
    "hsv": ["Cote (m)", "Surface (ha)"],
    "seuils": ["Instrument", "Seuil alerte", "Seuil alarme"],
    "metre": ["Lot", "Désignation", "Unité", "Quantité", "PU"],
    "taches": ["Tâche", "Début", "Durée (j)", "Avancement (%)", "Responsable", "Prédécesseurs"],
    "risques": ["Risque", "Phase", "Probabilité", "Gravité", "Mesure de maîtrise"],
    "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
}
DATES = {"releves": ["Date"], "journal": ["Date"], "essais": ["Date"], "compactage": ["Date"], "taches": ["Début"]}
NUMS = {
    "releves": ["Valeur", "Niveau retenue (m)"], "journal": ["Effectif"],
    "essais": ["Âge (j)", "Résistance (MPa)"],
    "compactage": ["Densité sèche (t/m³)", "OPM (t/m³)", "Teneur en eau (%)", "w OPM (%)"],
    "hsv": ["Cote (m)", "Surface (ha)"], "seuils": ["Seuil alerte", "Seuil alarme"],
    "metre": ["Quantité", "PU"], "taches": ["Durée (j)", "Avancement (%)"], "risques": ["Probabilité", "Gravité"],
    "ev": ["Mois", "PV cumulé", "EV cumulée", "AC cumulé"],
}
LABELS = {
    "releves": "Auscultation", "journal": "Journal de chantier", "essais": "Essais béton",
    "compactage": "Compactage remblai", "hsv": "Courbe hauteur-surface", "seuils": "Seuils instruments",
    "metre": "Métré", "taches": "Planning", "risques": "Risques", "ev": "Suivi coûts",
}
INSTR = {"Piézomètre": "m", "Débit de fuite": "L/min", "Tassement": "mm", "Déplacement de crête": "mm",
         "Pression interstitielle": "kPa", "Température béton": "°C"}
TYPES_BARRAGE = ["Barrage en remblai zoné", "Barrage en remblai homogène", "Barrage-poids en béton",
                 "Barrage en BCR (béton compacté)", "Barrage-voûte"]
ZONES = ["Noyau", "Recharge amont", "Recharge aval", "Filtre / drain", "Fondation"]
METEO = ["Ensoleillé", "Nuageux", "Pluie légère", "Pluie forte", "Vent fort", "Forte chaleur"]
CLASSES_BETON = ["C16/20", "C20/25", "C25/30", "C30/37", "C35/45"]
COMPACT_MIN = {"Noyau": 98.0, "Recharge amont": 95.0, "Recharge aval": 95.0, "Filtre / drain": 95.0, "Fondation": 95.0}
LANE = {"Sable très fin": 8.5, "Sable fin": 7.0, "Sable moyen": 6.0, "Sable grossier": 5.0, "Gravier fin": 4.0,
        "Gravier moyen": 3.5, "Gravier grossier / galets": 3.0, "Blocs": 2.5, "Argile molle": 3.0,
        "Argile moyenne": 2.0, "Argile dure": 1.8, "Roche saine": 1.6}


def coerce(df, key):
    d = df.copy()
    for c in COLS[key]:
        if c not in d.columns:
            d[c] = None
    d = d[COLS[key]]
    for c in DATES.get(key, []):
        d[c] = pd.to_datetime(d[c], errors="coerce").dt.date
        d[c] = d[c].where(d[c].notna(), None)
    for c in NUMS.get(key, []):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.reset_index(drop=True)


def metre_totals(df):
    d = df.copy()
    d["Quantité"], d["PU"] = num(d, "Quantité"), num(d, "PU")
    d["Total"] = d["Quantité"] * d["PU"]
    d["Lot"] = d["Lot"].fillna("Divers").astype(str)
    return d



# ===================== ÉDITEUR DE TABLEAUX (état fiable) =====================
def bump(key):
    S = st.session_state
    S[f"{key}__v"] = S.get(f"{key}__v", 0) + 1


def set_df(key, df):
    st.session_state[key] = df
    bump(key)


def add_rows(key, new):
    S = st.session_state
    set_df(key, pd.concat([S[key], coerce(new, key)], ignore_index=True))


def _apply_delta(key):
    S = st.session_state
    ver = S.get(f"{key}__v", 0)
    delta = S.get(f"ed_{key}_{ver}") or {}
    df = S[key].astype(object).reset_index(drop=True)
    for r, ch in (delta.get("edited_rows") or {}).items():
        r = int(r)
        if r < len(df):
            for c, v in ch.items():
                if c in df.columns:
                    df.iat[r, df.columns.get_loc(c)] = v
    for row in delta.get("added_rows") or []:
        df = pd.concat([df, pd.DataFrame([row], columns=df.columns)], ignore_index=True)
    dels = [int(i) for i in (delta.get("deleted_rows") or []) if int(i) < len(df)]
    if dels:
        df = df.drop(index=dels).reset_index(drop=True)
    S[key] = coerce(df, key) if key in COLS else df.infer_objects()
    S[f"{key}__v"] = ver + 1


def editor(key, config=None, dynamic=True):
    """Tableau éditable : S[key] reste la source de vérité (mise à jour par callback)."""
    S = st.session_state
    kw = dict(key=f"ed_{key}_{S.get(f'{key}__v', 0)}", column_config=config or {},
              num_rows="dynamic" if dynamic else "fixed", hide_index=True, on_change=_apply_delta, args=(key,))
    try:
        return st.data_editor(S[key], **WIDE, **kw)
    except TypeError:
        return st.data_editor(S[key], **kw)


# ===================== PLANNING (chemin critique) =====================
def cpm(df):
    d = df.dropna(subset=["Tâche"]).copy()
    d["Tâche"] = d["Tâche"].astype(str)
    d = d.drop_duplicates("Tâche").reset_index(drop=True)
    d["Durée (j)"] = pd.to_numeric(d["Durée (j)"], errors="coerce").fillna(0).clip(lower=0)
    names = d["Tâche"].tolist()
    dur = dict(zip(names, d["Durée (j)"]))
    preds = {n: [x.strip() for x in str(p).split(";") if x.strip() in dur and x.strip() != n]
             for n, p in zip(names, d["Prédécesseurs"].fillna(""))}
    order, state = [], {}

    def visit(n):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            raise ValueError(f"Boucle de dépendances autour de « {n} »")
        state[n] = 1
        for p in preds[n]:
            visit(p)
        state[n] = 2
        order.append(n)

    for n in names:
        visit(n)
    ES, EF = {}, {}
    for n in order:
        ES[n] = max([EF[p] for p in preds[n]], default=0.0)
        EF[n] = ES[n] + dur[n]
    T = max(EF.values(), default=0.0)
    succ = {n: [m for m in names if n in preds[m]] for n in names}
    LS, LF = {}, {}
    for n in reversed(order):
        LF[n] = min([LS[s] for s in succ[n]], default=T)
        LS[n] = LF[n] - dur[n]
    d["ES"] = d["Tâche"].map(ES)
    d["EF"] = d["Tâche"].map(EF)
    d["Marge (j)"] = d["Tâche"].map(lambda n: LS[n] - ES[n])
    d["Critique"] = d["Marge (j)"].abs() < 1e-9
    return d, T


# ===================== CALCULS : RETENUE, CRUE, ÉVACUATEUR =====================
G = 9.81
GW = 9.81  # poids volumique de l'eau (kN/m³)


def hsv_table(df):
    d = df.copy()
    for c in NUMS["hsv"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna().sort_values("Cote (m)").reset_index(drop=True)
    vol = [0.0]
    for i in range(1, len(d)):
        dz = d["Cote (m)"][i] - d["Cote (m)"][i - 1]
        vol.append(vol[-1] + (d["Surface (ha)"][i] + d["Surface (ha)"][i - 1]) / 2 * dz * 1e4)
    d["Volume (m³)"] = vol
    d["Volume (hm³)"] = d["Volume (m³)"] / 1e6
    return d


def vol_at(d, z):
    return float(np.interp(z, d["Cote (m)"], d["Volume (m³)"]))


def surf_at(d, z):
    return float(np.interp(z, d["Cote (m)"], d["Surface (ha)"]))


def weir_q(h, L, C):
    return C * L * max(h, 0.0) ** 1.5


def laminage(d, crest, L, C, Qp, tp_h, dt=600.0, q_vidange=0.0, z0=None):
    """Laminage de crue par la méthode de Puls (réservoir à niveau horizontal)."""
    tp = tp_h * 3600.0
    tb = 2.67 * tp
    n = int(3 * tb / dt) + 2
    t = np.arange(n) * dt
    inflow = np.where(t <= tp, Qp * t / tp, np.where(t <= tb, Qp * (tb - t) / (tb - tp), 0.0))
    zs, qs = [z0 if z0 is not None else crest], []
    zmin, zmax = float(d["Cote (m)"].min()), float(d["Cote (m)"].max()) + 5.0

    def out(z):
        return weir_q(z - crest, L, C) + q_vidange

    for k in range(n - 1):
        S0 = vol_at(d, zs[-1])
        O0 = out(zs[-1])
        avg_in = (inflow[k] + inflow[k + 1]) / 2
        lo, hi = zmin, zmax
        for _ in range(60):
            mid = (lo + hi) / 2
            f = vol_at(d, mid) - S0 - avg_in * dt + (O0 + out(mid)) / 2 * dt
            if f < 0:
                lo = mid
            else:
                hi = mid
        zs.append((lo + hi) / 2)
    zs = np.array(zs)
    q = np.array([out(z) for z in zs])
    return pd.DataFrame({"t (h)": t / 3600, "Entrant (m³/s)": inflow, "Sortant (m³/s)": q, "Niveau (m)": zs})


def chute_bassin(Q, B, drop, H0):
    """Coursier + ressaut : y1 supercritique au pied, Froude, conjuguée, longueur du bassin."""
    q = Q / B
    E = drop + H0 + 0.0
    yc = (q ** 2 / G) ** (1 / 3)
    lo, hi = 1e-3, yc
    for _ in range(80):
        mid = (lo + hi) / 2
        f = mid + q ** 2 / (2 * G * mid ** 2) - E
        if f > 0:
            lo = mid
        else:
            hi = mid
    y1 = (lo + hi) / 2
    V1 = q / y1
    Fr = V1 / math.sqrt(G * y1)
    y2 = y1 / 2 * (math.sqrt(1 + 8 * Fr ** 2) - 1)
    dE = (y2 - y1) ** 3 / (4 * y1 * y2)
    return dict(q=q, yc=yc, y1=y1, V1=V1, Fr=Fr, y2=y2, Lb=6.1 * y2, dE=dE, E=E)


def orifice_q(A, h, Cd=0.62):
    return Cd * A * math.sqrt(2 * G * max(h, 0.0))


def envasement(vol_hm3, apport_t_km2_an, bv_km2, densite=1.2, piege=0.9):
    t_an = apport_t_km2_an * bv_km2 * piege
    m3_an = t_an / densite
    return m3_an, vol_hm3 * 1e6 / m3_an if m3_an > 0 else float("inf")


def classe_barrage(H, V_hm3):
    k = H ** 2 * math.sqrt(max(V_hm3, 0.0))
    if H >= 20 and k >= 1500:
        return "A", k
    if H >= 10 and k >= 200:
        return "B", k
    if H >= 5 and k >= 20:
        return "C", k
    return "D", k


def froehlich(Vw_m3, Hw_m):
    """Rupture hypothétique (Froehlich 1995) : débit de pointe et temps de formation."""
    Qp = 0.607 * Vw_m3 ** 0.295 * Hw_m ** 1.24
    tf = 0.00254 * Vw_m3 ** 0.53 * Hw_m ** -0.90
    return Qp, tf


def eval_beton(df):
    d = df.copy()
    d["Âge (j)"] = pd.to_numeric(d["Âge (j)"], errors="coerce")
    d["Résistance (MPa)"] = pd.to_numeric(d["Résistance (MPa)"], errors="coerce")
    d = d.dropna(subset=["Classe", "Âge (j)", "Résistance (MPa)"])
    rows = []
    for cl, g in d[d["Âge (j)"].round() == 28].groupby("Classe"):
        try:
            fck = float(str(cl).replace("C", "").split("/")[0])
        except ValueError:
            continue
        v = g["Résistance (MPa)"].values
        n = len(v)
        if n < 3:
            rows.append({"Classe": cl, "n": n, "fcm (MPa)": round(float(v.mean()), 1), "f min (MPa)": round(float(v.min()), 1),
                         "Statut": "⚠️ Échantillon insuffisant"})
            continue
        ok = v.mean() >= fck + 4 and v.min() >= fck - 4
        rows.append({"Classe": cl, "n": n, "fcm (MPa)": round(float(v.mean()), 1), "f min (MPa)": round(float(v.min()), 1),
                     "Statut": "✅ Conforme" if ok else "❌ Non conforme"})
    return pd.DataFrame(rows, columns=["Classe", "n", "fcm (MPa)", "f min (MPa)", "Statut"])


def compaction_df(df):
    d = df.copy()
    for c in NUMS["compactage"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["Compactage (% OPM)"] = d["Densité sèche (t/m³)"] / d["OPM (t/m³)"] * 100
    d["Écart w (pts)"] = d["Teneur en eau (%)"] - d["w OPM (%)"]
    return d.dropna(subset=["Zone", "Compactage (% OPM)"])


def compaction_summary(df):
    rows = []
    for z, g in compaction_df(df).groupby("Zone"):
        v = g["Compactage (% OPM)"].values
        sv = COMPACT_MIN.get(z, 95.0)
        ok = v.mean() >= sv and v.min() >= sv - 2
        rows.append({"Zone": z, "n": len(v), "Moyenne (% OPM)": round(v.mean(), 1), "Min (% OPM)": round(v.min(), 1),
                     "Seuil": sv, "Statut": "✅ Conforme" if ok else "❌ Non conforme"})
    return pd.DataFrame(rows, columns=["Zone", "n", "Moyenne (% OPM)", "Min (% OPM)", "Seuil", "Statut"])


def instr_status(df, seuils):
    r = df.copy()
    r["Valeur"] = pd.to_numeric(r["Valeur"], errors="coerce")
    r["Date"] = pd.to_datetime(r["Date"], errors="coerce")
    r = r.dropna(subset=["Instrument", "Valeur", "Date"]).sort_values("Date")
    sm = {row["Instrument"]: (fnum(row["Seuil alerte"], float("inf")), fnum(row["Seuil alarme"], float("inf")))
          for _, row in seuils.iterrows()}
    rows = []
    for ins, g in r.groupby("Instrument"):
        last = float(g["Valeur"].iloc[-1])
        al, am = sm.get(ins, (float("inf"), float("inf")))
        st_ = "🚨 Alarme" if last >= am else "⚠️ Alerte" if last >= al else "✅ Normal"
        slope = float("nan")
        if len(g) >= 3:
            x = (g["Date"] - g["Date"].min()).dt.days.values.astype(float)
            if x.max() > 0:
                slope = float(np.polyfit(x, g["Valeur"].values, 1)[0]) * 30
        rows.append({"Instrument": ins, "Type": g["Type"].iloc[-1], "Dernière valeur": round(last, 2),
                     "Unité": g["Unité"].iloc[-1], "Alerte": al, "Alarme": am,
                     "Tendance (/mois)": None if slope != slope else round(slope, 3), "Statut": st_})
    return pd.DataFrame(rows, columns=["Instrument", "Type", "Dernière valeur", "Unité", "Alerte", "Alarme",
                                       "Tendance (/mois)", "Statut"])


# ===================== CALCULS : BARRAGE-POIDS =====================
def trap_uplift(a, b, L):
    """Sous-pression trapézoïdale : résultante et bras depuis l'extrémité d'ordonnée a."""
    area = (a + b) / 2 * L
    arm = L * (a + 2 * b) / (3 * (a + b)) if (a + b) > 0 else L / 2
    return area, arm


def stabilite(p, hw, tw, kh=0.0):
    """Stabilité d'un barrage-poids, par mètre linéaire. Origine au pied aval, x vers l'amont."""
    H, b, m, n = p["H"], p["b"], p["m"], p["n"]
    B = m * H + b + n * H
    hw = min(hw, H)
    comps = [("Crête", b * H * p["gc"], m * H + b / 2, H / 2),
             ("Parement aval", 0.5 * m * H * H * p["gc"], 2 * m * H / 3, H / 3),
             ("Parement amont", 0.5 * n * H * H * p["gc"], m * H + b + n * H / 3, H / 3)]
    Wc = sum(c[1] for c in comps)
    Mres = sum(c[1] * c[2] for c in comps)
    Ww = GW * n * hw * hw / 2
    Mres += Ww * (B - n * hw / 3)
    Ph = GW * hw ** 2 / 2
    Mov = Ph * hw / 3
    Hs = Ms = 0.0
    if p["hs"] > 0:
        Hs = p["Ks"] * p["gs"] * p["hs"] ** 2 / 2
        Ms = Hs * p["hs"] / 3
    Pe = Me = 0.0
    Fi = Mi = 0.0
    if kh > 0:
        Pe = 0.583 * kh * GW * hw ** 2
        Me = Pe * 0.4 * hw
        for _, w, x, y in comps:
            Fi += kh * w
            Mi += kh * w * y
    uh, ut = GW * hw, GW * tw
    ud = GW * (tw + (1 - p["E"]) * max(hw - tw, 0.0))
    xd = min(p["xd"], B)
    a1, r1 = trap_uplift(uh, ud, xd)
    a2, r2 = trap_uplift(ud, ut, B - xd)
    U = a1 + a2
    xU = (a1 * (B - r1) + a2 * ((B - xd) - r2)) / U if U > 0 else B / 2
    Mov_tot = Mov + Ms + Me + Mi + U * xU
    SH = Ph + Hs + Pe + Fi
    SV = Wc + Ww - U
    FSo = Mres / Mov_tot if Mov_tot > 0 else 99.0
    FSs = (p["c"] * B + SV * math.tan(math.radians(p["phi"]))) / SH if SH > 0 else 99.0
    xR = (Mres - Mov_tot) / SV if SV > 0 else 0.0
    e = B / 2 - xR
    s_toe = SV / B * (1 + 6 * e / B)
    s_heel = SV / B * (1 - 6 * e / B)
    return dict(B=B, W=Wc, Ww=Ww, Ph=Ph, Hs=Hs, Pe=Pe, Fi=Fi, U=U, SV=SV, SH=SH, FSo=FSo, FSs=FSs, xR=xR, e=e,
                s_toe=s_toe, s_heel=s_heel, tiers=(B / 3 <= xR <= 2 * B / 3), area=Wc / p["gc"])


# ===================== CALCULS : BARRAGE EN REMBLAI =====================
def hauteur_vague(F_km, V_kmh):
    hv = 0.032 * math.sqrt(V_kmh * F_km) + 0.763 - 0.271 * F_km ** 0.25 if F_km < 32 else 0.032 * math.sqrt(V_kmh * F_km)
    return max(hv, 0.1)


def revanche_stevenson(F_km, V_kmh):
    hv = hauteur_vague(F_km, V_kmh)
    vw = 1.5 + 2 * hv
    return hv, hv + vw ** 2 / (2 * G)


def fuite_casagrande(k, h, d):
    y0 = math.sqrt(d * d + h * h) - d
    return k * y0, y0


def pente_infinie(beta_deg, phi_deg, gsat, ru=0.0):
    b, f = math.radians(beta_deg), math.radians(phi_deg)
    return (1 - ru / math.cos(b) ** 2) * math.tan(f) / math.tan(b)


def fellenius(profil, xc, yc, R, gam, c, phi, ru):
    """FS d'un cercle de glissement (Fellenius, tranches). profil=(m1,H,b,m2)."""
    m1, H, b, m2 = profil
    xs = np.linspace(xc - R, xc + R, 600)
    yb = yc - np.sqrt(np.maximum(R ** 2 - (xs - xc) ** 2, 0))
    ys = np.interp(xs, [-1e3, 0, m1 * H, m1 * H + b, m1 * H + b + m2 * H, 1e4], [0, 0, H, H, 0, 0])
    mask = yb < ys
    if mask.sum() < 5:
        return float("nan")
    idx = np.where(mask)[0]
    x, ybb, yss = xs[idx], yb[idx], ys[idx]
    dx = xs[1] - xs[0]
    Wt = gam * (yss - ybb) * dx
    sin_a = np.clip((xc - x) / R, -0.999, 0.999)
    cos_a = np.sqrt(1 - sin_a ** 2)
    l = dx / cos_a
    resist = c * l + (Wt * cos_a - ru * Wt / dx * l) * math.tan(math.radians(phi))
    drive = Wt * sin_a
    dsum = drive.sum()
    return float(resist.sum() / dsum) if dsum > 1e-6 else float("nan")


def scan_talus_aval(profil, gam, c, phi, ru, n=8):
    m1, H, b, m2 = profil
    Bt = m1 * H + b + m2 * H
    best = (1e9, 0, 0, 0)
    pts = []
    for xc in np.linspace(m1 * H + b, Bt + 0.8 * H, n):
        for yc in np.linspace(1.0 * H, 2.2 * H, n):
            R = math.sqrt((Bt - xc) ** 2 + yc ** 2)
            fs = fellenius(profil, xc, yc, R, gam, c, phi, ru)
            if fs == fs:
                pts.append((xc, yc, fs))
                if fs < best[0]:
                    best = (fs, xc, yc, R)
    return best, pts


def filtre_terzaghi(D15f, D85b, D15b):
    r1, r2 = D15f / D85b, D15f / D15b
    return r1, r2, (r1 <= 5 and r2 >= 5)


def lane_creep(Lv, Lh, head):
    Lw = Lv + Lh / 3.0
    return Lw, Lw / head if head > 0 else 99.0


def delta_T_adiabatique(ciment, q_kj, rho=2400.0, cp=1.0):
    return ciment * q_kj / (rho * cp)


# ===================== ÉTAT INITIAL =====================
def init_state():
    S = st.session_state
    if "init" in S:
        return
    today = date.today()
    rng = np.random.default_rng(11)
    S.projet = dict(nom="Barrage de la Vallée Verte", moa="Agence Nationale des Barrages", lieu="",
                    type="Barrage en remblai zoné", H=40.0, cote_fond=100.0, cote_crete=140.0, cote_nnr=136.0,
                    cote_phe=138.5, lcrete=280.0, bv=120.0, budget=30_000_000.0,
                    debut=today - timedelta(days=120), fin=today + timedelta(days=700), devise="€")
    S.hsv = coerce(pd.DataFrame({"Cote (m)": [100.0, 105, 110, 115, 120, 125, 130, 135, 140],
                                 "Surface (ha)": [0.0, 2, 8, 22, 45, 80, 125, 180, 245]}), "hsv")
    S.seuils = coerce(pd.DataFrame([("PZ1", 110.0, 112.0), ("PZ2", 108.0, 110.0), ("DB1", 40.0, 60.0),
                                    ("TA1", 30.0, 50.0), ("DEP1", 15.0, 25.0), ("PI1", 90.0, 110.0)],
                                   columns=COLS["seuils"]), "seuils")
    rows = []
    for i in range(8):
        dt = today - timedelta(days=30 * (8 - i))
        niv = 120 + 2.5 * i
        vals = {"PZ1": ("Piézomètre", 105 + 0.30 * (niv - 120)), "PZ2": ("Piézomètre", 103 + 0.30 * (niv - 120)),
                "DB1": ("Débit de fuite", 14 + 1.0 * (niv - 120)), "TA1": ("Tassement", 5 + 2.0 * i),
                "DEP1": ("Déplacement de crête", 2 + 0.9 * i), "PI1": ("Pression interstitielle", 45 + 3.5 * i)}
        for nom, (tp, v) in vals.items():
            rows.append({"Date": dt, "Instrument": nom, "Type": tp, "Valeur": round(float(v + rng.normal(0, 0.4)), 2),
                         "Unité": INSTR[tp], "Niveau retenue (m)": niv, "Remarque": ""})
    S.releves = coerce(pd.DataFrame(rows), "releves")
    acts = ["Excavation de fondation rive gauche", "Injections du voile d'étanchéité", "Pose du filtre cheminée",
            "Mise en place du noyau (couches 25 cm)", "Compactage des recharges", "Bétonnage de l'évacuateur"]
    S.journal = coerce(pd.DataFrame([{"Date": today - timedelta(days=10 - 2 * i), "Météo": METEO[i % 3],
                                      "Effectif": int(60 + rng.integers(0, 40)), "Activités": a,
                                      "Observations": "RAS" if i % 2 == 0 else "Arrêt pluie 4 h"}
                                     for i, a in enumerate(acts)]), "journal")
    et = [{"Date": today - timedelta(days=90 - 8 * i), "Élément": f"Évacuateur plot {i + 1}", "Classe": "C25/30",
           "Âge (j)": 28.0, "Résistance (MPa)": round(float(rng.normal(34, 2)), 1)} for i in range(8)]
    et += [{"Date": today - timedelta(days=60 - 10 * i), "Élément": f"Vanne de fond bloc {i + 1}", "Classe": "C30/37",
            "Âge (j)": 28.0, "Résistance (MPa)": round(float(rng.normal(41, 2)), 1)} for i in range(4)]
    S.essais = coerce(pd.DataFrame(et), "essais")
    opm = {"Noyau": (1.85, 14.5, 98.8), "Recharge amont": (2.05, 9.0, 96.5), "Recharge aval": (2.05, 9.0, 96.8),
           "Filtre / drain": (1.95, 6.0, 97.0)}
    cp = []
    for z, (o, w, mc) in opm.items():
        for j in range(5):
            cp.append({"Date": today - timedelta(days=30 - 3 * j), "Zone": z,
                       "Densité sèche (t/m³)": round(o * rng.normal(mc, 0.9) / 100, 3), "OPM (t/m³)": o,
                       "Teneur en eau (%)": round(w + rng.normal(0, 0.6), 1), "w OPM (%)": w})
    S.compactage = coerce(pd.DataFrame(cp), "compactage")
    mt = [("01 Installation et dérivation", "Installation, batardeaux et galerie de dérivation", "forfait", 1, 2_000_000),
          ("02 Terrassements et fondation", "Excavation de fondation", "m³", 85000, 9),
          ("03 Traitement de fondation", "Forages d'injection", "ml", 9000, 120),
          ("03 Traitement de fondation", "Ciment d'injection", "t", 450, 380),
          ("04 Corps du barrage", "Noyau argileux compacté", "m³", 190000, 11),
          ("04 Corps du barrage", "Recharges compactées", "m³", 520000, 7),
          ("04 Corps du barrage", "Filtres et drains", "m³", 90000, 22),
          ("04 Corps du barrage", "Enrochements de protection (rip-rap)", "m³", 40000, 30),
          ("05 Évacuateur de crues", "Béton armé", "m³", 14000, 380),
          ("05 Évacuateur de crues", "Acier HA", "kg", 1_100_000, 1.7),
          ("05 Évacuateur de crues", "Vannes et équipements", "forfait", 1, 1_500_000),
          ("06 Vidange et prise d'eau", "Conduite en acier", "ml", 120, 5200),
          ("06 Vidange et prise d'eau", "Vannes de vidange et prise", "forfait", 1, 900_000),
          ("07 Auscultation", "Instrumentation et centrale d'acquisition", "forfait", 1, 650_000),
          ("08 Divers", "Pistes d'accès et remise en état", "forfait", 1, 1_200_000),
          ("08 Divers", "Études, contrôle et essais", "forfait", 1, 1_500_000)]
    S.metre = coerce(pd.DataFrame(mt, columns=COLS["metre"]), "metre")
    tk = [("Installation de chantier", 30, "Entreprise", "", 100), ("Dérivation provisoire", 90, "Entreprise",
          "Installation de chantier", 100), ("Batardeaux", 45, "Entreprise", "Dérivation provisoire", 100),
          ("Excavation de fondation", 80, "Terrassier", "Batardeaux", 85), ("Traitement de fondation", 100, "Injection",
          "Excavation de fondation", 40), ("Évacuateur de crues", 240, "Génie civil", "Excavation de fondation", 20),
          ("Corps du barrage (remblai)", 330, "Terrassier", "Traitement de fondation", 5),
          ("Vidange de fond et prise d'eau", 150, "Hydromécanique", "Excavation de fondation", 0),
          ("Instrumentation", 60, "Auscultation", "Corps du barrage (remblai)", 0),
          ("Protection des talus", 70, "Terrassier", "Corps du barrage (remblai)", 0),
          ("Mise en eau progressive", 120, "MOE / exploitant", "Évacuateur de crues;Vidange de fond et prise d'eau;Protection des talus;Instrumentation", 0),
          ("Réception", 20, "MOA / MOE", "Mise en eau progressive", 0)]
    tdf = pd.DataFrame([{"Tâche": a, "Début": today, "Durée (j)": b, "Avancement (%)": e, "Responsable": c,
                         "Prédécesseurs": d} for a, b, c, d, e in tk])
    sched, _ = cpm(tdf)
    tdf["Début"] = [S.projet["debut"] + timedelta(days=int(v)) for v in sched["ES"]]
    S.taches = coerce(tdf, "taches")
    rk = [("Surverse en crue (évacuateur sous-dimensionné)", "Exploitation", 2, 5, "Crue de sûreté, laminage vérifié"),
          ("Érosion interne (renard hydraulique)", "Corps du barrage", 2, 5, "Filtres, drains, contrôle de fuite"),
          ("Instabilité de talus", "Corps du barrage", 2, 5, "Pentes, drainage, auscultation"),
          ("Crue en cours de chantier (batardeau)", "Chantier", 3, 4, "Dérivation dimensionnée, alerte météo"),
          ("Séisme", "Exploitation", 2, 5, "Dimensionnement sismique, inspection post-séisme"),
          ("Éboulement en excavation de fondation", "Chantier", 3, 4, "Purge, soutènement, talutage"),
          ("Accident d'engins sur la crête / rampe", "Chantier", 3, 4, "Circulation, signalisation, formation"),
          ("Défaut d'étanchéité de la fondation", "Fondation", 3, 4, "Voile d'injection, drains, piézomètres")]
    S.risques = coerce(pd.DataFrame(rk, columns=COLS["risques"]), "risques")
    B = S.projet["budget"]
    S.ev = coerce(pd.DataFrame({"Mois": list(range(1, 13)),
                                "PV cumulé": [B * x for x in (.03, .07, .12, .18, .25, .33, .42, .52, .63, .75, .88, 1.0)],
                                "EV cumulée": [B * x for x in (.03, .065, .11, .16, .22)] + [np.nan] * 7,
                                "AC cumulé": [B * x for x in (.032, .07, .12, .175, .24)] + [np.nan] * 7}), "ev")
    S.crue = dict(Qp=450.0, tp=8.0, crest=136.0, L=40.0, C=2.2, vid=0.0)
    S.init = True


# ===================== PAGE : TABLEAU DE BORD =====================
def page_dashboard():
    S = st.session_state
    P = S.projet
    hero("🌊 Tableau de bord du barrage", f"{P['nom']} — {P['type']}")
    with st.expander("✏️ Informations générales du projet"):
        c1, c2, c3 = st.columns(3)
        P["nom"] = c1.text_input("Nom du projet", P["nom"])
        P["moa"] = c2.text_input("Maître d'ouvrage", P["moa"])
        P["lieu"] = c3.text_input("Localisation", P["lieu"])
        c1, c2, c3, c4 = st.columns(4)
        P["type"] = c1.selectbox("Type de barrage", TYPES_BARRAGE, index=TYPES_BARRAGE.index(P["type"]))
        P["cote_fond"] = float(c2.number_input("Cote de fondation (m)", 0.0, 5000.0, float(P["cote_fond"]), 0.5))
        P["cote_crete"] = float(c3.number_input("Cote de crête (m)", 1.0, 5000.0, float(P["cote_crete"]), 0.5))
        P["lcrete"] = float(c4.number_input("Longueur en crête (m)", 20.0, 20000.0, float(P["lcrete"]), 10.0))
        c1, c2, c3, c4 = st.columns(4)
        P["cote_nnr"] = float(c1.number_input("Cote de retenue normale (m)", 1.0, 5000.0, float(P["cote_nnr"]), 0.5))
        P["cote_phe"] = float(c2.number_input("Cote des plus hautes eaux (m)", 1.0, 5000.0, float(P["cote_phe"]), 0.5))
        P["bv"] = float(c3.number_input("Bassin versant (km²)", 1.0, 100000.0, float(P["bv"]), 5.0))
        P["budget"] = float(c4.number_input("Budget cible HT", 0.0, 1e11, float(P["budget"]), 100000.0))
        c1, c2, c3 = st.columns(3)
        P["debut"] = c1.date_input("Début des travaux", P["debut"])
        P["fin"] = c2.date_input("Fin contractuelle", P["fin"])
        devs = ["€", "FCFA", "$", "MAD", "DZD"]
        P["devise"] = c3.selectbox("Devise", devs, index=devs.index(P["devise"]) if P["devise"] in devs else 0)
        P["H"] = P["cote_crete"] - P["cote_fond"]
    dev = P["devise"]
    hv = hsv_table(S.hsv)
    Vnnr = vol_at(hv, P["cote_nnr"]) / 1e6 if len(hv) else 0.0
    cl, kk = classe_barrage(P["H"], Vnnr)
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() > 0 else 0.0
    tot = float(metre_totals(S.metre)["Total"].sum())
    ist = instr_status(S.releves, S.seuils)
    n_alm = int((ist["Statut"] == "🚨 Alarme").sum()) if len(ist) else 0
    n_alt = int((ist["Statut"] == "⚠️ Alerte").sum()) if len(ist) else 0
    comp = compaction_summary(S.compactage)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hauteur du barrage", f"{P['H']:.1f} m")
    c2.metric("Volume de la retenue (NNR)", f"{Vnnr:.2f} hm³")
    c3.metric("Classe de l'ouvrage", f"Classe {cl}", f"H²√V = {kk:.0f}")
    c4.metric("Avancement global", f"{avanc:.1f} %")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estimation du métré HT", f"{fmt(tot, 0)} {dev}",
              f"{(tot - P['budget']) / P['budget'] * 100:+.1f} % vs budget" if P["budget"] else None, delta_color="inverse")
    c2.metric("Instruments en alerte / alarme", f"{n_alt} / {n_alm}")
    c3.metric("Zones de remblai conformes", f"{int((comp['Statut'] == '✅ Conforme').sum())} / {len(comp)}")
    c4.metric("Jours avant échéance", f"{(P['fin'] - date.today()).days} j")
    g1, g2 = st.columns(2)
    with g1:
        tt = t.copy()
        tt["Avancement (%)"] = num(tt, "Avancement (%)")
        fig = px.bar(tt, x="Avancement (%)", y="Tâche", orientation="h", range_x=[0, 100], color="Avancement (%)",
                     color_continuous_scale=[[0, ACCENT_CLAIR], [1, NOIR]], title="Avancement par tâche")
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(coloraxis_showscale=False)
        pplot(fig, 440)
    with g2:
        lots = metre_totals(S.metre).groupby("Lot", as_index=False)["Total"].sum()
        if len(lots) and lots["Total"].sum() > 0:
            pplot(px.pie(lots, names="Lot", values="Total", hole=0.5, title="Répartition du coût par lot",
                         color_discrete_sequence=[NOIR, ACCENT, ROUGE, BLEU, VERT, ORANGE, GRIS, "#8D6E63"]), 440)
    if len(hv):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hv["Volume (hm³)"], y=hv["Cote (m)"], name="Volume", line=dict(color=NOIR, width=4)))
        fig.add_hline(y=P["cote_nnr"], line_dash="dash", line_color=ACCENT, annotation_text="Retenue normale")
        fig.add_hline(y=P["cote_phe"], line_dash="dash", line_color=ORANGE, annotation_text="Plus hautes eaux")
        fig.add_hline(y=P["cote_crete"], line_dash="dash", line_color=ROUGE, annotation_text="Crête")
        fig.update_layout(title="Courbe cote – volume de la retenue", xaxis_title="Volume (hm³)", yaxis_title="Cote (m)")
        pplot(fig, 340)


# ===================== PAGE : COLLECTE =====================
def page_collecte():
    S = st.session_state
    hero("📥 Collecte de données de chantier et d'auscultation", "Journal, relevés des instruments, import / fusion de fichiers")
    t1, t2, t3 = st.tabs(["📓 Journal de chantier", "📡 Relevés d'auscultation", "📎 Import / fusion"])
    with t1:
        with st.form("form_journal", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            d = c1.date_input("Date", date.today())
            m = c2.selectbox("Météo", METEO)
            e = c3.number_input("Effectif présent", 0, 2000, 80)
            act = st.text_area("Activités réalisées")
            obs = st.text_area("Incidents / observations")
            if st.form_submit_button("➕ Ajouter l'entrée"):
                add_rows("journal", pd.DataFrame([{"Date": d, "Météo": m, "Effectif": e, "Activités": act, "Observations": obs}]))
                st.rerun()
        editor("journal", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                           "Météo": st.column_config.SelectboxColumn("Météo", options=METEO)})
    with t2:
        with st.form("form_releve", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            d = c1.date_input("Date du relevé", date.today())
            nom = c2.text_input("Instrument (ex. PZ1)", "PZ1")
            tp = c3.selectbox("Type", list(INSTR))
            v = c4.number_input("Valeur", value=0.0, step=0.1, format="%.2f")
            c1, c2 = st.columns(2)
            nr = c1.number_input("Niveau de la retenue (m)", 0.0, 5000.0, float(S.projet["cote_nnr"]), 0.1)
            rem = c2.text_input("Remarque")
            if st.form_submit_button("➕ Enregistrer le relevé"):
                add_rows("releves", pd.DataFrame([{"Date": d, "Instrument": nom, "Type": tp, "Valeur": v, "Unité": INSTR[tp],
                                                   "Niveau retenue (m)": nr, "Remarque": rem}]))
                st.rerun()
        editor("releves", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                           "Type": st.column_config.SelectboxColumn("Type", options=list(INSTR))})
    with t3:
        key = st.selectbox("Jeu de données cible", list(LABELS), format_func=lambda k: LABELS[k])
        st.caption("Colonnes attendues : " + " | ".join(COLS[key]))
        up = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx"])
        if up is not None:
            try:
                df = pd.read_csv(up, sep=None, engine="python") if up.name.lower().endswith(".csv") else pd.read_excel(up)
                manque = [c for c in COLS[key] if c not in df.columns]
                if manque:
                    st.error("Colonnes manquantes : " + ", ".join(manque))
                else:
                    df = coerce(df, key)
                    show_df(df.head(20))
                    mode = st.radio("Mode", ["Ajouter aux données existantes", "Remplacer les données"], horizontal=True)
                    if st.button("📥 Importer"):
                        set_df(key, pd.concat([S[key], df], ignore_index=True) if mode.startswith("Ajouter") else df)
                        st.rerun()
            except Exception as ex:
                st.error(f"Lecture impossible : {ex}")


# ===================== PAGE : RETENUE =====================
def page_retenue():
    S = st.session_state
    P = S.projet
    hero("💧 Retenue : courbe hauteur-volume, bilan et envasement", "Courbe cote–surface–volume • évaporation • durée de vie")
    t1, t2 = st.tabs(["📈 Courbe cote – surface – volume", "🏜️ Bilan, évaporation et envasement"])
    with t1:
        note("Saisir la surface du plan d'eau (en hectares) pour plusieurs cotes ; les volumes sont calculés par la méthode du tronc de prisme.")
        editor("hsv")
        hv = hsv_table(S.hsv)
        if len(hv) < 2:
            st.info("Saisir au moins deux cotes.")
            return
        c1, c2, c3 = st.columns(3)
        c1.metric("Volume à la retenue normale", f"{vol_at(hv, P['cote_nnr']) / 1e6:.2f} hm³")
        c2.metric("Volume aux plus hautes eaux", f"{vol_at(hv, P['cote_phe']) / 1e6:.2f} hm³")
        c3.metric("Surface à la retenue normale", f"{surf_at(hv, P['cote_nnr']):.0f} ha")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hv["Volume (hm³)"], y=hv["Cote (m)"], name="Volume (hm³)", line=dict(color=NOIR, width=4)))
        fig.add_trace(go.Scatter(x=hv["Surface (ha)"], y=hv["Cote (m)"], name="Surface (ha)", line=dict(color=ACCENT, width=4),
                                 xaxis="x2"))
        fig.update_layout(title="Courbes cote – volume / cote – surface", xaxis_title="Volume (hm³)", yaxis_title="Cote (m)",
                          xaxis2=dict(overlaying="x", side="top", title="Surface (ha)"))
        pplot(fig, 400)
        show_df(hv[["Cote (m)", "Surface (ha)", "Volume (hm³)"]].round(3))
    with t2:
        hv = hsv_table(S.hsv)
        c1, c2, c3 = st.columns(3)
        apport = c1.number_input("Apport annuel moyen (hm³/an)", 0.1, 5000.0, 38.0, 1.0)
        demande = c1.number_input("Demande annuelle (hm³/an)", 0.0, 5000.0, 22.0, 1.0)
        evap = c2.number_input("Évaporation annuelle (mm)", 200.0, 3500.0, 1400.0, 50.0)
        vmort = c2.number_input("Volume mort (hm³)", 0.0, 500.0, 2.0, 0.5)
        ero = c3.number_input("Érosion spécifique (t/km²/an)", 10.0, 5000.0, 400.0, 10.0)
        pi_ = c3.slider("Taux de piégeage des sédiments", 0.3, 1.0, 0.9, 0.05)
        Vn = vol_at(hv, P["cote_nnr"]) / 1e6 if len(hv) else 0.0
        Sn = surf_at(hv, P["cote_nnr"]) if len(hv) else 0.0
        Ev = Sn * 1e4 * evap / 1000 / 1e6
        m3, ans = envasement(Vn, ero, P["bv"], 1.2, pi_)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Volume utile", f"{max(Vn - vmort, 0):.2f} hm³")
        c2.metric("Perte annuelle par évaporation", f"{Ev:.2f} hm³")
        c3.metric("Apport solide piégé", f"{m3 / 1e3:.0f} 10³ m³/an")
        c4.metric("Durée de vie vis-à-vis de l'envasement", f"{ans:.0f} ans" if ans < 1e6 else "—")
        reg = max(Vn - vmort, 0) / apport
        verdict(apport - Ev >= demande, f"Apports nets ({apport - Ev:.1f} hm³/an) ≥ demande ({demande:.1f}). Taux de régularisation : {reg * 100:.0f} %.",
                f"Apports nets ({apport - Ev:.1f} hm³/an) < demande ({demande:.1f}) : la retenue ne couvre pas la demande.")


# ===================== PAGE : CRUE ET ÉVACUATEUR =====================
def y_normal_rect(Q, B, S, n):
    lo, hi = 1e-3, 50.0
    for _ in range(80):
        y = (lo + hi) / 2
        A, P_ = B * y, B + 2 * y
        if A * (A / P_) ** (2 / 3) * math.sqrt(S) / n < Q:
            lo = y
        else:
            hi = y
    return (lo + hi) / 2


def page_crue():
    S = st.session_state
    P = S.projet
    cr = S.crue
    hero("🌪️ Crue de projet et évacuateur de crues", "Francou-Rodier • laminage de Puls • coursier et bassin de dissipation • vidange de fond")
    t1, t2, t3, t4 = st.tabs(["🌊 Crue de projet", "📉 Laminage", "⛲ Coursier et dissipation", "🚰 Vidange de fond"])
    hv = hsv_table(S.hsv)
    with t1:
        c1, c2, c3 = st.columns(3)
        K = c1.slider("Coefficient régional K de Francou-Rodier", 3.5, 6.5, 4.5, 0.1)
        Qfr = 1e6 * (P["bv"] / 1e8) ** (1 - K / 10)
        cr["Qp"] = float(c2.number_input("Débit de pointe retenu (m³/s)", 1.0, 100000.0, float(round(Qfr)), 10.0))
        cr["tp"] = float(c3.number_input("Temps de montée (h)", 0.5, 100.0, float(cr["tp"]), 0.5))
        c1, c2, c3 = st.columns(3)
        c1.metric("Q Francou-Rodier", f"{Qfr:.0f} m³/s")
        c2.metric("Temps de base", f"{2.67 * cr['tp']:.1f} h")
        c3.metric("Volume de crue", f"{0.5 * cr['Qp'] * 2.67 * cr['tp'] * 3600 / 1e6:.2f} hm³")
        note("Q = Q0·(S/S0)^(1 − K/10), Q0 = 10⁶ m³/s et S0 = 10⁸ km². À confirmer par une étude hydrologique (stations, gradex, pluies extrêmes).")
    with t2:
        if len(hv) < 2:
            st.info("Renseigner d'abord la courbe cote–volume.")
            return
        c1, c2, c3, c4 = st.columns(4)
        cr["crest"] = float(c1.number_input("Cote du seuil déversant (m)", 1.0, 5000.0, float(P["cote_nnr"]), 0.5))
        cr["L"] = float(c2.number_input("Largeur déversante (m)", 1.0, 500.0, float(cr["L"]), 1.0))
        cr["C"] = float(c3.selectbox("Coefficient de déversoir C", [2.2, 1.7, 1.5], index=0,
                                     format_func=lambda v: {2.2: "2,2 profil Creager", 1.7: "1,7 seuil épais", 1.5: "1,5 seuil mince"}[v]))
        cr["vid"] = float(c4.number_input("Débit de vidange en crue (m³/s)", 0.0, 1000.0, float(cr["vid"]), 5.0))
        df = laminage(hv, cr["crest"], cr["L"], cr["C"], cr["Qp"], cr["tp"], 600.0, cr["vid"])
        qmax, zmax = float(df["Sortant (m³/s)"].max()), float(df["Niveau (m)"].max())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Débit entrant max", f"{cr['Qp']:.0f} m³/s")
        c2.metric("Débit sortant max", f"{qmax:.0f} m³/s")
        c3.metric("Écrêtement", f"{(1 - qmax / cr['Qp']) * 100:.0f} %")
        c4.metric("Cote maximale atteinte", f"{zmax:.2f} m")
        rev = P["cote_crete"] - zmax
        verdict(rev >= 1.0, f"Revanche en crue : {rev:.2f} m (≥ 1,0 m).", f"Revanche en crue insuffisante : {rev:.2f} m — élargir le déversoir ou relever la crête.")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["t (h)"], y=df["Entrant (m³/s)"], name="Entrant", line=dict(color=NOIR, width=4)))
        fig.add_trace(go.Scatter(x=df["t (h)"], y=df["Sortant (m³/s)"], name="Sortant", line=dict(color=ACCENT, width=4)))
        fig.add_trace(go.Scatter(x=df["t (h)"], y=df["Niveau (m)"], name="Niveau (m)", yaxis="y2", line=dict(color=ORANGE, width=3, dash="dot")))
        fig.update_layout(title="Laminage de crue", xaxis_title="Temps (h)", yaxis_title="Débit (m³/s)",
                          yaxis2=dict(overlaying="y", side="right", title="Cote (m)"))
        pplot(fig, 400)
    with t3:
        c1, c2, c3 = st.columns(3)
        Q = c1.number_input("Débit dans le coursier (m³/s)", 1.0, 50000.0, float(max(round(cr["Qp"] * 0.6), 10)), 10.0)
        B = c1.number_input("Largeur du coursier (m)", 2.0, 300.0, 30.0, 1.0)
        drop = c2.number_input("Dénivelée seuil → bassin (m)", 2.0, 200.0, 30.0, 1.0)
        H0 = c2.number_input("Charge sur le seuil (m)", 0.2, 10.0, 2.5, 0.1)
        pente = c3.number_input("Pente du coursier (%)", 1.0, 80.0, 30.0, 1.0) / 100
        n = c3.number_input("n de Manning du béton", 0.010, 0.020, 0.014, 0.001, format="%.3f")
        r = chute_bassin(Q, B, drop, H0)
        yn = y_normal_rect(Q, B, pente, n)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tirant critique", f"{r['yc']:.2f} m")
        c2.metric("Tirant normal (coursier)", f"{yn:.2f} m")
        c3.metric("V et Froude au pied", f"{r['V1']:.1f} m/s / {r['Fr']:.1f}")
        c4.metric("Conjugué y2 / longueur du bassin", f"{r['y2']:.1f} m / {r['Lb']:.0f} m")
        typ = ("Pas de ressaut franc : prévoir un autre dissipateur" if r["Fr"] < 1.7 else
               "Ressaut faible" if r["Fr"] < 2.5 else "Ressaut oscillant : éviter / déflecteurs" if r["Fr"] < 4.5 else
               "Bassin USBR type III (blocs et seuil)" if r["Fr"] < 9 and r["V1"] < 18 else
               "Bassin USBR type II (V < 18 m/s) ou saut de ski" if r["Fr"] >= 4.5 and r["V1"] < 18 else "Saut de ski / cuillère recommandé (V ≥ 18 m/s)")
        st.info(f"Dissipation d'énergie : {r['dE']:.1f} m de charge. Type de dissipateur indicatif : {typ}.")
        verdict(r["V1"] < 30, "Vitesse < 30 m/s (risque de cavitation limité).", "Vitesse ≥ 30 m/s : risque de cavitation, aérer le coursier.")
    with t4:
        c1, c2, c3 = st.columns(3)
        D = c1.number_input("Diamètre de la conduite (m)", 0.3, 4.0, 1.2, 0.1)
        zax = c1.number_input("Cote de l'axe de la vidange (m)", 0.0, 5000.0, float(P["cote_fond"] + 5), 0.5)
        Cd = c2.number_input("Coefficient de débit", 0.4, 0.95, 0.62, 0.02)
        tgt = c3.slider("Niveau à atteindre (% du volume)", 0, 90, 50, 5)
        A = math.pi * D ** 2 / 4
        zn = P["cote_nnr"]
        Q0 = orifice_q(A, zn - zax, Cd)
        c1, c2 = st.columns(2)
        c1.metric("Débit initial de vidange", f"{Q0:.1f} m³/s")
        if len(hv) > 1:
            V0 = vol_at(hv, zn)
            z, t_h, vol = zn, 0.0, V0
            zs, ts = [zn], [0.0]
            while vol > V0 * tgt / 100 and t_h < 24 * 400:
                q = orifice_q(A, z - zax, Cd)
                vol -= q * 3600
                t_h += 1
                z = float(np.interp(vol, hv["Volume (m³)"], hv["Cote (m)"]))
                zs.append(z); ts.append(t_h)
                if q <= 0:
                    break
            c2.metric(f"Durée pour atteindre {tgt} % du volume", f"{t_h / 24:.1f} jours")
            pplot(px.line(x=np.array(ts) / 24, y=zs, labels={"x": "Jours", "y": "Cote (m)"}, title="Abaissement du plan d'eau",
                          color_discrete_sequence=[NOIR]), 300)


# ===================== PAGE : BARRAGE-POIDS =====================
def fig_poids(p, B, hw, xR):
    m, b, n, H = p["m"], p["b"], p["n"], p["H"]
    xp = lambda x: B - x
    fig = go.Figure()
    poly = [(0, 0), (B, 0), (m * H + b, H), (m * H, H), (0, 0)]
    fig.add_trace(go.Scatter(x=[xp(x) for x, _ in poly], y=[y for _, y in poly], fill="toself", fillcolor="#9AA5B1",
                             line=dict(color=NOIR, width=3), name="Corps du barrage"))
    ys = np.linspace(0, min(hw, H), 20)
    wx = [-0.4 * B] + [n * y for y in ys] + [-0.4 * B]
    wy = [0] + list(ys) + [min(hw, H)]
    fig.add_trace(go.Scatter(x=wx, y=wy, fill="toself", fillcolor="rgba(0,180,216,0.45)", line=dict(color=ACCENT),
                             name=f"Retenue (hw = {hw:.1f} m)"))
    fig.add_trace(go.Scatter(x=[xp(xR)], y=[0], mode="markers", marker=dict(size=14, color=ROUGE, symbol="triangle-up"),
                             name="Résultante"))
    fig.update_yaxes(scaleanchor="x", scaleratio=1, title="m")
    fig.update_layout(title="Section type du barrage-poids")
    return fig


def page_poids():
    S = st.session_state
    P = S.projet
    hero("🧱 Barrage-poids en béton", "Stabilité au renversement, au glissement, contraintes de base • sous-pression • séisme")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### Géométrie")
        H = c1.number_input("Hauteur H (m)", 5.0, 250.0, float(round(P["H"])), 1.0)
        b = c1.number_input("Largeur en crête (m)", 2.0, 30.0, 6.0, 0.5)
        m = c1.number_input("Fruit aval (H/V)", 0.4, 1.2, 0.75, 0.05)
        n = c1.number_input("Fruit amont (H/V)", 0.0, 0.3, 0.0, 0.02)
        gc = c1.number_input("Poids volumique du béton (kN/m³)", 22.0, 26.0, 24.0, 0.5)
    with c2:
        st.markdown("#### Fondation et drainage")
        cc = c2.number_input("Cohésion de contact c (kPa)", 0.0, 2000.0, 100.0, 10.0)
        phi = c2.number_input("Angle de frottement φ (°)", 20.0, 60.0, 45.0, 1.0)
        E = c2.slider("Efficacité des drains", 0.0, 0.9, 0.5, 0.05)
        xd = c2.number_input("Distance heel → rideau de drains (m)", 0.0, 60.0, 4.0, 0.5)
        sa = c2.number_input("Contrainte admissible au pied (kPa)", 200.0, 10000.0, 3000.0, 100.0)
    with c3:
        st.markdown("#### Charges")
        hn = c3.number_input("Hauteur d'eau normale hw (m)", 1.0, 250.0, float(P["cote_nnr"] - P["cote_fond"]), 0.5)
        hc = c3.number_input("Hauteur d'eau en crue hw (m)", 1.0, 250.0, float(P["cote_phe"] - P["cote_fond"]), 0.5)
        tw = c3.number_input("Hauteur d'eau aval en crue (m)", 0.0, 100.0, 3.0, 0.5)
        hs = c3.number_input("Épaisseur de sédiments (m)", 0.0, 60.0, 5.0, 0.5)
        kh = c3.number_input("Coefficient sismique horizontal kh", 0.0, 0.5, 0.10, 0.01)
    p = dict(H=H, b=b, m=m, n=n, gc=gc, c=cc, phi=phi, E=E, xd=xd, hs=hs, gs=8.0, Ks=0.5)
    cases = [("Normal", hn, 0.0, 0.0, 2.0, 1.5), ("Crue", hc, tw, 0.0, 1.7, 1.3), ("Séisme", hn, 0.0, kh, 1.3, 1.1)]
    rows, res = [], {}
    for nom, hw, t_, k_, fs_s, fs_o in cases:
        r = stabilite(p, hw, t_, k_)
        res[nom] = r
        rows.append({"Cas": nom, "ΣV (kN/m)": round(r["SV"]), "ΣH (kN/m)": round(r["SH"]), "FS renversement": round(r["FSo"], 2),
                     "Exigé (renv.)": fs_o, "FS glissement": round(r["FSs"], 2), "Exigé (gliss.)": fs_s,
                     "σ pied (kPa)": round(r["s_toe"]), "σ talon (kPa)": round(r["s_heel"]),
                     "Tiers central": "✅" if r["tiers"] else ("⚠️ (séisme admis)" if nom == "Séisme" else "❌"),
                     "Statut": "✅" if (r["FSo"] >= fs_o and r["FSs"] >= fs_s and r["s_toe"] <= sa and r["s_heel"] >= (-0.0 if nom != "Séisme" else -1e9)) else "❌"})
    show_df(pd.DataFrame(rows))
    r = res["Normal"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Base du barrage B", f"{r['B']:.1f} m")
    c2.metric("Poids du barrage", f"{r['W']:.0f} kN/m")
    c3.metric("Sous-pression (normal)", f"{r['U']:.0f} kN/m")
    c4.metric("Béton par ml de crête", f"{r['area']:.0f} m³/m")
    pplot(fig_poids(p, r["B"], hn, r["xR"]), 420)
    ms = np.linspace(0.5, 1.0, 11)
    sc = [stabilite(dict(p, m=mm), hn, 0.0, 0.0) for mm in ms]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ms, y=[s["FSo"] for s in sc], name="Renversement", line=dict(color=NOIR, width=4)))
    fig.add_trace(go.Scatter(x=ms, y=[s["FSs"] for s in sc], name="Glissement", line=dict(color=ACCENT, width=4)))
    fig.add_hline(y=2.0, line_dash="dash", line_color=ROUGE)
    fig.update_layout(title="Influence du fruit aval (cas normal)", xaxis_title="Fruit aval m", yaxis_title="Coefficient de sécurité")
    pplot(fig, 320)
    note("Calcul 2D par mètre linéaire, plan de rupture à la base. Sous-pression linéaire avec rideau de drains, séisme pseudo-statique "
         "avec pression hydrodynamique de Westergaard. Coefficients exigés indicatifs : à ajuster selon la réglementation du pays.")


# ===================== PAGE : BARRAGE EN REMBLAI =====================
def page_remblai():
    S = st.session_state
    P = S.projet
    hero("⛰️ Barrage en remblai", "Géométrie et volumes • revanche (Stevenson) • infiltration (Casagrande) • filtres • stabilité des talus")
    t1, t2, t3 = st.tabs(["📐 Géométrie, volumes et revanche", "💦 Infiltration et filtres", "🛡️ Stabilité des talus"])
    H0 = float(round(P["H"]))
    with t1:
        c1, c2, c3 = st.columns(3)
        H = c1.number_input("Hauteur maximale H (m)", 5.0, 300.0, H0, 1.0)
        b = c1.number_input("Largeur en crête (m)", 3.0, 30.0, float(round(H / 5 + 3, 1)), 0.5)
        m1 = c2.number_input("Talus amont (H/V)", 1.5, 5.0, 3.0, 0.25)
        m2 = c2.number_input("Talus aval (H/V)", 1.5, 4.0, 2.5, 0.25)
        kv = c3.slider("Coefficient de forme de la vallée", 0.3, 1.0, 0.55, 0.05)
        pn = c3.slider("Part du noyau dans le volume (%)", 5, 50, 25, 1)
        pf = c3.slider("Part des filtres / drains (%)", 1, 15, 5, 1)
        Bt = b + (m1 + m2) * H
        A = H * (b + (m1 + m2) * H / 2)
        V = A * P["lcrete"] * kv
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Largeur de base", f"{Bt:.0f} m")
        c2.metric("Aire de la section maximale", f"{A:.0f} m²")
        c3.metric("Volume total du remblai", f"{V / 1e3:.0f} 10³ m³")
        c4.metric("Largeur crête conseillée (H/5 + 3)", f"{H / 5 + 3:.1f} m")
        vz = pd.DataFrame({"Zone": ["Noyau", "Filtres / drains", "Recharges"], "Volume (10³ m³)": [V * pn / 100 / 1e3, V * pf / 100 / 1e3, V * (100 - pn - pf) / 100 / 1e3]})
        show_df(vz.round(1))
        c1, c2, c3, c4 = st.columns(4)
        F = c1.number_input("Fetch (km)", 0.1, 60.0, 4.0, 0.5)
        Vw = c2.number_input("Vitesse du vent (km/h)", 20.0, 200.0, 90.0, 5.0)
        ts = c3.slider("Tassement post-construction (%)", 0.0, 2.0, 0.8, 0.1)
        hv_, rev = revanche_stevenson(F, Vw)
        crete_req = P["cote_phe"] + rev + ts / 100 * H
        c4.metric("Hauteur de vague", f"{hv_:.2f} m")
        c1, c2 = st.columns(2)
        c1.metric("Revanche (vague + run-up)", f"{rev:.2f} m")
        c2.metric("Cote de crête requise", f"{crete_req:.2f} m")
        verdict(P["cote_crete"] >= crete_req, f"Cote de crête du projet ({P['cote_crete']:.1f} m) suffisante.",
                f"Cote de crête du projet ({P['cote_crete']:.1f} m) < {crete_req:.2f} m requis : relever la crête.")
        x0 = 0
        pts = [(0, 0), (m1 * H, H), (m1 * H + b, H), (Bt, 0), (0, 0)]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[p_[0] for p_ in pts], y=[p_[1] for p_ in pts], fill="toself", fillcolor="#C8B79A",
                                 line=dict(color=NOIR, width=3), name="Recharges"))
        cx = m1 * H + b / 2
        wn = lambda y: (b / 2 + 0.15 * (H - y) * 1.0)
        ys = np.linspace(0, H, 20)
        fig.add_trace(go.Scatter(x=[cx - wn(y) for y in ys] + [cx + wn(y) for y in ys[::-1]], y=list(ys) + list(ys[::-1]),
                                 fill="toself", fillcolor="#7A6A55", line=dict(color=NOIR), name="Noyau"))
        fig.update_yaxes(scaleanchor="x", scaleratio=1, title="m")
        fig.update_layout(title="Section type du remblai zoné")
        pplot(fig, 360)
    with t2:
        c1, c2, c3 = st.columns(3)
        lk = c1.slider("log10 de la perméabilité du remblai k (m/s)", -11.0, -5.0, -8.0, 0.5)
        hh = c1.number_input("Charge hydraulique h (m)", 1.0, 250.0, float(P["cote_nnr"] - P["cote_fond"]), 0.5)
        Ld = c2.number_input("Longueur du tapis drainant (m)", 0.0, 200.0, 30.0, 1.0)
        Bt2 = b + (m1 + m2) * H
        d = Bt2 - Ld - 0.7 * m1 * hh
        q, y0 = fuite_casagrande(10 ** lk, hh, max(d, 1.0))
        Lq = P["lcrete"] * kv
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Distance d (Casagrande)", f"{d:.0f} m")
        c2.metric("Ordonnée y0", f"{y0:.1f} m")
        c3.metric("Débit de fuite par ml", f"{q * 1000 * 60:.4f} L/min/m")
        c4.metric("Fuite totale (remblai)", f"{q * Lq * 1000 * 60:.2f} L/min")
        i_moy = hh / max(Bt2 - 0.7 * m1 * hh, 1.0)
        st.info(f"Gradient hydraulique moyen à travers le remblai : {i_moy:.2f}.")
        st.markdown("##### Critères de filtre (Terzaghi) — diamètres en mm")
        c1, c2, c3 = st.columns(3)
        D15f = c1.number_input("D15 du filtre", 0.01, 50.0, 0.4, 0.05)
        D85b = c2.number_input("D85 du sol à protéger", 0.01, 50.0, 0.12, 0.01)
        D15b = c3.number_input("D15 du sol à protéger", 0.001, 50.0, 0.01, 0.001, format="%.3f")
        r1, r2, ok = filtre_terzaghi(D15f, D85b, D15b)
        c1, c2 = st.columns(2)
        c1.metric("D15f / D85b (≤ 5 : rétention)", f"{r1:.1f}")
        c2.metric("D15f / D15b (≥ 5 : perméabilité)", f"{r2:.1f}")
        verdict(ok, "Filtre compatible avec le sol protégé.", "Filtre non conforme : revoir la granulométrie.")
    with t3:
        c1, c2, c3 = st.columns(3)
        gam = c1.number_input("γ du remblai (kN/m³)", 14.0, 24.0, 20.0, 0.5)
        cp = c2.number_input("Cohésion c' (kPa)", 0.0, 100.0, 15.0, 1.0)
        ph = c3.number_input("Angle de frottement φ' (°)", 15.0, 45.0, 32.0, 1.0)
        c1, c2 = st.columns(2)
        ru1 = c1.slider("ru en fin de construction", 0.0, 0.6, 0.35, 0.05)
        ru2 = c2.slider("ru en régime permanent", 0.0, 0.5, 0.15, 0.05)
        prof = (m1, H, b, m2)
        b1, _ = scan_talus_aval(prof, gam, cp, ph, ru1, 7)
        b2, pts = scan_talus_aval(prof, gam, cp, ph, ru2, 7)
        bt = math.degrees(math.atan(1 / m2))
        fsi = pente_infinie(bt, ph, gam, ru2)
        rows = [{"Cas": "Fin de construction", "ru": ru1, "FS minimal": round(b1[0], 2), "Exigé": 1.3},
                {"Cas": "Régime permanent", "ru": ru2, "FS minimal": round(b2[0], 2), "Exigé": 1.5}]
        show_df(pd.DataFrame(rows))
        c1, c2 = st.columns(2)
        c1.metric("Inclinaison du talus aval", f"{bt:.1f} °")
        c2.metric("FS pente infinie (permanent)", f"{fsi:.2f}")
        verdict(b1[0] >= 1.3 and b2[0] >= 1.5, "Talus aval stable pour les cas étudiés.", "Facteur de sécurité insuffisant : adoucir le talus ou drainer.")
        if pts:
            fig = px.scatter(x=[p_[0] for p_ in pts], y=[p_[1] for p_ in pts], color=[p_[2] for p_ in pts],
                             color_continuous_scale="RdYlGn", labels={"x": "xc (m)", "y": "yc (m)", "color": "FS"},
                             title="Facteur de sécurité selon le centre du cercle (régime permanent)")
            pplot(fig, 340)
        note("Méthode ordinaire des tranches (Fellenius), sol homogène, cercles passant par le pied aval, pression interstitielle par ru. "
             "Une analyse de Bishop / éléments finis reste nécessaire pour l'étude finale.")


# ===================== PAGE : FONDATION =====================
def page_fondation():
    P = st.session_state.projet
    hero("🪨 Fondation et étanchéité", "Cheminement de Lane • voile d'injection • perméabilité (Lugeon) • débit de fuite")
    t1, t2 = st.tabs(["📏 Cheminement de l'eau (Lane)", "💉 Voile d'injection et fuites"])
    with t1:
        c1, c2, c3 = st.columns(3)
        h = c1.number_input("Charge maximale (m)", 1.0, 250.0, float(P["cote_nnr"] - P["cote_fond"]), 0.5)
        sol = c1.selectbox("Nature du sol de fondation", list(LANE), index=11)
        Lv = c2.number_input("Somme des cheminements verticaux (m)", 0.0, 300.0, 40.0, 1.0)
        Lh = c3.number_input("Somme des cheminements horizontaux (m)", 0.0, 500.0, 90.0, 5.0)
        Lw, Cw = lane_creep(Lv, Lh, h)
        c1, c2, c3 = st.columns(3)
        c1.metric("Longueur pondérée Lw", f"{Lw:.0f} m")
        c2.metric("Rapport Lw / h", f"{Cw:.2f}")
        c3.metric("Rapport minimal (Lane)", f"{LANE[sol]:.1f}")
        verdict(Cw >= LANE[sol], "Cheminement suffisant contre le renard hydraulique.", "Cheminement insuffisant : allonger l'écran, ajouter un parafouille ou un voile.")
    with t2:
        c1, c2, c3 = st.columns(3)
        h = c1.number_input("Charge hydraulique h (m)", 1.0, 250.0, float(P["cote_nnr"] - P["cote_fond"]), 0.5, key="inj_h")
        lug = c1.number_input("Perméabilité en Lugeon (UL)", 0.1, 200.0, 8.0, 0.5)
        nf = c2.number_input("Nombre de canaux d'écoulement Nf", 1.0, 20.0, 2.0, 0.5)
        nd = c2.number_input("Nombre de chutes de potentiel Nd", 2.0, 40.0, 10.0, 1.0)
        kv = c3.slider("Coefficient de forme de la vallée", 0.3, 1.0, 0.55, 0.05, key="inj_kv")
        k = lug * 1.3e-7
        q = k * h * nf / nd
        Lq = P["lcrete"] * kv
        prof = h / 3 + 8
        esp = c3.number_input("Espacement des forages (m)", 1.0, 6.0, 3.0, 0.5)
        absorb = c3.number_input("Absorption moyenne de coulis (kg/ml)", 10.0, 500.0, 60.0, 10.0)
        nforages = math.ceil(Lq / esp)
        c1, c2, c3 = st.columns(3)
        c1.metric("Perméabilité k", f"{k:.1e} m/s")
        c2.metric("Fuite en fondation (par ml)", f"{q * 1000 * 60:.3f} L/min/m")
        c3.metric("Fuite totale en fondation", f"{q * Lq * 1000 * 60:.0f} L/min")
        c1, c2, c3 = st.columns(3)
        c1.metric("Profondeur du voile (h/3 + 8 m)", f"{prof:.0f} m")
        c2.metric("Forages (une ligne)", f"{nforages} u / {nforages * prof:,.0f} ml".replace(",", " "))
        c3.metric("Ciment estimé", f"{nforages * prof * absorb / 1000:.0f} t")
        note("1 Lugeon ≈ 1,3·10⁻⁷ m/s. Le voile d'injection est à dimensionner d'après les essais Lugeon et un planche d'essai.")


# ===================== PAGE : CONTRÔLE DES MATÉRIAUX =====================
def page_materiaux():
    S = st.session_state
    hero("🔬 Contrôle des matériaux", "Compactage du remblai • essais béton • thermique du béton massif")
    t1, t2, t3 = st.tabs(["🪣 Compactage du remblai", "🧱 Essais de béton", "🌡️ Thermique du béton massif"])
    with t1:
        editor("compactage", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                              "Zone": st.column_config.SelectboxColumn("Zone", options=ZONES)})
        st.subheader("Conformité par zone")
        show_df(compaction_summary(S.compactage))
        d = compaction_df(S.compactage)
        if len(d):
            fig = px.box(d, x="Zone", y="Compactage (% OPM)", points="all", color="Zone", color_discrete_sequence=PALETTE,
                         title="Compactage mesuré par zone")
            for z, sv in COMPACT_MIN.items():
                fig.add_hline(y=sv, line_dash="dot", line_color=GRIS)
            pplot(fig, 340)
            wx = d["Écart w (pts)"]
            st.info(f"Écart moyen de teneur en eau par rapport à l'optimum : {wx.mean():+.1f} point(s).")
    with t2:
        editor("essais", {"Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                          "Classe": st.column_config.SelectboxColumn("Classe", options=CLASSES_BETON)})
        ev = eval_beton(S.essais)
        show_df(ev)
        e = S.essais.copy()
        e["Résistance (MPa)"] = pd.to_numeric(e["Résistance (MPa)"], errors="coerce")
        e["Âge (j)"] = pd.to_numeric(e["Âge (j)"], errors="coerce")
        e = e.dropna(subset=["Résistance (MPa)", "Classe"])
        if len(e):
            fig = px.scatter(e, x="Âge (j)", y="Résistance (MPa)", color="Classe", hover_data=["Élément"],
                             color_discrete_sequence=PALETTE, title="Résistances mesurées")
            fig.update_traces(marker=dict(size=12, line=dict(width=2, color=NOIR)))
            pplot(fig, 320)
    with t3:
        c1, c2, c3 = st.columns(3)
        cim = c1.number_input("Dosage en ciment (kg/m³)", 80.0, 450.0, 220.0, 10.0)
        q = c1.number_input("Chaleur d'hydratation (kJ/kg)", 150.0, 450.0, 300.0, 10.0)
        Tp = c2.number_input("Température de mise en place (°C)", 5.0, 40.0, 20.0, 1.0)
        Te = c2.number_input("Température ambiante moyenne (°C)", -10.0, 45.0, 22.0, 1.0)
        red = c3.slider("Fraction de l'échauffement adiabatique atteinte", 0.4, 1.0, 0.75, 0.05)
        lev = c3.number_input("Épaisseur de levée (m)", 0.3, 4.0, 1.5, 0.1)
        dTa = delta_T_adiabatique(cim, q)
        Tmax = Tp + dTa * red
        grad = Tmax - Te
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Échauffement adiabatique", f"{dTa:.1f} °C")
        c2.metric("Température maximale au cœur", f"{Tmax:.1f} °C")
        c3.metric("Écart cœur / ambiance", f"{grad:.1f} °C")
        c4.metric("Levée", f"{lev:.1f} m")
        verdict(Tmax <= 65, "Température au cœur ≤ 65 °C (limite usuelle).", "Température au cœur excessive (> 65 °C) : réduire le ciment, refroidir les granulats.")
        verdict(grad <= 20, "Gradient thermique ≤ 20 °C : risque de fissuration limité.", "Gradient > 20 °C : prévoir refroidissement, levées plus minces ou coffrages isolants.")


# ===================== PAGE : AUSCULTATION =====================
def page_instrumentation():
    S = st.session_state
    P = S.projet
    hero("📡 Auscultation et surveillance", "Seuils d'alerte et d'alarme • tendances • corrélation avec le niveau de la retenue")
    st.markdown("##### Seuils par instrument (valeurs maximales)")
    editor("seuils")
    ist = instr_status(S.releves, S.seuils)
    if ist.empty:
        st.info("Aucun relevé d'auscultation.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Instruments suivis", len(ist))
    c2.metric("En alerte", int((ist["Statut"] == "⚠️ Alerte").sum()))
    c3.metric("En alarme", int((ist["Statut"] == "🚨 Alarme").sum()))
    show_df(ist)
    r = S.releves.copy()
    r["Valeur"] = pd.to_numeric(r["Valeur"], errors="coerce")
    r["Niveau retenue (m)"] = pd.to_numeric(r["Niveau retenue (m)"], errors="coerce")
    r["Date"] = pd.to_datetime(r["Date"], errors="coerce")
    r = r.dropna(subset=["Instrument", "Valeur", "Date"]).sort_values("Date")
    sel = st.selectbox("Instrument à analyser", sorted(r["Instrument"].unique()))
    g = r[r["Instrument"] == sel]
    sm = S.seuils[S.seuils["Instrument"] == sel]
    fig = px.line(g, x="Date", y="Valeur", markers=True, title=f"{sel} — évolution", color_discrete_sequence=[NOIR])
    if len(sm):
        fig.add_hline(y=fnum(sm["Seuil alerte"].iloc[0], 0.0), line_dash="dash", line_color=ORANGE, annotation_text="alerte")
        fig.add_hline(y=fnum(sm["Seuil alarme"].iloc[0], 0.0), line_dash="dash", line_color=ROUGE, annotation_text="alarme")
    pplot(fig, 340)
    gg = g.dropna(subset=["Niveau retenue (m)"])
    if len(gg) >= 3 and gg["Niveau retenue (m)"].nunique() > 1:
        a, b = np.polyfit(gg["Niveau retenue (m)"], gg["Valeur"], 1)
        pred = np.polyval([a, b], gg["Niveau retenue (m)"])
        ss_res = float(((gg["Valeur"] - pred) ** 2).sum())
        ss_tot = float(((gg["Valeur"] - gg["Valeur"].mean()) ** 2).sum())
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
        v_phe = float(np.polyval([a, b], P["cote_phe"]))
        fig = px.scatter(gg, x="Niveau retenue (m)", y="Valeur", title=f"{sel} en fonction du niveau de la retenue",
                         color_discrete_sequence=[NOIR])
        xs = np.linspace(gg["Niveau retenue (m)"].min(), P["cote_phe"], 30)
        fig.add_trace(go.Scatter(x=xs, y=np.polyval([a, b], xs), name="Régression", line=dict(color=ACCENT, width=4)))
        pplot(fig, 340)
        c1, c2, c3 = st.columns(3)
        c1.metric("Pente de corrélation", f"{a:.3f} / m de retenue")
        c2.metric("R²", f"{r2:.2f}")
        c3.metric("Valeur extrapolée aux plus hautes eaux", f"{v_phe:.1f}")
        if len(sm):
            verdict(v_phe < fnum(sm["Seuil alarme"].iloc[0], 1e9),
                    "L'extrapolation reste sous le seuil d'alarme.", "L'extrapolation dépasse le seuil d'alarme avant les plus hautes eaux.")
        note("Extrapolation linéaire à titre indicatif : le comportement réel peut devenir non linéaire à haut niveau. Mise en eau par paliers recommandée.")


# ===================== PAGE : SÉCURITÉ =====================
def page_securite():
    S = st.session_state
    P = S.projet
    hero("🛟 Sécurité de l'ouvrage et du chantier", "Classe de l'ouvrage • rupture hypothétique (Froehlich) • risques • indicateurs HSE")
    t1, t2, t3 = st.tabs(["🏷️ Classe et rupture hypothétique", "⚠️ Matrice des risques", "📈 Indicateurs HSE"])
    hv = hsv_table(S.hsv)
    Vn = vol_at(hv, P["cote_nnr"]) / 1e6 if len(hv) else 1.0
    with t1:
        cl, kk = classe_barrage(P["H"], Vn)
        c1, c2, c3 = st.columns(3)
        c1.metric("Hauteur H", f"{P['H']:.1f} m")
        c2.metric("Volume V", f"{Vn:.2f} hm³")
        c3.metric("Classe", f"{cl}", f"H²√V = {kk:.0f}")
        note("Classes : A (H ≥ 20 m et H²√V ≥ 1500), B (H ≥ 10 m et ≥ 200), C (H ≥ 5 m et ≥ 20), D (autres). Critères type réglementation française, à adapter au pays.")
        c1, c2 = st.columns(2)
        Vw = c1.number_input("Volume d'eau au moment de la rupture (hm³)", 0.01, 5000.0, float(round(max(Vn, 0.1), 2)), 0.5) * 1e6
        Hw = c2.number_input("Hauteur d'eau (m)", 1.0, 250.0, float(P["cote_nnr"] - P["cote_fond"]), 0.5, key="rup_h")
        Qp, tf = froehlich(Vw, Hw)
        c1, c2 = st.columns(2)
        c1.metric("Débit de pointe de brèche", f"{Qp:,.0f} m³/s".replace(",", " "))
        c2.metric("Temps de formation de la brèche", f"{tf:.2f} h")
        st.markdown("##### Propagation indicative vers l'aval")
        c1, c2, c3, c4 = st.columns(4)
        W = c1.number_input("Largeur de la vallée aval (m)", 20.0, 3000.0, 300.0, 10.0)
        Sv = c2.number_input("Pente de la vallée (%)", 0.01, 10.0, 0.3, 0.05) / 100
        nv = c3.number_input("n de Manning du lit", 0.02, 0.15, 0.05, 0.005, format="%.3f")
        La = c4.number_input("Longueur d'amortissement (km)", 5.0, 300.0, 40.0, 5.0)
        xs = np.array([1.0, 2.0, 5.0, 10.0, 20.0, 40.0])
        Qx = Qp * np.exp(-xs / La)
        yx = (Qx * nv / (W * math.sqrt(Sv))) ** 0.6
        vx = Qx / (W * yx)
        dfx = pd.DataFrame({"Distance (km)": xs, "Débit de pointe (m³/s)": Qx.round(0), "Hauteur d'eau (m)": yx.round(1),
                            "Vitesse (m/s)": vx.round(1), "Arrivée de l'onde (h)": (xs * 1000 / np.maximum(vx, 0.5) / 3600).round(2)})
        show_df(dfx)
        pplot(px.line(dfx, x="Distance (km)", y="Hauteur d'eau (m)", markers=True, title="Hauteur d'eau de l'onde de rupture",
                      color_discrete_sequence=[ROUGE]), 300)
        note("Estimation grossière (formule empirique + lit rectangulaire) : le plan particulier d'intervention exige une modélisation hydrodynamique et une cartographie d'inondation.")
    with t2:
        editor("risques")
        r = S.risques.dropna(subset=["Risque"]).copy()
        r["Probabilité"] = pd.to_numeric(r["Probabilité"], errors="coerce").fillna(1).clip(1, 5).astype(int)
        r["Gravité"] = pd.to_numeric(r["Gravité"], errors="coerce").fillna(1).clip(1, 5).astype(int)
        r["Score"] = r["Probabilité"] * r["Gravité"]
        r["Niveau"] = pd.cut(r["Score"], [0, 4, 9, 14, 25], labels=["🟢 Faible", "🟡 Modéré", "🟠 Élevé", "🔴 Critique"]).astype(str)
        counts = np.zeros((5, 5), dtype=int)
        for _, x in r.iterrows():
            counts[x["Probabilité"] - 1, x["Gravité"] - 1] += 1
        sc = np.array([[(p + 1) * (g + 1) for g in range(5)] for p in range(5)])
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Heatmap(z=sc, x=[1, 2, 3, 4, 5], y=[1, 2, 3, 4, 5], text=counts, texttemplate="%{text}",
                                       colorscale=[[0, VERT], [0.25, ACCENT], [0.55, ORANGE], [1, ROUGE]], showscale=False))
            fig.update_layout(title="Matrice de criticité", xaxis_title="Gravité", yaxis_title="Probabilité")
            pplot(fig, 400)
        with c2:
            show_df(r[["Risque", "Phase", "Score", "Niveau", "Mesure de maîtrise"]].sort_values("Score", ascending=False))
    with t3:
        c1, c2, c3 = st.columns(3)
        hrs = c1.number_input("Heures travaillées (cumul)", 1000.0, 1e9, 400000.0, 1000.0)
        acc = c2.number_input("Accidents avec arrêt", 0, 500, 3)
        jp = c3.number_input("Jours d'arrêt perdus", 0, 100000, 70)
        c1, c2 = st.columns(2)
        c1.metric("Taux de fréquence TF", f"{acc * 1e6 / hrs:.1f}")
        c2.metric("Taux de gravité TG", f"{jp * 1e3 / hrs:.2f}")


# ===================== PAGE : MÉTRÉ =====================
def page_metre():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("🧮 Métré et estimation des coûts", "Bordereau • quantités du corps du barrage • synthèse")
    t1, t2, t3 = st.tabs(["📋 Bordereau", "🏗️ Quantités du corps du barrage", "💶 Synthèse"])
    with t1:
        editor("metre", {"Unité": st.column_config.SelectboxColumn("Unité", options=["m³", "m²", "ml", "kg", "t", "u", "forfait", "j"])})
        st.metric("Total HT du bordereau", f"{fmt(metre_totals(S.metre)['Total'].sum(), 0)} {dev}")
    with t2:
        c1, c2, c3 = st.columns(3)
        H = c1.number_input("Hauteur H (m)", 5.0, 300.0, float(round(P["H"])), 1.0, key="mq_H")
        b = c1.number_input("Largeur en crête (m)", 3.0, 30.0, 8.0, 0.5, key="mq_b")
        m1 = c1.number_input("Talus amont (H/V)", 1.5, 5.0, 3.0, 0.25, key="mq_m1")
        m2 = c2.number_input("Talus aval (H/V)", 1.5, 4.0, 2.5, 0.25, key="mq_m2")
        kv = c2.slider("Coefficient de forme de la vallée", 0.3, 1.0, 0.55, 0.05, key="mq_kv")
        pn = c2.slider("Part du noyau (%)", 5, 50, 25, 1, key="mq_pn")
        pf = c2.slider("Part des filtres (%)", 1, 15, 5, 1, key="mq_pf")
        sf = c3.number_input("Surface d'excavation de fondation (m²)", 1000.0, 1e6, 22000.0, 500.0)
        pe = c3.number_input("Profondeur moyenne d'excavation (m)", 0.5, 30.0, 4.0, 0.5)
        pr = c3.number_input("Surface de rip-rap amont (m²)", 0.0, 1e6, 18000.0, 500.0)
        V = H * (b + (m1 + m2) * H / 2) * P["lcrete"] * kv
        rows = [("04 Corps du barrage", "Noyau argileux compacté", "m³", V * pn / 100, 11.0),
                ("04 Corps du barrage", "Filtres et drains", "m³", V * pf / 100, 22.0),
                ("04 Corps du barrage", "Recharges compactées", "m³", V * (100 - pn - pf) / 100, 7.0),
                ("02 Terrassements et fondation", "Excavation de fondation", "m³", sf * pe, 9.0),
                ("04 Corps du barrage", "Enrochements de protection (rip-rap)", "m³", pr * 0.8, 30.0)]
        q = pd.DataFrame(rows, columns=COLS["metre"])
        q["Total"] = q["Quantité"] * q["PU"]
        show_df(q.round(0))
        c1, c2 = st.columns(2)
        c1.metric("Volume de remblai", f"{V / 1e3:.0f} 10³ m³")
        c2.metric("Coût de ces postes", f"{fmt(q['Total'].sum(), 0)} {dev}")
        if st.button("➕ Envoyer ces quantités au bordereau"):
            add_rows("metre", q[COLS["metre"]].round(1))
            st.rerun()
    with t3:
        mt = metre_totals(S.metre)
        c1, c2, c3 = st.columns(3)
        ale = c1.slider("Aléas (%)", 0, 25, 10)
        fg = c2.slider("Frais généraux et bénéfice (%)", 0, 30, 12)
        tva = c3.slider("TVA (%)", 0.0, 25.0, 20.0, 0.5)
        ht = float(mt["Total"].sum())
        ht2 = ht * (1 + ale / 100) * (1 + fg / 100)
        ttc = ht2 * (1 + tva / 100)
        c1, c2, c3 = st.columns(3)
        c1.metric("HT brut", fmt(ht, 0))
        c2.metric("HT avec aléas et FG", fmt(ht2, 0))
        c3.metric("Total TTC", f"{fmt(ttc, 0)} {dev}")
        lots = mt.groupby("Lot", as_index=False)["Total"].sum().sort_values("Total")
        fig = px.bar(lots, x="Total", y="Lot", orientation="h", title="Coût par lot", color_discrete_sequence=[ACCENT])
        fig.update_traces(marker_line_color=NOIR, marker_line_width=2)
        pplot(fig, 380)


# ===================== PAGE : PLANNING =====================
def page_planning():
    S = st.session_state
    P = S.projet
    hero("📅 Planning et chemin critique", "Gantt • calage automatique • marges • avancement réel")
    note("Prédécesseurs : noms de tâches séparés par « ; ».")
    editor("taches", {"Début": st.column_config.DateColumn("Début", format="DD/MM/YYYY")})
    mode = st.radio("Calendrier", ["Dates saisies", "Calage automatique selon prédécesseurs"], horizontal=True)
    try:
        d, T = cpm(S.taches)
    except ValueError as ex:
        st.error(str(ex))
        return
    d["Avancement (%)"] = pd.to_numeric(d["Avancement (%)"], errors="coerce").fillna(0).clip(0, 100)
    if mode.startswith("Calage"):
        d["Début_"] = [pd.Timestamp(P["debut"]) + pd.Timedelta(days=float(v)) for v in d["ES"]]
    else:
        d["Début_"] = pd.to_datetime(d["Début"], errors="coerce").fillna(pd.Timestamp(P["debut"]))
    d["Fin_"] = d["Début_"] + pd.to_timedelta(d["Durée (j)"], unit="D")
    today = pd.Timestamp(date.today())
    d["Statut"] = [("Terminé" if a >= 100 else "En retard" if f < today else "En cours" if s <= today else "À venir")
                   for a, f, s in zip(d["Avancement (%)"], d["Fin_"], d["Début_"])]
    if mode.startswith("Calage") and st.button("💾 Appliquer ces dates au tableau"):
        tt = S.taches.copy()
        mp = dict(zip(d["Tâche"], d["Début_"].dt.date))
        tt["Début"] = [mp.get(n, x) for n, x in zip(tt["Tâche"], tt["Début"])]
        set_df("taches", tt)
        st.rerun()
    fig = px.timeline(d, x_start="Début_", x_end="Fin_", y="Tâche", color="Statut",
                      color_discrete_map={"Terminé": VERT, "En cours": ACCENT, "En retard": ROUGE, "À venir": "#C9C5AA"},
                      title="Diagramme de Gantt")
    fig.update_yaxes(autorange="reversed")
    fig.add_shape(type="line", x0=today, x1=today, y0=0, y1=1, yref="paper", line=dict(color=ROUGE, width=2, dash="dash"))
    pplot(fig, 140 + 32 * len(d))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Durée (chemin critique)", f"{T:.0f} j")
    c2.metric("Fin prévue", (pd.Timestamp(P["debut"]) + pd.Timedelta(days=T)).strftime("%d/%m/%Y"))
    c3.metric("Tâches en retard", int((d["Statut"] == "En retard").sum()))
    c4.metric("Tâches critiques", int(d["Critique"].sum()))
    out = d[["Tâche", "Responsable", "Durée (j)", "Avancement (%)", "Marge (j)", "Critique", "Statut"]].copy()
    out["Critique"] = out["Critique"].map({True: "🔴 Oui", False: "—"})
    show_df(out)


# ===================== PAGE : COÛTS (EVM) =====================
def page_cout():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    hero("💰 Suivi des coûts — valeur acquise", "PV, EV, AC • CPI, SPI • prévision à l'achèvement")
    bac = st.number_input(f"Budget à l'achèvement BAC ({dev})", 0.0, 1e10, float(P["budget"]), 10000.0)
    note("Saisir les valeurs cumulées par mois : valeur planifiée (PV), acquise (EV) et coût réel (AC).")
    editor("ev")
    ev = S.ev.copy()
    for c in COLS["ev"]:
        ev[c] = pd.to_numeric(ev[c], errors="coerce")
    ev = ev.dropna(subset=["Mois"]).sort_values("Mois")
    last = ev.dropna(subset=["EV cumulée", "AC cumulé", "PV cumulé"])
    if last.empty:
        st.info("Renseigner au moins un mois complet.")
        return
    r = last.iloc[-1]
    PV, EV, AC = float(r["PV cumulé"]), float(r["EV cumulée"]), float(r["AC cumulé"])
    CPI = EV / AC if AC else float("nan")
    SPI = EV / PV if PV else float("nan")
    EAC = bac / CPI if CPI else float("nan")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CPI (coût)", f"{CPI:.2f}", "sous budget" if CPI >= 1 else "dépassement", delta_color="normal" if CPI >= 1 else "inverse")
    c2.metric("SPI (délai)", f"{SPI:.2f}", "en avance" if SPI >= 1 else "en retard", delta_color="normal" if SPI >= 1 else "inverse")
    c3.metric("CV = EV − AC", f"{fmt(EV - AC, 0)} {dev}")
    c4.metric("SV = EV − PV", f"{fmt(EV - PV, 0)} {dev}")
    c1, c2, c3 = st.columns(3)
    c1.metric("EAC (prévision finale)", f"{fmt(EAC, 0)} {dev}")
    c2.metric("ETC (reste à dépenser)", f"{fmt(EAC - AC, 0)} {dev}")
    c3.metric("VAC (écart final)", f"{fmt(bac - EAC, 0)} {dev}")
    fig = go.Figure()
    for col, color in [("PV cumulé", GRIS), ("EV cumulée", ACCENT), ("AC cumulé", ROUGE)]:
        fig.add_trace(go.Scatter(x=ev["Mois"], y=ev[col], name=col, mode="lines+markers", line=dict(color=color, width=4)))
    fig.add_hline(y=bac, line_dash="dot", line_color=NOIR, annotation_text="BAC")
    fig.update_layout(title="Courbes en S", xaxis_title="Mois", yaxis_title=dev)
    pplot(fig, 400)




# ===================== PAGE : EXPORT =====================
def build_excel():
    S = st.session_state
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame({"Clé": list(S.projet), "Valeur": [str(v) for v in S.projet.values()]}).to_excel(xw, sheet_name="Projet", index=False)
        for k in COLS:
            S[k].to_excel(xw, sheet_name=LABELS[k][:31], index=False)
        metre_totals(S.metre).to_excel(xw, sheet_name="Metre avec totaux", index=False)
    return buf.getvalue()


def build_rapport():
    S = st.session_state
    P = S.projet
    dev = P["devise"]
    t = S.taches.dropna(subset=["Tâche"])
    dur = num(t, "Durée (j)")
    avanc = float((dur * num(t, "Avancement (%)")).sum() / dur.sum()) if dur.sum() else 0.0
    hv = hsv_table(S.hsv)
    Vn = vol_at(hv, P["cote_nnr"]) / 1e6 if len(hv) else 0.0
    cl, kk = classe_barrage(P["H"], Vn)
    mt = metre_totals(S.metre)
    L = [f"# Rapport de synthèse — {P['nom']}", f"*Édité le {date.today().strftime('%d/%m/%Y')}*", "",
         "## Ouvrage", f"- Type : {P['type']}", f"- Hauteur : {P['H']:.1f} m — crête {P['lcrete']:.0f} m — cote de crête {P['cote_crete']:.1f} m",
         f"- Retenue normale {P['cote_nnr']:.1f} m — plus hautes eaux {P['cote_phe']:.1f} m — volume {Vn:.2f} hm³",
         f"- Classe de l'ouvrage : **{cl}** (H²√V = {kk:.0f})", "", "## Avancement et délais",
         f"- Avancement global pondéré : **{avanc:.1f} %**", f"- Période : {P['debut']} → {P['fin']}", "", "## Coûts",
         f"- Estimation du métré HT : **{mt['Total'].sum():,.0f} {dev}**".replace(",", " "),
         f"- Budget cible : {P['budget']:,.0f} {dev}".replace(",", " "), "", "## Compactage du remblai"]
    comp = compaction_summary(S.compactage)
    L += [f"- {x['Zone']} : moyenne {x['Moyenne (% OPM)']} % OPM → {x['Statut']}" for _, x in comp.iterrows()] or ["- Aucun essai."]
    L += ["", "## Auscultation"]
    ist = instr_status(S.releves, S.seuils)
    L += [f"- {x['Instrument']} ({x['Type']}) : {x['Dernière valeur']} {x['Unité']} → {x['Statut']}" for _, x in ist.iterrows()] or ["- Aucun relevé."]
    L += ["", "---", "*Généré par GC Barrage Pro — résultats indicatifs à valider par un ingénieur spécialisé en barrages.*"]
    return "\n".join(L)


def page_export():
    S = st.session_state
    hero("📤 Export, rapport et sauvegarde", "Classeur Excel • rapport de synthèse • restauration")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Classeur Excel complet", build_excel(), "projet_barrage.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    rap = build_rapport()
    c2.download_button("⬇️ Rapport de synthèse (Markdown)", rap.encode("utf-8"), "rapport_barrage.md", "text/markdown")
    with st.expander("👁️ Aperçu du rapport", expanded=True):
        st.markdown(rap)
    cols = st.columns(4)
    for i, k in enumerate(COLS):
        cols[i % 4].download_button(f"⬇️ {LABELS[k]}", S[k].to_csv(index=False).encode("utf-8-sig"), f"{k}.csv", "text/csv", key=f"csv_{k}")
    up = st.file_uploader("Restaurer un classeur exporté", type=["xlsx"])
    if up is not None and st.button("♻️ Restaurer les données"):
        try:
            sheets = pd.read_excel(up, sheet_name=None)
            inv = {v[:31]: k for k, v in LABELS.items()}
            for nom, df in sheets.items():
                if nom in inv:
                    set_df(inv[nom], coerce(df, inv[nom]))
            st.success("Données restaurées.")
            st.rerun()
        except Exception as ex:
            st.error(f"Restauration impossible : {ex}")
    if st.button("🗑️ Recharger les données de démonstration"):
        for k in list(S.keys()):
            del S[k]
        st.rerun()


# ===================== NAVIGATION =====================
PAGES = {
    "🏠 Tableau de bord": page_dashboard,
    "📥 Collecte et journal": page_collecte,
    "💧 Retenue et envasement": page_retenue,
    "🌪️ Crue et évacuateur": page_crue,
    "🧱 Barrage-poids béton": page_poids,
    "⛰️ Barrage en remblai": page_remblai,
    "🪨 Fondation et étanchéité": page_fondation,
    "🔬 Contrôle des matériaux": page_materiaux,
    "📡 Auscultation": page_instrumentation,
    "🛟 Sécurité et rupture": page_securite,
    "🧮 Métré et coûts": page_metre,
    "📅 Planning": page_planning,
    "💰 Suivi des coûts (EVM)": page_cout,
    "📤 Export et rapport": page_export,
}


def main():
    init_state()
    with st.sidebar:
        st.markdown("<div class='brand'>🌊 GC Barrage Pro</div>", unsafe_allow_html=True)
        choix = st.radio("Navigation", list(PAGES), label_visibility="collapsed")
        st.markdown("---")
        st.caption(f"Projet : {st.session_state.projet['nom']}")
        st.caption("Résultats indicatifs — validation par un ingénieur spécialisé en barrages requise.")
    PAGES[choix]()


if __name__ == "__main__":
    main()
