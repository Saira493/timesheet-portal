import streamlit as st
import mysql.connector
import pandas as pd
import holidays
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Timesheet Portal", page_icon="📅", layout="wide")

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
        return True, "Weekend Shift"  # Set to True so manually inputted weekend days calculate correctly
        
    uk_holidays = holidays.UnitedKingdom(subdiv='England', years=dt.year)
    if dt in uk_holidays:
        return False, f"Bank Holiday ({uk_holidays.get(dt)})"
        
    return True, "Payable Workday"

# --- SESSION STATE INITIALIZATION ---
if "current_role" not in st.session_state:
    st.session_state.current_role = "NONE"

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
            st.image("logo.png", width="stretch")
            
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
       
        st.markdown("### 📅 Add Your Worked Shifts")
        
        locations_list = [
            "Select the Location", "Al-Khair Foundation", "Al-Khair Schools", 
            "BizAv Media Ltd", "Saks London", "Photocopiers Direct", 
            "EVA International", "Fidelis College", "IQRA ELM", "Heretoga", 
            "Tarbiya", "Clarity Housing", "Collfin", "Leicester Islamic Academy", 
            "Marathon School", "Suffah Primary School", "Vestro Marketing", "UIKAM", 
            "Other (Type Below)"
        ]
        
        # --- PRIMARY SHIFT BLOCK ---
        selected_dropdown = st.selectbox("📍 Select Your Work Location Site:", options=locations_list, key="primary_loc")
        
        final_location = ""
        if selected_dropdown == "Other (Type Below)":
            final_location = st.text_input("✏️ Type Your Custom Work Location Site:", value="", key="primary_custom").strip()
        else:
            final_location = selected_dropdown
        
        st.write("📅 **Select Date Range Worked:**")
        date_range = st.date_input(
            "Click to choose start and end dates:",
            value=[datetime.now().date(), datetime.now().date() + timedelta(days=2)],
            key="bulk_date"
        )
        
        # --- ADDITIONAL SHIFT BLOCK (IN A SINGLE LINE BELOW) ---
        st.markdown("---")
        
        # Using a checkbox to keep the optional extra workspace clean
        has_additional = st.checkbox("➕ Add an extra location and date range", value=False)
        
        final_additional_location = ""
        additional_date_range = None
        
        if has_additional:
            st.markdown("#### **Additional Shift Block**")
            # Create a 2-column layout to place Location and Dates side-by-side
            add_col1, add_col2 = st.columns(2)
            
            with add_col1:
                additional_dropdown = st.selectbox("📍 Select Additional Work Location:", options=locations_list, key="add_loc")
                if additional_dropdown == "Other (Type Below)":
                    final_additional_location = st.text_input("✏️ Type Custom Additional Location:", value="", key="add_custom").strip()
                else:
                    final_additional_location = additional_dropdown
                    
            with add_col2:
                additional_date_range = st.date_input(
                    "📅 Select Additional Date Range Worked:",
                    value=[datetime.now().date(), datetime.now().date() + timedelta(days=2)],
                    key="add_date"
                )
        
        st.markdown("---")

        if st.button("Process & Submit Timesheet", type="primary", width="stretch"):
            if not employee_name.strip() or employee_name == "Enter your name":
                st.error("⚠️ Please fill in your name.")
            elif selected_dropdown == "Select the Location":
                st.error("⚠️ Please select a valid primary work location.")
            elif selected_dropdown == "Other (Type Below)" and not final_location:
                st.error("⚠️ Please type your custom primary location name in the text box.")
            elif not date_range or (isinstance(date_range, list) and len(date_range) == 0):
                st.warning("ℹ️ Please select at least one date for your primary range.")
            # Validation steps for the optional field if active
            elif has_additional and additional_dropdown == "Select the Location":
                st.error("⚠️ Please select a valid location for your additional shift block.")
            elif has_additional and additional_dropdown == "Other (Type Below)" and not final_additional_location:
                st.error("⚠️ Please type your custom additional location name in the text box.")
            elif has_additional and (not additional_date_range or (isinstance(additional_date_range, list) and len(additional_date_range) == 0)):
                st.warning("ℹ️ Please select at least one date for your additional range.")
            else:
                # --- 1. Process Primary Range (Handles both 1 date and 2 date selections safely) ---
            if isinstance(date_range, (list, tuple)):
                if len(date_range) == 2:
                    start_date, end_date = date_range[0], date_range[1]
                elif len(date_range) == 1:
                    start_date = date_range[0]
                    end_date = start_date
                else:
                    st.error("⚠️ Please select a valid date range.")
                    st.stop()
            else:
                start_date = date_range
                end_date = start_date

                
                # Generate dates
                delta = end_date - start_date
                generated_dates = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
                
                                
                # --- 2. Process Additional Range if selected ---
                # --- 2. ✅ SAFE PROCESS ADDITIONAL RANGE ---

                additional_dates = []
                
                if has_additional:
                    if additional_date_range is None:
                        st.error("⚠️ No additional dates selected.")
                        st.stop()
                
                    # Convert to list
                    if not isinstance(additional_date_range, list):
                        additional_date_range = [additional_date_range]

                    # Extract safely
                    if len(additional_date_range) == 1:
                        add_start = additional_date_range[0]
                        add_end = additional_date_range[0]
                    elif len(additional_date_range) == 2:
                        add_start, add_end = additional_date_range
                    else:
                        st.error("⚠️ Invalid additional date selection.")
                        st.stop()

                # Final safety
                if not add_start or not add_end:
                    st.error("⚠️ Additional dates missing.")
                    st.stop()
            
                add_delta = add_end - add_start
                additional_dates = [add_start + timedelta(days=i) for i in range(add_delta.days + 1)]
                            
                # --- 3. Database Insertion ---
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        success_count = 0
                        
                        # Process Main Date Range (Skips weekends automatically)
                        for single_date in generated_dates:
                            if single_date.weekday() in [5, 6]:
                                continue
                                
                            query = """
                            INSERT INTO daily_records (employee_name, work_date, location)
                            VALUES (%s, %s, %s)
                            ON DUPLICATE KEY UPDATE location = VALUES(location);
                            """
                            cursor.execute(query, (employee_name.strip(), single_date, final_location))
                            success_count += 1
                            
                        # Process Additional Date Range if active (Skips weekends automatically)
                        if has_additional:
                            for single_date in additional_dates:
                                if single_date.weekday() in [5, 6]:
                                    continue
                                    
                                query = """
                                INSERT INTO daily_records (employee_name, work_date, location)
                                VALUES (%s, %s, %s)
                                ON DUPLICATE KEY UPDATE location = VALUES(location);
                                """
                                cursor.execute(query, (employee_name.strip(), single_date, final_additional_location))
                                success_count += 1
                                
                        conn.commit()
                        st.success(f"🎉 Successfully logged {success_count} total days for {employee_name} into your live data pools!")
                        st.balloons()
                    except mysql.connector.Error as err:
                        st.error(f"❌ Database error: {err}")
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
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)
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
                        st.dataframe(audit_display_df, use_container_width=True, hide_index=True)
