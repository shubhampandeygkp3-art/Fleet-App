import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
DB_FILE = "fleet_management_v3.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Config / Settings Table
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, 
                    value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('max_buses', '13')")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('expense_categories', 'Tyres,Repairs,Toll,Insurance,Fitness Certificate')")
    
    # 2. Buses Table
    c.execute('''CREATE TABLE IF NOT EXISTS buses (
                    bus_number TEXT PRIMARY KEY, 
                    route_name TEXT, 
                    route_km REAL, 
                    monthly_emi REAL,
                    insurance_expiry TEXT,
                    fitness_expiry TEXT)''')
    
    # 3. Staff Table
    c.execute('''CREATE TABLE IF NOT EXISTS staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT, 
                    role TEXT, 
                    daily_wage REAL)''')
    
    # 4. Daily Operations Table
    c.execute('''CREATE TABLE IF NOT EXISTS daily_ops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    bus_number TEXT,
                    start_odometer REAL,
                    end_odometer REAL,
                    diesel_liters REAL,
                    diesel_rate REAL,
                    def_cost REAL,
                    expense_type TEXT,
                    custom_expense_cost REAL,
                    earnings REAL,
                    penalty REAL,
                    FOREIGN KEY(bus_number) REFERENCES buses(bus_number))''')
    
    # 5. Payroll Table
    c.execute('''CREATE TABLE IF NOT EXISTS payroll_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    month_year TEXT,
                    staff_id INTEGER,
                    days_worked INTEGER,
                    advance_received REAL,
                    FOREIGN KEY(staff_id) REFERENCES staff(id))''')
    
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    return sqlite3.connect(DB_FILE)

# --- APP CONFIG & LOAD SETTINGS ---
st.set_page_config(page_title="Custom Fleet Manager Pro", layout="wide")
st.title("🚌 Advanced Fleet, Payroll & Compliance Management Engine")
st.markdown("---")

conn = get_db_connection()
max_buses = int(conn.execute("SELECT value FROM settings WHERE key='max_buses'").fetchone()[0])
exp_cat_raw = conn.execute("SELECT value FROM settings WHERE key='expense_categories'").fetchone()[0]
expense_categories = [cat.strip() for cat in exp_cat_raw.split(",")]
conn.close()

# --- SIDEBAR CONFIGURATION & NAVIGATION ---
st.sidebar.header("⚙️ App Configurations")
new_max_buses = st.sidebar.number_input("Set Fleet Capacity (Max Buses)", min_value=1, max_value=500, value=max_buses, step=1)
if new_max_buses != max_buses:
    conn = get_db_connection()
    conn.execute("UPDATE settings SET value=? WHERE key='max_buses'", (str(new_max_buses),))
    conn.commit()
    conn.close()
    st.sidebar.success(f"Fleet capacity updated!")
    st.rerun()

new_exp_cats = st.sidebar.text_area("Custom Expense Categories (Comma-separated)", value=exp_cat_raw)
if st.sidebar.button("Save Custom Expense Types"):
    conn = get_db_connection()
    conn.execute("UPDATE settings SET value=? WHERE key='expense_categories'", (new_exp_cats,))
    conn.commit()
    conn.close()
    st.sidebar.success("Expense categories updated!")
    st.rerun()

st.sidebar.markdown("---")
menu = ["📊 Dashboard & Analytics", "🚏 Bus & Route Management", "🧑‍🔧 Daily Entry Logs", "👥 Staff Payroll Engine", "📋 Compliance & Expiries"]
choice = st.sidebar.selectbox("Navigate Menu", menu)

# =========================================================
# MODULE 1: BUS & ROUTE MANAGEMENT
# =========================================================
if choice == "🚏 Bus & Route Management":
    st.header(f"Manage Fleet Assets (Limit: {max_buses} Buses)")
    col1, col2 = st.columns([1, 2])
    
    conn = get_db_connection()
    df_buses = pd.read_sql_query("SELECT * FROM buses", conn)
    conn.close()
    
    with col1:
        st.subheader("Add / Modify Bus Documents")
        if len(df_buses) >= max_buses:
            st.error(f"🛑 Fleet Limit Reached ({max_buses}/{max_buses}).")
        else:
            with st.form("bus_form", clear_on_submit=True):
                bus_num = st.text_input("Bus Plate Number").upper().strip()
                route = st.text_input("Route Assignment Name")
                km = st.number_input("Total Route Distance (KM)", min_value=0.0, step=1.0)
                emi = st.number_input("Fixed Monthly EMI (₹)", min_value=0.0, step=500.0)
                ins_exp = st.date_input("Insurance Expiry Date", datetime.now()).strftime("%Y-%m-%d")
                fit_exp = st.date_input("Fitness Certificate Expiry", datetime.now()).strftime("%Y-%m-%d")
                submit_bus = st.form_submit_button("Save Vehicle Asset")
                
                if submit_bus and bus_num:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT OR REPLACE INTO buses VALUES (?, ?, ?, ?, ?, ?)", (bus_num, route, km, emi, ins_exp, fit_exp))
                    conn.commit()
                    conn.close()
                    st.success(f"Bus {bus_num} saved successfully!")
                    st.rerun()

    with col2:
        st.subheader("Active Registered Fleet Ledger")
        if not df_buses.empty:
            st.dataframe(df_buses, use_container_width=True)
        else:
            st.info("No buses added yet.")

# =========================================================
# MODULE 2: DAILY ENTRY LOGS
# =========================================================
elif choice == "🧑‍🔧 Daily Entry Logs":
    st.header("Daily Entry Operations Terminal")
    
    conn = get_db_connection()
    buses_list = [row[0] for row in conn.execute("SELECT bus_number FROM buses").fetchall()]
    conn.close()
    
    if not buses_list:
        st.warning("Please add buses in the management tab first!")
    else:
        with st.form("daily_log_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                log_date = st.date_input("Transaction Date", datetime.now()).strftime("%Y-%m-%d")
                selected_bus = st.selectbox("Select Bus Unit", buses_list)
                earnings = st.number_input("Gross Collections/Ticket Sales (₹)", min_value=0.0)
                penalty = st.number_input("Route Penalties / Fines (₹)", min_value=0.0)
            with c2:
                start_odo = st.number_input("Odometer Start Reading (KM)", min_value=0.0)
                end_odo = st.number_input("Odometer End Reading (KM)", min_value=0.0)
                d_liters = st.number_input("Diesel Refueled (Liters)", min_value=0.0)
            with c3:
                d_rate = st.number_input("Diesel Rate (₹/Liter)", min_value=0.0)
                def_cost = st.number_input("Urea / DEF Costs (₹)", min_value=0.0)
                selected_cat = st.selectbox("Custom Expense Type", expense_categories)
                custom_cost = st.number_input("Custom Expense Amount (₹)", min_value=0.0)
                
            submit_log = st.form_submit_button("Commit Daily Record Entry")
            
            if submit_log:
                if end_odo < start_odo and end_odo > 0:
                    st.error("End Odometer cannot be less than Start Odometer.")
                else:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("""INSERT INTO daily_ops (date, bus_number, start_odometer, end_odometer, diesel_liters, diesel_rate, def_cost, expense_type, custom_expense_cost, earnings, penalty) 
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                              (log_date, selected_bus, start_odo, end_odo, d_liters, d_rate, def_cost, selected_cat, custom_cost, earnings, penalty))
                    conn.commit()
                    conn.close()
                    st.success("Log successfully appended to database!")

# =========================================================
# MODULE 3: STAFF PAYROLL ENGINE
# =========================================================
elif choice == "👥 Staff Payroll Engine":
    st.header("Staff Management & Settlement Control Matrix")
    tab1, tab2 = st.tabs(["Add Employee Profile", "Log Attendance & Track Advances"])
    
    with tab1:
        col1, col2 = st.columns([1, 2])
        with col1:
            st.subheader("New Entry")
            with st.form("staff_form", clear_on_submit=True):
                s_name = st.text_input("Employee Name").title().strip()
                s_role = st.selectbox("Position Type", ["Driver", "Conductor", "Helper/Mechanic"])
                s_wage = st.number_input("Fixed Daily Wage Sheet Rate (₹)", min_value=0.0, step=50.0)
                submit_staff = st.form_submit_button("Save Profile")
                if submit_staff and s_name:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO staff (name, role, daily_wage) VALUES (?, ?, ?)", (s_name, s_role, s_wage))
                    conn.commit()
                    conn.close()
                    st.success(f"Profile saved.")
                    st.rerun()
        with col2:
            st.subheader("Active Master Employee Roll Call")
            conn = get_db_connection()
            df_staff = pd.read_sql_query("SELECT * FROM staff", conn)
            conn.close()
            if not df_staff.empty:
                st.dataframe(df_staff, use_container_width=True)

    with tab2:
        target_month = st.selectbox("Payroll Working Period", ["Jan-2026", "Feb-2026", "Mar-2026", "Apr-2026", "May-2026", "Jun-2026", "Jul-2026", "Aug-2026", "Sep-2026", "Oct-2026", "Nov-2026", "Dec-2026"], index=5)
        
        conn = get_db_connection()
        staff_data = conn.execute("SELECT id, name, role, daily_wage FROM staff").fetchall()
        
        payroll_report = []
        for s_id, name, role, wage in staff_data:
            c = conn.cursor()
            record = c.execute("SELECT days_worked, advance_received FROM payroll_logs WHERE staff_id=? AND month_year=?", (s_id, target_month)).fetchone()
            current_days = record[0] if record else 0
            current_advance = record[1] if record else 0.0
            gross = current_days * wage
            net_due = gross - current_advance
            
            payroll_report.append({
                "Employee Name": name, "Role": role, "Daily Wage (₹)": wage,
                "Days Worked": current_days, "Gross Earned (₹)": gross,
                "Advances Paid (₹)": current_advance, "Balance Due (₹)": net_due
            })
            
            with st.expander(f"👤 {name} ({role})"):
                ec1, ec2, ec3, ec4 = st.columns(4)
                with ec1:
                    new_days = st.number_input("Days Worked", min_value=0, max_value=31, value=int(current_days), key=f"days_{s_id}")
                with ec2:
                    add_advance = st.number_input("Add Advance Paid Amount (₹)", min_value=0.0, step=100.0, key=f"adv_{s_id}")
                with ec3:
                    st.metric("Gross Payroll", f"₹{new_days * wage:,}")
                with ec4:
                    st.metric("Net Balance Due", f"₹{(new_days * wage) - (current_advance + add_advance):,}")
                
                if st.button(f"Save Record Update for {name}", key=f"btn_{s_id}"):
                    c.execute("INSERT OR REPLACE INTO payroll_logs (id, month_year, staff_id, days_worked, advance_received) VALUES ((SELECT id FROM payroll_logs WHERE staff_id=? AND month_year=?), ?, ?, ?, ?)",
                              (s_id, target_month, target_month, s_id, new_days, current_advance + add_advance))
                    conn.commit()
                    st.success("Ledger balance computed!")
                    st.rerun()
        conn.close()
        
        if payroll_report:
            st.markdown("---")
            st.subheader("📥 Export Payroll Accounts")
            df_pay_report = pd.DataFrame(payroll_report)
            csv_pay = df_pay_report.to_csv(index=False).encode('utf-8')
            st.download_button("Download Monthly Payroll Spreadsheet (CSV)", data=csv_pay, file_name=f"payroll_{target_month}.csv", mime='text/csv')

# =========================================================
# MODULE 4: ANALYTICS & THEFT DETECTION ENGINE
# =========================================================
elif choice == "📊 Dashboard & Analytics":
    st.header("Global Operational Control & Theft Audit Center")
    
    conn = get_db_connection()
    df_ops = pd.read_sql_query("SELECT * FROM daily_ops", conn)
    df_buses = pd.read_sql_query("SELECT * FROM buses", conn)
    conn.close()
    
    if df_ops.empty:
        st.info("Awaiting tracking records to process metrics.")
    else:
        df_ops['diesel_cost'] = df_ops['diesel_liters'] * df_ops['diesel_rate']
        df_ops['total_expenses'] = df_ops['diesel_cost'] + df_ops['def_cost'] + df_ops['custom_expense_cost'] + df_ops['penalty']
        
        st.subheader("Global Fleet Overview Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Gross Income", f"₹{df_ops['earnings'].sum():,}")
        m2.metric("Total Expenses Deducted", f"₹{df_ops['total_expenses'].sum():,}")
        m3.metric("Net Margin Yield", f"₹{(df_ops['earnings'].sum() - df_ops['total_expenses'].sum()):,}")
        m4.metric("Total Diesel Burned", f"{df_ops['diesel_liters'].sum():,} Ltrs")
        
        st.markdown("---")
        st.subheader("🚨 Real-time Mileage Efficiency Alerts (Theft/Anomaly Tracker)")
        
        bus_perf = []
        for _, bus in df_buses.iterrows():
            b_num = bus['bus_number']
            b_emi = bus['monthly_emi']
            b_logs = df_ops[df_ops['bus_number'] == b_num]
            
            total_km_travelled = 0.0
            mileage = 0.0
            for _, log in b_logs.iterrows():
                if log['end_odometer'] > log['start_odometer']:
                    total_km_travelled += (log['end_odometer'] - log['start_odometer'])
            
            total_liters = b_logs['diesel_liters'].sum()
            if total_liters > 0:
                mileage = total_km_travelled / total_liters
                
            # Fixed warning logic to avoid false positives on fresh entries
            if 0 < mileage < 3.5: 
                st.warning(f"⚠️ Low Fuel Mileage Anomaly on Bus {b_num}! Yielding only {mileage:.2f} KM/L. Inspect for diesel leaks, structural engine wear, or potential fuel theft.")
            
            earnings = b_logs['earnings'].sum()
            diesel = b_logs['diesel_cost'].sum()
            def_c = b_logs['def_cost'].sum()
            custom_exp_total = b_logs['custom_expense_cost'].sum()
            penalties = b_logs['penalty'].sum()
            total_cost = diesel + def_c + custom_exp_total + penalties + b_emi
            
            bus_perf.append({
                "Bus Identification": b_num, "Assigned Route": bus['route_name'],
                "Distance Driven (KM)": total_km_travelled, "Avg Mileage (KM/L)": round(mileage, 2),
                "Revenue (₹)": earnings, "Total Expenses (₹)": total_cost, "P&L Spread (₹)": earnings - total_cost
            })
            
        st.markdown("---")
        st.subheader("Granular Individual Bus Analytics Matrix")
        df_perf = pd.DataFrame(bus_perf)
        st.dataframe(df_perf, use_container_width=True)
        
        csv_fleet = df_perf.to_csv(index=False).encode('utf-8')
        st.download_button("Download Global Fleet Performance Report (CSV)", data=csv_fleet, file_name="fleet_performance.csv", mime='text/csv')

# =========================================================
# MODULE 5: COMPLIANCE MONITOR
# =========================================================
elif choice == "📋 Compliance & Expiries":
    st.header("Document Compliance & Regulatory Monitor")
    
    conn = get_db_connection()
    df_buses = pd.read_sql_query("SELECT bus_number, route_name, insurance_expiry, fitness_expiry FROM buses", conn)
    conn.close()
    
    if df_buses.empty:
        st.info("No vehicles registered to run compliance scans on.")
    else:
        st.subheader("Current Compliance Timeline Status")
        today_str = datetime.now().strftime("%Y-%m-%d")
        today = datetime.strptime(today_str, "%Y-%m-%d")
        
        compliance_data = []
        for _, row in df_buses.iterrows():
            ins_date = datetime.strptime(row['insurance_expiry'], "%Y-%m-%d")
            fit_date = datetime.strptime(row['fitness_expiry'], "%Y-%m-%d")
            
            ins_status = "✅ Active" if ins_date >= today else "🚨 EXPIRED"
            fit_status = "✅ Active" if fit_date >= today else "🚨 EXPIRED"
            
            if ins_status == "🚨 EXPIRED":
                st.error(f"Critical Action Required: Insurance for Bus **{row['bus_number']}** expired on {row['insurance_expiry']}!")
            if fit_status == "🚨 EXPIRED":
                st.error(f"Critical Action Required: Fitness Certificate for Bus **{row['bus_number']}** expired on {row['fitness_expiry']}!")
                
            compliance_data.append({
                "Bus Identification": row['bus_number'],
                "Insurance Renewal Date": row['insurance_expiry'],
                "Insurance Status": ins_status,
                "Fitness Renewal Date": row['fitness_expiry'],
                "Fitness Status": fit_status
            })
            
        st.table(pd.DataFrame(compliance_data))