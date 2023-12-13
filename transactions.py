import requests
from eth_account import Account
from loguru import logger
from web3 import Web3

from abis import bridge_eth_abi, zora_nft_abi
from config import minfun_nfts, use_proxy, PAUSA_MAX, PAUSA_MIN
from consts import RPCS
from services import Dapp, get_default_mint_fun_headers, go_sleep

def bridge_eth_to_zora(acc: Account, amount: float):
    amount_wei = Web3.to_wei(amount, 'ether')
    bridge_addy = '0x1a0ad011913A150f69f6A19DF447A0CfD9551054'
    bridge = Dapp('eth', bridge_addy, bridge_eth_abi)
    txn_hash = bridge.send_eip1559_txn(
        acc,
        'depositTransaction',
        [acc.address, amount_wei, 100000, False, b''],
        amount_wei,
        float(Web3.from_wei(bridge.w3.eth.gas_price, 'gwei')) + 0.5,  # MaxFeePerGas
        0.05  # MaxPriorityFee
    )
    go_sleep(PAUSA_MIN, PAUSA_MAX)
    return txn_hash


def mint_on_zora(acc: Account, current_account, zora_nft_addy: str, proxys=None):
    if use_proxy and proxys:
        proxy_list = proxys[current_account].split(':')
        proxy = f'http://{proxy_list[2]}:{proxy_list[3]}@{proxy_list[0]}:{proxy_list[1]}'
        web3 = Web3(
            Web3.HTTPProvider(RPCS.get('zora'), request_kwargs={"proxies": {'https': proxy, 'http': proxy}}))
    else:
        web3 = Web3(Web3.HTTPProvider(RPCS.get('zora')))

    zora_nft = web3.eth.contract(address=web3.to_checksum_address(zora_nft_addy),
                                 abi=zora_nft_abi)
    mint_txn = zora_nft.functions.mintWithRewards(
        acc.address,
        1,
        '',
        '0x0000000000000000000000000000000000000000'
    ).build_transaction({
        'from': acc.address,
        "nonce": web3.eth.get_transaction_count(acc.address),
        'chainId': web3.eth.chain_id,
        'value': Web3.to_wei(0.000777, 'ether'),
        'maxPriorityFeePerGas': int(0.005 * 10 ** 9),
        'maxFeePerGas': int(0.005 * 10 ** 9)
    })

    logger.info(f'[{acc.address}] Mint NFT:')
    signed_tx = web3.eth.account.sign_transaction(mint_txn, acc.key)
    txn_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.rawTransaction))
    status = web3.eth.wait_for_transaction_receipt(txn_hash, timeout=360).status
    if status == 1:
        tx_link = f'https://explorer.zora.energy/tx/{txn_hash}'
        logger.success(f'Success: {tx_link}')
    else:
        logger.error(f'Error mint!')
    go_sleep(PAUSA_MIN, PAUSA_MAX)
    return txn_hash


def mint_mintfun(acc: Account, current_account, proxys=None):
    for minfun_nft_addy, amount in minfun_nfts.items():
        if use_proxy and proxys:
            proxy_list = proxys[current_account].split(':')
            proxy = f'http://{proxy_list[2]}:{proxy_list[3]}@{proxy_list[0]}:{proxy_list[1]}'
            web3 = Web3(
                Web3.HTTPProvider(RPCS.get('zora'), request_kwargs={"proxies": {'https': proxy, 'http': proxy}}))
        else:
            web3 = Web3(Web3.HTTPProvider(RPCS.get('zora')))

        nft = web3.eth.contract(address=web3.to_checksum_address(minfun_nft_addy),
                                abi='[{"inputs":[{"internalType":"uint256","name":"quantity","type":"uint256"}],"name":"mint","outputs":[],"stateMutability":"payable","type":"function"}]')

        mint_txn = nft.functions.mint(amount).build_transaction({
            'from': acc.address,
            "nonce": web3.eth.get_transaction_count(acc.address),
            'chainId': web3.eth.chain_id,
            'value': 0,
            'maxPriorityFeePerGas': int(0.005 * 10 ** 9),
            'maxFeePerGas': int(0.005 * 10 ** 9)
        })

        signed_tx = web3.eth.account.sign_transaction(mint_txn, acc.key)
        txn_hash = web3.to_hex(web3.eth.send_raw_transaction(signed_tx.rawTransaction))
        tx_link = f'https://explorer.zora.energy/tx/{txn_hash}'
        logger.info(f'[{acc.address}] Mint {amount} Free NFT')
        status = web3.eth.wait_for_transaction_receipt(txn_hash).status

        if status != 1:
            logger.error(f"[{acc.address}] transaction failed | {tx_link}")
            continue

        logger.success(f"Success minted: {tx_link}")

        http_proxies = {}
        if use_proxy and proxys:
            http_proxies = {'http': proxy, 'https': proxy}

        try:
            requests.post('https://mint.fun/api/mintfun/submit-tx',
                          json={
                              'address': str(acc.address),
                              'hash': txn_hash,
                              'isAllowlist': False,
                              'chainId': 7777777,
                              'source': 'projectPage',
                          },
                          headers=get_default_mint_fun_headers(acc),
                          proxies=http_proxies)

            logger.success(f'Mint: Mint.fun points added')
        except Exception as mfe:
            logger.error(f'Mint: Error claiming mint.fun points: {mfe}', color='red')
        go_sleep(PAUSA_MIN, PAUSA_MAX)
