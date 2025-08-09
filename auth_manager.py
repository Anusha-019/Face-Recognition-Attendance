import json
import os
from typing import Dict, Optional, List
import hashlib
import secrets
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, auth_dir: str = "auth"):
        self.auth_dir = auth_dir
        if not os.path.exists(auth_dir):
            os.makedirs(auth_dir)
            
        self.users_file = os.path.join(auth_dir, "users.json")
        self.sessions_file = os.path.join(auth_dir, "sessions.json")
        self.roles = {
            "admin": {
                "permissions": [
                    "manage_employees",
                    "manage_attendance",
                    "view_reports",
                    "manage_users",
                    "delete_records",
                    "export_data",
                    "system_settings",
                    "view_logs"
                ]
            },
            "user": {
                "permissions": [
                    "mark_attendance",
                    "view_own_attendance",
                    "view_own_reports"
                ]
            }
        }
        self._initialize_files()
        
    def _initialize_files(self):
        """Initialize authentication files."""
        if not os.path.exists(self.users_file):
            # Create default admin user
            default_users = {
                "admin": {
                    "password": self._hash_password("admin123"),  # Default password
                    "role": "admin",
                    "name": "System Admin",
                    "email": "admin@example.com",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_login": None,
                    "status": "active"
                }
            }
            with open(self.users_file, 'w') as f:
                json.dump(default_users, f, indent=4)
                
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'w') as f:
                json.dump({}, f, indent=4)
                
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_session_token(self) -> str:
        """Generate a random session token."""
        return secrets.token_urlsafe(32)
    
    def login(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and create session."""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
            
        if username in users and users[username]["password"] == self._hash_password(password):
            if users[username]["status"] != "active":
                return None
                
            # Update last login
            users[username]["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.users_file, 'w') as f:
                json.dump(users, f, indent=4)
            
            # Create session
            session_token = self._generate_session_token()
            session_data = {
                "username": username,
                "role": users[username]["role"],
                "name": users[username]["name"],
                "permissions": self.roles[users[username]["role"]]["permissions"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "expires_at": (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            
            sessions[session_token] = session_data
            
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=4)
                
            return {"token": session_token, **session_data}
        return None
    
    def verify_session(self, token: str) -> Optional[Dict]:
        """Verify if session is valid and not expired."""
        if not token:
            return None
            
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
            
        if token in sessions:
            session = sessions[token]
            expires_at = datetime.strptime(session["expires_at"], "%Y-%m-%d %H:%M:%S")
            
            if expires_at > datetime.now():
                return session
                
            # Remove expired session
            del sessions[token]
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=4)
                
        return None
    
    def has_permission(self, token: str, permission: str) -> bool:
        """Check if the session has the required permission."""
        session = self.verify_session(token)
        if not session:
            return False
        return permission in session.get("permissions", [])
    
    def logout(self, token: str) -> bool:
        """Invalidate user session."""
        with open(self.sessions_file, 'r') as f:
            sessions = json.load(f)
            
        if token in sessions:
            del sessions[token]
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=4)
            return True
        return False
    
    def create_user(self, username: str, password: str, role: str, name: str, email: str) -> bool:
        """Create a new user."""
        if role not in self.roles:
            return False
            
        with open(self.users_file, 'r') as f:
            users = json.load(f)
            
        if username in users:
            return False
            
        users[username] = {
            "password": self._hash_password(password),
            "role": role,
            "name": name,
            "email": email,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_login": None,
            "status": "active"
        }
        
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    
    def update_user(self, username: str, updates: Dict) -> bool:
        """Update user details."""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
            
        if username not in users:
            return False
            
        if "password" in updates:
            updates["password"] = self._hash_password(updates["password"])
            
        users[username].update(updates)
        
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    
    def delete_user(self, username: str) -> bool:
        """Delete a user."""
        if username == "admin":  # Prevent deletion of main admin account
            return False
            
        with open(self.users_file, 'r') as f:
            users = json.load(f)
            
        if username not in users:
            return False
            
        del users[username]
        
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    
    def get_all_users(self) -> List[Dict]:
        """Get list of all users."""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
        
        return [{
            "username": username,
            "role": details["role"],
            "name": details["name"],
            "email": details["email"],
            "created_at": details["created_at"],
            "last_login": details["last_login"],
            "status": details["status"]
        } for username, details in users.items()]
    
    def change_user_status(self, username: str, status: str) -> bool:
        """Change user account status (active/inactive)."""
        if username == "admin":  # Prevent disabling main admin account
            return False
            
        if status not in ["active", "inactive"]:
            return False
            
        return self.update_user(username, {"status": status})
    
    def reset_password(self, username: str, new_password: str) -> bool:
        """Reset user password."""
        return self.update_user(username, {"password": new_password})
    
    def get_user_permissions(self, username: str) -> List[str]:
        """Get list of permissions for a user."""
        with open(self.users_file, 'r') as f:
            users = json.load(f)
            
        if username not in users:
            return []
            
        role = users[username]["role"]
        return self.roles[role]["permissions"] 