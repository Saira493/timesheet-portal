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

def format_time_string(val):
    if pd.isna(val) or val is None or str(val).strip() == "" or "NULL" in str(val).upper():
        return "-"
    val_str = str(val).strip().lower().replace("0 days", "").replace("hours", "").replace("hour", "").strip()
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

# Flow trackers for password resetting
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
            
            # Sub-step A: Standard Verification Fields
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
                            # Catch default factory password trigger!
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

            # Sub-step B: Force Custom Password Update Interface
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
                                st.success("🎉 Custom password set successfully!")
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
        locations_list = ["Select the Location", "Al-Khair Foundation", "Al-Khair Schools", "BizAv Media Ltd", "Saks London"]
        
        selected_dropdown = st.selectbox("📍 Select Your Main Work Location Site:", options=locations_list, key="primary_loc")
        p_col1, p_col2, p_col3 = st.columns([2, 1, 1])
        with p_col1:
            date_range = st.date_input("Select Date Range Worked:", value=[datetime.now().date(), datetime.now().date() + timedelta(days=2)])
        with p_col2:
            p_start = st.time_input("Start", value=time(9, 0), key="p_start_time")
        with p_col3:
            p_end = st.time_input("End", value=time(17, 0), key="p_end_time")
        
        st.markdown("---")
        if st.button("Process & Submit Timesheet", type="primary", use_container_width=True):
            primary_is_active = (selected_dropdown != "Select the Location")
            if primary_is_active:
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        start_date, end_date = date_range[0], date_range[1] if len(date_range) == 2 else date_range[0]
                        delta = end_date - start_date
                        success_count = 0
                        for i in range(delta.days + 1):
                            single_date = start_date + timedelta(days=i)
                            if single_date.weekday() in [5, 6]: continue
                            query = "INSERT INTO daily_records (employee_name, work_date, location, start_time, end_time) VALUES (%s, %s, %s, %s, %s)"
                            cursor.execute(query, (employee_name.strip(), single_date, selected_dropdown, p_start.strftime("%H:%M"), p_end.strftime("%H:%M")))
                            success_count += 1
                        conn.commit()
                        st.success(f"🎉 Timesheet submitted completely! Saved {success_count} entries.")
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
    with col_logout:
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.auth_status = False
            st.session_state.current_role = "NONE"
            st.session_state.logged_user_name = ""
            st.rerun()
            
    st.markdown("---")
    st.info("📊 Authenticated. Management reporting system fully accessible.")
