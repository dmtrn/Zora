import random
import time
from typing import Any

import ua_generator
from eth_account import Account
from loguru import logger
from tqdm import tqdm
from web3 import Web3

from consts import RPCS, SCANS


class Dapp:
    def __init__(self, chain: str, contract_addy: str, abi: dict) -> None:
        self.w3 = Web3(Web3.HTTPProvider(RPCS.get(chain), None))
        self._scan = SCANS.get(chain, None)
        self.contract = self.w3.eth.contract(address=Web3.to_checksum_address(contract_addy), abi=abi)

    def send_txn(self,
                 account: Account,
                 func_name: str,
                 txn_data: tuple,
                 value: int,
                 gasPrice: int) -> hash:
        txn = getattr(self.contract.functions, func_name)(
            *txn_data
        ).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'from': account.address,
            'value': value,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gasPrice': self.w3.to_wei(gasPrice, 'gwei')
        })

        txn["gas"] = int(self.w3.eth.estimate_gas(txn))
        signed_txn = self.w3.eth.account.sign_transaction(txn, account.key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
        time.sleep(2)

        logger.info(f'[{account.address}] {func_name}: {self._scan}{txn_hash}')
        return txn_hash

    def send_eip1559_txn(self,
                         account: Account,
                         func_name: str,
                         txn_data: list,
                         value: int,
                         maxFeePerGas: float,
                         maxPriorityFeePerGas: float
                         ) -> hash:
        txn = getattr(self.contract.functions, func_name)(
            *txn_data
        ).build_transaction({
            'chainId': self.w3.eth.chain_id,
            'from': account.address,
            'value': value,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'maxFeePerGas': self.w3.to_wei(maxFeePerGas, 'gwei'),
            'maxPriorityFeePerGas': self.w3.to_wei(maxPriorityFeePerGas, 'gwei'),
        })

        signed_txn = self.w3.eth.account.sign_transaction(txn, account.key)
        txn_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
        time.sleep(2)
        status = self.w3.eth.wait_for_transaction_receipt(txn_hash, timeout=360).status
        logger.info(f'[{account.address}] {func_name} {value/10**18} ETH')
        if status == 1:
            logger.success(f'Success: {self._scan}{txn_hash}')
        else:
            logger.error(f'Error!')
        return txn_hash

    def read_contract(self, func_name: str, data: list | None = None) -> Any:
        if data is None:
            data = []
        return getattr(self.contract.functions, func_name)(*data).call()


def get_accounts(path):
    with open(f'{path}', 'r') as w:
        try:
            return [Account.from_key(line.removesuffix("\n").strip(' ,.')) for line in w.readlines()]
        except ValueError:
            quit(f'Error in one of the keys.')


def get_proxys():
    with open('proxy.txt', 'r') as proxy_file:
        proxys = [line.strip() for line in proxy_file]
        return proxys


def go_sleep(sleeping_min, sleeping_max):
    x = random.randint(sleeping_min, sleeping_max)
    for _ in tqdm(range(x), desc='sleep ', bar_format='{desc}: {n_fmt}/{total_fmt}'):
        time.sleep(1)


address2ua = {}
def get_default_mint_fun_headers(acc):
    if acc.address not in address2ua:
        address2ua[acc.address] = ua_generator.generate(device='desktop', browser='chrome')
    ua = address2ua[acc.address]

    return {
        'authority': 'mint.fun',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://mint.fun',
        'pragma': 'no-cache',
        'referer': 'https://mint.fun/',
        'sec-ch-ua': f'"{ua.ch.brands[2:]}"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': f'"{ua.platform.title()}"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': ua.text,
    }
