"""
Create Demo User Script
Creates a demo user for testing authentication
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from infrastructure.database.mongodb import MongoDB
from infrastructure.auth_service import auth_service
from domain.auth_models_mongo import User

async def create_demo_user():
    """Create a demo user in the database"""
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        await MongoDB.connect_db()
        print("Connected to MongoDB!")

        # Check if demo user exists
        demo_email = "demo@example.com"
        existing_user = await User.find_one(User.email == demo_email)

        if existing_user:
            print(f"Demo user already exists: {demo_email}")
            return

        # Create demo user
        demo_user = User(
            email=demo_email,
            username="demo",
            full_name="Demo User",
            password_hash=auth_service.hash_password("Demo@123"),
            is_verified=True,
            is_active=True
        )

        await demo_user.insert()
        print(f"Demo user created successfully!")
        print(f"Email: {demo_email}")
        print(f"Password: Demo@123")

    except Exception as e:
        print(f"Error creating demo user: {e}")
    finally:
        # Close MongoDB connection
        await MongoDB.close_db()

if __name__ == "__main__":
    asyncio.run(create_demo_user())