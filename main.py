import os
from dotenv import load_dotenv

load_dotenv()

from t_tech.invest.grpc import Client
from t_tech.invest.grpc.common import MoneyValue, Quotation
from t_tech.invest.grpc.sandbox import SandboxPayInRequest
from t_tech.invest.grpc.operations import PortfolioRequest
from t_tech.invest.grpc.orders import PostOrderRequest, OrderDirection, OrderType


class InvestClient:
    def __init__(self, token):
        self.token = token

        with Client(token) as client:
            accounts = client.sandbox.get_sandbox_accounts()

            if accounts.accounts:
                self.account_id = accounts.accounts[0].id
            else:
                result = self.client.sandbox.open_sandbox_account()
                self.account_id = result.account_id

            self.trade(client)

        '''# Пополняем счёт
        amount = MoneyValue(units=10000, nano=0, currency="rub")
        request = SandboxPayInRequest(account_id=self.account_id, amount=amount)
        pay_result = self.client.sandbox.sandbox_pay_in(request)
        print(f"Пополнение: 10000 RUB")
        print(f"Баланс после пополнения: {pay_result.balance}")

        # Проверяем портфель
        portfolio = self.client.sandbox.get_sandbox_portfolio(PortfolioRequest(account_id=self.account_id))
        print(f"Портфель:")
        print(f"  Акции: {portfolio.total_amount_shares}")
        print(f"  Облигации: {portfolio.total_amount_bonds}")
        print(f"  ETF: {portfolio.total_amount_etf}")
        print(f"  Валюта: {portfolio.total_amount_currencies}")
        print(f"  Итого: {portfolio.total_amount_portfolio}")
        print(f"  Ожидаемая доходность: {portfolio.expected_yield}")
        print(f"  Ежедневная доходность: {portfolio.daily_yield}")'''


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


def main():
    token = os.getenv("INVEST_TOKEN")

    InvestClient(token)


if __name__ == "__main__":
    main()


    main()
