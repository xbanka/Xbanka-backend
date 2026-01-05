from app.core.base.services import Service
from app.models.transactions import Transaction
from app.schemas.transactions import TransactionCreatePayload
from sqlalchemy.orm import Session
from app.core.enums import ServiceTypeEnum
from app.utils.currency import convert_amount, parse_crypto_pair


class TransactionService(Service):
    @staticmethod
    def create(db: Session, obj_in: TransactionCreatePayload):
        if obj_in.service_type == ServiceTypeEnum.crypto:
            # Calculate expected payout for crypto and gift card transactions
            xbanka_rate = getattr(obj_in, "xbanka_rate")
            vendor_rate = getattr(obj_in, "vendor_rate")
            margin = getattr(obj_in, "margin")
            
            crypto_pair = getattr(obj_in, "crypto_pair")
            currency_in, currency_out = parse_crypto_pair(crypto_pair)
            expected_payout = convert_amount(
                float(obj_in.amount_in), xbanka_rate, currency_in, currency_out
            )
        elif obj_in.service_type == ServiceTypeEnum.gift_card:
            xbanka_rate = getattr(obj_in, "xbanka_rate")
            vendor_rate = getattr(obj_in, "vendor_rate")
            margin = getattr(obj_in, "margin")

            expected_payout = convert_amount(
                float(obj_in.amount_in), xbanka_rate, "USD", getattr(obj_in, "currency")
            )
            currency_in = getattr(obj_in, "currency", None)
            currency_out = "NGN"

        else:
            xbanka_rate, vendor_rate, margin = None, None, None
            expected_payout = obj_in.amount_in
            currency_in = currency_out = "NGN"

        new_transaction = Transaction(
            service_type=obj_in.service_type,
            amount_in=obj_in.amount_in,
            amount_out=expected_payout,
            affiliate_source=obj_in.affiliate_source,
            xbanka_rate=xbanka_rate,
            vendor_rate=vendor_rate,
            margin=margin,
            crypto_pair=getattr(obj_in, "crypto_pair", None),
            gift_card_type=getattr(obj_in, "gift_card_type", None),
            currency_in=currency_in,
            currency_out=currency_out,
            quantity=getattr(obj_in, "quantity", None),
            customer_id=obj_in.customer_id,
        )

        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
        return new_transaction
