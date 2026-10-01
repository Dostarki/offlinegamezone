"""Create/cleanup disposable wallet fixtures for injected-browser gameplay testing."""

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from motor.motor_asyncio import AsyncIOMotorClient

import sys
sys.path.insert(0, '/app/backend')
from player_accounts import sync_db_to_file


ROOT = Path('/app')
FIXTURE_PATH = ROOT / 'test_reports' / 'browser_wallet_fixture.json'


def _load_env():
    load_dotenv(ROOT / 'frontend' / '.env')
    load_dotenv(ROOT / 'backend' / '.env')
    mongo_url = (os.environ.get('MONGO_URL') or '').strip().strip('"')
    db_name = (os.environ.get('DB_NAME') or '').strip().strip('"')
    if not mongo_url or not db_name:
        raise RuntimeError('MONGO_URL/DB_NAME are required')
    return mongo_url, db_name


async def _seed_fixture(address: str, mongo_url: str, db_name: str):
    client = AsyncIOMotorClient(mongo_url)
    try:
        db = client[db_name]
        account_id = address.lower()
        now_iso = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        await db.access_entitlements.update_one(
            {'account_id': account_id},
            {'$set': {
                'account_id': account_id,
                'paid': True,
                'chain_id': 4663,
                'source_order_id': 'TEST_ONLY_BROWSER_ENTITLEMENT',
                'tx_hash': '0x' + '2' * 64,
                'quote': {'test_only': True, 'source': 'browser_wallet_fixture'},
                'confirmed_at': now_iso,
            }},
            upsert=True,
        )

        await db.player_progress.update_one(
            {'account_id': account_id},
            {'$set': {
                'account_id': account_id,
                'revision': 1,
                'unlocked_weapons': ['glock18', 'ak47'],
                'equipped_weapon': 'glock18',
                'inventory': {
                    'glock18': {'ammo': 17, 'reserve': 0, 'infinite_reserve': True},
                    'ak47': {'ammo': 30, 'reserve': 90, 'infinite_reserve': False},
                },
                'weapon_parts': [
                    {'id': 'barrel_common', 'tier': 1},
                    {'id': 'receiver_uncommon', 'tier': 2},
                    {'id': 'optic_rare', 'tier': 3},
                ],
            }},
            upsert=True,
        )

        await sync_db_to_file(db)
    finally:
        client.close()


async def _cleanup_fixture(address: str, mongo_url: str, db_name: str):
    client = AsyncIOMotorClient(mongo_url)
    try:
        db = client[db_name]
        account_id = address.lower()
        await db.auth_challenges.delete_many({'account_id': account_id})
        await db.auth_sessions.delete_many({'account_id': account_id})
        await db.purchase_orders.delete_many({'account_id': account_id})
        await db.access_entitlements.delete_many({'account_id': account_id})
        await db.player_progress.delete_many({'account_id': account_id})
        await db.player_accounts.delete_many({'account_id': account_id})
        await sync_db_to_file(db)
    finally:
        client.close()


def create_fixture():
    mongo_url, db_name = _load_env()
    account = Account.create()
    payload = {
        'address': account.address.lower(),
        'private_key': account.key.hex(),
        'created_at': int(time.time()),
        'test_only': True,
    }
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(payload), encoding='utf-8')
    asyncio.run(_seed_fixture(payload['address'], mongo_url, db_name))
    print(json.dumps({'fixture': str(FIXTURE_PATH), 'address': payload['address']}))


def cleanup_fixture():
    mongo_url, db_name = _load_env()
    if not FIXTURE_PATH.exists():
        print(json.dumps({'cleanup': 'skipped', 'reason': 'fixture file missing'}))
        return
    payload = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))
    asyncio.run(_cleanup_fixture(payload['address'], mongo_url, db_name))
    FIXTURE_PATH.unlink(missing_ok=True)
    print(json.dumps({'cleanup': 'done', 'address': payload['address']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['create', 'cleanup'])
    args = parser.parse_args()
    if args.action == 'create':
        create_fixture()
    else:
        cleanup_fixture()
