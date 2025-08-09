# Face Attendance Monitoring System

This is a face recognition-based attendance monitoring system built using dlib, OpenCV, and Streamlit.

## Features
- Face detection and recognition
- Real-time attendance tracking
- Easy-to-use web interface
- Attendance record management
- CSV export functionality

## Setup Instructions

1. Install Python 3.8 or higher
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a folder named 'known_faces' and add reference images of people
4. Create a folder named 'attendance' for storing attendance records

## Usage

1. Run the application:
   ```bash
   streamlit run app.py
   ```
2. Use the web interface to:
   - Register new faces
   - Take attendance
   - View attendance records
   - Export attendance data

## Project Structure
- `app.py`: Main Streamlit application
- `face_utils.py`: Face detection and recognition utilities
- `attendance_manager.py`: Attendance record management
- `known_faces/`: Directory for storing reference face images
- `attendance/`: Directory for storing attendance records 