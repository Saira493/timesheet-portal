import streamlit as st
import mysql.connector
import pandas as pd
import holidays
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Timesheet Portal", page_icon="📅", layout="wide")

# --- CUSTOM CSS FOR PROFESSIONAL LOOK & GREEN BUTTON ---
st.markdown("""
    <style>
    /* Turn Streamlit Primary Buttons Green */
    div.stButton > button[kind="primary"] {
        background-color: #2e7d32 !important;
        color: white !important;
        border-color: #1b5e20 !important;
        font-weight: bold;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1b5e20 !important;
        border-color: #1b5e20 !important;
    }
    /* Style metrics for professional look */
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION FUNCTION ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["db_host"],
            port=int(st.secrets["db_port"]),
            user=st.secrets["db_user"],
            password=st.secrets["db_password"],
            database=st.secrets["db_name"]
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"❌ Database Connection Error: {err}")
        return None

# --- PAYROLL FILTER HELPERS ---
def calculate_billable_status(input_date):
    if isinstance(input_date, str):
        dt = datetime.strptime(input_date, "%Y-%m-%d").date()
    elif isinstance(input_date, datetime):
        dt = input_date.date()
    else:
        dt = input_date

    if dt.weekday() in [5, 6]:
        return True, "Weekend Shift"  # Allowed and treated as payable since employee explicitly added it manually
        
    uk_holidays = holidays.UnitedKingdom(subdiv='England', years=dt.year)
    if dt in uk_holidays:
        return False, f"Bank Holiday ({uk_holidays.get(dt)})"
        
    return True, "Payable Workday"

# --- SESSION STATE INITIALIZATION ---
if "current_role" not in st.session_state:
    st.session_state.current_role = "NONE"
if "shift_batch" not in st.session_state:
    st.session_state.shift_batch = []

# ==========================================
# SCREEN 1: IDENTITY SETUP (HOME SCREEN)
# ==========================================
if st.session_state.current_role == "NONE":
    left_space, center_card, right_space = st.columns([1, 2, 1])
    
    with center_card:
        st.write("")
        st.write("")
        
        col_img_left, col_img_center, col_img_right = st.columns([1, 2, 1])
        with col_img_center:
            try:
                st.image("logo.png", width="stretch")
            except Exception:
                st.markdown("<h2 style='text-align: center; color: #2e7d32; margin-bottom:0;'>iTEA SOLUTIONS</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; font-style: italic; color: gray;'>We've got IT covered</p>", unsafe_allow_html=True)
            
        st.write("")
        st.write("")
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown("### 🛡️")
            with col2:
                st.markdown("**Manager**")
                st.markdown("<span style='color: gray; font-size: 14px;'>View all employee records, counts, and payroll audit tracking pages.</span>", unsafe_allow_html=True)
            
            if st.button("Select as Manager", key="btn_manager", width="stretch"):
                st.session_state.current_role = "MANAGER"
                st.rerun()

        st.write("")

        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown("### 👤")
            with col2:
                st.markdown("**Employee**")
                st.markdown("<span style='color: gray; font-size: 14px;'>Log your daily work locations and submit timesheets seamlessly.</span>", unsafe_allow_html=True)
                
            if st.button("Select as Employee", key="btn_emp", width="stretch"):
                st.session_state.current_role = "EMPLOYEE"
                st.rerun()

# ==========================================
# SCREEN 2: EMPLOYEE TIMESHEET FORM
# ==========================================
elif st.session_state.current_role == "EMPLOYEE":
    left_space, center_content, right_space = st.columns([1, 3, 1])
    
    with center_content:
        col_title, col_logout = st.columns([4, 1])
        with col_title:
            st.title("📝 Employee Entry Workspace")
        with col_logout:
            if st.button("↩️ Change Role", width="stretch"):
                st.session_state.current_role = "NONE"
                st.rerun()
                
        st.markdown("---")
        
        employee_name = st.text_input("👤 Your Full Name:", value="Enter your name")
        
        locations_list = [
            "Select the Location", "Al-Khair Foundation", "Al-Khair Schools", 
            "BizAv Media Ltd", "Saks London", "Photocopiers Direct", 
            "EVA International", "Fidelis College", "IQRA ELM", "Heretoga", 
            "Tarbiya", "Clarity Housing", "Collfin", "Leicester Islamic Academy", 
            "Marathon School", "Suffah Primary School", "Vestro Marketing", "UIKAM",
            "Other (Type Below)"
        ]
        
        # ---------------------------------------------------------
        # MAIN SECTION: BULK DATE RANGE ENTRY (AUTOMATICALLY SKIPS WEEKENDS)
        # ---------------------------------------------------------
        st.markdown("### 📅 1. Bulk Date Range Entry")
        st.caption("Select your main date range. Weekends (Saturdays & Sundays) will be automatically skipped.")
        
        bulk_loc_dropdown = st.selectbox("📍 Select Location for Range:", options=locations_list, key="bulk_loc")
        
        final_bulk_loc = ""
        if bulk_loc_dropdown == "Other (Type Below)":
            final_bulk_loc = st.text_input("✏️ Type Your Custom Location for Range:", value="", key="bulk_custom_text").strip()
        else:
            final_bulk_loc = bulk_loc_dropdown

        date_range = st.date_input(
            "Click to choose start and end dates:",
            value=[datetime.now().date(), datetime.now().date() + timedelta(days=2)],
            key="bulk_date"
        )
        
        if st.button("➕ Add Range to Batch", key="add_bulk_btn", width="stretch"):
            if bulk_loc_dropdown == "Select the Location" or (bulk_loc_dropdown == "Other (Type Below)" and not final_bulk_loc):
                st.error("⚠️ Please select or type a valid work location site.")
            elif not isinstance(date_range, list) or len(date_range) != 2:
                st.warning("ℹ️ Please select both a Start Date and an End Date on the calendar.")
            else:
                start_date, end_date = date_range[0], date_range[1]
                delta = end_date - start_date
                added_counter = 0
                
                for i in range(delta.days + 1):
                    current_day = start_date + timedelta(days=i)
                    
                    # STRICT RULE: Automatically skip Saturdays (5) and Sundays (6)
                    if current_day.weekday() in [5, 6]:
                        continue
                        
                    # Add to batch, overwrite if duplicate date exists
                    st.session_state.shift_batch = [d for d in st.session_state.shift_batch if d['date'] != current_day]
                    st.session_state.shift_batch.append({'date': current_day, 'location': final_bulk_loc})
                    added_counter += 1
                    
                st.toast(f"✅ Automatically skipped weekends and added {added_counter} weekdays to your batch!")

        st.markdown("---")

        # ---------------------------------------------------------
        # EXTRA SECTION: INDIVIDUAL SHIFT BUILDER (ALLOWS WEEKENDS MANUAL ENTRY)
        # ---------------------------------------------------------
        st.markdown("### ➕ 2. Add Extra Individual Shifts (Weekends / Extra Days)")
        st.caption("Use this section to manually add individual extra shifts. Saturdays, Sundays, and any specific custom dates are allowed here.")
        
        col_date, col_loc = st.columns(2)
        with col_date:
            single_date = st.date_input("Choose Specific Date Worked:", value=datetime.now().date(), key="single_date_picker")
        with col_loc:
            single_loc_dropdown = st.selectbox("Assign Location to This Specific Date:", options=locations_list, key="single_loc")
            
        final_single_loc = ""
        if single_loc_dropdown == "Other (Type Below)":
            final_single_loc = st.text_input("✏️ Type Your Custom Location for This Specific Date:", value="", key="single_custom_text").strip()
        else:
            final_single_loc = single_loc_dropdown
            
        if st.button("➕ Add Extra Individual Shift to Batch", key="add_single_btn", width="stretch"):
            if single_loc_dropdown == "Select the Location" or (single_loc_dropdown == "Other (Type Below)" and not final_single_loc):
                st.error("⚠️ Please assign a valid location for this specific date entry.")
            else:
                # Add individual custom selection to batch (can be added as much as they want)
                st.session_state.shift_batch = [d for d in st.session_state.shift_batch if d['date'] != single_date]
                st.session_state.shift_batch.append({'date': single_date, 'location': final_single_loc})
                st.toast(f"✅ Manually added shift for {single_date} at {final_single_loc}!")

        st.markdown("---")
        st.markdown("### 📋 Your Pending Submission Batch")
        
        # --- RENDER BATCH ENTRIES WITH DYNAMIC DELETE LOGIC ---
        if not st.session_state.shift_batch:
            st.info("Your current batch list is empty. Add shifts using the range entry or extra individual entry sections above.")
        else:
            # Sort chronologically so it reads naturally
            st.session_state.shift_batch = sorted(st.session_state.shift_batch, key=lambda x: x['date'])
            
            for idx, item in enumerate(st.session_state.shift_batch):
                day_name = item['date'].strftime('%A')
                
                # Visual callout to clearly flag manual weekend entries to the employee
                if item['date'].weekday() in [5, 6]:
                    display_text = f"⭐ **{item['date']} ({day_name}) [Weekend Shift]** — Site: *{item['location']}*"
                else:
                    display_text = f"🔹 {item['date']} ({day_name}) — Site: *{item['location']}*"
                
                col_display, col_del = st.columns([5, 1])
                with col_display:
                    st.markdown(display_text)
                with col_del:
                    if st.button("❌ Delete", key=f"del_{idx}_{item['date']}", width="stretch"):
                        st.session_state.shift_batch.pop(idx)
                        st.rerun()
                        
            st.write("")
            
            # --- FINAL SUBMIT TO LIVE DATABASE ---
            if st.button("🚀 Process & Submit All Batched Shifts", type="primary", width="stretch"):
                if not employee_name.strip() or employee_name == "Enter your name":
                    st.error("⚠️ Please enter your Full Name before submitting.")
                else:
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            success_count = 0
                            
                            for item in st.session_state.shift_batch:
                                query = """
                                INSERT INTO daily_records (employee_name, work_date, location)
                                VALUES (%s, %s, %s)
                                ON DUPLICATE KEY UPDATE location = VALUES(location);
                                """
                                cursor.execute(query, (employee_name.strip(), item['date'], item['location']))
                                success_count += 1
                                
                            conn.commit()
                            st.success(f"🎉 Successfully logged {success_count} shifts into your database for {employee_name}!")
                            st.balloons()
                            st.session_state.shift_batch = []  # Clear batch array buffer on success
                            st.rerun()
                        except mysql.connector.Error as err:
                            st.error(f"❌ Database error encountered: {err}")
                        finally:
                            cursor.close()
                            conn.close()

# ==========================================
# SCREEN 3: THE BOSS MONITORING DASHBOARD
# ==========================================
elif st.session_state.current_role == "MANAGER":
    col_title, col_logout = st.columns([5, 1])
    with col_title:
        st.title("💼 Management Dashboard")
        st.subheader("UK Multi-Site Operations Overview & Payroll Audit")
    with col_logout:
        if st.button("↩️ Change Role", width="stretch"):
            st.session_state.current_role = "NONE"
            st.rerun()
            
    st.markdown("---")
    
    records = []
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT employee_name, work_date, location FROM daily_records ORDER BY work_date DESC")
            records = cursor.fetchall()
        except mysql.connector.Error as err:
            st.error(f"⚠️ Could not pull entries table: {err}")
        finally:
            cursor.close()
            conn.close()
            
    if not records:
        st.info("📂 No logged timesheets found in your live database tables yet.")
    else:
        df = pd.DataFrame(records)
        df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        df['Month_Year'] = pd.to_datetime(df['work_date']).dt.strftime('%B %Y')
        
        status_results = df['work_date'].apply(calculate_billable_status)
        df['Is Payable'] = [res[0] for res in status_results]
        df['Day Categorization'] = [res[1] for res in status_results]
        
        st.markdown("### 🔍 Filter Work Records")
        filter_col1, filter_col2 = st.columns(2)
        
        with filter_col1:
            unique_employees = sorted(list(df['employee_name'].unique()))
            selected_emp = st.selectbox("1. Select an Employee:", unique_employees)
            
        with filter_col2:
            emp_months = df[df['employee_name'] == selected_emp]['Month_Year'].unique()
            selected_month = st.selectbox("2. Choose Pay-Period Month:", sorted(list(emp_months)))
            
        st.markdown("---")
        
        if selected_emp and selected_month:
            filtered_df = df[(df['employee_name'] == selected_emp) & (df['Month_Year'] == selected_month)]
            payable_df = filtered_df[filtered_df['Is Payable'] == True]
            
            summary_df = payable_df.groupby('location').size().reset_index(name='Payable Days')
            summary_df.columns = ['UK Work Location Site', 'Total Days Owed Pay']
            
            total_days_logged = len(filtered_df)
            total_payable_days = summary_df['Total Days Owed Pay'].sum()
            total_excluded_days = total_days_logged - total_payable_days
            
            st.markdown(f"### 📊 Breakdown for {selected_emp} during **{selected_month}**")
            m1, m2, m3 = st.columns(3)
            m1.metric("📅 Total Days Logged", f"{total_days_logged} Days")
            m2.metric("💰 Approved Payable Days", f"{total_payable_days} Days")
            m3.metric("🛑 Excluded (Weekends / Holidays)", f"{total_excluded_days} Days")
            
            st.write("")
            
            st.markdown("#### **Approved Payroll Summary Table**")
            if not summary_df.empty:
                st.dataframe(summary_df, width="stretch", hide_index=True)
            else:
                st.warning(f"This staff user has 0 payable days within the selection parameter month.")
                
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download This Filtered Report to CSV",
                data=csv,
                file_name=f"payroll_{selected_emp.replace(' ', '_')}_{selected_month.replace(' ', '_')}.csv",
                mime="text/csv",
                width="stretch"
            )
            
            st.write("")
            
            with st.expander("🔍 In-Depth Shift Audit Log (View Classification Breakdown)"):
                audit_display_df = filtered_df[['work_date', 'location', 'Day Categorization', 'Is Payable']].copy()
                audit_display_df.columns = ['Calendar Date', 'Location Site', 'Payroll Classification', 'Paid Status']
                st.dataframe(audit_display_df, width="stretch", hide_index=True)
