import streamlit as st
import pandas as pd
import json
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="🏦 Complete Finance Tool", layout="wide")

# ==================== STYLING ====================
st.markdown("""
    <style>
    .main-header { font-size: 2rem; color: #1E88E5; text-align: center; padding: 1rem; background: #f0f2f6; border-radius: 10px; }
    .bank-format { background: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 5px solid #1E88E5; margin: 10px 0; }
    .stButton>button { width: 100%; background-color: #1E88E5; color: white; font-weight: bold; border-radius: 8px; }
    .stButton>button:hover { background-color: #1565C0; color: white; }
    </style>
""", unsafe_allow_html=True)

# ==================== DATABASE ====================
conn = sqlite3.connect('finance.db', check_same_thread=False)
c = conn.cursor()

# Assets Table
c.execute('''CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, category TEXT, cost REAL, purchase_date TEXT,
    wdv REAL, rate REAL, dep REAL, closing REAL, fy TEXT
)''')

# Transactions Table
c.execute('''CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT, type TEXT, party TEXT, amount REAL, mode TEXT, category TEXT
)''')

# Project Data Table
c.execute('''CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, fy TEXT, sales REAL, purchases REAL, expenses REAL,
    other_income REAL, interest REAL, dep REAL, net_profit REAL
)''')

conn.commit()

# ==================== DEPRECIATION RATES (Income Tax Act) ====================
DEP_RATES = {
    "Building (Residential)": 5,
    "Building (Commercial)": 10,
    "Plant & Machinery": 15,
    "Plant (New)": 15,
    "Furniture & Fittings": 10,
    "Computer & Software": 40,
    "Laptop": 40,
    "Vehicle (Car)": 15,
    "Vehicle (Commercial)": 15,
    "Office Equipment": 10,
    "Intangible Assets": 25,
    "Goodwill": 25,
    "Patents": 25,
    "Trademarks": 25,
}

# ==================== CALCULATIONS ====================
class FinanceCalc:
    def calc_depreciation(self, name, wdv, rate=None):
        if rate is None:
            rate = DEP_RATES.get(name, 15) / 100
        dep = wdv * rate
        closing = wdv - dep
        return {'dep': round(dep, 2), 'closing': round(closing, 2), 'rate': round(rate * 100, 2)}
    
    def calc_emi(self, principal, rate, tenure):
        r = rate / 12 / 100
        emi = principal * r * ((1+r)**(tenure*12)) / (((1+r)**(tenure*12)) - 1)
        return {'emi': round(emi, 2), 'total': round(emi*tenure*12, 2), 'interest': round(emi*tenure*12 - principal, 2)}
    
    def calc_mpbf(self, ca, cl):
        wc = ca - cl
        mpbf = wc * 0.75
        return {'wc': round(wc, 2), 'mpbf': round(mpbf, 2), 'own': round(wc - mpbf, 2)}
    
    def calc_ratios(self, data):
        ratios = {}
        # Current Ratio
        if data.get('cl', 0) > 0:
            ratios['Current Ratio'] = round(data.get('ca', 0) / data.get('cl', 0), 2)
        # Quick Ratio
        if data.get('cl', 0) > 0:
            quick = (data.get('ca', 0) - data.get('inventory', 0)) / data.get('cl', 0)
            ratios['Quick Ratio'] = round(quick, 2)
        # Debt/Equity
        equity = data.get('capital', 0) + data.get('reserves', 0)
        if equity > 0:
            ratios['Debt/Equity'] = round(data.get('loans', 0) / equity, 2)
        # Gross Profit Margin
        if data.get('sales', 0) > 0:
            ratios['Gross Profit Margin'] = round((data.get('gp', 0) / data.get('sales', 0)) * 100, 2)
        # Net Profit Margin
        if data.get('sales', 0) > 0:
            ratios['Net Profit Margin'] = round((data.get('net_profit', 0) / data.get('sales', 0)) * 100, 2)
        # ROCE
        if data.get('total_assets', 0) > 0:
            ratios['ROCE'] = round((data.get('net_profit', 0) / data.get('total_assets', 0)) * 100, 2)
        # Interest Coverage
        if data.get('interest', 0) > 0:
            ratios['Interest Coverage'] = round((data.get('net_profit', 0) + data.get('interest', 0) + data.get('dep', 0)) / data.get('interest', 0), 2)
        return ratios

calc = FinanceCalc()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/accounting.png", width=70)
    st.title("🏦 Finance Tool")
    
    # Year Selector
    years = ['2023-24', '2024-25', '2025-26', '2026-27']
    selected_fy = st.selectbox("📅 Financial Year", years, index=2)
    
    pages = {
        "🏠 Dashboard": "dash",
        "📦 Assets Register": "assets",
        "📒 Balance Sheet": "bs",
        "📈 P&L Statement": "pnl",
        "📊 CMA Data": "cma",
        "📋 Project Report": "project",
        "📉 Depreciation": "dep",
        "💳 Payment/Receipt": "pr",
        "⚙️ Settings": "settings"
    }
    
    page = st.radio("📌 Menu", list(pages.keys()))
    page_key = pages[page]

# ==================== PAGE: DASHBOARD ====================
if page_key == "dash":
    st.markdown('<div class="main-header">🏠 Dashboard</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Get total assets
    c.execute("SELECT COUNT(*), SUM(cost), SUM(closing) FROM assets WHERE fy=?", (selected_fy,))
    asset_count, total_cost, total_wdv = c.fetchone()
    if total_cost is None: total_cost = 0
    if total_wdv is None: total_wdv = 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Assets", asset_count if asset_count else 0)
    col2.metric("💰 Total Cost", f"₹{total_cost:,.2f}")
    col3.metric("📉 Total WDV", f"₹{total_wdv:,.2f}")
    col4.metric("📅 FY", selected_fy)
    
    # Asset Chart
    if asset_count and asset_count > 0:
        df = pd.read_sql_query("SELECT name, cost, closing FROM assets WHERE fy=?", conn, params=(selected_fy,))
        if not df.empty:
            fig = px.bar(df, x='name', y=['cost', 'closing'], title="Asset Summary", barmode='group')
            st.plotly_chart(fig, use_container_width=True)

# ==================== PAGE: ASSETS REGISTER ====================
elif page_key == "assets":
    st.markdown('<div class="main-header">📦 ASSETS REGISTER</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.info("📌 Add multiple assets. Depreciation automatically calculated as per Income Tax Act.")
    
    # Add Asset Form
    with st.expander("➕ Add New Asset", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            asset_name = st.selectbox("Asset Name", list(DEP_RATES.keys()))
        with col2:
            cost = st.number_input("Purchase Cost (₹)", value=100000.0, step=10000.0, min_value=0.0)
        with col3:
            purchase_date = st.date_input("Purchase Date", datetime.now())
        
        col1, col2 = st.columns(2)
        with col1:
            wdv = st.number_input("Opening WDV (₹)", value=cost * 0.8, step=10000.0, min_value=0.0)
        with col2:
            rate = DEP_RATES.get(asset_name, 15)
            st.metric("Depreciation Rate", f"{rate}%")
        
        if st.button("➕ Add Asset", use_container_width=True):
            if cost > 0 and wdv > 0:
                result = calc.calc_depreciation(asset_name, wdv)
                c.execute("""INSERT INTO assets (name, category, cost, purchase_date, wdv, rate, dep, closing, fy)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (asset_name, "Fixed Asset", cost, purchase_date.strftime('%Y-%m-%d'),
                          wdv, result['rate'], result['dep'], result['closing'], selected_fy))
                conn.commit()
                st.success(f"✅ Asset Added! Depreciation: ₹{result['dep']:,.2f} | Closing WDV: ₹{result['closing']:,.2f}")
                st.balloons()
    
    # Show existing assets
    st.markdown("---")
    st.subheader("📋 Asset Register")
    
    df = pd.read_sql_query("SELECT id, name, cost, purchase_date, wdv, rate, dep, closing FROM assets WHERE fy=? ORDER BY id DESC", 
                           conn, params=(selected_fy,))
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Summary
        total_cost = df['cost'].sum()
        total_dep = df['dep'].sum()
        total_closing = df['closing'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Cost", f"₹{total_cost:,.2f}")
        col2.metric("Total Depreciation", f"₹{total_dep:,.2f}")
        col3.metric("Total WDV", f"₹{total_closing:,.2f}")
        
        # Delete option
        if st.button("🗑️ Delete Selected Asset", use_container_width=True):
            # Show delete dropdown
            asset_list = df['id'].tolist()
            # We'll use a simple approach - just delete last
            # Better: use session state for selection
            st.warning("Click on specific asset to delete (coming soon)")
    else:
        st.info("No assets added for this financial year")

# ==================== PAGE: BALANCE SHEET ====================
elif page_key == "bs":
    st.markdown('<div class="main-header">📒 BALANCE SHEET</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Get assets data
    c.execute("SELECT SUM(cost), SUM(closing) FROM assets WHERE fy=?", (selected_fy,))
    total_cost, total_wdv = c.fetchone()
    if total_cost is None: total_cost = 0
    if total_wdv is None: total_wdv = 0
    
    with st.expander("📥 Enter Data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💎 Assets")
            cash = st.number_input("Cash", 100000.0, step=10000.0)
            bank = st.number_input("Bank", 500000.0, step=10000.0)
            debtors = st.number_input("Debtors", 200000.0, step=10000.0)
            inventory = st.number_input("Inventory", 300000.0, step=10000.0)
            investments = st.number_input("Investments", 100000.0, step=10000.0)
            # Fixed Assets from register
            fixed_assets = total_wdv
            st.metric("Fixed Assets (WDV)", f"₹{fixed_assets:,.2f}")
            total_assets = cash + bank + debtors + inventory + investments + fixed_assets
        
        with col2:
            st.subheader("📋 Liabilities")
            creditors = st.number_input("Creditors", 150000.0, step=10000.0)
            loans = st.number_input("Long Term Loans", 500000.0, step=10000.0)
            capital = st.number_input("Capital", 1000000.0, step=10000.0)
            reserves = st.number_input("Reserves", 200000.0, step=10000.0)
            total_liabilities = creditors + loans + capital + reserves
    
    if st.button("📊 Generate Balance Sheet", use_container_width=True):
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Assets", f"₹{total_assets:,.2f}")
        col2.metric("Total Liabilities", f"₹{total_liabilities:,.2f}")
        diff = total_assets - total_liabilities
        col3.metric("Difference", f"₹{diff:,.2f}", "Balanced ✅" if abs(diff) < 1 else "Check ⚠️")
        
        # Detailed Balance Sheet
        st.subheader("📄 Detailed Balance Sheet")
        bs_data = pd.DataFrame({
            'Particulars': [
                '**ASSETS**', 'Cash', 'Bank', 'Debtors', 'Inventory', 'Investments', 
                'Fixed Assets (WDV)', '**Total Assets**',
                '', '**LIABILITIES**', 'Creditors', 'Long Term Loans', 
                'Capital', 'Reserves', '**Total Liabilities**'
            ],
            'Amount': [
                '', cash, bank, debtors, inventory, investments, fixed_assets, total_assets,
                '', '', creditors, loans, capital, reserves, total_liabilities
            ]
        })
        st.dataframe(bs_data, use_container_width=True, hide_index=True)

# ==================== PAGE: P&L ====================
elif page_key == "pnl":
    st.markdown('<div class="main-header">📈 PROFIT & LOSS STATEMENT</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Get depreciation from assets
    c.execute("SELECT SUM(dep) FROM assets WHERE fy=?", (selected_fy,))
    total_dep = c.fetchone()[0]
    if total_dep is None: total_dep = 0
    
    with st.expander("📥 Enter Data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💰 Income")
            revenue = st.number_input("Revenue", 1200000.0, step=100000.0)
            other_income = st.number_input("Other Income", 50000.0, step=10000.0)
        with col2:
            st.subheader("💸 Expenses")
            cogs = st.number_input("COGS", 700000.0, step=10000.0)
            salaries = st.number_input("Salaries", 200000.0, step=10000.0)
            rent = st.number_input("Rent", 50000.0, step=10000.0)
            admin = st.number_input("Admin Expenses", 30000.0, step=10000.0)
            interest = st.number_input("Interest", 30000.0, step=10000.0)
            # Depreciation from assets
            depreciation = total_dep
            st.metric("Depreciation (Auto)", f"₹{depreciation:,.2f}")
    
    if st.button("📊 Generate P&L", use_container_width=True):
        st.markdown("---")
        
        total_income = revenue + other_income
        total_expenses = cogs + salaries + rent + admin + interest + depreciation
        gross_profit = revenue - cogs
        net_profit = total_income - total_expenses
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Income", f"₹{total_income:,.2f}")
        col2.metric("Total Expenses", f"₹{total_expenses:,.2f}")
        col3.metric("Gross Profit", f"₹{gross_profit:,.2f}")
        col4.metric("Net Profit", f"₹{net_profit:,.2f}", "Profit ✅" if net_profit > 0 else "Loss ❌")
        
        # Detailed P&L
        pnl_data = pd.DataFrame({
            'Particulars': [
                '**INCOME**', 'Revenue', 'Other Income', '**Total Income**',
                '', '**EXPENSES**', 'COGS', 'Salaries', 'Rent', 
                'Admin Expenses', 'Interest', 'Depreciation', '**Total Expenses**',
                '', '**Gross Profit**', '**Net Profit**'
            ],
            'Amount': [
                '', revenue, other_income, total_income,
                '', '', cogs, salaries, rent, admin, interest, depreciation, total_expenses,
                '', gross_profit, net_profit
            ]
        })
        st.dataframe(pnl_data, use_container_width=True, hide_index=True)

# ==================== PAGE: CMA DATA ====================
elif page_key == "cma":
    st.markdown('<div class="main-header">📊 CMA DATA - BANK FORMAT</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("📥 Enter Data", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Operating Statement")
            sales = st.number_input("Sales", 1200000.0, step=100000.0)
            gp = st.number_input("Gross Profit", 500000.0, step=100000.0)
            op_exp = st.number_input("Operating Expenses", 250000.0, step=10000.0)
            interest = st.number_input("Interest", 30000.0, step=10000.0)
            dep = st.number_input("Depreciation", 20000.0, step=10000.0)
            net_profit = gp - op_exp - interest - dep
        
        with col2:
            st.subheader("Balance Sheet")
            ca = st.number_input("Current Assets", 500000.0, step=100000.0)
            cl = st.number_input("Current Liabilities", 300000.0, step=100000.0)
            inventory = st.number_input("Inventory", 150000.0, step=10000.0)
            loans = st.number_input("Long Term Loans", 500000.0, step=100000.0)
            capital = st.number_input("Capital", 800000.0, step=100000.0)
            reserves = st.number_input("Reserves", 200000.0, step=100000.0)
            fixed_assets = st.number_input("Fixed Assets", 800000.0, step=100000.0)
            total_assets = ca + fixed_assets
    
    if st.button("📊 Generate CMA Report", use_container_width=True):
        st.markdown("---")
        
        # Calculate
        mpbf_data = calc.calc_mpbf(ca, cl)
        ratios = calc.calc_ratios({
            'ca': ca, 'cl': cl, 'inventory': inventory, 'loans': loans,
            'capital': capital, 'reserves': reserves, 'sales': sales,
            'gp': gp, 'net_profit': net_profit, 'total_assets': total_assets,
            'interest': interest, 'dep': dep
        })
        
        st.markdown('<div class="bank-format">', unsafe_allow_html=True)
        st.subheader("📄 1. OPERATING STATEMENT")
        op_data = pd.DataFrame({
            'Particulars': ['Sales', 'Gross Profit', 'Operating Exp', 'Interest', 'Depreciation', 'Net Profit'],
            'Amount': [f"₹{sales:,.2f}", f"₹{gp:,.2f}", f"₹{op_exp:,.2f}", 
                      f"₹{interest:,.2f}", f"₹{dep:,.2f}", f"₹{net_profit:,.2f}"]
        })
        st.dataframe(op_data, use_container_width=True, hide_index=True)
        
        st.subheader("📄 2. MPBF CALCULATION")
        mpbf_df = pd.DataFrame({
            'Particulars': ['Working Capital', 'MPBF (75%)', 'Own Funds'],
            'Amount': [f"₹{mpbf_data['wc']:,.2f}", f"₹{mpbf_data['mpbf']:,.2f}", f"₹{mpbf_data['own']:,.2f}"]
        })
        st.dataframe(mpbf_df, use_container_width=True, hide_index=True)
        
        st.subheader("📄 3. RATIO ANALYSIS")
        ratio_df = pd.DataFrame({
            'Ratio': list(ratios.keys()),
            'Value': [str(v) for v in ratios.values()]
        })
        st.dataframe(ratio_df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ==================== PAGE: PROJECT REPORT ====================
elif page_key == "project":
    st.markdown('<div class="main-header">📋 PROJECT REPORT</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("📥 Enter Project Details", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Project Name", "New Project")
            total_cost = st.number_input("Total Project Cost", 5000000.0, step=100000.0)
            own_funds = st.number_input("Own Funds", 1000000.0, step=100000.0)
            sales = st.number_input("Estimated Sales", 1500000.0, step=100000.0)
            purchases = st.number_input("Estimated Purchases", 800000.0, step=100000.0)
        with col2:
            expenses = st.number_input("Operating Expenses", 300000.0, step=10000.0)
            other_income = st.number_input("Other Income", 50000.0, step=10000.0)
            interest_rate = st.number_input("Loan Interest Rate (%)", 10.5, step=0.5)
            tenure = st.number_input("Loan Tenure (Years)", 5, min_value=1, max_value=20)
            net_profit = sales - purchases - expenses + other_income
    
    if st.button("📊 Generate Project Report", use_container_width=True):
        st.markdown("---")
        
        loan = total_cost - own_funds
        emi_data = calc.calc_emi(loan, interest_rate, tenure)
        
        st.markdown('<div class="bank-format">', unsafe_allow_html=True)
        st.subheader("📄 1. PROJECT SUMMARY")
        summary = pd.DataFrame({
            'Particulars': ['Project Name', 'Total Cost', 'Own Funds', 'Bank Loan', 'Tenure', 'Interest Rate'],
            'Details': [project_name, f"₹{total_cost:,.2f}", f"₹{own_funds:,.2f}", 
                       f"₹{loan:,.2f}", f"{tenure} Years", f"{interest_rate}%"]
        })
        st.dataframe(summary, use_container_width=True, hide_index=True)
        
        st.subheader("📄 2. EMI DETAILS")
        emi_df = pd.DataFrame({
            'Particulars': ['Monthly EMI', 'Total Payment', 'Total Interest'],
            'Amount': [f"₹{emi_data['emi']:,.2f}", f"₹{emi_data['total']:,.2f}", f"₹{emi_data['interest']:,.2f}"]
        })
        st.dataframe(emi_df, use_container_width=True, hide_index=True)
        
        st.subheader("📄 3. PROJ