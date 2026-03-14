from app import create_app
from extensions import db
from models import User
import sys

app = create_app()

def list_users():
    with app.app_context():
        users = User.query.all()
        print("-" * 60)
        print(f"{'ID':<5} {'Name':<20} {'Email':<25} {'Is Admin'}")
        print("-" * 60)
        for user in users:
            print(f"{user.id:<5} {user.name:<20} {user.email:<25} {user.is_admin}")
        print("-" * 60)

def create_admin(email, password, name):
    with app.app_context():
        if User.query.filter_by(email=email).first():
            print(f"Error: User with email {email} already exists.")
            return

        user = User(name=name, email=email, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f"Success: Admin user {email} created.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "create":
        # Usage: python manage_users.py create email password name
        if len(sys.argv) < 5:
            print("Usage: python manage_users.py create <email> <password> <name>")
        else:
            create_admin(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        list_users()
