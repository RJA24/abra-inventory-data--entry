import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- PAGE CONFIG ---
st.set_page_config(page_title="Abra PHO | Secure Data Entry", layout="wide", page_icon="🔐")

# --- UI HEADER ---
st.title("🔐 Secure Data Entry Portal")
st.markdown("Update live inventory vials here. Changes will instantly reflect on the main Command Center.")
st.warning("⚠️ **SECURITY NOTICE:** Do not share this link. Editing this grid permanently alters the Google Sheet database.")

# --- CONNECT TO DATABASE (NO CACHING) ---
# We use ttl=0 here so it ALWAYS pulls the freshest data for you to edit
conn = st.connection("gsheets", type=GSheetsConnection)

with st.spinner("Connecting to secure database..."):
    try:
        raw_df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1CYarF3POk_UYyXxff2jj-k803nfBA8nhghQ-9OAz0Y4",
            worksheet="PHYSICAL INVENTORY1",
            header=None,
            ttl=0 
        )
    except Exception as e:
        st.error(f"🚨 Connection Failed. Check your Google credentials: {e}")
        st.stop()

# --- PARSE THE MATRIX FOR EDITING ---
vaccines = pd.Series(raw_df.iloc[0, 2:]).ffill().values 
lots = raw_df.iloc[2, 2:].values

# Isolate the actual grid where the numbers live
grid_df = raw_df.iloc[4:, 1:].copy()

# Create highly readable column headers (Vaccine Name + Lot Number)
editor_cols = ['Health Facility']
for i in range(len(vaccines)):
    editor_cols.append(f"{vaccines[i]} (Lot: {lots[i]})")
    
grid_df.columns = editor_cols

# Remove completely empty rows to keep the editor clean
grid_df = grid_df.dropna(subset=['Health Facility'])
grid_df = grid_df[~grid_df['Health Facility'].astype(str).str.contains('TOTAL|EXPIRING|MONTHS', case=False, na=False)]

st.markdown("---")
st.info("💡 **HOW TO USE:** Click any cell below to update the vial count. Press **Enter** to confirm the cell, then click the **Save Updates** button at the bottom.")

# --- THE INTERACTIVE EDITOR ---
edited_df = st.data_editor(
    grid_df,
    use_container_width=True,
    num_rows="dynamic", # Allows you to add a new facility if one opens!
    height=600
)

st.markdown("---")

# --- SAVE ENGINE ---
if st.button("💾 Save Updates to Database", type="primary", use_container_width=True):
    with st.spinner("Encrypting and writing to Google Sheets..."):
        try:
            # Create a copy of the raw sheet to inject the new numbers into
            new_raw = raw_df.copy()
            
            start_row = 4
            start_col = 1
            
            # Loop through the edited grid and update the exact coordinates in the raw sheet
            for i in range(len(edited_df)):
                row_idx = start_row + i
                
                # If you added a new row at the bottom, expand the raw dataframe
                if row_idx >= len(new_raw):
                    new_row = pd.Series([None] * len(new_raw.columns))
                    new_raw.loc[row_idx] = new_row
                    
                # Write the Facility Name
                new_raw.iat[row_idx, 1] = edited_df.iloc[i, 0]
                
                # Write the Vials
                for j in range(len(vaccines)):
                    new_raw.iat[row_idx, 2+j] = edited_df.iloc[i, 1+j]
            
            # Send the payload back to Google Sheets
            conn.update(worksheet="PHYSICAL INVENTORY1", data=new_raw)
            
            st.success("✅ Database successfully overwritten! The Command Center is now live with your new data.")
            st.balloons()
            
        except Exception as e:
            st.error(f"🚨 Failed to save. Please check your Google Service Account Editor permissions. Error: {e}")
