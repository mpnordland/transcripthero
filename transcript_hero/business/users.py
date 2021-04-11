from typing import Union, Optional
from transcript_hero.database.models import User, Role


class UserService:
    def __init__(self, db, config):
        self.db = db
        self.config = config

    def get(self, user_id: int) -> User:
        with self.db.session() as session:
            return session.query(User).get(user_id)

    def get_by_email(self, user_email: str) -> User:
        with self.db.session() as session:
            return session.query(User).filter_by(email=user_email).first()

    def save(self, user: User) -> None:
        self.db.save(user)

    def delete(self, user: User) -> None:
        """
        Used when a user requests their account to be deleted
        Some records, like transactions and subscriptions need to be kept.
        But we will delete all other data.
        """

        # unlink the subscriptions and transactions
        user.subscription = None
        user.transactions.clear()
        self.save(user)
        self.db.delete(user)

    def find(self, **kwargs) -> Optional[User]:
        with self.db.session() as session:
            return session.query(User).filter_by(**kwargs).first()

    def find_role(self, role_name: str) -> Role:
        with self.db.session() as session:
            return session.query(Role).filter_by(name=role_name).first()

    def remove_user_role(self, user: User, role: Union[str, Role]) -> None:
        if isinstance(role, str):
            role = self.find_role(role)

        if role in user.roles:
            user.roles.remove(role)

    def add_user_role(self, user: User, role: Union[str, Role]) -> None:
        if isinstance(role, str):
            role = self.find_role(role)

        if role not in user.roles:
            user.roles.append(role)

    def start_benefits(self, user: User) -> None:
        self.add_user_role(user, "subscriber")
        self.save(user)

    def stop_benefits(self, user: User) -> None:
        self.remove_user_role(user, "subscriber")
        self.save(user)
