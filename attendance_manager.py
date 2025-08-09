import pandas as pd
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
import threading
import streamlit as st

class AttendanceManager:
    def __init__(self, attendance_dir: str = "attendance", employee_file: str = "employees.json"):
        self.attendance_dir = attendance_dir
        self.employee_file = employee_file
        self.employees = {}
        self.lock = threading.Lock()  # For thread-safe file operations
        self.last_processed = {}  # For tracking last processed time for each employee
        self.COOLDOWN_SECONDS = 60  # Cooldown period of 60 seconds
        self.MIN_CHECKOUT_MINUTES = 60  # Minimum time before checkout (changed to 60 minutes)
        
        # Ensure attendance directory exists
        try:
            if not os.path.exists(attendance_dir):
                os.makedirs(attendance_dir)
                print(f"Debug - Created attendance directory: {attendance_dir}")
        except Exception as e:
            print(f"Error creating attendance directory: {str(e)}")
            
        # Load or create employee database
        if os.path.exists(employee_file):
            with open(employee_file, 'r') as f:
                self.employees = json.load(f)
        else:
            self._save_employee_data()

    def _save_employee_data(self):
        """Save employee data to JSON file."""
        with self.lock:
            with open(self.employee_file, 'w') as f:
                json.dump(self.employees, f, indent=4)

    def add_employee(self, emp_id: str, name: str, department: str, position: str) -> bool:
        """Add a new employee to the system."""
        if emp_id in self.employees:
            return False
            
        self.employees[emp_id] = {
            'name': name,
            'department': department,
            'position': position,
            'registration_date': datetime.now().strftime("%Y-%m-%d")
        }
        self._save_employee_data()
        return True

    def get_employee_details(self, emp_id: str) -> Dict:
        """Get employee details by ID."""
        return self.employees.get(emp_id, {})

    def get_employee_by_name(self, name: str) -> Dict:
        """Get employee details by name."""
        for emp_id, details in self.employees.items():
            if details['name'] == name:
                return {'emp_id': emp_id, **details}
        return {}

    def process_attendance(self, names: List[str], mode: str) -> List[Dict]:
        """Process attendance for recognized faces."""
        print(f"Debug - Processing attendance with names={names}, mode={mode}")
        processed_records = []
        current_time = datetime.now()
        
        # Normalize mode to uppercase
        mode = mode.upper()
        
        for name in names:
            print(f"Debug - Processing name: {name}")
            if name != "Unknown":
                emp_details = self.get_employee_by_name(name)
                print(f"Debug - Employee details: {emp_details}")
                if emp_details:
                    emp_id = emp_details['emp_id']
                    
                    # Check cooldown period
                    if emp_id in self.last_processed:
                        time_since_last = (current_time - self.last_processed[emp_id]).total_seconds()
                        if time_since_last < self.COOLDOWN_SECONDS:
                            result = {
                                "status": "ERROR",
                                "message": f"⏳ Please wait {int(self.COOLDOWN_SECONDS - time_since_last)} seconds before trying again"
                            }
                            processed_records.append(result)
                            print(f"Debug - Process result (cooldown): {result}")
                            continue
                    
                    # Get current status
                    status = self.get_current_status(emp_id)
                    print(f"Debug - Current status: {status}")
                    
                    if mode == "CHECK_IN" or mode == "CHECK IN":
                        print("Debug - Processing CHECK_IN")
                        if status["already_checked_in_today"]:
                            result = {
                                "status": "ERROR",
                                "message": f"❌ {emp_details['name']} has already completed attendance for today (Last check-out: {status['last_check_out']})"
                            }
                        elif status["is_checked_in"]:
                            result = {
                                "status": "INFO",
                                "message": f"✅ {emp_details['name']} already checked in at {status['check_in_time']}"
                            }
                        else:
                            # Only allow check-in if there's no incomplete record
                            if not status["has_incomplete_record"]:
                                print("Debug - No incomplete record, proceeding with check-in")
                                result = self._process_check_in(emp_id)
                                if result["status"] == "SUCCESS":
                                    self.last_processed[emp_id] = current_time
                            else:
                                print("Debug - Found incomplete record, preventing check-in")
                                result = {
                                    "status": "ERROR",
                                    "message": f"❌ {emp_details['name']} must check out from previous session first"
                                }
                    elif mode == "CHECK_OUT" or mode == "CHECK OUT":
                        print("Debug - Processing CHECK_OUT")
                        if status["already_checked_in_today"]:
                            result = {
                                "status": "ERROR",
                                "message": f"❌ {emp_details['name']} has already completed attendance for today"
                            }
                        elif not status["is_checked_in"]:
                            result = {
                                "status": "ERROR",
                                "message": f"❌ {emp_details['name']} has not checked in today"
                            }
                        elif status["elapsed_minutes"] < self.MIN_CHECKOUT_MINUTES:
                            result = {
                                "status": "ERROR",
                                "message": f"⏳ Must wait {self.MIN_CHECKOUT_MINUTES - int(status['elapsed_minutes'])} minutes before check-out (Minimum {self.MIN_CHECKOUT_MINUTES} minutes required)"
                            }
                        else:
                            result = self._process_check_out(emp_id)
                            if result["status"] == "SUCCESS":
                                self.last_processed[emp_id] = current_time
                    else:
                        result = {
                            "status": "ERROR",
                            "message": f"❌ Invalid mode: {mode}. Must be CHECK_IN or CHECK_OUT"
                        }
                    
                    processed_records.append(result)
                    print(f"Debug - Process result: {result}")

        return processed_records

    def _process_check_in(self, emp_id: str) -> Dict:
        """Process check-in for an employee."""
        print(f"Debug - Starting check-in process for emp_id: {emp_id}")
        current_time = datetime.now()
        date = current_time.strftime("%Y-%m-%d")
        time = current_time.strftime("%H:%M:%S")
        emp_details = self.get_employee_details(emp_id)
        print(f"Debug - Employee details for check-in: {emp_details}")

        # Ensure attendance directory exists
        if not os.path.exists(self.attendance_dir):
            try:
                os.makedirs(self.attendance_dir)
                print(f"Debug - Created attendance directory: {self.attendance_dir}")
            except Exception as e:
                print(f"Error creating attendance directory: {str(e)}")
                return {
                    "status": "ERROR",
                    "message": f"❌ Failed to create attendance directory: {str(e)}"
                }

        file_path = os.path.join(self.attendance_dir, f"attendance_{date}.csv")
        print(f"Debug - Attendance file path: {file_path}")
        
        # Check current status
        status = self.get_current_status(emp_id)
        print(f"Debug - Current status for check-in: {status}")
        if status["is_checked_in"] or status["has_incomplete_record"]:
            return {
                "status": "ERROR",
                "message": f"❌ {emp_details['name']} must check out from previous session first"
            }

        try:
            # Create or load attendance file
            if os.path.exists(file_path):
                print("Debug - Loading existing attendance file")
                df = pd.read_csv(file_path)
            else:
                print("Debug - Creating new attendance file")
                df = pd.DataFrame(columns=[
                    'Employee_ID', 'Name', 'Department', 'Position', 
                    'Date', 'Check_In', 'Check_Out', 'Total_Hours', 'Status'
                ])

            # Add new attendance record
            new_record = pd.DataFrame({
                'Employee_ID': [emp_id],
                'Name': [emp_details['name']],
                'Department': [emp_details['department']],
                'Position': [emp_details['position']],
                'Date': [date],
                'Check_In': [time],
                'Check_Out': [''],
                'Total_Hours': [0],
                'Status': ['Present']
            })
            print(f"Debug - New record to be added: {new_record.to_dict('records')}")
            
            with self.lock:
                # Ensure the directory exists again (in case it was deleted)
                os.makedirs(self.attendance_dir, exist_ok=True)
                
                # Concatenate and save
                df = pd.concat([df, new_record], ignore_index=True)
                df.to_csv(file_path, index=False)
                print(f"Debug - Successfully wrote attendance record to {file_path}")
                
                # Verify the file was written
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"Debug - Verified file exists with size: {file_size} bytes")
                else:
                    raise Exception("File was not created after writing")

        except Exception as e:
            error_msg = f"Failed to record attendance: {str(e)}"
            print(f"Debug - Error: {error_msg}")
            return {
                "status": "ERROR",
                "message": f"❌ {error_msg}"
            }
        
        return {
            "status": "SUCCESS",
            "message": f"✅ Successfully checked in {emp_details['name']}"
        }

    def _process_check_out(self, emp_id: str) -> Dict:
        """Process check-out for an employee."""
        current_time = datetime.now()
        date = current_time.strftime("%Y-%m-%d")
        time = current_time.strftime("%H:%M:%S")
        emp_details = self.get_employee_details(emp_id)
        
        # Verify current status
        status = self.get_current_status(emp_id)
        if not status["is_checked_in"]:
            return {
                "status": "ERROR",
                "message": f"{emp_details['name']} is not checked in"
            }
        
        # Check minimum time requirement
        if status["elapsed_minutes"] < self.MIN_CHECKOUT_MINUTES:
            return {
                "status": "ERROR",
                "message": f"Cannot check out before {self.MIN_CHECKOUT_MINUTES} minutes. Time elapsed: {int(status['elapsed_minutes'])} minutes"
            }
        
        file_path = os.path.join(self.attendance_dir, f"attendance_{date}.csv")
        
        with self.lock:
            df = pd.read_csv(file_path)
            record_index = status["record_index"]
            
            # Calculate total hours
            check_in_time = datetime.strptime(f"{date} {status['check_in_time']}", "%Y-%m-%d %H:%M:%S")
            check_out_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")
            total_hours = (check_out_time - check_in_time).total_seconds() / 3600
            
            # Update record
            df.loc[record_index, 'Check_Out'] = time
            df.loc[record_index, 'Total_Hours'] = round(total_hours, 2)
            df.to_csv(file_path, index=False)
        
        return {
            "status": "SUCCESS",
            "message": f"Successfully checked out {emp_details['name']} after {int(status['elapsed_minutes'])} minutes"
        }

    def manual_attendance(self, emp_id: str, action: str) -> Dict:
        """Manually process check-in or check-out for an employee."""
        if emp_id not in self.employees:
            return {"status": "ERROR", "message": "Employee not found"}

        if action == "CHECK_IN":
            return self._process_check_in(emp_id)
        elif action == "CHECK_OUT":
            return self._process_check_out(emp_id)
        else:
            return {"status": "ERROR", "message": "Invalid action"}

    def get_today_present_employees(self) -> List[Dict]:
        """Get list of employees present today with their status."""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(self.attendance_dir, f"attendance_{today}.csv")
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['Check_Out'] = df['Check_Out'].fillna('')
            
            if not df.empty:
                present_employees = []
                for _, row in df.iterrows():
                    status = "Checked Out" if row['Check_Out'] else "Checked In"
                    duration = ""
                    if row['Check_Out']:
                        duration = f"{row['Total_Hours']:.1f} hours"
                    else:
                        elapsed = self._calculate_elapsed_minutes(today, row['Check_In'])
                        duration = f"{int(elapsed)} minutes"
                    
                    present_employees.append({
                        'Employee_ID': row['Employee_ID'],
                        'Name': row['Name'],
                        'Department': row['Department'],
                        'Check_In': row['Check_In'],
                        'Check_Out': row['Check_Out'],
                        'Duration': duration,
                        'Status': status
                    })
                return present_employees
        return []

    def get_today_attendance(self) -> pd.DataFrame:
        """Get attendance records for today."""
        date = datetime.now().strftime("%Y-%m-%d")
        return self.get_attendance_by_date(date)

    def get_attendance_by_date(self, date: str) -> pd.DataFrame:
        """Get attendance records for a specific date."""
        file_path = os.path.join(self.attendance_dir, f"attendance_{date}.csv")
        
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        return pd.DataFrame(columns=[
            'Employee_ID', 'Name', 'Department', 'Position', 
            'Date', 'Check_In', 'Status'
        ])

    def get_all_attendance(self) -> pd.DataFrame:
        """Get all attendance records."""
        all_records = []
        
        for file in os.listdir(self.attendance_dir):
            if file.startswith("attendance_") and file.endswith(".csv"):
                file_path = os.path.join(self.attendance_dir, file)
                df = pd.read_csv(file_path)
                all_records.append(df)
        
        if all_records:
            return pd.concat(all_records, ignore_index=True)
        return pd.DataFrame(columns=[
            'Employee_ID', 'Name', 'Department', 'Position', 
            'Date', 'Check_In', 'Status'
        ])

    def get_department_report(self, department: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get attendance report for a specific department."""
        df = self.get_all_attendance()
        if df.empty:
            return df
            
        dept_df = df[df['Department'] == department]
        
        if start_date and end_date:
            dept_df = dept_df[(dept_df['Date'] >= start_date) & (dept_df['Date'] <= end_date)]
            
        return dept_df

    def get_employee_report(self, emp_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get attendance report for a specific employee."""
        df = self.get_all_attendance()
        if df.empty:
            return df
            
        emp_df = df[df['Employee_ID'] == emp_id]
        
        if start_date and end_date:
            emp_df = emp_df[(emp_df['Date'] >= start_date) & (emp_df['Date'] <= end_date)]
            
        return emp_df

    def remove_employee(self, emp_id: str) -> bool:
        """Remove an employee from the system."""
        if emp_id not in self.employees:
            return False
            
        # Remove from employees dictionary
        employee_name = self.employees[emp_id]['name']
        del self.employees[emp_id]
        self._save_employee_data()
        
        # Remove face image if exists
        image_path = os.path.join("known_faces", f"{employee_name}.jpg")
        if os.path.exists(image_path):
            os.remove(image_path)
            
        return True

    def get_all_employees(self) -> List[Dict]:
        """Get list of all employees."""
        return [{"emp_id": emp_id, **details} for emp_id, details in self.employees.items()]

    def get_active_sessions(self) -> List[Dict]:
        """Get list of currently active sessions (employees who are checked in but haven't checked out)."""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(self.attendance_dir, f"attendance_{today}.csv")
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df['Check_Out'] = df['Check_Out'].fillna('')
            
            # Filter for employees who are checked in but haven't checked out
            active_df = df[df['Check_Out'] == '']
            
            if not active_df.empty:
                active_sessions = []
                for _, row in active_df.iterrows():
                    elapsed = self._calculate_elapsed_minutes(today, row['Check_In'])
                    active_sessions.append({
                        'Employee_ID': row['Employee_ID'],
                        'Name': row['Name'],
                        'Department': row['Department'],
                        'Check_In': row['Check_In'],
                        'Duration': f"{int(elapsed)} minutes"
                    })
                return active_sessions
        return []

    def _ensure_attendance_file(self, date: str) -> Tuple[bool, str, pd.DataFrame]:
        """Ensure attendance file exists and is properly formatted."""
        file_path = os.path.join(self.attendance_dir, f"attendance_{date}.csv")
        
        try:
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
            else:
                df = pd.DataFrame(columns=[
                    'Employee_ID', 'Name', 'Department', 'Position', 
                    'Date', 'Check_In', 'Check_Out', 'Total_Hours', 'Status'
                ])
                # Create directory if it doesn't exist
                os.makedirs(self.attendance_dir, exist_ok=True)
                # Save empty DataFrame
                df.to_csv(file_path, index=False)
            
            return True, "", df
            
        except Exception as e:
            error_msg = f"Error accessing attendance file: {str(e)}"
            print(f"Debug - {error_msg}")
            return False, error_msg, pd.DataFrame()

    def get_current_status(self, emp_id: str) -> Dict:
        """Get current check-in status of an employee."""
        print(f"Debug - Getting current status for emp_id: {emp_id}")
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure file exists and is accessible
        success, error_msg, df = self._ensure_attendance_file(today)
        if not success:
            print(f"Debug - Error in get_current_status: {error_msg}")
            return {
                "is_checked_in": False,
                "check_in_time": None,
                "elapsed_minutes": 0,
                "record_index": None,
                "has_incomplete_record": False,
                "error": error_msg,
                "already_checked_in_today": False
            }
        
        df['Check_Out'] = df['Check_Out'].fillna('')
        
        # Get all records for today
        emp_records = df[df['Employee_ID'] == emp_id]
        print(f"Debug - Found {len(emp_records)} records for employee")
        
        if not emp_records.empty:
            # Check if user has any completed check-in/out for today
            completed_records = emp_records[emp_records['Check_Out'] != '']
            if not completed_records.empty:
                print("Debug - User has already completed a check-in/out cycle today")
                return {
                    "is_checked_in": False,
                    "check_in_time": None,
                    "elapsed_minutes": 0,
                    "record_index": None,
                    "has_incomplete_record": False,
                    "already_checked_in_today": True,
                    "last_check_out": completed_records.iloc[-1]['Check_Out']
                }
            
            # Get the latest record
            latest_record = emp_records.iloc[-1]
            print(f"Debug - Latest record: {latest_record.to_dict()}")
            
            # If no check-out time in latest record, employee is checked in
            if latest_record['Check_Out'] == '':
                check_in_time = latest_record['Check_In']
                elapsed_minutes = self._calculate_elapsed_minutes(today, check_in_time)
                print(f"Debug - Employee is checked in, elapsed minutes: {elapsed_minutes}")
                return {
                    "is_checked_in": True,
                    "check_in_time": check_in_time,
                    "elapsed_minutes": elapsed_minutes,
                    "record_index": latest_record.name,
                    "has_incomplete_record": True,
                    "already_checked_in_today": False
                }
        
        print("Debug - No records found for employee today")
        return {
            "is_checked_in": False,
            "check_in_time": None,
            "elapsed_minutes": 0,
            "record_index": None,
            "has_incomplete_record": False,
            "already_checked_in_today": False
        }

    def _calculate_elapsed_minutes(self, date: str, time_str: str) -> float:
        """Calculate elapsed minutes since given time."""
        current_time = datetime.now()
        given_time = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
        return (current_time - given_time).total_seconds() / 60

    def get_today_attendance(self) -> pd.DataFrame:
        """Get attendance records for today."""
        date = datetime.now().strftime("%Y-%m-%d")
        return self.get_attendance_by_date(date)

    def get_attendance_by_date(self, date: str) -> pd.DataFrame:
        """Get attendance records for a specific date."""
        file_path = os.path.join(self.attendance_dir, f"attendance_{date}.csv")
        
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        return pd.DataFrame(columns=[
            'Employee_ID', 'Name', 'Department', 'Position', 
            'Date', 'Check_In', 'Status'
        ])

    def get_all_attendance(self) -> pd.DataFrame:
        """Get all attendance records."""
        all_records = []
        
        for file in os.listdir(self.attendance_dir):
            if file.startswith("attendance_") and file.endswith(".csv"):
                file_path = os.path.join(self.attendance_dir, file)
                df = pd.read_csv(file_path)
                all_records.append(df)
        
        if all_records:
            return pd.concat(all_records, ignore_index=True)
        return pd.DataFrame(columns=[
            'Employee_ID', 'Name', 'Department', 'Position', 
            'Date', 'Check_In', 'Status'
        ])

    def get_department_report(self, department: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get attendance report for a specific department."""
        df = self.get_all_attendance()
        if df.empty:
            return df
            
        dept_df = df[df['Department'] == department]
        
        if start_date and end_date:
            dept_df = dept_df[(dept_df['Date'] >= start_date) & (dept_df['Date'] <= end_date)]
            
        return dept_df

    def get_employee_report(self, emp_id: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Get attendance report for a specific employee."""
        df = self.get_all_attendance()
        if df.empty:
            return df
            
        emp_df = df[df['Employee_ID'] == emp_id]
        
        if start_date and end_date:
            emp_df = emp_df[(emp_df['Date'] >= start_date) & (emp_df['Date'] <= end_date)]
            
        return emp_df

    def remove_employee(self, emp_id: str) -> bool:
        """Remove an employee from the system."""
        if emp_id not in self.employees:
            return False
            
        # Remove from employees dictionary
        employee_name = self.employees[emp_id]['name']
        del self.employees[emp_id]
        self._save_employee_data()
        
        # Remove face image if exists
        image_path = os.path.join("known_faces", f"{employee_name}.jpg")
        if os.path.exists(image_path):
            os.remove(image_path)
            
        return True

    def get_all_employees(self) -> List[Dict]:
        """Get list of all employees."""
        return [{"emp_id": emp_id, **details} for emp_id, details in self.employees.items()] 