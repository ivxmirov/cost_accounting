from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.enum import CurrencyEnum, OperationType, WalletType


class GroupCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=127)
    members_logins: list[str] = Field(...)

    @field_validator("name")
    @classmethod
    def group_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Название группы не может быть пустым")
        return v

    @field_validator("members_logins")
    @classmethod
    def validate_members_logins(cls, v: list[str]) -> list[str]:
        # Нормализуем и убираем дубликаты
        normalized = list(set(login.strip().lower() for login in v))
        return normalized


class MemberBalanceSchema(BaseModel):
    """Схема баланса участника группы."""

    login: str
    effective_balance: Decimal = Decimal("0")


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


class WalletCreateSchema(BaseModel):
    name: str = Field(..., max_length=127)
    initial_balance: Decimal = Decimal("0")
    currency: CurrencyEnum = CurrencyEnum.RUB
    type: WalletType
    credit_limit: Decimal | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Введите название кошелька")
        return v

    @field_validator("initial_balance")
    @classmethod
    def balance_not_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Текущий баланс кошелька не должен быть отрицательным")
        return v

    @field_validator("initial_balance")
    @classmethod
    def validate_initial_balance_precision(cls, v: Decimal) -> Decimal:
        if v is not None:
            # Правильный способ получить экспоненту
            exponent = v.as_tuple().exponent
            # exponent может быть int или str ('n', 'N', 'F' для special values)
            if isinstance(exponent, int) and exponent < -2:
                raise ValueError("Баланс кошелька не может иметь более 2 знаков после запятой")
        return v

    @field_validator("credit_limit")
    @classmethod
    def validate_credit_limit_precision(cls, v: Decimal) -> Decimal:
        if v is not None:
            exponent = v.as_tuple().exponent
            if isinstance(exponent, int) and exponent < -2:
                raise ValueError("Кредитный лимит не может иметь более 2 знаков после запятой")
        return v


class UserRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=127, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6)


class UserResponseSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    login: str


class WalletResponseSchema(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    name: str
    balance: Decimal
    currency: CurrencyEnum
    type: WalletType
    credit_limit: Decimal | None
    user_id: int


class WalletTableSchema(BaseModel):
    """Упрощенная схема кошелька для таблицы"""
    model_config = {"from_attributes": True}
    id: int
    name: str
    currency: CurrencyEnum
    type: WalletType
    effective_balance: Decimal


class GroupResponseSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    creator: int | None = None
    creator_login: str | None = None
    members: list[str] = []
    created_at: datetime
    total_balance: Decimal = Decimal("0")
    member_balances: list[MemberBalanceSchema] = []
    wallets: list[WalletResponseSchema] = []

    @field_validator("members", mode="before")
    @classmethod
    def extract_member_logins(cls, v):
        """Извлекает логины из объектов User"""
        if not v:
            return []
        if isinstance(v, list) and v and hasattr(v[0], "login"):
            return [member.login for member in v]
        return v


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


class TransferResponseSchema(BaseModel):
    model_config = {"from_attributes": True}
    success: bool
    from_wallet: WalletResponseSchema
    to_wallet: WalletResponseSchema
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
    user_id: int
    login: str


class RefreshRequest(BaseModel):
    refresh_token: str
