from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repository import wallets as wallets_repository
from app.schemas import OperationRequest


def add_income(db: Session, operation: OperationRequest):
    if not wallets_repository.is_wallet_exist(db, operation.wallet_name):
        raise HTTPException(
            status_code=404, detail=f"Wallet <{operation.wallet_name}> not found."
        )

    wallet = wallets_repository.add_income(db, operation.wallet_name, operation.amount)

    db.commit()

    return {
        "message": "Income has been added.",
        "wallet": operation.wallet_name,
        "amount": operation.amount,
        "description": operation.description,
        "new_balance": wallet.balance,  # type: ignore
    }


def add_expense(db: Session, operation: OperationRequest):
    if not wallets_repository.is_wallet_exist(db, operation.wallet_name):
        raise HTTPException(
            status_code=404, detail=f"Wallet <{operation.wallet_name}> not found."
        )

    wallet = wallets_repository.get_wallet_balance_by_name(db, operation.wallet_name)

    if wallet.balance < operation.amount:  # type: ignore

        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds. Available: {wallet.balance}.",  # type: ignore
        )

    wallet = wallets_repository.add_expense(db, operation.wallet_name, operation.amount)

    db.commit()

    return {
        "message": "Expense has been added.",
        "wallet": operation.wallet_name,
        "amount": operation.amount,
        "description": operation.description,
        "new_balance": wallet.balance,  # type: ignore
    }
