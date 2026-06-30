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
            database=st.secrets["db_name"],
            ssl_disabled=False
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

def format_time_string(val):
    if pd.isna(val) or val is None or str(val).strip() == "" or "NULL" in str(val).upper():
        return "-"
    val_str = str(val).strip().lower().replace("0 days", "").strip()
    try:
        if ":" in val_str:
            parts = val_str.split(":")
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        else:
            return f"{int(float(val_str)):02d}:00"
    except ValueError:
        return str(val).strip()

# --- VERIFY CREDENTIALS VIA DATABASE ---
def verify_user_login(email, expected_role):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT id, password, full_name, role FROM users WHERE email = %s AND role = %s"
            cursor.execute(query, (email.strip().lower(), expected_role))
            user = cursor.fetchone()
            return user
        except mysql.connector.Error as err:
            st.error(f"⚠️ Security lookup failure: {err}")
        finally:
            cursor.close()
            conn.close()
    return None

# --- UPDATE PASSWORD IN DATABASE ---
def update_user_password(user_id, new_password):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "UPDATE users SET password = %s WHERE id = %s"
            cursor.execute(query, (new_password, user_id))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            st.error(f"⚠️ Could not save your custom password: {err}")
        finally:
            cursor.close()
            conn.close()
    return False

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

if "force_password_change" not in st.session_state:
    st.session_state.force_password_change = False
if "matched_user_record" not in st.session_state:
    st.session_state.matched_user_record = None

# ==========================================
# SCREEN 1: IDENTITY SETUP (HOME SCREEN)
# ==========================================
if st.session_state.current_role == "NONE" and not st.session_state.auth_status:
    left_space, center_card, right_space = st.columns([1, 2, 1])
    with center_card:
        st.write("")
        col_img_left, col_img_center, col_img_right = st.columns([1, 2, 1])
        with col_img_center:
            st.image("logo.png", use_container_width=True)
            
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1: st.markdown("### 🛡️")
            with col2:
                st.markdown("**Manager Workspace**")
                st.markdown("<span style='color: gray; font-size: 14px;'>View employee records, hours split, and payroll summaries.</span>", unsafe_allow_html=True)
            if st.button("Select as Manager", key="btn_manager", use_container_width=True):
                st.session_state.current_role = "MANAGER_LOGIN"
                st.session_state.force_password_change = False
                st.session_state.matched_user_record = None
                st.rerun()

        st.write("")

        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1: st.markdown("### 👤")
            with col2:
                st.markdown("**Employee Workspace**")
                st.markdown("<span style='color: gray; font-size: 14px;'>Log your daily work locations and submit timesheets seamlessly.</span>", unsafe_allow_html=True)
            if st.button("Select as Employee", key="btn_emp", use_container_width=True):
                st.session_state.current_role = "EMPLOYEE_LOGIN"
                st.session_state.force_password_change = False
                st.session_state.matched_user_record = None
                st.rerun()

# ==========================================
# SCREEN 2: AUTHENTICATION & DEFAULT PASSWORD RESET
# ==========================================
elif "_LOGIN" in st.session_state.current_role and not st.session_state.auth_status:
    target_role = "MANAGER" if "MANAGER" in st.session_state.current_role else "EMPLOYEE"
    
    left_space, center_card, right_space = st.columns([1, 1.5, 1])
    with center_card:
        st.write("")
        with st.container(border=True):
            if not st.session_state.force_password_change:
                st.markdown(f"### 🔐 {target_role.title()} Secure Sign-In")
                with st.form("standard_login_form"):
                    input_email = st.text_input("📧 Email Address:", placeholder="name@company.com")
                    input_password = st.text_input("🔑 Password:", type="password", placeholder="••••••••")
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        submit = st.form_submit_button("Authenticate & Log In", type="primary", use_container_width=True)
                    with col_b2:
                        cancel = st.form_submit_button("↩️ Cancel", use_container_width=True)
                    
                    if submit:
                        user_db = verify_user_login(input_email, target_role)
                        if user_db and user_db['password'] == input_password:
                            if input_password == "admin123":
                                st.session_state.matched_user_record = user_db
                                st.session_state.force_password_change = True
                                st.rerun()
                            else:
                                st.session_state.auth_status = True
                                st.session_state.current_role = user_db['role']
                                st.session_state.logged_user_name = user_db['full_name']
                                st.rerun()
                        else:
                            st.error("❌ Authentication rejected. Double check email/password combinations.")
                    
                    if cancel:
                        st.session_state.current_role = "NONE"
                        st.rerun()

            else:
                st.markdown("### 🔄 Setup Custom Account Password")
                st.warning(f"Hello {st.session_state.matched_user_record['full_name']}. For security reasons, you must change your password from the default 'admin123' configuration.")
                
                with st.form("force_reset_form"):
                    new_pass = st.text_input("🔒 Type New Custom Password:", type="password", placeholder="Choose a new safe password")
                    confirm_pass = st.text_input("🔄 Retype New Password to Verify:", type="password", placeholder="Confirm new password")
                    
                    if st.form_submit_button("Save Account Settings & Access Portal", type="primary", use_container_width=True):
                        if new_pass == "admin123":
                            st.error("⚠️ You cannot reuse the temporary 'admin123' password. Please select a secure custom alternative.")
                        elif len(new_pass) < 4:
                            st.error("⚠️ Your new custom password must be at least 4 characters long.")
                        elif new_pass != confirm_pass:
                            st.error("❌ Confirmation mismatch. Ensure both passwords entered are identical.")
                        else:
                            if update_user_password(st.session_state.matched_user_record['id'], new_pass):
                                st.session_state.auth_status = True
                                st.session_state.current_role = st.session_state.matched_user_record['role']
                                st.session_state.logged_user_name = st.session_state.matched_user_record['full_name']
                                st.session_state.force_password_change = False
                                st.session_state.matched_user_record = None
                                 st.session_state.reset_success = True
                               # st.success("🎉 Custom password set successfully!")
                              #  st.rerun()

elif st.session_state.reset_success:
    left_space, center_card, right_space = st.columns([1, 1.5, 1])
    with center_card:
        st.write("")
        with st.container(border=True):
            st.markdown("### ✅ Password Updated")
            st.success("🎉 Custom password set successfully! Please sign in with your new password.")
            if st.button("🔑 Go to Sign In", type="primary", use_container_width=True):
                st.session_state.reset_success = False
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
            st.caption(f"👤 Connected Profile: **{st.session_state.logged_user_name}**")
        with col_logout:
            if st.button("🚪 Log Out", use_container_width=True):
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
            "Marathon School", "Suffah Primary School", "Vestro Marketing", "Health Care", "SPC Coatings", "UIKAM"
        ]
        
        st.markdown("#### **Primary Bulk Shift Block (Optional)**")
        selected_dropdown = st.selectbox("📍 Select Your Main Work Location Site:", options=locations_list, key="primary_loc")
        p_col1, p_col2, p_col3 = st.columns([2, 1, 1])
        with p_col1:
            date_range = st.date_input("Select Date Range Worked:", value=[datetime.now().date(), datetime.now().date() + timedelta(days=2)])
        with p_col2:
            p_start = st.time_input("Start", value=time(9, 0), key="p_start_time")
        with p_col3:
            p_end = st.time_input("End", value=time(17, 0), key="p_end_time")
        
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
        
        extra_locations_selected, extra_dates_selected, extra_start_times, extra_end_times = [], [], [], []
        for i in range(st.session_state.extra_shifts_count):
            st.markdown(f"##### **Extra Shift Entry #{i+1}**")
            add_col1, add_col2, add_col3, add_col4 = st.columns([2, 2, 1, 1])
            with add_col1:
                extra_locations_selected.append(st.selectbox(f"Location #{i+1}:", options=locations_list, key=f"extra_loc_{i}"))
            with add_col2:
                extra_dates_selected.append(st.date_input(f"Date #{i+1}:", value=datetime.now().date(), key=f"extra_date_{i}"))
            with add_col3:
                extra_start_times.append(st.time_input(f"Start #{i+1}:", value=time(9, 0), key=f"extra_start_{i}"))
            with add_col4:
                extra_end_times.append(st.time_input(f"End #{i+1}:", value=time(17, 0), key=f"extra_end_{i}"))
        
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
            primary_is_active = (selected_dropdown != "Select the Location")
            
            has_errors = False
            if not primary_is_active and st.session_state.extra_shifts_count == 0 and st.session_state.holiday_days_count == 0:
                st.error("⚠️ Please choose a primary location, add a holiday date, or use an additional shift row.")
                has_errors = True
                
            for idx, loc_check in enumerate(extra_locations_selected):
                if loc_check == "Select the Location":
                    st.error(f"⚠️ Please choose a valid work site location for extra entry row #{idx+1}.")
                    has_errors = True
                    
            if not has_errors:
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        success_count = 0
                        
                        if primary_is_active:
                            start_date, end_date = date_range[0], date_range[1] if len(date_range) == 2 else date_range[0]
                            delta = end_date - start_date
                            for i in range(delta.days + 1):
                                single_date = start_date + timedelta(days=i)
                                if single_date.weekday() in [5, 6]: continue  
                                query = "INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time) VALUES (%s, %s, %s, %s, %s)"
                                cursor.execute(query, (employee_name.strip(), single_date, selected_dropdown, p_start.strftime("%H:%M"), p_end.strftime("%H:%M")))
                                success_count += 1
                        
                        for h_date in holiday_dates_selected:
                            query = "INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time) VALUES (%s, %s, %s, NULL, NULL)"
                            cursor.execute(query, (employee_name.strip(), h_date, "Holidays (Day off)"))
                            success_count += 1
                        
                        for idx in range(len(extra_locations_selected)):
                            query = "INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time) VALUES (%s, %s, %s, %s, %s)"
                            cursor.execute(query, (employee_name.strip(), extra_dates_selected[idx], extra_locations_selected[idx], extra_start_times[idx].strftime("%H:%M"), extra_end_times[idx].strftime("%H:%M")))
                            success_count += 1
                                
                        conn.commit()
                        st.success(f"🎉 Timesheet submitted completely! Saved {success_count} entries.")
                        st.balloons()
                        st.session_state.extra_shifts_count = 0
                        st.session_state.holiday_days_count = 0
                      #  st.rerun()
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
        if st.button("🚪 Log Out", use_container_width=True):
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
            cursor.execute("SELECT employee_name, work_date, location, start_time, end_time FROM daily_records ORDER BY work_date DESC")
            records = cursor.fetchall()
        except mysql.connector.Error as err:
            st.error(f"⚠️ Could not pull entries table: {err}")
        finally:
            cursor.close()
            conn.close()
            
    if records:
        df = pd.DataFrame(records)
        df['work_date'] = pd.to_datetime(df['work_date']).dt.date
        df['Month_Year'] = pd.to_datetime(df['work_date']).dt.strftime('%B %Y')
        
        status_results = df['work_date'].apply(calculate_billable_status)
        df['Is Payable'] = [res[0] for res in status_results]
        df['Day Categorization'] = [res[1] for res in status_results]
        
        df['start_time'] = df['start_time'].apply(format_time_string)
        df['end_time'] = df['end_time'].apply(format_time_string)
        
        unique_employees = sorted(list(df['employee_name'].unique()))
        unique_months = sorted(list(df['Month_Year'].unique()), key=lambda x: datetime.strptime(x, "%B %Y"), reverse=True)
        
        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            selected_emp = st.selectbox("👤 Select Employee Profile:", unique_employees)
        with filt_col2:
            selected_month = st.selectbox("📅 Filter by Payroll Month:", unique_months)
            
        f_df = df[(df['employee_name'] == selected_emp) & (df['Month_Year'] == selected_month)].copy()
        
        st.markdown(f"## 📊 Breakdown for {selected_emp} during {selected_month}")
        
        # --- CALCULATE UNIQUE CALENDAR DAYS ---
        total_days = f_df['work_date'].nunique()
        payable_days = f_df[(f_df['Is Payable'] == True) & (f_df['location'] != "Holidays (Day off)")]['work_date'].nunique()
        holiday_days = f_df[f_df['location'] == "Holidays (Day off)"]['work_date'].nunique()
        excluded_days = max(0, total_days - payable_days - holiday_days)
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("📅 Total Unique Days Logged", f"{total_days} Days")
        kpi2.metric("💰 Approved Payable Days", f"{payable_days} Days")
        kpi3.metric("🏖️ Holidays / Days Off", f"{holiday_days} Days")
        kpi4.metric("🛑 Excluded (Weekends / Holidays)", f"{excluded_days} Days")
        
        st.markdown("### Approved Payroll Summary Table (Site Distribution)")
        summary_pivot = f_df.groupby('location').agg(
            Days_Logged=('work_date', 'nunique')
        ).reset_index()
        summary_pivot.columns = ['UK Work Location Site / Status', 'Total Unique Days Worked']
        st.dataframe(summary_pivot, use_container_width=True, hide_index=True)
        
        csv_data = f_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download This Filtered Report to CSV", data=csv_data, file_name=f"Payroll_{selected_emp}_{selected_month.replace(' ', '_')}.csv", mime='text/csv', use_container_width=True)
        
        # --- RESTORED: START TIME & END TIME DISPLAYED WITHOUT SUMMED HOURS ---
        with st.expander("🔍 In-Depth Shift Audit Log (Detailed Shifts Split)", expanded=True):
            audit_display = f_df[['work_date', 'location', 'start_time', 'end_time', 'Day Categorization']].copy()
            audit_display.columns = ['Calendar Date', 'Location Site / Status', 'Start Time', 'End Time', 'Payroll Classification']
            st.dataframe(audit_display, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No entries have been submitted to the logs table yet.")
