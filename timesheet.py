import streamlit as st
import mysql.connector
import pandas as pd
import holidays
from datetime import datetime, timedelta, time

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
        return True, "Weekend Shift"
        
    uk_holidays = holidays.UnitedKingdom(subdiv='England', years=dt.year)
    if dt in uk_holidays:
        return False, f"Bank Holiday ({uk_holidays.get(dt)})"
        
    return True, "Payable Workday"

# --- HELPER TO CLEAN AND FORMAT TIME VALUES ---
def format_time_string(val):
    if pd.isna(val) or val is None or str(val).strip() == "" or "NULL" in str(val).upper():
        return "-"
    
    val_str = str(val).strip().lower()
    val_str = val_str.replace("0 days", "").replace("hours", "").replace("hour", "").strip()
    
    try:
        if ":" in val_str:
            parts = val_str.split(":")
            hr = int(parts[0])
            mn = int(parts[1])
            return f"{hr:02d}:{mn:02d}"
        else:
            hr = int(float(val_str))
            return f"{hr:02d}:00"
    except ValueError:
        return str(val).strip()

# --- VERIFY CREDENTIALS VIA DATABASE ---
def verify_login(email, password, expected_role):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT role, full_name FROM users WHERE email = %s AND password = %s AND role = %s"
            cursor.execute(query, (email.strip().lower(), password, expected_role))
            user = cursor.fetchone()
            return user
        except mysql.connector.Error as err:
            st.error(f"⚠️ Login lookup failure: {err}")
        finally:
            cursor.close()
            conn.close()
    return None

# --- SESSION STATE INITIALIZATION ---
if "auth_status" not in st.session_state:
    st.session_state.auth_status = False

if "current_role" not in st.session_state:
    st.session_state.current_role = "NONE"

if "logged_user_name" not in st.session_state:
    st.session_state.logged_user_name = ""

if "extra_shifts_count" not in st.session_state:
    st.session_state.extra_shifts_count = 0

if "holiday_days_count" not in st.session_state:
    st.session_state.holiday_days_count = 0


# ==========================================
# SCREEN 1: IDENTITY SETUP (HOME SCREEN)
# ==========================================
if st.session_state.current_role == "NONE" and not st.session_state.auth_status:
    left_space, center_card, right_space = st.columns([1, 2, 1])
    
    with center_card:
        st.write("")
        st.write("")
        col_img_left, col_img_center, col_img_right = st.columns([1, 2, 1])
        with col_img_center:
            st.image("logo.png", use_container_width=True)
            
        st.write("")
        st.write("")
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown("### 🛡️")
            with col2:
                st.markdown("**Manager Workspace**")
                st.markdown("<span style='color: gray; font-size: 14px;'>View employee records, hours split, and payroll summaries.</span>", unsafe_allow_html=True)
            
            if st.button("Select as Manager", key="btn_manager", use_container_width=True):
                st.session_state.current_role = "MANAGER_LOGIN"
                st.rerun()

        st.write("")

        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown("### 👤")
            with col2:
                st.markdown("**Employee Workspace**")
                st.markdown("<span style='color: gray; font-size: 14px;'>Log your daily work locations and submit timesheets seamlessly.</span>", unsafe_allow_html=True)
                
            if st.button("Select as Employee", key="btn_emp", use_container_width=True):
                st.session_state.current_role = "EMPLOYEE_LOGIN"
                st.rerun()

# ==========================================
# SCREEN 2: AUTHENTICATION GATE (SIGN-IN SCREEN)
# ==========================================
elif "_LOGIN" in st.session_state.current_role and not st.session_state.auth_status:
    target_role = "MANAGER" if "MANAGER" in st.session_state.current_role else "EMPLOYEE"
    
    left_space, center_card, right_space = st.columns([1, 1.5, 1])
    with center_card:
        st.write("")
        col_img_left, col_img_center, col_img_right = st.columns([1, 2, 1])
        with col_img_center:
            st.image("logo.png", use_container_width=True)
            
        st.write("")
        with st.form("login_gateway_form", clear_on_submit=False):
            st.markdown(f"### 🔐 {target_role.title()} Secure Sign-In")
            input_email = st.text_input("📧 Email Address:", placeholder="name@company.com")
            input_password = st.text_input("🔑 Password:", type="password", placeholder="••••••••")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit_login = st.form_submit_button("Authenticate & Log In", type="primary", use_container_width=True)
            with col_btn2:
                go_back = st.form_submit_button("↩️ Cancel & Go Back", use_container_width=True)
            
            if submit_login:
                if not input_email or not input_password:
                    st.error("⚠️ Please fill out both email and password fields.")
                else:
                    user_record = verify_login(input_email, input_password, target_role)
                    if user_record:
                        st.session_state.auth_status = True
                        st.session_state.current_role = user_record['role']
                        st.session_state.logged_user_name = user_record['full_name']
                        st.success(f"🔓 Access Granted. Welcome, {user_record['full_name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ Invalid credentials for a {target_role.title()} account.")
            
            if go_back:
                st.session_state.current_role = "NONE"
                st.rerun()

# ==========================================
# SCREEN 3: EMPLOYEE TIMESHEET WORKSPACE
# ==========================================
elif st.session_state.auth_status and st.session_state.current_role == "EMPLOYEE":
    left_space, center_content, right_space = st.columns([1, 3, 1])
    
    with center_content:
        col_title, col_logout = st.columns([4, 1])
        with col_title:
            st.title("📝 Employee Entry Workspace")
            st.caption(f"👤 Connected User Profile: **{st.session_state.logged_user_name}**")
        with col_logout:
            if st.button("🚪 Log Out", use_container_width=True, type="secondary"):
                st.session_state.auth_status = False
                st.session_state.current_role = "NONE"
                st.session_state.logged_user_name = ""
                st.rerun()
                
        st.markdown("---")
        employee_name = st.text_input("👤 Your Registered Work Name:", value=st.session_state.logged_user_name, disabled=True)
       
        st.markdown("### 📅 Add Your Worked Shifts")
        locations_list = [
            "Select the Location", "Al-Khair Foundation", "Al-Khair Schools", 
            "BizAv Media Ltd", "Saks London", "Photocopiers Direct", 
            "EVA International", "Fidelis College", "IQRA ELM", "Heretoga", 
            "Tarbiya", "Clarity Housing", "Collfin", "Leicester Islamic Academy", 
            "Marathon School", "Suffah Primary School", "Vestro Marketing", "UIKAM"
        ]
        
        st.markdown("#### **Primary Bulk Shift Block (Optional)**")
        selected_dropdown = st.selectbox("📍 Select Your Main Work Location Site:", options=locations_list, key="primary_loc")
        
        p_col1, p_col2, p_col3 = st.columns([2, 1, 1])
        with p_col1:
            st.write("📅 **Select Primary Date Range Worked:**")
            date_range = st.date_input(
                "Click to choose start and end dates:",
                value=[datetime.now().date(), datetime.now().date() + timedelta(days=2)],
                key="bulk_date"
            )
        with p_col2:
            st.write("⏰ **Start Time:**")
            p_start = st.time_input("Start", value=time(9, 0), key="p_start_time", label_visibility="collapsed")
        with p_col3:
            st.write("⏰ **End Time:**")
            p_end = st.time_input("End", value=time(17, 0), key="p_end_time", label_visibility="collapsed")
        
        st.markdown("---")
        st.markdown("#### **Holiday / DayOff (Optional)**")
        
        holiday_dates_selected = []
        for h in range(st.session_state.holiday_days_count):
            h_col1, h_col2 = st.columns([2, 2])
            with h_col1:
                h_date = st.date_input(f"Select Holiday Date #{h+1}:", value=datetime.now().date(), key=f"holiday_date_{h}")
                holiday_dates_selected.append(h_date)
        
        h_act1, h_act2 = st.columns([1, 2])
        with h_act1:
            if st.button("➕ Add Another Holiday Date", use_container_width=True):
                st.session_state.holiday_days_count += 1
                st.rerun()
        with h_act2:
            if st.session_state.holiday_days_count > 0:
                if st.button("🗑️ Clear Last Holiday Row", key="clear_h_btn", type="secondary"):
                    st.session_state.holiday_days_count -= 1
                    st.rerun()

        st.markdown("---")
        st.markdown("#### **Additional Individual Shifts**")
        
        extra_locations_selected = []
        extra_dates_selected = []
        extra_start_times = []
        extra_end_times = []
        
        for i in range(st.session_state.extra_shifts_count):
            st.markdown(f"##### **Extra Shift Entry #{i+1}**")
            add_col1, add_col2, add_col3, add_col4 = st.columns([2, 2, 1, 1])
            
            with add_col1:
                loc_entry = st.selectbox(f"Select Location for Shift #{i+1}:", options=locations_list, key=f"extra_loc_{i}")
                extra_locations_selected.append(loc_entry)
            with add_col2:
                date_entry = st.date_input(f"Select Single Date for Shift #{i+1}:", value=datetime.now().date(), key=f"extra_date_{i}")
                extra_dates_selected.append(date_entry)
            with add_col3:
                t_start = st.time_input(f"Start Time #{i+1}:", value=time(9, 0), key=f"extra_start_{i}")
                extra_start_times.append(t_start)
            with add_col4:
                t_end = st.time_input(f"End Time #{i+1}:", value=time(17, 0), key=f"extra_end_{i}")
                extra_end_times.append(t_end)
        
        act_col1, act_col2 = st.columns([1, 2])
        with act_col1:
            if st.button("➕ Add Another Single-Shift Location", use_container_width=True):
                st.session_state.extra_shifts_count += 1
                st.rerun()
        with act_col2:
            if st.session_state.extra_shifts_count > 0:
                if st.button("🗑️ Clear Last Additional Entry Row", type="secondary"):
                    st.session_state.extra_shifts_count -= 1
                    st.rerun()
        
        st.markdown("---")

        if st.button("Process & Submit Timesheet", type="primary", use_container_width=True):
            has_errors = False
            primary_is_active = (selected_dropdown != "Select the Location")
            
            if not primary_is_active and st.session_state.extra_shifts_count == 0 and st.session_state.holiday_days_count == 0:
                st.error("⚠️ Please choose a primary location, add a holiday date, or use an additional shift row.")
                has_errors = True
                
            for idx, loc_check in enumerate(extra_locations_selected):
                if loc_check == "Select the Location":
                    st.error(f"⚠️ Please choose a valid work site location for extra entry row #{idx+1}.")
                    has_errors = True
            
            if not has_errors:
                generated_dates = []
                if primary_is_active:
                    if isinstance(date_range, (list, tuple)):
                        if len(date_range) == 2:
                            start_date, end_date = date_range[0], date_range[1]
                        elif len(date_range) == 1:
                            start_date = date_range[0]
                            end_date = start_date
                    else:
                        start_date = date_range
                        end_date = start_date

                    delta = end_date - start_date
                    generated_dates = [start_date + timedelta(days=i) for i in range(delta.days + 1)]
                
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        success_count = 0
                        
                        if primary_is_active:
                            for single_date in generated_dates:
                                if single_date.weekday() in [5, 6]:
                                    continue
                                query = """
                                INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time)
                                VALUES (%s, %s, %s, %s, %s);
                                """
                                cursor.execute(query, (employee_name.strip(), single_date, selected_dropdown, p_start.strftime("%H:%M"), p_end.strftime("%H:%M")))
                                success_count += 1
                        
                        for h_date in holiday_dates_selected:
                            query = """
                            INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time)
                            VALUES (%s, %s, %s, NULL, NULL);
                            """
                            cursor.execute(query, (employee_name.strip(), h_date, "Holidays (Day off)"))
                            success_count += 1
                            
                        for idx in range(len(extra_locations_selected)):
                            chosen_loc = extra_locations_selected[idx]
                            chosen_date = extra_dates_selected[idx]
                            c_start = extra_start_times[idx]
                            c_end = extra_end_times[idx]
                            query = """
                            INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time)
                            VALUES (%s, %s, %s, %s, %s);
                            """
                            cursor.execute(query, (employee_name.strip(), chosen_date, chosen_loc, c_start.strftime("%H:%M"), c_end.strftime("%H:%M")))
                            success_count += 1
                                
                        conn.commit()
                        st.success(f"🎉 Timesheet submitted completely! Saved {success_count} entries.")
                        st.balloons()
                        
                        st.session_state.extra_shifts_count = 0
                        st.session_state.holiday_days_count = 0
                        st.rerun()
                        
                    except mysql.connector.Error as err:
                        st.error(f"❌ Database error: {err}")
                    finally:
                        cursor.close()
                        conn.close()

# ==========================================
# SCREEN 4: MANAGEMENT DASHBOARD WORKSPACE
# ==========================================
elif st.session_state.auth_status and st.session_state.current_role == "MANAGER":
    col_title, col_logout = st.columns([5, 1])
    with col_title:
        st.title("💼 Management Dashboard")
        st.subheader("UK Multi-Site Operations Overview & Payroll Audit")
    with col_logout:
        if st.button("🚪 Log Out", use_container_width=True, type="secondary"):
            st.session_state.auth_status = False
            st.session_state.current_role = "NONE"
            st.session_state.logged_user_name = ""
            st.rerun()
            
    st.markdown("---")
    
    records = []
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT employee_name, work_date, location, start_time, end_time FROM daily_records ORDER BY work_date DESC, start_time ASC")
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
        
        df['start_time'] = df['start_time'].apply(format_time_string)
        df['end_time'] = df['end_time'].apply(format_time_string)
        
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
            filtered_df = df[(df['employee_name'] == selected_emp) & (df['Month_Year'] == selected_month)].copy()
            
            work_payable_df = filtered_df[(filtered_df['Is Payable'] == True) & (filtered_df['location'] != "Holidays (Day off)")]
            holiday_df = filtered_df[filtered_df['location'] == "Holidays (Day off)"]
            
            total_days_logged = filtered_df['work_date'].nunique()
            total_payable_days = work_payable_df['work_date'].nunique()
            total_holiday_days = holiday_df['work_date'].nunique()
            total_excluded_days = max(0, total_days_logged - total_payable_days - total_holiday_days)
            
            st.markdown(f"### 📊 Breakdown for {selected_emp} during **{selected_month}**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📅 Total Days Logged", f"{total_days_logged} Days")
            m2.metric("💰 Approved Payable Days", f"{total_payable_days} Days")
            m3.metric("🏖️ Holidays / Days Off", f"{total_holiday_days} Days")
            m4.metric("🛑 Excluded (Weekends / Bank Holidays)", f"{total_excluded_days} Days")
            
            st.write("")
            st.markdown("#### **Approved Payroll Summary Table (Site Overview)**")
            summary_df = filtered_df.groupby('location').agg({'work_date': 'count'}).reset_index()
            summary_df.columns = ['UK Work Location Site / Status', 'Total Shift Entries Logged']
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
                
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download This Filtered Report to CSV",
                data=csv,
                file_name=f"payroll_{selected_emp.replace(' ', '_')}_{selected_month.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            st.write("")
            with st.expander("🔍 In-Depth Shift Audit Log (Detailed Shift Windows)", expanded=True):
                audit_display_df = filtered_df[['work_date', 'location', 'start_time', 'end_time', 'Day Categorization']].copy()
                audit_display_df.columns = ['Calendar Date', 'Location Site / Status', 'Start Time', 'End Time', 'Payroll Classification']
                st.dataframe(audit_display_df, use_container_width=True, hide_index=True)
