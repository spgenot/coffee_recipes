from flask_login import UserMixin


class User(UserMixin):
    """User model for Flask-Login."""
    
    def __init__(self, user_id, email, password_hash=None, created_at=None):
        self.id = user_id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
    
    def get_id(self):
        """Return the user ID as a string (required by Flask-Login)."""
        return str(self.id)
    
    @staticmethod
    def from_dict(user_dict):
        """Create User instance from database dictionary."""
        if not user_dict:
            return None
        return User(
            user_id=user_dict['id'],
            email=user_dict['email'],
            password_hash=user_dict.get('password_hash'),
            created_at=user_dict.get('created_at')
        )
