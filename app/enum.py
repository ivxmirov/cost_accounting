from enum import StrEnum, auto

from sqlalchemy.dialects.postgresql import ENUM


class CurrencyEnum(StrEnum):
    RUB = auto()
    USD = auto()
    EUR = auto()


class OperationType(StrEnum):
    EXPENSE = auto()
    INCOME = auto()
    TRANSFER = auto()


class WalletType(StrEnum):
    DEBIT = auto()
    CREDIT = auto()


wallet_type_enum = ENUM(
    WalletType,
    name="wallettype",
    create_type=False,
    checkfirst=True,
    values_callable=lambda x: [e.value for e in x],
)

currency_type_enum = ENUM(
    CurrencyEnum,
    name="currencyenum",
    create_type=False,
    checkfirst=True,
    values_callable=lambda x: [e.value for e in x],
)

operation_type_enum = ENUM(
    OperationType,
    name="operationtype",
    create_type=False,
    checkfirst=True,
    values_callable=lambda x: [e.value for e in x],
)
