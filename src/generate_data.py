"""
Generate realistic synthetic data for the case study:
"AI Operations Audit - Top 3 Time Drains at a Mid-Sized Japanese 3PL"

Company profile (fictional, unnamed): third-party logistics provider in the
Kanto region, ~60 office staff across Customer Service, Operations, Finance,
Sales Admin and Management. Period: Nov 2025 - Oct 2026 (12 months).

Outputs (data/raw/):
  employees.csv               - staff list with division and loaded hourly cost (JPY)
  time_logs.csv               - task-level time tracking (~150k rows, intentionally dirty)
  cs_tickets.csv              - customer service emails/tickets with free text
  shipping_documents.csv      - manually keyed shipping documents
  carrier_invoice_lines.csv   - carrier invoice lines vs expected rates
  employee_survey.csv         - perceived time drains (perception vs data)
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 20261102
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

START, END = "2025-11-01", "2026-10-31"

# ---------------------------------------------------------------- calendar
JP_HOLIDAYS = pd.to_datetime([
    "2025-11-03", "2025-11-24", "2025-12-29", "2025-12-30", "2025-12-31",
    "2026-01-01", "2026-01-02", "2026-01-12", "2026-02-11", "2026-02-23",
    "2026-03-20", "2026-04-29", "2026-05-04", "2026-05-05", "2026-05-06",
    "2026-07-20", "2026-08-11", "2026-08-13", "2026-08-14", "2026-09-21",
    "2026-09-22", "2026-09-23", "2026-10-12",
])
days = pd.bdate_range(START, END)
workdays = days[~days.isin(JP_HOLIDAYS)]

# workload multiplier: year-end rush, fiscal year-end (March), peak season
month_load = {11: 1.00, 12: 1.18, 1: 0.95, 2: 1.00, 3: 1.15, 4: 1.02,
              5: 0.93, 6: 1.00, 7: 1.05, 8: 0.92, 9: 1.02, 10: 1.06}

# ---------------------------------------------------------------- employees
first = ["Haruto", "Yuto", "Sota", "Ren", "Takumi", "Kenta", "Daiki", "Shota",
         "Yui", "Hina", "Aoi", "Sakura", "Misaki", "Nanami", "Yuka", "Ayaka",
         "Kaito", "Riku", "Mei", "Rin", "Koji", "Hiroshi", "Naoko", "Emi"]
last = ["Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito", "Yamamoto",
        "Nakamura", "Kobayashi", "Kato", "Yoshida", "Yamada", "Sasaki",
        "Yamaguchi", "Matsumoto", "Inoue", "Kimura", "Hayashi", "Shimizu", "Mori"]

divisions = {  # headcount, hourly loaded cost range (JPY)
    "Customer Service": (14, 2400, 3200),
    "Operations": (22, 2600, 3600),
    "Finance": (10, 2900, 4000),
    "Sales Admin": (8, 2500, 3300),
    "Management": (6, 5500, 7500),
}
rows, i = [], 1
for div, (n, lo, hi) in divisions.items():
    for k in range(n):
        role = ("Manager" if div == "Management" else
                "Team Lead" if k == 0 else
                rng.choice(["Staff", "Senior Staff"], p=[0.7, 0.3]))
        rows.append({
            "employee_id": f"E{i:03d}",
            "name": f"{rng.choice(first)} {rng.choice(last)}",
            "division": div,
            "role": role,
            "hire_date": (pd.Timestamp("2012-04-01") + pd.Timedelta(days=int(rng.integers(0, 4900)))).date(),
            "hourly_cost_jpy": int(round(rng.uniform(lo, hi), -1)),
        })
        i += 1
employees = pd.DataFrame(rows)
employees.to_csv(OUT / "employees.csv", index=False)

# ---------------------------------------------------------------- task catalogue
# (task_type, share of day, mean minutes per entry, system, repetitive 1-5)
TASKS = {
    "Customer Service": [
        ("Shipment status inquiry (WISMO)", 0.34, 9, "Email/Phone", 5),
        ("Delivery exception handling", 0.15, 22, "TMS", 3),
        ("Booking change request", 0.12, 14, "TMS", 4),
        ("Damage / claim handling", 0.08, 35, "Email", 2),
        ("CS reporting", 0.07, 40, "Excel", 4),
        ("Internal meetings", 0.10, 45, "Meeting", 1),
        ("Training / admin", 0.07, 30, "Other", 1),
        ("Other", 0.07, 20, "Other", 2),
    ],
    "Operations": [
        ("Shipping document data entry", 0.30, 12, "WMS/Excel", 5),
        ("Carrier booking", 0.13, 15, "Carrier portal", 4),
        ("Manual tracking updates", 0.11, 8, "TMS", 5),
        ("Warehouse coordination", 0.14, 25, "Phone/Chat", 2),
        ("Exception resolution", 0.10, 30, "TMS", 2),
        ("Internal meetings", 0.11, 45, "Meeting", 1),
        ("Ops reporting", 0.06, 35, "Excel", 4),
        ("Other", 0.05, 20, "Other", 2),
    ],
    "Finance": [
        ("Carrier invoice reconciliation", 0.36, 18, "Excel/ERP", 5),
        ("Customer billing", 0.17, 20, "ERP", 4),
        ("Accounts payable processing", 0.14, 15, "ERP", 4),
        ("Month-end close", 0.12, 50, "ERP/Excel", 3),
        ("Finance reporting", 0.08, 45, "Excel", 4),
        ("Internal meetings", 0.09, 45, "Meeting", 1),
        ("Other", 0.04, 20, "Other", 2),
    ],
    "Sales Admin": [
        ("Quote preparation", 0.30, 35, "Excel", 4),
        ("Rate lookup", 0.18, 10, "Rate sheets", 5),
        ("CRM updates", 0.15, 8, "CRM", 4),
        ("Internal meetings", 0.15, 45, "Meeting", 1),
        ("Sales reporting", 0.12, 40, "Excel", 4),
        ("Other", 0.10, 20, "Other", 2),
    ],
    "Management": [
        ("Internal meetings", 0.42, 50, "Meeting", 1),
        ("Management reporting", 0.23, 45, "Excel", 3),
        ("Approvals", 0.20, 10, "Email/ERP", 3),
        ("Other", 0.15, 30, "Other", 2),
    ],
}
task_meta = pd.DataFrame(
    [(d, t, s, m, sysm, rep) for d, lst in TASKS.items() for t, s, m, sysm, rep in lst],
    columns=["division", "task_type", "share", "mean_min", "system", "repetitiveness"],
)

# ---------------------------------------------------------------- time logs
log_rows = []
log_id = 1
emp_div = dict(zip(employees.employee_id, employees.division))
for d in workdays:
    load = month_load[d.month]
    for emp, div in emp_div.items():
        if rng.random() < 0.045:  # leave / absence
            continue
        lst = TASKS[div]
        names = [t[0] for t in lst]
        shares = np.array([t[1] for t in lst])
        means = np.array([t[2] for t in lst])
        # repetitive tasks scale with volume, fixed ones don't
        reps = np.array([t[4] for t in lst])
        adj = shares * np.where(reps >= 4, load, 1.0)
        day_min = rng.normal(455, 25) * (1 + (load - 1) * 0.6)  # overtime in busy months
        minutes_per_task = adj / adj.sum() * day_min
        for name, tot, mean in zip(names, minutes_per_task, means):
            # staff log work in blocks (e.g. "WISMO emails, 40 min, 5 items")
            block = max(mean, 38)
            n = max(1, int(round(tot / block * rng.uniform(0.8, 1.2))))
            durs = rng.lognormal(np.log(block), 0.35, n)
            durs = durs / durs.sum() * tot * rng.uniform(0.95, 1.05)
            for du in durs:
                items = max(1, int(round(du / mean * rng.uniform(0.85, 1.15))))
                log_rows.append((f"L{log_id:07d}", emp, d.date(), name, items, round(float(du), 1)))
                log_id += 1

logs = pd.DataFrame(log_rows, columns=["log_id", "employee_id", "work_date", "task_type", "items_handled", "duration_min"])
logs = logs.merge(task_meta[["division", "task_type", "system"]],
                  left_on=[logs.employee_id.map(emp_div), "task_type"],
                  right_on=["division", "task_type"], how="left").drop(columns=["division", "key_0"], errors="ignore")
logs = logs[["log_id", "employee_id", "work_date", "task_type", "system", "items_handled", "duration_min"]]

# ---- inject realistic dirt
n = len(logs)
idx = rng.choice(n, int(n * 0.06), replace=False)  # inconsistent labels
def messy(s):
    r = rng.random()
    return s.lower() if r < 0.35 else s.upper() if r < 0.5 else f"  {s} " if r < 0.8 else s.replace(" ", "  ")
logs.iloc[idx, logs.columns.get_loc("task_type")] = [messy(s) for s in logs.iloc[idx]["task_type"]]
logs.iloc[rng.choice(n, int(n * 0.006), replace=False), logs.columns.get_loc("duration_min")] = np.nan
neg = rng.choice(n, 90, replace=False)
logs.iloc[neg, logs.columns.get_loc("duration_min")] = -logs.iloc[neg]["duration_min"].abs()
big = rng.choice(n, 60, replace=False)  # timer left running
logs.iloc[big, logs.columns.get_loc("duration_min")] = rng.uniform(600, 1400, 60).round(1)
logs["work_date"] = logs["work_date"].astype(str)
alt = rng.choice(n, int(n * 0.03), replace=False)  # mixed date format (JP style)
logs.iloc[alt, logs.columns.get_loc("work_date")] = pd.to_datetime(logs.iloc[alt]["work_date"]).dt.strftime("%Y/%m/%d")
dups = logs.sample(frac=0.012, random_state=1)  # double submissions
logs = pd.concat([logs, dups]).sort_values(["work_date", "employee_id"], kind="stable").reset_index(drop=True)
logs.to_csv(OUT / "time_logs.csv", index=False)

# ---------------------------------------------------------------- CS tickets
cities = ["Tokyo", "Yokohama", "Osaka", "Nagoya", "Fukuoka", "Sapporo", "Sendai",
          "Kobe", "Kyoto", "Hiroshima", "Saitama", "Chiba", "Niigata", "Shizuoka"]
customers = ["retail", "e-commerce", "manufacturer", "pharma distributor", "apparel brand", "electronics wholesaler"]
TEMPL = {
    "WISMO": [
        "Hi, could you tell me where shipment {sid} is? It was supposed to arrive in {city} {when}.",
        "Tracking for {sid} hasn't updated since {when}. Can you confirm the current status?",
        "Our store in {city} is asking about order {sid}. What is the ETA please?",
        "Please advise delivery status of {sid}. Customer is waiting.",
        "Is {sid} out for delivery today? Need to inform our {city} warehouse.",
        "Following up again on {sid} - no update on the tracking page.",
        "Can you check whether {sid} has left your Saitama DC yet?",
    ],
    "Delivery exception": [
        "Shipment {sid} was returned to sender - the address in {city} is correct. Please investigate.",
        "Driver reported nobody at the {city} site for {sid}, but we were open. Please redeliver.",
        "{sid} arrived with only {n} of {m} cartons. Where are the rest?",
        "Delivery of {sid} missed the time slot at our {city} DC. Need rebooking urgently.",
    ],
    "Booking change": [
        "Please change the delivery date of {sid} to next {day}.",
        "We need to update the consignee address for {sid} to our new {city} branch.",
        "Can we add {n} more pallets to booking {sid}?",
        "Please cancel pickup for {sid}, the goods are not ready.",
    ],
    "Damage / claim": [
        "{sid} arrived damaged - {n} cartons crushed. Photos attached. How do we file a claim?",
        "Products in {sid} were wet on arrival in {city}. We want to submit a claim.",
        "Claim follow-up for {sid}: any update on compensation?",
    ],
    "Billing question": [
        "Invoice for {sid} shows a fuel surcharge we did not agree to. Please check.",
        "We were billed twice for {sid}. Please issue a credit note.",
        "Could you send a copy of the invoice for last month's {city} deliveries?",
    ],
    "Other": [
        "Do you offer temperature-controlled delivery to {city}?",
        "Please update our contact person for future shipments.",
        "What are your operating hours during Golden Week?",
        "Can you share your new rate card for {city}?",
    ],
}
cat_p = {"WISMO": 0.46, "Delivery exception": 0.15, "Booking change": 0.14,
         "Damage / claim": 0.06, "Billing question": 0.08, "Other": 0.11}
cats = list(cat_p)
n_t = 26_000
t_cat = rng.choice(cats, n_t, p=list(cat_p.values()))
day_w = np.array([month_load[d.month] for d in workdays]); day_w /= day_w.sum()
t_day = rng.choice(workdays, n_t, p=day_w)
t_time = pd.to_datetime(t_day) + pd.to_timedelta(rng.normal(13 * 60, 150, n_t).clip(8 * 60, 19.5 * 60), unit="m")
whens = ["yesterday", "on Monday", "two days ago", "this morning", "last Friday"]
daysw = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
greet = ["", "", "Hi team, ", "Hello, ", "Good morning. ", "Dear CS, ", "Hi, ", "Urgent: ", "Re: "]
sign = ["", "", " Thanks.", " Thank you.", " Regards.", " Please reply asap.", " Many thanks!",
        " We appreciate your quick help.", " Best regards, logistics team."]
def fill(tpl):
    m = int(rng.integers(5, 40))
    return tpl.format(sid=f"KT{rng.integers(10**7, 10**8)}", city=rng.choice(cities),
                      when=rng.choice(whens), n=int(rng.integers(1, m)), m=m, day=rng.choice(daysw))
def typo(s):
    if rng.random() < 0.15 and len(s) > 20:
        k = int(rng.integers(5, len(s) - 5))
        s = s[:k] + s[k + 1:]  # dropped character
    return s.lower() if rng.random() < 0.08 else s
texts = []
for c in t_cat:
    body = fill(TEMPL[c][rng.integers(len(TEMPL[c]))])
    if rng.random() < 0.12:  # real emails often mix two topics
        other = rng.choice([x for x in cats if x != c])
        extra = fill(TEMPL[other][rng.integers(len(TEMPL[other]))])
        body = f"{body} Also, {extra[0].lower()}{extra[1:]}"
    texts.append(typo(f"{rng.choice(greet)}{body}{rng.choice(sign)}"))
# ~3% of agent labels are wrong, as in any manually tagged inbox
flip = rng.random(n_t) < 0.03
t_cat = np.where(flip, rng.choice(cats, n_t), t_cat)
handle_mean = {"WISMO": 9, "Delivery exception": 24, "Booking change": 13,
               "Damage / claim": 38, "Billing question": 20, "Other": 10}
tickets = pd.DataFrame({
    "ticket_id": [f"T{j:06d}" for j in range(1, n_t + 1)],
    "created_at": t_time.round("min"),
    "channel": rng.choice(["Email", "Phone", "Web form"], n_t, p=[0.62, 0.28, 0.10]),
    "customer_segment": rng.choice(customers, n_t),
    "message_text": texts,
    "category": t_cat,
    "handling_min": [round(float(rng.lognormal(np.log(handle_mean[c]), 0.4)), 1) for c in t_cat],
    "first_response_min": rng.lognormal(np.log(95), 0.8, n_t).round(0),
    "reopened": rng.random(n_t) < np.where(t_cat == "WISMO", 0.22, 0.08),
})
tickets = tickets.sort_values("created_at").reset_index(drop=True)
# ~4% unlabeled, like a real inbox
tickets.loc[rng.random(n_t) < 0.04, "category"] = np.nan
tickets.to_csv(OUT / "cs_tickets.csv", index=False)

# ---------------------------------------------------------------- shipping docs
n_d = 41_000
doc_types = ["Delivery note", "Packing list", "Commercial invoice", "Bill of lading", "Customs declaration"]
dt = rng.choice(doc_types, n_d, p=[0.38, 0.27, 0.15, 0.12, 0.08])
fields = {"Delivery note": 14, "Packing list": 22, "Commercial invoice": 28, "Bill of lading": 34, "Customs declaration": 40}
nf = np.array([fields[x] for x in dt]) + rng.integers(-3, 6, n_d)
entry = (nf * rng.lognormal(np.log(0.42), 0.25, n_d)).round(1)
err = rng.binomial(nf, 0.012)
ops = employees[employees.division == "Operations"].employee_id.values
docs = pd.DataFrame({
    "doc_id": [f"D{j:06d}" for j in range(1, n_d + 1)],
    "received_date": pd.to_datetime(rng.choice(workdays, n_d, p=day_w)).date,
    "doc_type": dt,
    "source_format": rng.choice(["PDF (email)", "Scanned paper", "Fax", "Excel"], n_d, p=[0.48, 0.27, 0.10, 0.15]),
    "pages": rng.integers(1, 5, n_d),
    "fields_keyed": nf,
    "entry_min": entry,
    "field_errors": err,
    "rework_min": np.where(err > 0, (err * rng.uniform(6, 15, n_d)).round(1), 0.0),
    "keyed_by": rng.choice(ops, n_d),
})
docs.to_csv(OUT / "shipping_documents.csv", index=False)

# ---------------------------------------------------------------- carrier invoices
carriers = ["Carrier A (national parcel)", "Carrier B (LTL)", "Carrier C (FTL)",
            "Carrier D (regional)", "Carrier E (cold chain)"]
n_i = 34_000
car = rng.choice(carriers, n_i, p=[0.34, 0.24, 0.16, 0.16, 0.10])
expected = rng.lognormal(np.log(18_000), 0.7, n_i).round(-1)
mism = rng.random(n_i) < 0.14
reason = np.where(mism, rng.choice(["Fuel surcharge", "Wrong weight tier", "Duplicate charge",
                                    "Accessorial not agreed", "Rate not updated"], n_i,
                                   p=[0.30, 0.25, 0.12, 0.18, 0.15]), "")
billed = np.where(mism, expected * rng.uniform(1.03, 1.35, n_i), expected).round(-1)
inv = pd.DataFrame({
    "line_id": [f"I{j:06d}" for j in range(1, n_i + 1)],
    "invoice_month": rng.choice(pd.period_range("2025-11", "2026-10", freq="M").astype(str), n_i),
    "carrier": car,
    "shipment_ref": [f"KT{x}" for x in rng.integers(10**7, 10**8, n_i)],
    "expected_amount_jpy": expected,
    "billed_amount_jpy": billed,
    "mismatch_reason": reason,
    "check_min": rng.lognormal(np.log(3.2), 0.4, n_i).round(1),
    "dispute_min": np.where(mism, rng.lognormal(np.log(28), 0.5, n_i), 0).round(1),
    "recovered": np.where(mism, rng.random(n_i) < 0.62, False),
})
inv.to_csv(OUT / "carrier_invoice_lines.csv", index=False)

# ---------------------------------------------------------------- survey
perceived = ["Internal meetings", "Shipment status inquiries (WISMO)", "Shipping document data entry",
             "Carrier invoice reconciliation", "Reporting in Excel", "Exception handling", "Quote preparation"]
base_p = {
    "Customer Service": [0.30, 0.25, 0.02, 0.01, 0.20, 0.20, 0.02],
    "Operations": [0.30, 0.05, 0.25, 0.02, 0.18, 0.18, 0.02],
    "Finance": [0.28, 0.02, 0.03, 0.30, 0.30, 0.04, 0.03],
    "Sales Admin": [0.30, 0.05, 0.02, 0.02, 0.26, 0.05, 0.30],
    "Management": [0.45, 0.10, 0.05, 0.05, 0.25, 0.08, 0.02],
}
srows = []
for _, e in employees.iterrows():
    if rng.random() < 0.13:  # non-response
        continue
    p = np.array(base_p[e.division]); p /= p.sum()
    top = rng.choice(perceived, 3, replace=False, p=p)
    srows.append({
        "employee_id": e.employee_id, "division": e.division,
        "biggest_time_drain_1": top[0], "biggest_time_drain_2": top[1], "biggest_time_drain_3": top[2],
        "est_hours_per_week_on_drain_1": int(rng.integers(3, 15)),
        "open_to_ai_tools_1to5": int(rng.choice([2, 3, 4, 5], p=[0.12, 0.28, 0.38, 0.22])),
        "comment": rng.choice([
            "Too many meetings, hard to focus.",
            "Customers keep asking the same tracking questions.",
            "Retyping PDFs into the WMS takes forever.",
            "Checking carrier invoices line by line is exhausting.",
            "Weekly Excel reports are copy-paste work.",
            "", "", ""]),
    })
pd.DataFrame(srows).to_csv(OUT / "employee_survey.csv", index=False)

# ---------------------------------------------------------------- summary
for f in sorted(OUT.glob("*.csv")):
    print(f"{f.name:28s} {sum(1 for _ in open(f, encoding='utf-8')) - 1:>8,} rows")
