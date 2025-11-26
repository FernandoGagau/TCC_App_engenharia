#!/usr/bin/env python3
"""
Script para criar usuário teste@teste
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, 'src')

async def create_test_user():
    """Create test user with teste@teste credentials"""
    try:
        # Import models and services
        from infrastructure.database.mongodb import mongodb
        from infrastructure.auth_service import auth_service
        from domain.auth_models_mongo import User

        print("Conectando ao MongoDB...")
        await mongodb.connect_db()

        email = "teste@exemplo.com"
        password = "Teste@123"
        username = "teste"

        # Check if user already exists
        existing_user = await User.find_one(User.email == email)
        if existing_user:
            print(f"❌ Usuário {email} já existe!")
            print(f"   ID: {existing_user.id}")
            print(f"   Username: {existing_user.username}")
            print(f"   Full name: {existing_user.full_name}")
            return

        # Create test user
        print(f"Criando usuário {email}...")

        user = User(
            email=email,
            username=username,
            full_name="Usuário Teste",
            password_hash=auth_service.hash_password(password),
            is_verified=True  # Already verified for testing
        )

        await user.insert()

        print("✅ Usuário teste criado com sucesso!")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Username: {username}")
        print(f"   Full name: {user.full_name}")
        print(f"   ID: {user.id}")

    except Exception as e:
        print(f"❌ Erro ao criar usuário: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        await mongodb.close_db()
        print("Conexão MongoDB fechada.")

if __name__ == "__main__":
    asyncio.run(create_test_user())