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
            st.image("logo.png", use_container_width=True)
            
        st.write("")
        st.write("")
        
        with st.container(border=True):
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown("### 🛡️")
            with col2:
                st.markdown("**Manager**")
                st.markdown("<span style='color: gray; font-size: 14px;'>View all employee records, counts, and payroll audit tracking pages.</span>", unsafe_allow_html=True)
            
            if st.button("Select as Manager", key="btn_manager", use_container_width=True):
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
                
            if st.button("Select as Employee", key="btn_emp", use_container_width=True):
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
            if st.button("↩️ Change Role", use_container_width=True):
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
        
        # --- ADDITIONAL SHIFT BLOCK ---
        st.markdown("---")
        
        has_additional = st.checkbox("➕ Add an extra location and date range", value=False)
        
        final_additional_location = ""
        additional_date_range = None
        
        if has_additional:
            st.markdown("#### **Additional Shift Block**")
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
                    key="
