import random

from eth_account import Account
from loguru import logger

from config import amount_to_bridge, use_proxy, zora_nfts
from services import get_proxys, get_accounts
from transactions import bridge_eth_to_zora, mint_on_zora, mint_mintfun
from sys import stderr

logger.remove()
logger.add(stderr, format="<white>{time:HH:mm:ss}</white> | <level>{level: <3}</level> | <level>{message}</level>")

def use_menu(accs: [Account]):
    option = int(input(
        f'\n1. Бридж ETH -> Zora\n'
        f'2. Mint NFTs on Zora\n'
        f'3. Mint Mint.fun\n'
        f'0. Выход\n'
        f'Действие номер: '
    ))

    if option not in range(1, 4):
        quit('Пока!')

    proxys = None
    if use_proxy:
        proxys = get_proxys()

    if option == 1:
        for acc_num, acc in enumerate(accs):
            amount = round(random.uniform(*amount_to_bridge), 5)
            try:
                bridge_eth_to_zora(acc, amount)
            except Exception as e:
                logger.error(f'[{acc.address}] Bridge Error: {e}')

    elif option == 2:
        for acc_num, acc in enumerate(accs):
            for nft in zora_nfts:
                try:
                    mint_on_zora(acc, acc_num, nft, proxys=proxys)
                except Exception as e:
                    logger.error(f'[{acc.address}] {nft} Mint Error: {e}')

    elif option == 3:
        for acc_num, acc in enumerate(accs):
            try:
                mint_mintfun(acc, acc_num, proxys=proxys)
            except Exception as e:
                logger.error(f'[{acc.address}] Mint Error: {e}')

    return use_menu(accs)



if __name__ == '__main__':
    accounts = get_accounts('keys.txt')
    use_menu(accounts)



