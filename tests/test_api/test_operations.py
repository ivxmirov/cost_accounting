import uuid
from decimal import Decimal

from app.enum import CurrencyEnum
from app.models import Wallet



def test_add_income_success(db_session, client, test_user, auth_headers):
    
    wallet = Wallet(
        name="card",
        balance=Decimal(50),
        user_id=test_user.id,
        currency=CurrencyEnum.USD,
    )
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)

    
    response = client.put(
        "/api/v1/operations/income",
        json={"transaction_id": str(uuid.uuid4()), "wallet_name": wallet.name, "amount": 100.0, "description": "Salary"},
        headers=auth_headers,
    )

    
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "income"
    assert data["wallet_id"] == wallet.id
    assert Decimal(str(data["amount"])) == Decimal(100)
    assert data["category"] == "Salary"  
    
    db_session.refresh(wallet)
    assert wallet.balance == Decimal(150)



def test_add_income_wallet_not_exists(db_session, client, test_user, auth_headers):
    
    

    
    response = client.put(
        "/api/v1/operations/income",
        json={"transaction_id": str(uuid.uuid4()), "wallet_name": "nonexistent", "amount": 100.0, "description": "Salary"},
        headers=auth_headers,
    )

    
    assert response.status_code == 404
    data = response.json()
    assert "nonexistent" in data["message"]



def test_add_income_unauthorized(client):
    
    response = client.put(
        "/api/v1/operations/income",
        json={"transaction_id": str(uuid.uuid4()), "wallet_name": "test", "amount": 100.0, "description": "Salary"},
    )

    
    assert response.status_code == 403


def test_add_expense_success(db_session, client, test_user, auth_headers):
    
    wallet = Wallet(
        name="card", balance=200, user_id=test_user.id, currency=CurrencyEnum.USD
    )  
    db_session.add(wallet)  
    db_session.commit()  
    db_session.refresh(wallet)  

    
    response = client.put(
        "/api/v1/operations/expense",  
        json={
            "transaction_id": str(uuid.uuid4()),  
            "wallet_name": "card",  
            "amount": 50.0,  
            "description": "Food",  
        },
        headers=auth_headers,  
    )

    
    assert response.status_code == 201  
    data = response.json()
    assert data["type"] == "expense"  
    assert data["wallet_id"] == wallet.id  
    assert Decimal(str(data["amount"])) == Decimal(50)  
    assert data["category"] == "Food"  
    
    db_session.refresh(wallet)
    assert wallet.balance == Decimal(150)  


def test_add_expense_negative_amount(db_session, client, test_user, auth_headers):
    
    wallet = Wallet(
        name="card", balance=200, user_id=test_user.id, currency=CurrencyEnum.USD
    )  
    db_session.add(wallet)  
    db_session.commit()  
    db_session.refresh(wallet)  

    
    response = client.put(
        "/api/v1/operations/expense",  
        json={
            "transaction_id": str(uuid.uuid4()),  
            "wallet_name": "card",  
            "amount": -100.0,  
            "description": "Food",  
        },
        headers=auth_headers,  
    )

    
    assert response.status_code == 422  


def test_add_expense_empty_name(db_session, client, test_user, auth_headers):
    
    wallet = Wallet(
        name="card", balance=200, user_id=test_user.id, currency=CurrencyEnum.USD
    )  
    db_session.add(wallet)  
    db_session.commit()  
    db_session.refresh(wallet)  

    
    response = client.put(
        "/api/v1/operations/expense",  
        json={
            "transaction_id": str(uuid.uuid4()),  
            "wallet_name": "   ",  
            "amount": 100.0,  
            "description": "Food",  
        },
        headers=auth_headers,  
    )

    
    assert response.status_code == 422  


def test_add_expense_wallet_not_exists(db_session, client, test_user, auth_headers):
    
    

    
    response = client.put(
        "/api/v1/operations/expense",  
        json={
            "transaction_id": str(uuid.uuid4()),  
            "wallet_name": "card",  
            "amount": 100.0,  
            "description": "Food",  
        },
        headers=auth_headers,  
    )

    
    assert response.status_code == 404  


def test_add_expense_unauthorized(client):
    

    
    response = client.put(
        "/api/v1/operations/expense",  
        json={
            "transaction_id": str(uuid.uuid4()),  
            "wallet_name": "card",  
            "amount": 100.0,  
            "description": "Food",  
        },
        headers={
            "Authorization": "Bearer notexists"
        },  
    )

    
    assert (
        response.status_code == 401
    )  


def test_add_expense_not_enough_money(db_session, client, test_user, auth_headers):
    
    wallet = Wallet(
        name="card", balance=200, user_id=test_user.id, currency=CurrencyEnum.USD
    )  
    db_session.add(wallet)  
    db_session.commit()  
    db_session.refresh(wallet)  

    
    response = client.put(
        "/api/v1/operations/expense",  
        json={
            "transaction_id": str(uuid.uuid4()),  
            "wallet_name": "card",  
            "amount": 250.0,  
            "description": "Food",  
        },
        headers=auth_headers,  
    )

    
    assert (
        response.status_code == 400
    )  

