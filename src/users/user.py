"""
User class for managing user accounts and authentication.
"""
from typing import Dict, Any
from datetime import datetime


class User:
    """Represents a user in the market making system."""
    
    def __init__(
        self,
        username: str,
        display_name: str,
        balance: float,
        hashed_pass: str,
        account_creation_time: int,
        db: Any,
        role: int = 10,
        linked_accounts: Dict[str, str] = None
    ):
        self.username = username
        self.display_name = display_name
        self.balance = balance
        self.hashed_pass = hashed_pass
        self.account_creation_time = account_creation_time
        self.role = role
        self.my_db = db
        self.linked_accounts = linked_accounts or {}
    
    def get_balance(self) -> float:
        """Get the current balance of the user."""
        return self.balance
    
    def set_balance(self, new_balance: float) -> None:
        """Set the balance of the user."""
        self.balance = new_balance
    
    def change_password(self, old_password: str, new_password: str) -> None:
        """Change the user's password."""
        pass
    
    def change_username(self, password: str, new_username: str) -> None:
        """Change the user's username."""
        pass
    
    def change_display_name(self, new_display_name: str) -> None:
        """Change the user's display name."""
        pass
    
    def save(self) -> None:
        """Save user to database."""
        from ..models import UserModel
        
        user_model = self.my_db.query(UserModel).filter(UserModel.username == self.username).first()
        if user_model:
            user_model.display_name = self.display_name
            user_model.balance = self.balance
            user_model.hashed_pass = self.hashed_pass
            user_model.account_creation_time = self.account_creation_time
            user_model.role = self.role
            user_model.linked_accounts = self.linked_accounts
        else:
            user_model = UserModel(
                username=self.username,
                display_name=self.display_name,
                balance=self.balance,
                hashed_pass=self.hashed_pass,
                account_creation_time=self.account_creation_time,
                role=self.role,
                linked_accounts=self.linked_accounts
            )
            self.my_db.add(user_model)
        self.my_db.commit()

