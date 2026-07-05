from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.enum import CurrencyEnum, OperationType


class OperationRequest(BaseModel):
    wallet_name: str = Field(..., max_length=127)
    amount: Decimal
    description: str | None = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("wallet_name")
    @classmethod
    def wallet_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Wallet name cannot be empty")
        return v


class CreateWalletRequest(BaseModel):
    name: str = Field(..., max_length=127)
    initial_balance: Decimal = Decimal(0)
    currency: CurrencyEnum = CurrencyEnum.RUB

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Wallet name cannot be empty")
        return v

    @field_validator("initial_balance")
    @classmethod
    def balance_not_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Initial balance cannot be negative")
        return v


class UserRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=127, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    login: str


class WalletResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    balance: Decimal
    currency: CurrencyEnum


class OperationResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    wallet_id: int
    type: str
    amount: Decimal
    currency: CurrencyEnum
    category: str | None
    subcategory: str | None
    created_at: datetime

    @field_serializer("amount")
    def serialize_amount(self, amount: Decimal) -> str:
        return f"{amount:.2f}"


class TransferCreateSchema(BaseModel):
    transaction_id: UUID
    from_wallet_id: int
    to_wallet_id: int
    amount: Decimal

    @field_validator("to_wallet_id")
    @classmethod
    def wallets_must_differ(cls, v, info):
        if "from_wallet_id" in info.data and v == info.data["from_wallet_id"]:
            raise ValueError("Same wallets ids!")
        return v

    @field_validator("amount")
    @classmethod
    def amount_gt_zero(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v


class TransferCreateSchemaV2(TransferCreateSchema):
    received_amount: Decimal | None = None

    @field_validator("received_amount")
    @classmethod
    def received_amount_gt_zero(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError("Received amount cannot be negative")
        return v

    @field_validator("received_amount")
    @classmethod
    def round_received_amount(cls, v: Decimal | None) -> Decimal | None:
        if v is not None:
            return round(v, 2)
        return v


class TransferResponse(BaseModel):
    model_config = {"from_attributes": True}
    success: bool
    from_wallet: WalletResponse
    to_wallet: WalletResponse
    transferred_amount: Decimal
    received_amount: Decimal
    exchange_rate: Decimal

    @field_serializer("transferred_amount")
    def serialize_transferred_amount(self, amount: Decimal) -> str:
        return f"{amount:.2f}"

    @field_serializer("received_amount")
    def serialize_received_amount(self, amount: Decimal) -> str:
        return f"{amount:.2f}"

    @field_serializer("exchange_rate")
    def serialize_exchange_rate(self, rate: Decimal) -> float:
        return float(rate)


class TotalBalance(BaseModel):
    total_balance: Decimal


class IncomeCreateSchema(BaseModel):
    transaction_id: UUID
    wallet_name: str = Field(..., max_length=127)
    amount: Decimal = Field(..., gt=0)
    description: str | None = Field(None, max_length=500)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)

    @field_validator("wallet_name")
    @classmethod
    def wallet_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Wallet name cannot be empty")
        return v


class ExpenseCreateSchema(BaseModel):
    transaction_id: UUID
    wallet_name: str = Field(..., max_length=127)
    amount: Decimal = Field(..., gt=0)
    description: str | None = Field(None, max_length=500)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)

    @field_validator("wallet_name")
    @classmethod
    def wallet_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Wallet name cannot be empty")
        return v


class BulkOperationBase(BaseModel):
    """Базовая схема для массовых операций"""

    wallet_id: int
    amount: Decimal = Field(..., gt=0)
    description: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=255)
    subcategory: str | None = Field(None, max_length=255)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return round(v, 2)


class BulkIncomeOperationSchema(BulkOperationBase):
    operation_type: Literal[OperationType.INCOME] = OperationType.INCOME


class BulkExpenseOperationSchema(BulkOperationBase):
    operation_type: Literal[OperationType.EXPENSE] = OperationType.EXPENSE


BulkOperation = Annotated[
    Union[BulkIncomeOperationSchema, BulkExpenseOperationSchema],
    Field(discriminator="operation_type"),
]


class BulkOperationsCreateSchema(BaseModel):
    operations: list[BulkOperation] = Field(..., min_length=1)


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
