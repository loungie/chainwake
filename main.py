import time
import json
import argparse
import requests
from datetime import datetime
from typing import Dict, List

try:
    from telegram import Bot
except ImportError:
    Bot = None


class WalletWatcher:
    def __init__(self, config: Dict):
        self.api_key = config["etherscan_api_key"]
        self.addresses = config["watch_addresses"]
        self.poll_interval = config.get("poll_interval_sec", 60)
        self.last_txns = {}
        self.bot = None
        self.chat_id = config.get("telegram_chat_id")

        if "telegram_bot_token" in config and self.chat_id and Bot:
            self.bot = Bot(token=config["telegram_bot_token"])

    def get_transactions(self, address: str) -> List[Dict]:
        url = (
            f"https://api.etherscan.io/api?module=account&action=txlist&"
            f"address={address}&startblock=0&endblock=99999999&sort=desc&apikey={self.api_key}"
        )
        response = requests.get(url)
        data = response.json()
        return data.get("result", [])

    def check_wallets(self):
        for address in self.addresses:
            txns = self.get_transactions(address)
            if not txns:
                continue

            latest_tx = txns[0]
            latest_hash = latest_tx["hash"]

            if address not in self.last_txns:
                self.last_txns[address] = latest_hash
                continue

            if self.last_txns[address] != latest_hash:
                self.alert(address, latest_tx)
                self.last_txns[address] = latest_hash

    def alert(self, address: str, txn: Dict):
        msg = (
            f"🔔 Активность обнаружена!\n"
            f"Кошелёк: {address}\n"
            f"Tx Hash: {txn['hash']}\n"
            f"Сумма: {int(txn['value']) / 1e18:.4f} ETH\n"
            f"Время: {datetime.utcfromtimestamp(int(txn['timeStamp']))}"
        )
        print(msg)
        if self.bot:
            self.bot.send_message(chat_id=self.chat_id, text=msg)

    def run(self):
        print("⏳ Старт мониторинга...")
        while True:
            try:
                self.check_wallets()
            except Exception as e:
                print(f"[ERROR] {e}")
            time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.load(f)

    watcher = WalletWatcher(config)
    watcher.run()


if __name__ == "__main__":
    main()
