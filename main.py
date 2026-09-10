import os
import uuid
from dotenv import load_dotenv

from _decimal import Decimal

from t_tech.invest.grpc.common import MoneyValue, Quotation
from t_tech.invest.grpc.sandbox import SandboxPayInRequest
from t_tech.invest.grpc.operations import PortfolioRequest
from t_tech.invest.constants import INVEST_GRPC_API_SANDBOX
from t_tech.invest.grpc.orders import PostOrderRequest, OrderDirection, OrderType
from t_tech.invest.grpc import Client, InstrumentStatus

from t_tech.invest.grpc.schemas import (
    PostStopOrderRequest,
    PostStopOrderResponse,
    Quotation,
    StopOrderDirection,
    StopOrderExpirationType,
    StopOrderType,
    TrailingValueType,
    GetOrderPriceRequest,
    GetOrderPriceResponse,
    OrderDirection,
    GetLastPricesRequest
)
from t_tech.invest.utils import decimal_to_quotation

load_dotenv()

class InvestClient:
    def __init__(self, token):
        self.token = token

        with Client(token, target=INVEST_GRPC_API_SANDBOX) as client:
            accounts = client.sandbox.get_sandbox_accounts()

            if accounts.accounts:
                self.account_id = accounts.accounts[0].id
            else:
                result = self.client.sandbox.open_sandbox_account()
                self.account_id = result.account_id

            print(f"SANDBOX ACCOUNT ID: {self.account_id}")

            portfolio = client.operations.get_portfolio(PortfolioRequest(account_id=self.account_id,))
            currencies = portfolio.total_amount_currencies
            if not isinstance(currencies, (list, tuple)):
                currencies = [currencies]
            for money in currencies:
                amount = money.units + money.nano / 1e9
                print(f"Баланс: {amount:.2f} {money.currency}")

            response = client.market_data.get_last_prices(GetLastPricesRequest(
                figi=["BBG004730ZJ9"], 
                instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE,)
            )
            
            price_info = response.last_prices[0]
            price = price_info.price
            price_value = price.units + price.nano / 1e9
            print(f"Цена бумаги : {price_value}")

            '''response = self.post_stop_order(
                    client,
                    self.account_id,
                    "BBG004730ZJ9",
                    stop_order_direction=StopOrderDirection.STOP_ORDER_DIRECTION_BUY,
                    quantity=1,
                    price=Quotation(units=10, nano=0),
                )
            print(response)'''

    def get_order_price(
        sandbox_service, account_id, instrument_id, price
    ) -> GetOrderPriceResponse:
        return sandbox_service.sandbox.get_sandbox_order_price(
            request=GetOrderPriceRequest(
                account_id=account_id,
                instrument_id=instrument_id,
                direction=OrderDirection.ORDER_DIRECTION_BUY,
                quantity=1,
                price=utils.decimal_to_quotation(Decimal(price)),  # type: ignore[arg-type]
            )
        )

    def post_stop_order(
            sandbox_service, account_id, instrument_id, stop_order_direction, quantity, price
        ) -> PostStopOrderResponse:
            return sandbox_service.sandbox.post_sandbox_stop_order(
                request=PostStopOrderRequest(
                    account_id=account_id,
                    instrument_id=instrument_id,
                    direction=stop_order_direction,
                    quantity=quantity,
                    price=price,
                    order_id=str(uuid.uuid4()),
                    expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
                    stop_price=price,
                    stop_order_type=StopOrderType.STOP_ORDER_TYPE_TAKE_PROFIT,
                    trailing_data=PostStopOrderRequest.TrailingData(
                        indent_type=TrailingValueType.TRAILING_VALUE_RELATIVE,
                        indent=decimal_to_quotation(Decimal(1)),  # type: ignore[arg-type]
                    ),
                )
            )

    def trade(self,client):
        """Покупаем дешевле, продаём подороже"""
        figi = "BBG0047303N7"  # SBER
        quantity = 10
        spread = 0.02  # 2%

        # Получаем текущую цену
        last_prices = client.market_data.get_last_prices([figi])
        if not last_prices.prices:
            print("Не удалось получить цену")
            return

        current_price = last_prices.prices[0].price
        price_value = current_price.units + current_price.nano / 1e9

        print(f"\nТекущая цена {figi}: {price_value:.2f} RUB")

        # Цена покупки на 2% ниже
        buy_price_value = price_value * (1 - spread)
        buy_price = Quotation(
            units=int(buy_price_value),
            nano=int((buy_price_value - int(buy_price_value)) * 1e9)
        )

        # Цена продажи на 2% выше
        sell_price_value = price_value * (1 + spread)
        sell_price = Quotation(
            units=int(sell_price_value),
            nano=int((sell_price_value - int(sell_price_value)) * 1e9)
        )

        print(f"Цена покупки (лимит): {buy_price_value:.2f}")
        print(f"Цена продажи (лимит): {sell_price_value:.2f}")

        # Покупка
        buy_request = PostOrderRequest(
            figi=figi,
            quantity=quantity,
            price=buy_price,
            direction=OrderDirection.ORDER_DIRECTION_BUY,
            account_id=self.account_id,
            order_type=OrderType.ORDER_TYPE_LIMIT,
            order_id="buy_order_001"
        )

        buy_response = client.operations.post_order(buy_request)
        print(f"\nЗаявка на покупку:")
        print(f"  ID: {buy_response.order_id}")
        print(f"  Статус: {buy_response.execution_report_status}")
        print(f"  Исполнено: {buy_response.lots_executed}/{buy_response.lots_requested}")

        # Продажа
        sell_request = PostOrderRequest(
            figi=figi,
            quantity=quantity,
            price=sell_price,
            direction=OrderDirection.ORDER_DIRECTION_SELL,
            account_id=self.account_id,
            order_type=OrderType.ORDER_TYPE_LIMIT,
            order_id="sell_order_001"
        )

        sell_response = client.operations.post_order(sell_request)
        print(f"\nЗаявка на продажу:")
        print(f"  ID: {sell_response.order_id}")
        print(f"  Статус: {sell_response.execution_report_status}")
        print(f"  Исполнено: {sell_response.lots_executed}/{sell_response.lots_requested}")

        # Профит
        profit = (sell_price_value - buy_price_value) * quantity
        print(f"\nОжидаемый профит: {profit:.2f} RUB")

    def pay_in(self,client,amount):
        value = MoneyValue(units=amount, nano=0, currency="rub")
        request = SandboxPayInRequest(account_id=self.account_id, amount=amount)
        pay_result = self.client.sandbox.sandbox_pay_in(request)

        print(f"Баланс += {amount}: {pay_result.balance}")

def main():
    token = os.getenv("INVEST_TOKEN")

    InvestClient(token)

if __name__ == "__main__":
    main()
