import os
import sys
from datetime import datetime
from getpass import getpass
from sqlalchemy.orm import scoped_session
from flask_security.utils import encrypt_password
from transcript_hero import parse_config
from transcript_hero.database import Database
from transcript_hero.database.models import User
from transcript_hero.business.users import UserService
from transcript_hero_web import app


def usage():
    print("create_superuser.py <email> <name>")


def main():
    if len(sys.argv) == 3:
        config = parse_config(os.environ["TRANSCRIPT_HERO_SETTINGS"])
        db = Database(config["SQLALCHEMY_DATABASE_URI"],
                      scoped_session=scoped_session)
        user_service = UserService(db, config)
        user = User()
        user.email = sys.argv[1]
        user.name = sys.argv[2]
        user.active = True
        user.confirmed_at = datetime.now()
        password = None
        confirm_password = None
        while password != confirm_password or password is None:
            password = getpass("Password:")
            confirm_password = getpass("Confirm password:")
        with app.app_context():
            user.password = encrypt_password(password)
        user_service.save(user)
        user_service.add_user_role(user, "superuser")
        user_service.add_user_role(user, "subscriber")
        user_service.save(user)

    else:
        usage()


if __name__ == "__main__":
    main()
