def parse_crypto_pair(crypto_pair: str) -> tuple[str, str]:
    """Parse a cryptocurrency pair string into its base and quote currencies.

    Args:
        crypto_pair (str): The cryptocurrency pair string (e.g., "USDT-NGN").

    Returns:
        tuple[str, str]: A tuple containing the base currency and quote currency.
    """
    try:
        base_currency, quote_currency = crypto_pair.split("-")
        return base_currency, quote_currency
    except ValueError:
        raise ValueError(
            f"Invalid crypto pair format: {crypto_pair}. Expected format 'BASE-QUOTE'."
        )


def calculate_expected_payout(amount: float, xbanka_rate: float) -> float:
    """Calculate the expected payout based on the amount and xbanka rate.

    Args:
        amount (float): The transaction amount.
        xbanka_rate (float): The xbanka rate.

    Returns:
        float: The expected payout.
    """

    return amount * xbanka_rate


def convert_amount(
    amount: float, xbanka_rate: float, base_currency: str, quote_currency: str
) -> float:
    """Convert the amount based on the xbanka rate and cryptocurrency pair.

    Args:
        amount (float): The transaction amount.
        xbanka_rate (float): The xbanka rate.
        base_currency (str): The base currency of the crypto pair.
        quote_currency (str): The quote currency of the crypto pair.

    Returns:
        float: The converted amount.
    """

    # Example conversion logic (this can be adjusted based on actual requirements)
    if quote_currency == "NGN":
        # USDT or other to NGN conversion
        converted_amount = amount * xbanka_rate
    else:
        # NGN to USDT or other conversion
        converted_amount = amount / xbanka_rate

    return converted_amount
