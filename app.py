import streamlit as st
import pandas as pd
from fpdf import FPDF
import os
import sys

# Add the app directory to path so we can import our component
sys.path.insert(0, os.path.dirname(__file__))
from barcode_scanner_component import barcode_scanner

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Store Scan & Print", page_icon="📦", layout="centered")
st.title("📦 Store Scan & POP Print App")

# ─── 1. LOAD DATA ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=10)
def load_data():
    file_path = "Data.xlsx"
    if not os.path.exists(file_path):
        st.error(f"❌ '{file_path}' file nahi mili!")
        return None
    try:
        df_ean = pd.read_excel(file_path, sheet_name="EAN")
        df_ean.columns = [c.strip().lower() for c in df_ean.columns]

        df_stock = pd.read_excel(file_path, sheet_name="Stock And Rate")
        df_stock.columns = [c.strip().lower() for c in df_stock.columns]

        required_ean   = {'item code', 'eancode'}
        required_stock = {'item code'}
        if not required_ean.issubset(df_ean.columns) or not required_stock.issubset(df_stock.columns):
            st.error("❌ Excel columns match nahi ho rahe! Columns check karein.")
            return None

        df_ean['item code']   = df_ean['item code'].astype(str).str.strip()
        df_ean['eancode']     = df_ean['eancode'].astype(str).str.strip()
        df_stock['item code'] = df_stock['item code'].astype(str).str.strip()

        return pd.merge(df_stock, df_ean[['item code', 'eancode']], on='item code', how='left')

    except Exception as e:
        st.error(f"❌ Excel read karne me galti: {e}")
        return None

inventory_data = load_data()
if inventory_data is None:
    st.stop()

# ─── 2. STORE SELECTION ───────────────────────────────────────────────────────
st.sidebar.header("🏪 Store Settings")
if 'outlet name' in inventory_data.columns:
    unique_stores = inventory_data['outlet name'].dropna().unique().tolist()
    selected_store = st.sidebar.selectbox("Apna Store Chunein:", unique_stores)
    filtered_df = inventory_data[inventory_data['outlet name'] == selected_store]
else:
    selected_store = "All Stores"
    filtered_df = inventory_data

st.sidebar.success(f"✅ {selected_store} ({len(filtered_df)} Items)")

# ─── 3. BARCODE SCANNER ───────────────────────────────────────────────────────
st.subheader("📷 Live Barcode Scanner")
st.caption("Camera se barcode scan karein — result automatically neeche aa jayega.")

# This now WORKS: uses declare_component so JS→Python communication is proper
camera_result = barcode_scanner(key="main_scanner")

# Manual / gun scanner fallback
manual_input = st.text_input(
    "Ya yahan barcode manually type/paste karein:",
    value="",
    placeholder="e.g. 8901234567890",
    key="manual_barcode"
)

# Priority: camera scan > manual input
scanned_input = ""
if camera_result:
    scanned_input = str(camera_result).strip()
    st.success(f"📷 Camera se scanned: **{scanned_input}**")
elif manual_input.strip():
    scanned_input = manual_input.strip()

# ─── 4. PRODUCT LOOKUP ────────────────────────────────────────────────────────
if scanned_input:
    product_rows = filtered_df[
        (filtered_df['eancode'] == scanned_input) |
        (filtered_df['item code'] == scanned_input)
    ]

    if not product_rows.empty:
        st.subheader("📋 Product Details")

        for index, row in product_rows.iterrows():
            item_name     = str(row.get('item name', 'Unknown')).title()
            selling_rate  = float(row['selling'])
            mrp_rate      = float(row['mrp']) if 'mrp' in filtered_df.columns else selling_rate
            current_stock = row.get('current stk.', 'N/A')
            item_code_val = row['item code']
            savings       = mrp_rate - selling_rate

            st.markdown(f"""
            <div style="background:#f0f2f6; padding:15px; border-radius:10px;
                        border-left:5px solid #2ecc71; margin-bottom:15px;">
                <h4 style="margin:0; color:#31333f;">📦 {item_name} &nbsp;<small>(Code: {item_code_val})</small></h4>
                <p style="margin:6px 0; font-size:20px; color:#27ae60;">
                    <b>Selling Price: ₹{int(selling_rate)}</b>
                </p>
                <p style="margin:4px 0; font-size:13px; color:#7f8c8d;">
                    MRP: ₹{int(mrp_rate)} &nbsp;|&nbsp; Stock: {current_stock} Pcs
                    {"&nbsp;|&nbsp; 💰 Save ₹" + str(int(savings)) if savings > 0 else ""}
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🖨️ Label Print karein — ₹{int(selling_rate)}"):
                new_rate = st.number_input(
                    "Price (change if needed):",
                    value=selling_rate,
                    step=1.0,
                    key=f"rate_{index}"
                )

                if st.button("📄 Generate POP PDF", key=f"genpdf_{index}", type="primary"):
                    pdf = FPDF(orientation="L", unit="in", format=(3.0, 2.0))
                    pdf.add_page()
                    pdf.set_margins(0.1, 0.1, 0.1)
                    pdf.rect(0.05, 0.05, 2.9, 1.9)

                    # Item name
                    pdf.set_font("Helvetica", style="B", size=11)
                    pdf.cell(0, 0.3, txt=item_name[:28], ln=1, align="C")
                    pdf.ln(0.05)

                    # Big price
                    pdf.set_font("Helvetica", style="B", size=30)
                    pdf.set_text_color(231, 76, 60)
                    pdf.cell(0, 0.5, txt=f"Rs. {int(new_rate)}/-", ln=1, align="C")
                    pdf.set_text_color(0, 0, 0)

                    # Item code
                    pdf.set_font("Helvetica", size=8)
                    pdf.cell(0, 0.2, txt=f"Item Code: {item_code_val}", ln=1, align="C")

                    # MRP / savings line
                    label_save = int(mrp_rate - new_rate)
                    if label_save > 0:
                        pdf.cell(0, 0.2,
                                 txt=f"MRP: Rs.{int(mrp_rate)}  |  Save Rs.{label_save}",
                                 ln=1, align="C")
                    else:
                        pdf.cell(0, 0.2, txt=f"MRP: Rs.{int(mrp_rate)}", ln=1, align="C")

                    pdf_bytes = bytes(pdf.output())
                    st.download_button(
                        label="📥 Download & Print",
                        data=pdf_bytes,
                        file_name=f"POP_{item_code_val}_{int(new_rate)}.pdf",
                        mime="application/pdf",
                        key=f"dl_{index}"
                    )
                    st.balloons()
    else:
        st.error(
            f"❌ **'{scanned_input}'** — yeh code **{selected_store}** ke database me nahi mila!\n\n"
            "Item code ya EAN code check karein."
        )
