from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Employee(Base):
    __tablename__ = 'employees'
    
    id = Column(String(50), primary_key=True)  # emp_id
    name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    position = Column(String(100), nullable=False)
    registration_date = Column(DateTime, default=datetime.now)
    attendances = relationship("Attendance", back_populates="employee")

class Attendance(Base):
    __tablename__ = 'attendances'
    
    id = Column(Integer, primary_key=True)
    employee_id = Column(String(50), ForeignKey('employees.id'), nullable=False)
    date = Column(DateTime, nullable=False)
    check_in = Column(DateTime, nullable=False)
    check_out = Column(DateTime, nullable=True)
    total_hours = Column(Float, default=0)
    status = Column(String(20), default='Present')
    
    employee = relationship("Employee", back_populates="attendances")

def init_db(db_path='attendance.db'):
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

# Create a global session
session = init_db() 