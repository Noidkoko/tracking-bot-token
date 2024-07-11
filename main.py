import logging
from aiogram import Bot, Dispatcher, executor, types
import aiohttp  # Pour les requêtes asynchrones HTTP
import aiogram
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, date, timedelta
import time
import json
from collections import defaultdict


from urllib.parse import quote

# Au début du fichier, après les imports
message_ids = {}

# Configurations
API_TOKEN = '7434584612:AAE9KkHcCQwIbEcaMC-xBxMzrFzNRLzReMc'
TON_API_KEY = 'AEPUWOTKOWQ6N4AAAAANXAT5ZOSYTZNK67Z2FLJBRQUQUVQRYG3EFWE2GAPNRNJVOE3TZBQ'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialisation du bot et du dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

async def fetch(session, url, headers):
    async with session.get(url, headers=headers) as response:
        response_text = await response.text()
        try:
            response_json = await response.json()
            return response_json
        except Exception:
            with open('response_dump.txt', 'w', encoding='utf-8') as file:
                file.write(response_text)
            raise ValueError(f"Failed to parse JSON response, content saved to 'response_dump.txt'. Error: {response_text}")

async def get_token_info(token_address):
    headers = {'Authorization': f'Bearer {TON_API_KEY}'}
    url = f"https://tonapi.io/v2/jettons/{token_address}"  # Correction de l'URL ici pour obtenir les infos jetton
    print(url)
    async with aiohttp.ClientSession() as session:
        try:
            response = await fetch(session, url, headers)
            return response
        except Exception as e:
            logging.error(f"Failed to get token info: {e}")
            return None

async def get_token_price(token_address):
    url = f"https://api.dexscreener.io/latest/dex/tokens/{token_address}"
    headers = {'Content-Type': 'application/json'}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logging.error(f"Failed to retrieve token price: {response.status}")
                return None

def get_square_number_emoji(number):
    square_numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    return square_numbers[number - 1] if 1 <= number <= 10 else str(number)


@dp.message_handler(commands=['scan'])
async def scan_token(message: types.Message):
    track_usage('scan')
    token_address = message.get_args()
    
    if not token_address:
        await message.reply("Please enter a correct address.")
        return
    
    token_info = await get_token_info(token_address)  # Cette fonction appelle l'API et récupère les données
    price_info = await get_token_price(token_address)  # Récupération des données de prix
    price = price_info['pairs'][0]['priceUsd'] if price_info and price_info['pairs'] else 'Non disponible'
    
    # Utilisation de .get() pour éviter KeyError
    admin_info = token_info.get('admin', {})
    metadata = token_info.get('metadata', {})

    # Default values in case of missing data
    price = price_info['pairs'][0]['priceUsd'] if price_info and price_info['pairs'] else 'Not available'
    market_cap = f"${price_info['pairs'][0].get('marketCapUsd', 'Not available')}"
    liquidity = f"${price_info['pairs'][0].get('liquidity', {}).get('usd', 'Not available')}"
    price_change_24h = f"{price_info['pairs'][0].get('priceChange', {}).get('h24', 'Not available')}%"
    volume_24h = f"${price_info['pairs'][0].get('volume', {}).get('h24', 'Not available')}"
    launch_market_cap = f"${price_info['pairs'][0].get('launchMarketCapUsd', 'Not available')}"
    ath_price = f"${price_info['pairs'][0].get('athPrice', 'Not available')}"

    # Construction du message avec les données de l'API
    response_message = (
        f"📌 *Token:* [{metadata.get('name', 'Non disponible')}](https://tonviewer.com/{token_address})\n\n"

        f"💲 *Current Price:* `${price}`\n\n"

        f"💰 *Market Cap:* {market_cap} | *Liquidity:* {liquidity}\n"
        f"📈 *24h Change:* {price_change_24h} | *24h Volume:* {volume_24h}\n"
        f"💵 *Launch Market Cap:* {launch_market_cap}\n"
        f"👆 *All-Time High (ATH):* {ath_price}\n\n"

        f"⚠️ *Mintable:* `{token_info.get('mintable', 'Non disponible')}`\n"
        f"📦 *Total Supply:* `{token_info.get('total_supply', 'Non disponible')}`\n"
        f"👤 *Admin Address:* [{admin_info.get('address', 'Non disponible')}](https://tonviewer.com/{admin_info.get('address', 'Non disponible')})\n"
        f"📛 *Admin Name:* `{admin_info.get('name', 'Non disponible')}`\n"
        f"🚨 *Is Scam:* `{admin_info.get('is_scam', 'Non disponible')}`\n"
        f"🔖 *Metadata Address:* [{metadata.get('address', 'Non disponible')}](https://tonviewer.com/{metadata.get('address', 'Non disponible')})\n"
        f"🏷️ *Token Name:* `{metadata.get('name', 'Non disponible')}`\n"
        f"📐 *Symbol:* `{metadata.get('symbol', 'Non disponible')}`\n"
        f"🔢 *Decimals:* `{metadata.get('decimals', 'Non disponible')}`\n"
        f"📝 *Description:* `{metadata.get('description', 'Non disponible')}`\n\n"


        f"🌐 *Social Links:* " +
        " | ".join([f"[{site.split('/')[-1]}]({site})" for site in metadata.get('social', [])]) + "\n"
        f"🔗 *Websites:* " +
        " | ".join([f"[{site.split('/')[-1]}]({site})" for site in metadata.get('websites', [])]) + "\n"
        f"🏦 *Catalogs:* " +
        " | ".join([f"[{site.split('/')[-1]}]({site})" for site in metadata.get('catalogs', [])]) + "\n"
        f"✔️ *Verification:* `{token_info.get('verification', 'Non disponible')}`\n"
        f"👥 *Holders Count:* `{token_info.get('holders_count', 'Non disponible')}`"
    )

    # Ajout des boutons interactifs
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Chart", url=f"https://dexscreener.com/ton/{token_address}"),
                 InlineKeyboardButton("Holders", callback_data=f"holders|{token_address}"))
    keyboard.add(InlineKeyboardButton("Refresh", callback_data=f"refresh|{token_address}"))

    sent_message = await message.answer(response_message, parse_mode='Markdown', reply_markup=keyboard)
    message_ids[token_address] = sent_message.message_id
    
@dp.callback_query_handler(lambda c: c.data.startswith('refresh|'))
async def handle_refresh(callback_query: types.CallbackQuery):
    token_address = callback_query.data.split('|')[1]
    
    token_info = await get_token_info(token_address)
    price_info = await get_token_price(token_address)
    
    if not token_info or not price_info:
        await callback_query.answer("Failed to fetch token info.", show_alert=True)
        return

    admin_info = token_info.get('admin', {})
    metadata = token_info.get('metadata', {})

    price = price_info['pairs'][0]['priceUsd'] if price_info and price_info['pairs'] else 'Not available'
    market_cap = f"${price_info['pairs'][0].get('fdv', 'Not available')}"
    liquidity = f"${price_info['pairs'][0].get('liquidity', {}).get('usd', 'Not available')}"
    price_change_24h = f"{price_info['pairs'][0].get('priceChange', {}).get('h24', 'Not available')}%"
    volume_24h = f"${price_info['pairs'][0].get('volume', {}).get('h24', 'Not available')}"
    launch_market_cap = f"${price_info['pairs'][0].get('launchMarketCapUsd', 'Not available')}"
    ath_price = f"${price_info['pairs'][0].get('athPrice', 'Not available')}"

    response_message = (
        f"📌 *Token:* [{metadata.get('name', 'Non disponible')}](https://tonviewer.com/{token_address})\n\n"
        f"💲 *Current Price:* `${price}`\n\n"
        f"💰 *Market Cap:* {market_cap} | *Liquidity:* {liquidity}\n"
        f"📈 *24h Change:* {price_change_24h} | *24h Volume:* {volume_24h}\n"
        f"💵 *Launch Market Cap:* {launch_market_cap}\n"
        f"👆 *All-Time High (ATH):* {ath_price}\n\n"
        f"⚠️ *Mintable:* `{token_info.get('mintable', 'Non disponible')}`\n"
        f"📦 *Total Supply:* `{token_info.get('total_supply', 'Non disponible')}`\n"
        f"👤 *Admin Address:* [{admin_info.get('address', 'Non disponible')}](https://tonviewer.com/{admin_info.get('address', 'Non disponible')})\n"
        f"📛 *Admin Name:* `{admin_info.get('name', 'Non disponible')}`\n"
        f"🚨 *Is Scam:* `{admin_info.get('is_scam', 'Non disponible')}`\n"
        f"🔖 *Metadata Address:* [{metadata.get('address', 'Non disponible')}](https://tonviewer.com/{metadata.get('address', 'Non disponible')})\n"
        f"🏷️ *Token Name:* `{metadata.get('name', 'Non disponible')}`\n"
        f"📐 *Symbol:* `{metadata.get('symbol', 'Non disponible')}`\n"
        f"🔢 *Decimals:* `{metadata.get('decimals', 'Non disponible')}`\n"
        f"📝 *Description:* `{metadata.get('description', 'Non disponible')}`\n\n"
        f"🌐 *Social Links:* " +
        " | ".join([f"[{site.split('/')[-1]}]({site})" for site in metadata.get('social', [])]) + "\n"
        f"🔗 *Websites:* " +
        " | ".join([f"[{site.split('/')[-1]}]({site})" for site in metadata.get('websites', [])]) + "\n"
        f"🏦 *Catalogs:* " +
        " | ".join([f"[{site.split('/')[-1]}]({site})" for site in metadata.get('catalogs', [])]) + "\n"
        f"✔️ *Verification:* `{token_info.get('verification', 'Non disponible')}`\n"
        f"👥 *Holders Count:* `{token_info.get('holders_count', 'Non disponible')}`"
    )

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Chart", url=f"https://dexscreener.com/ton/{token_address}"),
                 InlineKeyboardButton("Holders", callback_data=f"holders|{token_address}"))
    keyboard.add(InlineKeyboardButton("Refresh", callback_data=f"refresh|{token_address}"))

    try:
        await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
    except aiogram.utils.exceptions.MessageNotModified:
        pass

    await callback_query.answer()

async def fetch_token_holders(token_address, limit=10):
    headers = {'Authorization': f'Bearer {TON_API_KEY}'}
    print(token_address)
    url = f"https://tonapi.io/v2/jettons/{token_address}/holders?limit={limit}"
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, headers=headers)
        if response.status == 200:
            data = await response.json()
            return data.get('addresses', [])
        else:
            print(f"Failed to fetch data: {response.status} {await response.text()}")
            return None

@dp.callback_query_handler(lambda c: c.data.startswith('holders|'))
async def handle_holders(callback_query: types.CallbackQuery):
    token_address = callback_query.data.split('|')[1]
    token_info = await get_token_info(token_address)
    price_info = await get_token_price(token_address)
   
    if not token_info or not price_info:
        await callback_query.answer("Failed to fetch token info.", show_alert=True)
        return

    current_price = float(price_info['pairs'][0]['priceUsd']) if price_info and price_info.get('pairs') else 0
    total_supply = int(token_info.get('total_supply', '1'))
    token_symbol = token_info.get('metadata', {}).get('symbol', '')
    holders = await fetch_token_holders(token_address, limit=10)  # Fetch top 10 holders

    if not holders:
        await callback_query.answer("Failed to fetch token holders or no holders found.", show_alert=True)
        return

    response_message = "👥 *Top Token Holders:*\n\n"
    keyboard = InlineKeyboardMarkup()
    buttons = []

    for i, holder in enumerate(holders[:10], 1):  # Limite à 10 holders pour s'assurer d'avoir assez d'emojis
        balance = int(holder['balance'])
        balance_percent = (balance / total_supply) * 100 if total_supply else 0
        wallet_value_usd = balance * current_price
        address = holder['owner']['address']
        short_address = f"{address}"
        
        square_number = get_square_number_emoji(i)
        
        response_message += (
            f"{square_number} `{short_address}`\n├─💰*{balance:,} {token_symbol}*\n"
            f"├─💵 *~${wallet_value_usd:,.2f}*\n└─📊 `{balance_percent:.2f}%` of total supply\n\n"
        )
        buttons.append(InlineKeyboardButton(f"🔎 SCAN {i}", callback_data=f"scan_holder|{token_address}|{i}"))

    # Ajouter les boutons en deux colonnes
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.row(buttons[i], buttons[i+1])
        else:
            keyboard.row(buttons[i])

    keyboard.row(InlineKeyboardButton("Chart", url=f"https://dexscreener.com/ton/{token_address}"),
                InlineKeyboardButton("Refresh", callback_data=f"holders|{token_address}"))
    keyboard.add(InlineKeyboardButton("Back to Token Info", callback_data=f"refresh|{token_address}"))

    try:
        await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
    except aiogram.utils.exceptions.MessageNotModified:
        pass
    except aiogram.utils.exceptions.MessageToEditNotFound:
        # Si le message à éditer n'est pas trouvé, envoyez un nouveau message
        await callback_query.message.answer(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)

    await callback_query.answer()
    

async def analyze_transactions(token_address, limit=1000):
    # Fetch token info
    token_info = await get_token_info(token_address)
    if not token_info:
        return "Failed to fetch token information."

    total_supply = int(token_info.get('total_supply', '1'))
    token_symbol = token_info.get('metadata', {}).get('symbol', 'TOKEN')

    # Fetch top holders
    holders = await fetch_token_holders(token_address, limit=10)
    if not holders:
        return "Failed to fetch holders information."

    suspicious_activities = []

    for holder in holders:
        holder_address = holder['owner']['address']
        holder_balance = int(holder['balance'])
        holder_percentage = (holder_balance / total_supply) * 100

        transactions = await get_recent_transactions(holder_address, limit)
        if not transactions:
            continue

        out_transactions = []
        large_transactions = []
        token_transfers = []

        for tx in transactions:
            tx_type = "IN" if tx.get('in_msg', {}).get('source') else "OUT"
            if tx_type == "OUT":
                for out_msg in tx.get('out_msgs', []):
                    amount = float(out_msg.get('value', 0)) / 1e9
                    tx_hash = tx.get('transaction_id', {}).get('hash', 'Unknown')
                    destination = out_msg.get('destination', 'Unknown')

                    out_transactions.append((amount, tx_hash, destination))

                    if amount > total_supply * 0.01:  # Transactions larger than 1% of total supply
                        large_transactions.append((amount, tx_hash, destination))

                    # Check for token transfers
                    if out_msg.get('message', '').startswith('te6'):  # This might indicate a token transfer
                        token_transfers.append((tx_hash, destination))

        if out_transactions or large_transactions or token_transfers:
            activity = f"Address: {holder_address[:6]}...{holder_address[-6:]}\n"
            activity += f"Balance: {holder_balance} {token_symbol} ({holder_percentage:.2f}% of supply)\n\n"

            if out_transactions:
                activity += f"OUT transactions ({len(out_transactions)}):\n"
                for amount, tx_hash, destination in out_transactions[:5]:  # Show top 5
                    activity += f"  • {amount:.2f} TON to {destination[:6]}...{destination[-6:]}\n"
                    activity += f"    TX: {tx_hash}\n"

            if large_transactions:
                activity += f"\nLarge transactions ({len(large_transactions)}):\n"
                for amount, tx_hash, destination in large_transactions[:5]:  # Show top 5
                    activity += f"  • {amount:.2f} TON to {destination[:6]}...{destination[-6:]}\n"
                    activity += f"    TX: {tx_hash}\n"

            if token_transfers:
                activity += f"\nPotential {token_symbol} transfers ({len(token_transfers)}):\n"
                for tx_hash, destination in token_transfers[:5]:  # Show top 5
                    activity += f"  • To: {destination[:6]}...{destination[-6:]}\n"
                    activity += f"    TX: {tx_hash}\n"

            suspicious_activities.append(activity)

    if not suspicious_activities:
        return "No suspicious activity detected."
    else:
        response = f"Analysis for {token_symbol} ({token_address[:6]}...{token_address[-6:]}):\n\n"
        response += "Potential suspicious activities:\n\n"
        response += "\n---\n".join(suspicious_activities)
        return response

@dp.callback_query_handler(lambda c: c.data.startswith('scan_holder|'))
async def handle_scan_holder(callback_query: types.CallbackQuery):
    _, token_address, holder_index = callback_query.data.split('|')
    holder_index = int(holder_index) - 1
    
    print(f"\n--- API Call Results for Token: {token_address}, Holder Index: {holder_index} ---")
    
    token_info = await get_token_info(token_address)
    print("\nToken Info:")
    print(json.dumps(token_info, indent=2))
    
    price_info = await get_token_price(token_address)
    print("\nPrice Info:")
    print(json.dumps(price_info, indent=2))
    
    holders = await fetch_token_holders(token_address)
    print("\nHolders Info:")
    print(json.dumps(holders, indent=2))
    
    if not token_info or not price_info or not holders or holder_index >= len(holders):
        await callback_query.answer("❌ Failed to fetch information.", show_alert=True)
        print("❌ Failed to fetch complete information.")
        return
    
    holder_address = holders[holder_index]['owner']['address']
    holder_info = holders[holder_index]
    print("\nSelected Holder Info:")
    print(json.dumps(holder_info, indent=2))
    
    recent_transactions = await get_recent_transactions(holder_address)
    print("\nRecent Transactions:")
    print(json.dumps(recent_transactions, indent=2))
    
    # Le reste de votre code reste inchangé...
    token_symbol = token_info.get('metadata', {}).get('symbol', '')
    current_price = float(price_info['pairs'][0]['priceUsd']) if price_info and price_info.get('pairs') else 0
    total_supply = int(token_info.get('total_supply', '1'))
    balance = int(holder_info.get('balance', 0))
    balance_percent = (balance / total_supply) * 100 if total_supply else 0
    wallet_value_usd = balance * current_price
    
    response_message = (
        f"📍 *Address:* [{holder_address[:6]}...{holder_address[-6:]}](https://tonviewer.com/{holder_address})\n"
        f"💰 *Balance:* `{balance:,}` {token_symbol}\n"
        f"💵 *Value:* ~$`{wallet_value_usd:,.2f}`\n"
        f"📊 *Percentage:* `{balance_percent:.2f}%` of total supply\n\n"
        f"💲 *Recent Transactions:*\n"
    )
    
    if recent_transactions:
        for tx in recent_transactions[:5]:
            tx_type = "IN" if tx.get('in_msg', {}).get('source') else "OUT"
            amount = tx.get('in_msg', {}).get('value', 0) if tx_type == "IN" else tx.get('out_msgs', [{}])[0].get('value', 0)
            amount = float(amount) / 1e9
            timestamp = datetime.fromtimestamp(tx.get('utime', 0)).strftime('%Y-%m-%d %H:%M:%S')
            tx_hash = tx.get('transaction_id', {}).get('hash', '')
            tx_link = f"https://tonviewer.com/transaction/{tx_hash}"
            
            if tx_type == "IN":
                from_address = tx.get('in_msg', {}).get('source', 'Unknown')
                to_address = tx.get('in_msg', {}).get('destination', 'Unknown')
                emoji = "🟢"
            else:
                from_address = tx.get('out_msgs', [{}])[0].get('source', 'Unknown')
                to_address = tx.get('out_msgs', [{}])[0].get('destination', 'Unknown')
                emoji = "🔴"
            
            short_from = f"{from_address[:6]}...{from_address[-6:]}" if from_address != 'Unknown' else 'Unknown'
            short_to = f"{to_address[:6]}...{to_address[-6:]}" if to_address != 'Unknown' else 'Unknown'
            
            response_message += (
                f"{emoji} *{tx_type}:* `{amount:.2f} TON`\n"
                f"├─⏰ *Time:* `{timestamp}`\n"
                f"├─👤 *From:* `{short_from}`\n"
                f"├─👥 *To:* `{short_to}`\n"
                f"└─🔗 [View Transaction]({tx_link})\n\n"
            )
    else:
        response_message += "❌ No recent transactions found.\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔍 Analyze Suspicious Activity", callback_data=f"analyze|{token_address}|{holder_index+1}"))
    keyboard.add(InlineKeyboardButton("🔄 Refresh", callback_data=f"scan_holder|{token_address}|{holder_index+1}"))
    keyboard.add(InlineKeyboardButton("🔙 Back to Holders", callback_data=f"holders|{token_address}"))
    
    try:
        await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
    except aiogram.utils.exceptions.MessageNotModified:
        await callback_query.answer("Data is up to date!")
    
    print("\n--- End of API Call Results ---\n")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('analyze|'))
async def handle_analyze_suspicious(callback_query: types.CallbackQuery):
    _, token_address, holder_index = callback_query.data.split('|')
    holder_index = int(holder_index) - 1
    
    holders = await fetch_token_holders(token_address)
    if not holders or holder_index >= len(holders):
        await callback_query.answer("Failed to fetch holder information.", show_alert=True)
        return
    
    holder_address = holders[holder_index]['owner']['address']
    
    await callback_query.answer("Analyzing transactions... This may take a moment.")
    
    suspicious_activity = await analyze_transactions(holder_address)
    
    response_message = f"🚨 *Suspicious Activity Analysis for {holder_address[:6]}...{holder_address[-6:]}:*\n\n{suspicious_activity}\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Back to Holder Info", callback_data=f"scan_holder|{token_address}|{holder_index+1}"))
    
    try:
        await callback_query.message.edit_text(response_message, parse_mode='Markdown', reply_markup=keyboard, disable_web_page_preview=True)
    except aiogram.utils.exceptions.MessageNotModified:
        await callback_query.answer("No changes in analysis results.")

async def get_holder_info(holder_address, token_address):
    # Obtenir les informations du holder pour le token spécifique
    headers = {'Authorization': f'Bearer {TON_API_KEY}'}
    url = f"https://tonapi.io/v2/jettons/{token_address}/holders?addresses={holder_address}"
    async with aiohttp.ClientSession() as session:
        response = await session.get(url, headers=headers)
        if response.status == 200:
            data = await response.json()
            holder_data = data.get('addresses', [])[0] if data.get('addresses') else None
            return holder_data
        else:
            print(f"Failed to fetch holder data: {response.status}")
            return None

async def get_recent_transactions(holder_address, limit=100):
    url = f"https://toncenter.com/api/v2/getTransactions?address={holder_address}&limit={limit}&to_lt=0&archival=false"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('result', [])
                else:
                    print(f"Failed to fetch transactions: {response.status}")
                    return []
        except Exception as e:
            print(f"Error fetching transactions: {str(e)}")
            return []

def track_usage(command_name):
    current_date = date.today().isoformat()
    filename = f"{command_name}_usage.txt"
    try:
        # Read existing data
        with open(filename, 'r+') as file:
            lines = file.readlines()
            last_line = lines[-1].strip() if lines else ""
            last_date, last_count = last_line.split(',') if last_line else (None, 0)
            
            if last_date == current_date:
                # Update current date's count
                new_count = int(last_count) + 1
                lines[-1] = f"{current_date},{new_count}\n"
            else:
                # Add new date with count 1
                lines.append(f"{current_date},1\n")
            
            # Write back to file
            file.seek(0)
            file.writelines(lines)
            file.truncate()
    except FileNotFoundError:
        # If file doesn't exist, create it and add today's date with count 1
        with open(filename, 'w') as file:
            file.write(f"{current_date},1\n")

def show_usage_stats(command_name):
    filename = f"{command_name}_usage.txt"
    try:
        with open(filename, 'r') as file:
            print(f"Usage stats for {command_name}:")
            for line in file:
                date, count = line.strip().split(',')
                print(f"Date: {date}, Count: {count}")
    except FileNotFoundError:
        print("No usage data available.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
