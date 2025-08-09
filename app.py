import streamlit as st
import cv2
import numpy as np
from face_utils import FaceUtils
from attendance_manager import AttendanceManager
from auth_manager import AuthManager
import tempfile
import os
from datetime import datetime, timedelta
import time
import pandas as pd

# Initialize managers
face_utils = FaceUtils()
attendance_manager = AttendanceManager()
auth_manager = AuthManager()

def init_session_state():
    """Initialize session state variables."""
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'auth_token' not in st.session_state:
        st.session_state.auth_token = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'show_admin_login' not in st.session_state:
        st.session_state.show_admin_login = False

def admin_login_page():
    """Display admin login page."""
    st.sidebar.title("Admin Login")
    
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login"):
        result = auth_manager.login(username, password)
        if result and result["role"] == "admin":
            st.session_state.admin_authenticated = True
            st.session_state.auth_token = result["token"]
            st.session_state.username = result["username"]
            st.session_state.role = result["role"]
            st.sidebar.success("Admin login successful!")
            st.rerun()
        else:
            st.sidebar.error("Invalid admin credentials")

def admin_logout():
    """Logout admin."""
    if st.session_state.auth_token:
        auth_manager.logout(st.session_state.auth_token)
    st.session_state.admin_authenticated = False
    st.session_state.auth_token = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.show_admin_login = False
    st.rerun()

def toggle_admin_login():
    """Toggle admin login form visibility."""
    st.session_state.show_admin_login = not st.session_state.show_admin_login

def check_permission(permission):
    """Check if current user has the required permission."""
    if not st.session_state.auth_token:
        return False
    return auth_manager.has_permission(st.session_state.auth_token, permission)

def admin_menu():
    """Display admin menu."""
    return [
        "System Dashboard",
        "Manage Employees",
        "Manage Users",
        "View Attendance",
        "Department Reports",
        "Employee Reports",
        "Present Today",
        "Export Data",
        "System Settings"
    ]

def user_menu():
    """Display user menu."""
    return [
        "Mark Attendance",
        "View My Attendance",
        "My Reports"
    ]

def system_dashboard():
    """Display system dashboard."""
    st.header("System Dashboard")
    
    # Display statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_employees = len(attendance_manager.get_all_employees())
        st.metric("Total Employees", total_employees)
        
    with col2:
        today_attendance = len(attendance_manager.get_today_attendance())
        st.metric("Today's Attendance", today_attendance)
        
    with col3:
        active_sessions = len(attendance_manager.get_active_sessions())
        st.metric("Active Sessions", active_sessions)

def manage_users_page():
    """Admin page for managing users."""
    st.header("Manage Users")
    
    tab1, tab2, tab3 = st.tabs(["All Users", "Create User", "User Actions"])
    
    with tab1:
        users = auth_manager.get_all_users()
        st.dataframe(pd.DataFrame(users))
    
    with tab2:
        with st.form("create_user"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["user", "admin"])
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            
            if st.form_submit_button("Create User"):
                if auth_manager.create_user(new_username, new_password, role, name, email):
                    st.success("User created successfully")
                else:
                    st.error("Failed to create user")
    
    with tab3:
        users = auth_manager.get_all_users()
        user_list = [u["username"] for u in users if u["username"] != "admin"]
        
        if not user_list:
            st.info("No users available to manage")
            return
            
        username = st.selectbox("Select User", user_list)
        
        # Find the selected user
        selected_user = next((u for u in users if u["username"] == username), None)
        
        if selected_user:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Reset Password"):
                    new_pass = "password123"  # Default reset password
                    if auth_manager.reset_password(username, new_pass):
                        st.success(f"Password reset to: {new_pass}")
                    else:
                        st.error("Failed to reset password")
            
            with col2:
                current_status = selected_user.get("status", "active")
                new_status = "inactive" if current_status == "active" else "active"
                if st.button(f"Mark as {new_status.title()}"):
                    if auth_manager.change_user_status(username, new_status):
                        st.success(f"User marked as {new_status}")
                    else:
                        st.error("Failed to update user status")
        else:
            st.error("Selected user not found")

def delete_records_page():
    """Admin page for deleting attendance records."""
    st.header("Delete Attendance Records")
    
    date = st.date_input("Select Date")
    emp_id = st.selectbox("Select Employee", 
        ["All"] + [emp["emp_id"] for emp in attendance_manager.get_all_employees()])
    
    if st.button("Delete Records"):
        # Add confirmation dialog
        if st.warning("Are you sure you want to delete these records?"):
            if st.button("Yes, Delete"):
                # Implement delete functionality
                st.success("Records deleted successfully")

def export_data_page():
    """Admin page for exporting data."""
    st.header("Export Data")
    
    export_type = st.selectbox("Select Export Type", 
        ["All Attendance", "Department-wise", "Employee-wise"])
    
    if export_type == "Department-wise":
        department = st.selectbox("Select Department", 
            ["IT", "HR", "Finance", "Marketing", "Operations", "Sales"])
    elif export_type == "Employee-wise":
        emp_id = st.selectbox("Select Employee",
            [emp["emp_id"] for emp in attendance_manager.get_all_employees()])
    
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    
    if st.button("Export"):
        # Implement export functionality
        st.success("Data exported successfully")

def system_settings_page():
    """Admin page for system settings."""
    st.header("System Settings")
    
    tab1, tab2 = st.tabs(["General Settings", "Security Settings"])
    
    with tab1:
        st.subheader("General Settings")
        min_time = st.number_input("Minimum Check-out Time (minutes)", 
            value=30, min_value=1, max_value=120)
        working_hours = st.time_input("Working Hours Start")
        
        if st.button("Save General Settings"):
            # Implement settings save
            st.success("Settings saved successfully")
    
    with tab2:
        st.subheader("Security Settings")
        session_timeout = st.number_input("Session Timeout (hours)", 
            value=24, min_value=1, max_value=72)
        password_expiry = st.number_input("Password Expiry (days)", 
            value=90, min_value=30, max_value=180)
        
        if st.button("Save Security Settings"):
            # Implement settings save
            st.success("Settings saved successfully")

def main():
    init_session_state()
    
    # Main title
    st.title("Face Recognition Attendance System")
    
    # Sidebar for admin access
    if not st.session_state.admin_authenticated:
        if st.sidebar.button("Admin Access"):
            toggle_admin_login()
        
        if st.session_state.show_admin_login:
            admin_login_page()
    else:
        st.sidebar.button("Logout Admin", on_click=admin_logout)
        
        # Admin menu
        menu = st.sidebar.selectbox("Admin Menu", admin_menu())
        
        if menu == "System Dashboard":
            system_dashboard()
        elif menu == "Manage Employees":
            manage_employees_page()
        elif menu == "Manage Users":
            manage_users_page()
        elif menu == "View Attendance":
            view_attendance_page()
        elif menu == "Department Reports":
            department_reports_page()
        elif menu == "Employee Reports":
            employee_reports_page()
        elif menu == "Present Today":
            present_today_page()
        elif menu == "Export Data":
            export_data_page()
        elif menu == "System Settings":
            system_settings_page()
        return

    # Main attendance page (always visible)
    take_attendance_page()
    
    # Show today's attendance below
    st.subheader("Today's Attendance")
    present_employees = attendance_manager.get_today_present_employees()
    if present_employees:
        present_df = pd.DataFrame(present_employees)
        st.table(present_df)
    else:
        st.info("No attendance records for today")

def view_my_attendance_page():
    """Page for users to view their own attendance."""
    st.header("My Attendance")
    
    # Get employee ID for current user
    emp_details = next((emp for emp in attendance_manager.get_all_employees() 
        if emp["name"] == st.session_state.username), None)
    
    if emp_details:
        emp_id = emp_details["emp_id"]
        df = attendance_manager.get_employee_report(emp_id)
        if not df.empty:
            st.dataframe(df)
        else:
            st.info("No attendance records found")
    else:
        st.error("Employee record not found")

def my_reports_page():
    """Page for users to view their own reports."""
    st.header("My Reports")
    
    # Get employee ID for current user
    emp_details = next((emp for emp in attendance_manager.get_all_employees() 
        if emp["name"] == st.session_state.username), None)
    
    if emp_details:
        emp_id = emp_details["emp_id"]
        
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        
        if st.button("Generate Report"):
            df = attendance_manager.get_employee_report(
                emp_id,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            if not df.empty:
                st.dataframe(df)
                
                # Show statistics
                total_days = (end_date - start_date).days + 1
                days_present = len(df)
                attendance_rate = (days_present / total_days) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Days", total_days)
                col2.metric("Days Present", days_present)
                col3.metric("Attendance Rate", f"{attendance_rate:.2f}%")
            else:
                st.info("No attendance records found for the selected period")
    else:
        st.error("Employee record not found")

def take_attendance_page():
    st.header("Take Attendance")

    # Add mode selection
    mode = st.radio("Select Mode", ["Check In", "Check Out"])

    # Show current mode and instructions
    if mode == "Check In":
        st.info("📝 Check In Mode: Look at the camera to mark your attendance")
    else:
        st.info("🚪 Check Out Mode: Look at the camera to mark your departure")

    # Initialize webcam
    cap = cv2.VideoCapture(0)

    # Create placeholders
    frame_placeholder = st.empty()
    status_placeholder = st.empty()
    present_placeholder = st.empty()

    # Button controls
    stop = st.button("Stop Camera")
    process_button = st.button("Process Attendance")

    # Session state variables
    if 'last_status_message' not in st.session_state:
        st.session_state.last_status_message = {}
    if 'last_processed_time' not in st.session_state:
        st.session_state.last_processed_time = {}
    if 'confirmed' not in st.session_state:
        st.session_state.confirmed = False
    if 'latest_recognized_names' not in st.session_state:
        st.session_state.latest_recognized_names = []
    if 'latest_processed_frame' not in st.session_state:
        st.session_state.latest_processed_frame = None

    while not stop:
        ret, frame = cap.read()
        if not ret or frame is None:
            st.error("Failed to access webcam.")
            break

        # Process the frame
        processed_frame, recognized_names = face_utils.process_frame(frame)

        # Convert BGR to RGB and display
        rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(rgb_frame, channels="RGB")

        # Save the latest recognized names and frame for confirmation step
        st.session_state.latest_recognized_names = recognized_names
        st.session_state.latest_processed_frame = processed_frame

        # If recognized, ask for confirmation before processing
        if recognized_names and not st.session_state.confirmed:
            st.subheader("Face Detected")
            st.image(rgb_frame, channels="RGB", caption=f"Detected: {', '.join(recognized_names)}")
            if st.button("Confirm and Mark Attendance"):
                st.session_state.confirmed = True
                st.experimental_rerun()  # Rerun to continue after confirmation
            else:
                st.warning("Please confirm before proceeding.")
                time.sleep(0.1)
                continue

        # After confirmation and process button click, mark attendance
        if process_button and st.session_state.confirmed:
            for name in st.session_state.latest_recognized_names:
                if name != "Unknown":
                    emp_details = attendance_manager.get_employee_by_name(name)
                    if emp_details:
                        emp_id = emp_details['emp_id']
                        attendance_mode = mode.replace(" ", "_").upper()
                        result = attendance_manager.process_attendance([name], attendance_mode)
                        if result:
                            result = result[0]
                            if result['status'] == "SUCCESS":
                                st.session_state.last_status_message[emp_id] = result['message']
                                st.session_state.last_processed_time[emp_id] = time.time()
                                status_placeholder.success(result['message'])
                            elif result['status'] == "INFO":
                                if emp_id not in st.session_state.last_status_message or \
                                   st.session_state.last_status_message[emp_id] != result['message']:
                                    status_placeholder.info(result['message'])
                                    st.session_state.last_status_message[emp_id] = result['message']
                            else:
                                status_placeholder.error(result['message'])

            # Reset confirmation
            st.session_state.confirmed = False

        # Show today's attendance
        present_employees = attendance_manager.get_today_present_employees()
        if present_employees:
            present_placeholder.subheader("Today's Attendance:")
            present_df = pd.DataFrame(present_employees)
            present_placeholder.table(present_df)
        else:
            present_placeholder.info("No attendance records for today")

        # Slight delay
        time.sleep(0.1)

    # Cleanup
    st.session_state.confirmed = False
    cap.release()


def manual_attendance_page():
    st.header("Manual Attendance")
    
    # Get all employees
    employees = attendance_manager.get_all_employees()
    
    if not employees:
        st.info("No employees registered in the system.")
        return
    
    # Create columns for the form
    col1, col2 = st.columns(2)
    
    with col1:
        # Employee selection
        emp_id = st.selectbox(
            "Select Employee",
            options=[emp['emp_id'] for emp in employees],
            format_func=lambda x: f"{x} - {next(emp['name'] for emp in employees if emp['emp_id'] == x)}"
        )
        
        # Get current status
        status = attendance_manager.get_current_status(emp_id)
        is_checked_in = status["is_checked_in"]
        
        # Automatically select appropriate action based on current status
        action = "CHECK_OUT" if is_checked_in else "CHECK_IN"
        st.write("Action:", action.replace("_", " ").title())
    
    with col2:
        # Show employee details
        emp_details = next(emp for emp in employees if emp['emp_id'] == emp_id)
        st.write("Employee Details:")
        st.json({
            "Name": emp_details['name'],
            "Department": emp_details['department'],
            "Position": emp_details['position']
        })
        
        # Show current status
        if is_checked_in:
            elapsed_minutes = status["elapsed_minutes"]
            st.write("Status:", 
                    f"✅ Checked In at {status['check_in_time']} "
                    f"({int(elapsed_minutes)} minutes ago)")
            
            # Show minimum time requirement if not met
            if elapsed_minutes < 30:
                st.warning(f"⏳ Must wait {30 - int(elapsed_minutes)} more minutes before check-out")
        else:
            st.write("Status: ❌ Not checked in")
    
    # Process attendance
    if st.button(f"Process {action.replace('_', ' ').title()}", type="primary"):
        result = attendance_manager.manual_attendance(emp_id, action)
        if result['status'] == "SUCCESS":
            st.success(result['message'])
            time.sleep(1)
            st.rerun()
        else:
            st.error(result['message'])
    
    # Show today's attendance
    st.subheader("Today's Attendance")
    present_employees = attendance_manager.get_today_present_employees()
    if present_employees:
        present_df = pd.DataFrame(present_employees)
        st.table(present_df)
    else:
        st.info("No attendance records for today")

def active_sessions_page():
    st.header("Active Sessions Monitor")
    
    # Create a placeholder for the active sessions table
    sessions_placeholder = st.empty()
    
    # Add auto-refresh option
    auto_refresh = st.checkbox("Auto-refresh every 30 seconds", value=True)
    
    while True:
        # Get and display active sessions
        active_sessions = attendance_manager.get_active_sessions()
        
        if active_sessions:
            sessions_placeholder.subheader(f"Currently Checked In: {len(active_sessions)} employees")
            df = pd.DataFrame(active_sessions)
            
            # Calculate statistics
            dept_stats = df.groupby('Department').size().reset_index(name='Count')
            
            # Display information in columns
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("Active Sessions:")
                st.dataframe(df)
            
            with col2:
                st.write("Department Summary:")
                st.dataframe(dept_stats)
        else:
            sessions_placeholder.info("No active sessions at the moment")
        
        # If auto-refresh is enabled, wait 30 seconds
        if auto_refresh:
            time.sleep(30)
        else:
            break

def register_employee_page():
    st.header("Register New Employee")
    
    # Employee details form
    with st.form("employee_registration"):
        emp_id = st.text_input("Employee ID")
        name = st.text_input("Full Name")
        department = st.selectbox("Department", 
            ["IT", "HR", "Finance", "Marketing", "Operations", "Sales", "Other"])
        position = st.text_input("Position")
        
        # Upload image
        uploaded_file = st.file_uploader("Upload a clear face photo", type=['jpg', 'jpeg', 'png'])
        
        submitted = st.form_submit_button("Register Employee")
        
        if submitted and uploaded_file and emp_id and name:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

        if attendance_manager.add_employee(emp_id, name, department, position):
            if face_utils.register_new_face(tmp_path, name):
                face_utils.load_known_faces()  # ✅ RELOAD after adding
                st.success(f"Successfully registered employee: {name}")
            else:
                st.error("❌ Failed to register face. Make sure the image has exactly ONE clear face.")
        else:
            st.error(f"❌ Employee ID {emp_id} already exists.")

        os.unlink(tmp_path)


def manage_employees_page():
    st.header("Manage Employees")
    
    # Get all employees
    employees = attendance_manager.get_all_employees()
    
    if not employees:
        st.info("No employees registered in the system.")
        return
    
    # Display employees in a table
    df = pd.DataFrame(employees)
    df = df.rename(columns={
        'emp_id': 'Employee ID',
        'name': 'Name',
        'department': 'Department',
        'position': 'Position',
        'registration_date': 'Registration Date'
    })
    
    st.dataframe(df)
    
    # Remove employee section
    st.subheader("Remove Employee")
    col1, col2 = st.columns(2)
    
    with col1:
        emp_id = st.selectbox("Select Employee ID", 
            options=[emp['emp_id'] for emp in employees],
            format_func=lambda x: f"{x} - {next(emp['name'] for emp in employees if emp['emp_id'] == x)}"
        )
    
    with col2:
        if st.button("Remove Employee", type="primary"):
            if attendance_manager.remove_employee(emp_id):
                # Reload face utils to update known faces
                face_utils.load_known_faces()
                st.success("Employee removed successfully!")
                st.rerun()
            else:
                st.error("Failed to remove employee.")

def view_attendance_page():
    st.header("Attendance Records")
    
    # Add date selector
    view_option = st.radio("Select View Option", 
        ["Today's Attendance", "Date-wise Attendance", "All Records"])
    
    if view_option == "Today's Attendance":
        df = attendance_manager.get_today_attendance()
        st.write("Today's Attendance:")
        if not df.empty:
            st.dataframe(df)
            show_attendance_stats(df)
        else:
            st.info("No attendance records for today.")
        
    elif view_option == "Date-wise Attendance":
        date = st.date_input("Select Date")
        date_str = date.strftime("%Y-%m-%d")
        df = attendance_manager.get_attendance_by_date(date_str)
        st.write(f"Attendance for {date_str}:")
        if not df.empty:
            st.dataframe(df)
            show_attendance_stats(df)
        else:
            st.info("No attendance records for selected date.")
        
    else:  # All Records
        df = attendance_manager.get_all_attendance()
        st.write("All Attendance Records:")
        if not df.empty:
            st.dataframe(df)
            show_attendance_stats(df)
        else:
            st.info("No attendance records found.")
    
    # Add download button
    if not df.empty:
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f'attendance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv'
        )

def department_reports_page():
    st.header("Department-wise Reports")
    
    department = st.selectbox("Select Department",
        ["IT", "HR", "Finance", "Marketing", "Operations", "Sales", "Other"])
    
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")
    
    if st.button("Generate Report"):
        df = attendance_manager.get_department_report(
            department,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        if not df.empty:
            st.subheader("Attendance Report")
            st.dataframe(df)
            
            # Show department statistics
            st.subheader("Department Statistics")
            total_employees = len(df['Employee_ID'].unique())
            total_days = len(df['Date'].unique())
            attendance_rate = (len(df) / (total_employees * total_days)) * 100 if total_employees * total_days > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Employees", total_employees)
            col2.metric("Total Days", total_days)
            col3.metric("Attendance Rate", f"{attendance_rate:.2f}%")
            
            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Report",
                data=csv,
                file_name=f'department_report_{department}_{datetime.now().strftime("%Y%m%d")}.csv',
                mime='text/csv'
            )
        else:
            st.info("No attendance records found for the selected criteria.")

def employee_reports_page():
    st.header("Employee Reports")
    
    emp_id = st.text_input("Enter Employee ID")
    
    if emp_id:
        emp_details = attendance_manager.get_employee_details(emp_id)
        if emp_details:
            st.subheader("Employee Details")
            st.json(emp_details)
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")
            
            if st.button("Generate Report"):
                df = attendance_manager.get_employee_report(
                    emp_id,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
                
                if not df.empty:
                    st.subheader("Attendance Report")
                    st.dataframe(df)
                    
                    # Show employee statistics
                    st.subheader("Attendance Statistics")
                    total_days = (end_date - start_date).days + 1
                    days_present = len(df)
                    attendance_rate = (days_present / total_days) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Days", total_days)
                    col2.metric("Days Present", days_present)
                    col3.metric("Attendance Rate", f"{attendance_rate:.2f}%")
                    
                    # Download option
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Report",
                        data=csv,
                        file_name=f'employee_report_{emp_id}_{datetime.now().strftime("%Y%m%d")}.csv',
                        mime='text/csv'
                    )
                else:
                    st.info("No attendance records found for the selected period.")
        else:
            st.error("Employee ID not found.")

def show_attendance_stats(df):
    """Show basic statistics for attendance data."""
    if not df.empty:
        st.subheader("Quick Statistics")
        
        try:
            # Calculate statistics
            total_employees = len(df['Employee_ID'].unique()) if 'Employee_ID' in df.columns else 0
            departments = df['Department'].unique() if 'Department' in df.columns else []
            avg_hours = df['Total_Hours'].mean() if 'Total_Hours' in df.columns else 0
            early_birds = len(df[df['Check_In'] < '09:00:00']) if 'Check_In' in df.columns else 0
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Employees", total_employees)
            col2.metric("Departments", len(departments))
            col3.metric("Avg Hours", f"{avg_hours:.2f}")
            col4.metric("Early Birds", early_birds)
            
            # Show department-wise breakdown if department info is available
            if 'Department' in df.columns:
                st.subheader("Department Breakdown")
                metrics = ['Employee_ID']
                if 'Total_Hours' in df.columns:
                    metrics.append('Total_Hours')
                
                dept_stats = df.groupby('Department').agg({
                    metric: 'count' if metric == 'Employee_ID' else 'mean'
                    for metric in metrics
                }).reset_index()
                
                if len(metrics) > 1:
                    dept_stats.columns = ['Department', 'Employee Count', 'Average Hours']
                else:
                    dept_stats.columns = ['Department', 'Employee Count']
                
                st.dataframe(dept_stats)
                
        except Exception as e:
            st.error(f"Error calculating statistics: {str(e)}")

def manage_attendance_records_page():
    st.header("Manage Attendance Records")
    
    tab1, tab2 = st.tabs(["Delete Today's Records", "Delete by Date"])
    
    with tab1:
        st.subheader("Delete Today's Attendance Records")
        st.warning("⚠️ This will delete all attendance records for today and reset active sessions.")
        
        if st.button("Delete Today's Records", type="primary"):
            if attendance_manager.delete_todays_attendance():
                st.success("Successfully deleted today's attendance records")
                # Force page refresh
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to delete attendance records")
    
    with tab2:
        st.subheader("Delete Attendance by Date")
        date = st.date_input("Select Date")
        date_str = date.strftime("%Y-%m-%d")
        
        if st.button(f"Delete Records for {date_str}", type="primary"):
            if attendance_manager.delete_attendance_by_date(date_str):
                st.success(f"Successfully deleted attendance records for {date_str}")
                if date_str == datetime.now().strftime("%Y-%m-%d"):
                    time.sleep(1)
                    st.rerun()
            else:
                st.error("Failed to delete attendance records")
    
    # Show current active sessions
    st.subheader("Current Active Sessions")
    active_sessions = attendance_manager.get_active_sessions()
    if active_sessions:
        st.table(pd.DataFrame(active_sessions))
    else:
        st.info("No active sessions")

def present_today_page():
    """Display list of employees present today."""
    st.header("Employees Present Today")
    
    present_employees = attendance_manager.get_today_present_employees()
    if present_employees:
        # Create DataFrame
        df = pd.DataFrame(present_employees)
        
        # Add statistics
        total_present = len(df)
        total_employees = len(attendance_manager.get_all_employees())
        attendance_rate = (total_present / total_employees * 100) if total_employees > 0 else 0
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Present", total_present)
        col2.metric("Total Employees", total_employees)
        col3.metric("Attendance Rate", f"{attendance_rate:.1f}%")
        
        # Show department-wise breakdown
        if not df.empty:
            st.subheader("Department Breakdown")
            dept_stats = df.groupby('Department').size().reset_index(name='Count')
            st.table(dept_stats)
        
        # Show full attendance list
        st.subheader("Attendance List")
        st.table(df)
    else:
        st.info("No attendance records for today")

if __name__ == "__main__":
    main() 