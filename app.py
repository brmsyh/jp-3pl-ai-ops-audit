"""
AI Operations Audit - Top 3 Time Drains (Japanese 3PL case study)
Streamlit dashboard. Run locally:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union

st.set_page_config(page_title="AI Operations Audit · 3PL Japan", page_icon="📦", layout="wide")

APP = Path(__file__).parent / "data" / "app"
BLUE, ORANGE, GRAY, MUTED = "#2a78d6", "#eb6834", "#c9c8c3", "#52514e"
TOP3 = ["Shipping document data entry", "Shipment status inquiry (WISMO)", "Carrier invoice reconciliation"]


@st.cache_data
def load():
    names = ["task_scores", "monthly_task_hours", "division_task", "perception", "initiatives",
             "docs_by_type", "docs_by_format", "tickets_by_category", "tickets_monthly",
             "invoices_by_carrier", "invoices_by_reason"]
    d = {n: pd.read_csv(APP / f"{n}.csv") for n in names}
    d["kpis"] = pd.read_csv(APP / "kpis.csv", index_col=0)["value"]
    return d


@st.cache_resource
def train_classifier():
    t = pd.read_csv(APP / "tickets_text.csv").dropna(subset=["category"])
    model = make_pipeline(
        make_union(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                   TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3, sublinear_tf=True)),
        LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced"),
    )
    model.fit(t["message_text"], t["category"])
    return model


def yen_m(x):
    return f"¥{x / 1e6:,.1f}M"


def style(fig, height=380):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(size=13), legend_title_text="")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


d = load()
k = d["kpis"]
scores = d["task_scores"]
ini = d["initiatives"]

st.title("AI Operations Audit: Top 3 Time Drains")
st.caption("Case study · Mid-sized third-party logistics provider, Kanto region, Japan · ~60 office staff · "
           "Nov 2025 – Oct 2026 · built on realistic synthetic data")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Overview", "Top 3 deep dives", "Perception vs data", "ROI simulator", "Email classifier (PoC)"])

# ------------------------------------------------------------------ Overview
with tab1:
    t3 = scores[scores["task_type"].isin(TOP3)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hours logged / year", f"{k['total_hours']:,.0f} h")
    c2.metric("Loaded staff cost", yen_m(k["total_cost_jpy"]))
    c3.metric("Top 3 drains: share of hours", f"{t3['hours'].sum() / k['total_hours']:.0%}",
              help="Shipping document entry, WISMO inquiries, carrier invoice reconciliation")
    c4.metric("Net annual benefit (plan)", yen_m(ini["net_annual_jpy"].sum()),
              help="After running costs; see ROI simulator")

    left, right = st.columns(2)
    with left:
        top = scores.sort_values("hours", ascending=False).head(12).iloc[::-1]
        fig = px.bar(top, x="hours", y="task_type", orientation="h", title="Hours logged by task (top 12)",
                     color_discrete_sequence=[GRAY], hover_data={"share": ":.1%", "hours": ":,.0f"})
        st.plotly_chart(style(fig, 460).update_layout(yaxis_title="", xaxis_title="Hours per year"),
                        use_container_width=True)
    with right:
        s = scores.head(10).iloc[::-1].copy()
        s["group"] = s["task_type"].apply(lambda t: "Top 3" if t in TOP3 else "Other tasks")
        fig = px.bar(s, x="addressable_cost_jpy", y="task_type", orientation="h", color="group",
                     color_discrete_map={"Top 3": BLUE, "Other tasks": GRAY},
                     title="AI-addressable staff cost (¥/year)",
                     hover_data={"ai_addressable_pct": ":.0%", "ai_lever": True, "group": False})
        st.plotly_chart(style(fig, 460).update_layout(yaxis_title="", xaxis_title="¥ per year"),
                        use_container_width=True)
    st.info("Internal meetings are the largest block by hours, but AI can only trim them. Ranked by the time AI can "
            "realistically remove, the three biggest opportunities are document entry, WISMO inquiries and invoice "
            "reconciliation, which together take about a quarter of all logged hours.")

    m = d["monthly_task_hours"]
    m = m[m["task_type"].isin(TOP3)]
    fig = px.line(m, x="month", y="hours", color="task_type", markers=True,
                  color_discrete_sequence=[BLUE, ORANGE, "#1baf7a"], title="Monthly hours on the top 3 drains")
    st.plotly_chart(style(fig).update_layout(xaxis_title="", yaxis_title="Hours"), use_container_width=True)

    with st.expander("Hours by division and task"):
        div = d["division_task"].pivot_table(index="task_type", columns="division", values="hours", fill_value=0)
        st.dataframe(div.round(0).astype(int), use_container_width=True)

# ------------------------------------------------------------------ Deep dives
with tab2:
    choice = st.radio("Time drain", ["1 · Shipping document data entry", "2 · Shipment status inquiries (WISMO)",
                                     "3 · Carrier invoice reconciliation"], horizontal=True)
    if choice.startswith("1"):
        dt = d["docs_by_type"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Documents keyed / year", f"{k['docs']:,.0f}")
        c2.metric("Docs with ≥1 keying error", f"{(dt['error_rate'] * dt['docs']).sum() / dt['docs'].sum():.0%}")
        c3.metric("Rework hours from errors", f"{dt['rework_h'].sum():,.0f} h")
        a, b = st.columns(2)
        fig = px.bar(dt, x="doc_type", y="avg_entry_min", title="Average keying time per document (min)",
                     color_discrete_sequence=[BLUE])
        a.plotly_chart(style(fig).update_layout(xaxis_title="", yaxis_title="Minutes"), use_container_width=True)
        fmt = d["docs_by_format"]
        fig = px.bar(fmt.sort_values("docs"), x="docs", y="source_format", orientation="h",
                     title="How documents arrive", color_discrete_sequence=[GRAY])
        b.plotly_chart(style(fig).update_layout(xaxis_title="Documents", yaxis_title=""), use_container_width=True)
        st.success("**Recommendation:** intelligent document processing (OCR + LLM field extraction) with a human "
                   "validation step. About 75% of documents arrive as PDF or scans; Excel files can be imported "
                   "directly. Target: remove ~70% of keying time and most keying errors.")
    elif choice.startswith("2"):
        tc = d["tickets_by_category"]
        w = tc[tc["category"] == "WISMO"].iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("WISMO share of tickets", f"{w['share']:.0%}")
        c2.metric("WISMO reopen rate", f"{w['reopen_rate']:.0%}", help="Customer chased again before getting an answer")
        c3.metric("Median first response", f"{w['median_first_response_min']:.0f} min")
        a, b = st.columns(2)
        fig = px.bar(tc.sort_values("tickets"), x="tickets", y="category", orientation="h",
                     title="Tickets per year by category", color_discrete_sequence=[GRAY])
        fig.update_traces(marker_color=[BLUE if c == "WISMO" else GRAY for c in tc.sort_values("tickets")["category"]])
        a.plotly_chart(style(fig).update_layout(xaxis_title="Tickets", yaxis_title=""), use_container_width=True)
        tm = d["tickets_monthly"]
        fig = px.line(tm[tm["category"] == "WISMO"], x="month", y="tickets", markers=True,
                      title="WISMO tickets per month", color_discrete_sequence=[BLUE])
        b.plotly_chart(style(fig).update_layout(xaxis_title="", yaxis_title="Tickets"), use_container_width=True)
        st.success("**Recommendation:** (1) proactive SMS/email tracking updates from the TMS so customers don't need "
                   "to ask, and (2) an LLM reply assistant that answers WISMO emails from live tracking data. "
                   "The email classifier tab shows the routing model. Also fixes 'manual tracking updates' in Operations.")
    else:
        c = d["invoices_by_carrier"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Invoice lines checked by hand", f"{k['invoice_lines']:,.0f}")
        c2.metric("Overbilled in 12 months", yen_m(k["overbilled_jpy"]))
        c3.metric("Never recovered", yen_m(k["unrecovered_jpy"]),
                  f"{k['unrecovered_jpy'] / k['overbilled_jpy']:.0%} of overbilling", delta_color="off")
        a, b = st.columns(2)
        r = d["invoices_by_reason"].sort_values("overbilled_jpy")
        fig = px.bar(r, x="overbilled_jpy", y="mismatch_reason", orientation="h", title="Overbilling by reason (¥)",
                     color_discrete_sequence=[BLUE])
        a.plotly_chart(style(fig).update_layout(xaxis_title="¥", yaxis_title=""), use_container_width=True)
        cc = c.melt(id_vars="carrier", value_vars=["overbilled_jpy", "unrecovered_jpy"], var_name="measure")
        cc["measure"] = cc["measure"].map({"overbilled_jpy": "Overbilled", "unrecovered_jpy": "Not recovered"})
        fig = px.bar(cc, x="value", y="carrier", color="measure", barmode="group", orientation="h",
                     title="Overbilling by carrier (¥)", color_discrete_sequence=[GRAY, ORANGE])
        b.plotly_chart(style(fig).update_layout(xaxis_title="¥", yaxis_title=""), use_container_width=True)
        st.success("**Recommendation:** automated matching of every invoice line against the contract rate card, "
                   "with anomaly flags by reason. People handle only the ~14% of lines that fail the match, and "
                   "disputes start earlier, which improves recovery.")

# ------------------------------------------------------------------ Perception
with tab3:
    p = d["perception"].sort_values("actual_share")
    fig = go.Figure()
    for _, row in p.iterrows():
        fig.add_trace(go.Scatter(x=[row["perceived_share"], row["actual_share"]], y=[row["group"]] * 2, mode="lines",
                                 line=dict(color=GRAY, width=3), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=p["perceived_share"], y=p["group"], mode="markers", name="Perceived (survey)",
                             marker=dict(color=ORANGE, size=13, line=dict(color="white", width=2))))
    fig.add_trace(go.Scatter(x=p["actual_share"], y=p["group"], mode="markers", name="Actual (hours)",
                             marker=dict(color=BLUE, size=13, line=dict(color="white", width=2))))
    fig.update_layout(title="What staff think vs where the hours actually go", xaxis_tickformat=".0%")
    st.plotly_chart(style(fig, 440), use_container_width=True)
    st.markdown("Staff over-weight **meetings, Excel reporting and exception handling** (visible, frustrating work) and "
                "under-weight **document keying, WISMO and invoice checking**, which are high-volume tasks spread thinly "
                "through the day. This is why the audit starts from logged time, not opinion.")
    st.dataframe(p.sort_values("actual_share", ascending=False).style.format(
        {"perceived_share": "{:.1%}", "actual_share": "{:.1%}", "gap_pts": "{:+.1f}"}), use_container_width=True)

# ------------------------------------------------------------------ ROI
with tab4:
    st.markdown("Adjust the assumptions to see how the business case changes. Defaults come from the audit.")
    rows = []
    cols = st.columns(3)
    for col, (_, r) in zip(cols, ini.iterrows()):
        with col:
            st.subheader(r["initiative"])
            st.caption(f"Baseline: {r['baseline_hours']:,.0f} h/yr · ¥{r['avg_hourly_cost_jpy']:,.0f}/h")
            pct = st.slider("Time removed", 0, 90, int(r["automation_pct"] * 100), 5, format="%d%%",
                            key=f"pct_{r['task']}") / 100
            one = st.number_input("One-off cost (¥)", 0, 50_000_000, int(r["one_off_jpy"]), 500_000,
                                  key=f"one_{r['task']}")
            ann = st.number_input("Running cost per year (¥)", 0, 30_000_000, int(r["annual_jpy"]), 200_000,
                                  key=f"ann_{r['task']}")
            freed = r["baseline_hours"] * pct
            extra = r["extra_benefit_jpy"] * (pct / r["automation_pct"] if r["automation_pct"] else 0)
            net = freed * r["avg_hourly_cost_jpy"] + extra - ann
            pay = one / (net / 12) if net > 0 else float("nan")
            st.metric("Net benefit / year", yen_m(net))
            st.metric("Payback", f"{pay:.1f} months" if net > 0 else "never")
            rows.append(dict(initiative=r["initiative"], hours_freed=freed, fte=freed / k["fte_hours"],
                             net=net, one_off=one, payback=pay))
    res = pd.DataFrame(rows)
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hours freed / year", f"{res['hours_freed'].sum():,.0f} h")
    c2.metric("Capacity freed", f"{res['fte'].sum():.1f} FTE")
    c3.metric("Net benefit / year", yen_m(res["net"].sum()))
    tot_net = res["net"].sum()
    c4.metric("Blended payback", f"{res['one_off'].sum() / (tot_net / 12):.1f} months" if tot_net > 0 else "never")
    st.caption("Freed hours are capacity, not automatic cash savings: value is realised by absorbing growth without "
               "new hires, cutting peak-month overtime and redeploying staff. Invoice initiative also includes improved "
               "recovery of carrier overbilling. Costs are estimates to be replaced with vendor quotes.")

# ------------------------------------------------------------------ Classifier
with tab5:
    st.markdown("Proof of concept for the WISMO initiative: a TF-IDF + logistic regression model trained on the "
                "inbox history routes each email. Emails are **auto-handled only when the model is ≥ 90% confident "
                "it is WISMO**; everything else goes to an agent with a suggested category.")
    model = train_classifier()
    examples = {
        "Status question": "Hi team, tracking for KT48211930 hasn't updated since Monday. Can you confirm the ETA to our Osaka store?",
        "Damage claim": "Shipment KT55120394 arrived with 4 cartons crushed. How do we file a claim?",
        "Mixed topics": "Where is KT77310256? Also, we were billed twice for last month's Nagoya deliveries.",
    }
    ex = st.selectbox("Try an example or write your own", list(examples))
    text = st.text_area("Customer email", examples[ex], height=110)
    if text.strip():
        proba = pd.Series(model.predict_proba([text])[0], index=model.classes_).sort_values(ascending=False)
        top_cat, conf = proba.index[0], proba.iloc[0]
        auto = top_cat == "WISMO" and conf >= 0.90
        c1, c2 = st.columns([1, 2])
        c1.metric("Predicted category", top_cat, f"{conf:.0%} confidence", delta_color="off")
        if auto:
            c1.success("Auto-handle: reply with live tracking status")
        else:
            c1.warning("Route to an agent")
        pdf = pd.DataFrame({"category": proba.index, "probability": proba.values}).iloc[::-1]
        fig = px.bar(pdf, x="probability", y="category", orientation="h",
                     color_discrete_sequence=[BLUE], title="Model probabilities")
        c2.plotly_chart(style(fig, 300).update_layout(xaxis_title="", yaxis_title="", xaxis_tickformat=".0%"),
                        use_container_width=True)
    st.caption("Hold-out results: accuracy 97.4%, macro-F1 0.97 (keyword rules: 0.87). At the 0.90 threshold about "
               "80% of WISMO emails are auto-handled at ~97% precision. See notebook 03.")
