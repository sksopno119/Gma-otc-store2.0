from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import json
import asyncio
import logging
import random
import string
from datetime import datetime

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_balances():
    # Try loading from main file
    try:
        with open('balances.json', 'r') as f:
            data = json.loads(f.read())
            return ensure_data_structure(data)
    except (FileNotFoundError, json.JSONDecodeError):
        # If main file fails, try loading from backup
        try:
            with open('balances_backup.json', 'r') as f:
                data = json.loads(f.read())
                return ensure_data_structure(data)
        except (FileNotFoundError, json.JSONDecodeError):
            return get_default_data()

def ensure_data_structure(data):
    # Ensure proper structure
    if 'user_balances' not in data:
        data = {
            'user_balances': data,
            'sold_gmails': [],
            'gmail_price': 0.14,
            'old_gmail_price': 0.14,
            'min_withdrawal': 1.0,
            'how_to_link': 'https://t.me/+djhhtndhA1FjZWZl',
            '2fa_price': 0.25,
            'complete_price': 0.22,
            'referrals': {},
            'all_users_ever': [],
            'user_metadata': {}
        }
    if 'referrals' not in data: data['referrals'] = {}
    if 'all_users_ever' not in data: data['all_users_ever'] = []
    if 'user_metadata' not in data: data['user_metadata'] = {}
    
    # Ensure all user_balances keys are strings
    if 'user_balances' in data:
        new_balances = {}
        for k, v in data['user_balances'].items():
            new_balances[str(k)] = v
        data['user_balances'] = new_balances
        
    return data

def get_default_data():
    return {
        'user_balances': {},
        'sold_gmails': [],
        'gmail_price': 0.14,
        'old_gmail_price': 0.14,
        'min_withdrawal': 1.0,
        'how_to_link': 'https://t.me/+djhhtndhA1FjZWZl',
        '2fa_price': 0.25,
        'complete_price': 0.22,
        'referrals': {},
        'all_users_ever': [],
        'user_metadata': {}
    }

def save_balances(data):
    try:
        # Save to main database file
        with open('balances.json', 'w') as f:
            json.dump(data, f)
        
        # Create a backup copy
        with open('balances_backup.json', 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving data: {e}")

def get_user_keyboard():
    return ReplyKeyboardMarkup([
        ['➕ Register a new Gmail', '💰 Balance'],
        ['💸 Balance Transfer', '👥 Referral'],
        ['📧 Old Gmail sell', '🛒 Buy Gmail'],
        ['🎧 Support']
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Handle Referral
    if context.args and context.args[0].isdigit():
        referrer_id = context.args[0]
        if referrer_id != str(user_id):
            if str(user_id) not in context.bot_data.get('all_users_ever', []):
                if 'all_users_ever' not in context.bot_data: context.bot_data['all_users_ever'] = []
                context.bot_data['all_users_ever'].append(str(user_id))
                
                # Store who referred this user
                if 'user_metadata' not in context.bot_data: context.bot_data['user_metadata'] = {}
                context.bot_data['user_metadata'][str(user_id)] = {'referrer': referrer_id}
                
                if 'referrals' not in context.bot_data: context.bot_data['referrals'] = {}
                ref_data = context.bot_data['referrals'].get(referrer_id, {'count': 0, 'income': 0, 'history': []})
                ref_data['count'] += 1
                # No instant bonus now, bonus is per successful sell
                context.bot_data['referrals'][referrer_id] = ref_data

    if user_id == 5810613583:  # Admin ID
        keyboard = [
            ['👤 Userinfo', '🔄 Hold', '💰 Main'],
            ['📊 Stats', '💵 Mainusdt', '💎 hoblcon'],
            ['📢 Notification', '❓ Help', '💰 Price Control'],
            ['💸 Min Withdrawal', '🔗 How to', '📧 Old Gmail Price'],
            ['🟢 On', '🔴 Off'],
            ['🎧 Support']
        ]
    else:
        keyboard = [
            ['➕ Register a new Gmail', '💰 Balance'],
            ['💸 Balance Transfer', '👥 Referral'],
            ['📧 Old Gmail sell', '🛒 Buy Gmail'],
            ['🎧 Support']
        ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Welcome! Choose an option below:", reply_markup=reply_markup)

async def finalize_registration(update, context, user_id, price, tfa_info):
    is_old = context.user_data.get('is_old_gmail', False)
    actual_price = context.bot_data.get('old_gmail_price', 0.14) if is_old else price
    
    creds = context.user_data.get('last_gmail_credentials', {})
    address = creds.get('address', 'Unknown')
    password = creds.get('password', 'Unknown')

    if 'sold_gmails' not in context.bot_data: context.bot_data['sold_gmails'] = []
    if address != 'Unknown':
        context.bot_data['sold_gmails'].append(address)

    if str(user_id) not in context.bot_data["user_balances"]:
        context.bot_data["user_balances"][str(user_id)] = {'hold': 0, 'main': 0, 'pending_amounts': {}}
    
    if 'pending_amounts' not in context.bot_data["user_balances"][str(user_id)]:
        context.bot_data["user_balances"][str(user_id)]['pending_amounts'] = {}

    reg_id = str(random.randint(1000, 9999))
    context.bot_data["user_balances"][str(user_id)]['pending_amounts'][reg_id] = {
        'amount': actual_price,
        'address': address
    }
    context.bot_data["user_balances"][str(user_id)]['hold'] += actual_price
    
    admin_chat_id = 5810613583
    admin_message = f"New {'Old ' if is_old else ''}Registration\nID: <code>{user_id}</code>\n2FA: {tfa_info}\nGmail: <code>{address}</code>\nPassword: <code>{password}</code>\nPrice: {actual_price:.2f}"
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_gmail_{user_id}_{reg_id}")],
        [InlineKeyboardButton("❌ Not Registered", callback_data=f"not_registered_gmail_{user_id}_{reg_id}")],
        [InlineKeyboardButton("🚫 Gmail Blocked", callback_data=f"blocked_gmail_{user_id}_{reg_id}")]
    ]
    
    try:
        await context.bot.send_message(chat_id=admin_chat_id, text=admin_message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except: pass

    context.user_data.clear()
    await update.effective_message.reply_text(
        f"✅ Your Gmail registration has been successful. The amount has been added to your Hold Balance. Your Main Balance will be updated within 24 hours.", 
        reply_markup=get_user_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == '🔙 Back' or text == '🔙 Back to Main Menu':
        context.user_data.clear()
        await start(update, context)
        return

    if user_id != 5810613583 and not context.bot_data.get('bot_status', True):
        await update.message.reply_text("🔴 Bot is currently OFF!")
        return

    if str(user_id) not in context.bot_data["user_balances"]:
        context.bot_data["user_balances"][str(user_id)] = {'hold': 0, 'main': 0}

    if text == '💰 Balance':
        user_balances = context.bot_data["user_balances"][str(user_id)]
        hold_balance = user_balances.get('hold', 0)
        main_balance = user_balances.get('main', 0)
        keyboard = [['💸 Withdrawal'], ['🔙 Back to Main Menu']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        balance_text = f"💰 Your Balances:\n\n💰 Hold Balance: {hold_balance:.2f} USDT\n💰 Main Balance: {main_balance:.2f} USDT\n\n👤 Your Chat ID: <code>{user_id}</code>"
        await update.message.reply_text(balance_text, reply_markup=reply_markup, parse_mode='HTML')

    elif text == '➕ Register a new Gmail':
        processing = await update.message.reply_text("🔄 Initializing...")
        await asyncio.sleep(1)
        await processing.delete()
        
        first_names = ["Alexander", "Benjamin", "Christopher", "Daniel", "Edward"]
        last_names = ["Anderson", "Baker", "Carter", "Davis", "Evans"]
        first_name, last_name = random.choice(first_names), random.choice(last_names)
        email_user = ''.join(random.sample(string.ascii_lowercase, 12))
        password = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        gmail_price = context.bot_data.get('2fa_price', 0.25)
        message = f"Register a Gmail account using the specified data and get {gmail_price:.2f}$ USDT\n\nFirst name: {first_name}\nLast name: {last_name}\nGmail address. 👉 <code>{email_user}</code>@gmail.com\nPassword👉 <code>{password}</code>\n\n📌 Be sure to use the specified password"

        keyboard = [
            [InlineKeyboardButton("✅ Done", callback_data="gmail_done")],
            [InlineKeyboardButton("❌ Cancel", callback_data="gmail_cancel")],
            [InlineKeyboardButton("📢 Channel", url="https://t.me/+djhhtndhA1FjZWZl")]
        ]
        context.user_data['last_gmail_credentials'] = {'address': f"{email_user}@gmail.com", 'password': password}
        context.user_data['is_old_gmail'] = False
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif text == '📧 Old Gmail sell':
        processing = await update.message.reply_text("🔄 Loading...")
        await asyncio.sleep(1)
        await processing.delete()
        price = context.bot_data.get('old_gmail_price', 0.14)
        await update.message.reply_text(f"📧 Sell Your Gmail Account\n💰 Price: {price:.2f} USDT\n\nEnter Gmail address:", reply_markup=ReplyKeyboardMarkup([['❌ Cancel']], resize_keyboard=True))
        context.user_data['awaiting_gmail_address'] = True
        context.user_data['is_old_gmail'] = True

    elif text == '❌ Cancel' and (context.user_data.get('awaiting_gmail_address') or context.user_data.get('awaiting_gmail_password')):
        context.user_data.clear()
        await start(update, context)

    elif context.user_data.get('awaiting_gmail_address'):
        context.user_data['gmail_address'] = text
        context.user_data['awaiting_gmail_address'] = False
        context.user_data['awaiting_gmail_password'] = True
        await update.message.reply_text("Enter Gmail password:")

    elif context.user_data.get('awaiting_gmail_password'):
        address = context.user_data.get('gmail_address', '').lower().strip()
        password = text
        if address in context.bot_data.get('sold_gmails', []):
            await update.message.reply_text("❌ Already sold!")
            context.user_data.clear()
            await start(update, context)
            return
        
        context.user_data['last_gmail_credentials'] = {'address': address, 'password': password}
        keyboard = [
            [InlineKeyboardButton("🔒 Add 2FA key", callback_data="enable_2fa")],
            [InlineKeyboardButton("✔️ Done (without 2FA)", callback_data="complete_reg")],
            [InlineKeyboardButton("⊖ Cancel registration", callback_data="gmail_cancel")]
        ]
        await update.message.reply_text("How would you like to proceed?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif context.user_data.get('awaiting_2fa_key'):
        key = text
        price = context.bot_data.get('2fa_price' if not context.user_data.get('is_old_gmail') else 'old_gmail_price', 0.25)
        await finalize_registration(update, context, user_id, price, f"Key: {key}")

    elif text == '💸 Withdrawal':
        min_w = context.bot_data.get('min_withdrawal', 1.0)
        await update.message.reply_text(f"Min Withdrawal: {min_w:.2f} USDT\nSelect Currency:", reply_markup=ReplyKeyboardMarkup([['USDT', 'TON', 'ETH'], ['🔙 Back']], resize_keyboard=True))

    elif text == '🔄 Hold' and user_id == 5810613583:
        await update.message.reply_text("Enter User ID to manage Hold Balance:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['admin_managing_hold_v2'] = True

    elif context.user_data.get('admin_managing_hold_v2'):
        target_id = text
        if target_id not in context.bot_data.get("user_balances", {}):
            await update.message.reply_text("User not found.")
            context.user_data.clear()
            await start(update, context)
            return
        
        user_bal = context.bot_data["user_balances"][target_id]
        context.user_data['target_user_id'] = target_id
        context.user_data['admin_managing_hold_v2'] = False
        
        keyboard = [[InlineKeyboardButton("➕ Add", callback_data=f"adm_hold_add_{target_id}"), 
                     InlineKeyboardButton("➖ Remove", callback_data=f"adm_hold_rem_{target_id}")]]
        await update.message.reply_text(
            f"👤 User: {target_id}\n💰 Hold: {user_bal.get('hold', 0):.2f}\n💰 Main: {user_bal.get('main', 0):.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif text == '💰 Main' and user_id == 5810613583:
        await update.message.reply_text("Enter User ID to manage Main Balance:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['admin_managing_main_v2'] = True

    elif context.user_data.get('admin_managing_main_v2'):
        target_id = text
        if target_id not in context.bot_data.get("user_balances", {}):
            await update.message.reply_text("User not found.")
            context.user_data.clear()
            await start(update, context)
            return
        
        user_bal = context.bot_data["user_balances"][target_id]
        context.user_data['target_user_id'] = target_id
        context.user_data['admin_managing_main_v2'] = False
        
        keyboard = [[InlineKeyboardButton("➕ Add", callback_data=f"adm_main_add_{target_id}"), 
                     InlineKeyboardButton("➖ Remove", callback_data=f"adm_main_rem_{target_id}")]]
        await update.message.reply_text(
            f"👤 User: {target_id}\n💰 Hold: {user_bal.get('hold', 0):.2f}\n💰 Main: {user_bal.get('main', 0):.2f}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif context.user_data.get('awaiting_admin_amount'):
        try:
            amount = float(text)
            target_id = str(context.user_data.get('target_user_id'))
            action = context.user_data.get('admin_action') # add_hold, rem_hold, add_main, rem_main
            
            if target_id not in context.bot_data["user_balances"]:
                context.bot_data["user_balances"][target_id] = {'hold': 0, 'main': 0}
            
            # CRITICAL FIX: Ensure values are treated as floats and dict structure is preserved
            current_hold = float(context.bot_data["user_balances"][target_id].get('hold', 0))
            current_main = float(context.bot_data["user_balances"][target_id].get('main', 0))

            if action == 'add_hold':
                context.bot_data["user_balances"][target_id]['hold'] = current_hold + amount
                msg = f"✅ Added {amount:.2f} to Hold Balance of {target_id}"
            elif action == 'rem_hold':
                context.bot_data["user_balances"][target_id]['hold'] = current_hold - amount
                msg = f"✅ Removed {amount:.2f} from Hold Balance of {target_id}"
            elif action == 'add_main':
                context.bot_data["user_balances"][target_id]['main'] = current_main + amount
                msg = f"✅ Added {amount:.2f} to Main Balance of {target_id}"
            elif action == 'rem_main':
                context.bot_data["user_balances"][target_id]['main'] = current_main - amount
                msg = f"✅ Removed {amount:.2f} from Main Balance of {target_id}"
            
            # Save data immediately to ensure persistence
            save_balances(dict(context.bot_data))
            
            # Send notification to user
            try:
                bal_type = "Hold" if "hold" in action else "Main"
                change_type = "added" if "add" in action else "removed"
                await context.bot.send_message(
                    chat_id=int(target_id),
                    text=f"🔔 *Balance Update*\n\nAdmin has {change_type} *{amount:.2f} USDT* to your *{bal_type} Balance*.",
                    parse_mode='Markdown'
                )
            except: pass

            await update.message.reply_text(msg)
        except:
            await update.message.reply_text("Invalid amount.")
        context.user_data.clear()
        await start(update, context)

    elif text == '📊 Stats' and user_id == 5810613583:
        # Global Statistics calculation
        total_confirmed = 0
        total_blocked = 0
        total_rejected = 0
        all_meta = context.bot_data.get('user_metadata', {})
        for uid in all_meta:
            total_confirmed += all_meta[uid].get('confirmed_count', 0)
            total_blocked += all_meta[uid].get('blocked_count', 0)
            total_rejected += all_meta[uid].get('rejected_count', 0)
            
        stats_text = (
            f"📊 *Global Statistics*\n\n"
            f"✅ Total Confirmed: {total_confirmed}\n"
            f"🚫 Total Blocked: {total_blocked}\n"
            f"❌ Total Rejected: {total_rejected}\n\n"
            f"👥 Total Users: {len(context.bot_data.get('user_balances', {}))}"
        )
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    elif text == '📢 Notification' and user_id == 5810613583:
        keyboard = [['All Users', 'Custom User'], ['🔙 Back']]
        await update.message.reply_text("Choose notification type:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

    elif text == 'All Users' and user_id == 5810613583:
        await update.message.reply_text("Enter message for all users:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['awaiting_broadcast_msg'] = True

    elif context.user_data.get('awaiting_broadcast_msg'):
        msg = text
        count = 0
        for uid in context.bot_data.get('user_balances', {}):
            try:
                await context.bot.send_message(chat_id=int(uid), text=f"📢 *Notification*\n\n{msg}", parse_mode='Markdown')
                count += 1
            except: pass
        await update.message.reply_text(f"✅ Sent to {count} users.")
        context.user_data.clear()
        await start(update, context)

    elif text == 'Custom User' and user_id == 5810613583:
        await update.message.reply_text("Enter User Chat ID:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['awaiting_custom_notif_id'] = True

    elif context.user_data.get('awaiting_custom_notif_id'):
        context.user_data['target_notif_id'] = text
        context.user_data['awaiting_custom_notif_id'] = False
        context.user_data['awaiting_custom_notif_msg'] = True
        await update.message.reply_text("Enter message for this user:")

    elif context.user_data.get('awaiting_custom_notif_msg'):
        target_id = context.user_data.get('target_notif_id')
        try:
            await context.bot.send_message(chat_id=int(target_id), text=f"📢 *Notification*\n\n{text}", parse_mode='Markdown')
            await update.message.reply_text("✅ Message sent.")
        except: await update.message.reply_text("❌ Failed to send.")
        context.user_data.clear()
        await start(update, context)

    elif text == '👤 Userinfo' and user_id == 5810613583:
        await update.message.reply_text("Enter User Chat ID:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['awaiting_user_info_id'] = True

    elif context.user_data.get('awaiting_user_info_id'):
        target_id = text
        if target_id not in context.bot_data.get('user_balances', {}):
            await update.message.reply_text("User not found.")
        else:
            ub = context.bot_data['user_balances'][target_id]
            meta = context.bot_data.get('user_metadata', {}).get(target_id, {})
            confirmed = meta.get('confirmed_count', 0)
            blocked = meta.get('blocked_count', 0)
            rejected = meta.get('rejected_count', 0)
            
            info = f"👤 *User Info: {target_id}*\n\n"
            info += f"💰 Main Balance: {ub.get('main', 0):.2f} USDT\n"
            info += f"💰 Hold Balance: {ub.get('hold', 0):.2f} USDT\n\n"
            info += f"✅ Confirmed: {confirmed}\n"
            info += f"🚫 Blocked: {blocked}\n"
            info += f"❌ Rejected: {rejected}\n\n"
            
            pending = ub.get('pending_amounts', {})
            info += f"⏳ Pending Requests: {len(pending)}\n"
            for rid, pdata in pending.items():
                addr = pdata.get('address', 'Unknown') if isinstance(pdata, dict) else 'Unknown'
                info += f"• `{addr}`\n"
            
            confirmed_list = meta.get('confirmed_addresses', [])
            if confirmed_list:
                info += f"\n📧 Confirmed Gmails:\n"
                for addr in confirmed_list[-10:]:
                    info += f"• `{addr}`\n"
            
            await update.message.reply_text(info, parse_mode='Markdown')
        context.user_data.clear()
        await start(update, context)

    elif text == '🟢 On' and user_id == 5810613583:
        context.bot_data['bot_status'] = True
        await update.message.reply_text("✅ Bot is now ON")

    elif text == '🔴 Off' and user_id == 5810613583:
        context.bot_data['bot_status'] = False
        await update.message.reply_text("🔴 Bot is now OFF")

    elif text == 'Old Gmail Price' and user_id == 5810613583:
        await update.message.reply_text("Enter Old Gmail Price:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['awaiting_old_price'] = True
        
    elif context.user_data.get('awaiting_old_price'):
        try:
            context.bot_data['old_gmail_price'] = float(text)
            await update.message.reply_text("Updated!")
        except: await update.message.reply_text("Invalid")
        context.user_data.clear()
        await start(update, context)

    elif text == '2FA Price' and user_id == 5810613583:
        await update.message.reply_text("Enter 2FA Price:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['awaiting_2fa_price'] = True
        
    elif context.user_data.get('awaiting_2fa_price'):
        try:
            context.bot_data['2fa_price'] = float(text)
            await update.message.reply_text("Updated!")
        except: await update.message.reply_text("Invalid")
        context.user_data.clear()
        await start(update, context)

    elif text == 'Complete Price' and user_id == 5810613583:
        await update.message.reply_text("Enter Complete Price:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))
        context.user_data['awaiting_complete_price'] = True
        
    elif context.user_data.get('awaiting_complete_price'):
        try:
            context.bot_data['complete_price'] = float(text)
            await update.message.reply_text("Updated!")
        except: await update.message.reply_text("Invalid")
        context.user_data.clear()
        await start(update, context)

    elif text == '🛒 Buy Gmail':
        buy_text = (
            "🛒 *Buy Gmail Service*\n\n"
            "Our automated buying system is currently unavailable. However, if you wish to purchase accounts, please message us directly:\n\n"
            "👤 *Support:* @Deploper\_Gmail\_Ofc\_store\n\n"
            "💰 *Pricing:* \n"
            "• 1+ Year Old Account: *0.35 USDT*\n"
            "• 2+ Year Old Account: *0.50 USDT*\n"
            "• 5+ Year Old Account: *1.00 USDT*\n\n"
            "✨ *Custom Orders:* You can also request accounts with specific ages or requirements as per your needs!\n\n"
            "Please send your requirements to our support handle above."
        )
        await update.message.reply_text(buy_text, parse_mode='Markdown')

    elif text == '💸 Balance Transfer':
        await update.message.reply_text("💸 Balance Transfer\nEnter receiver Chat ID:", reply_markup=ReplyKeyboardMarkup([['❌ Cancel']], resize_keyboard=True))
        context.user_data['awaiting_transfer_id'] = True

    elif context.user_data.get('awaiting_transfer_id'):
        if text == '❌ Cancel':
            context.user_data.clear()
            await start(update, context)
            return
        try:
            receiver_id = int(text)
            context.user_data['transfer_receiver_id'] = receiver_id
            context.user_data['awaiting_transfer_id'] = False
            context.user_data['awaiting_transfer_amount'] = True
            await update.message.reply_text("Enter amount to transfer:")
        except ValueError:
            await update.message.reply_text("Invalid ID. Please enter a numerical Chat ID.")

    elif context.user_data.get('awaiting_transfer_amount'):
        if text == '❌ Cancel':
            context.user_data.clear()
            await start(update, context)
            return
        try:
            amount = float(text)
            sender_id = str(user_id)
            receiver_id = str(context.user_data.get('transfer_receiver_id'))
            
            if amount <= 0:
                await update.message.reply_text("Amount must be greater than 0.")
                return

            sender_balance = context.bot_data["user_balances"].get(sender_id, {}).get('main', 0)
            
            if sender_balance >= amount:
                # Deduct from sender
                context.bot_data["user_balances"][sender_id]['main'] -= amount
                # Add to receiver
                if receiver_id not in context.bot_data["user_balances"]:
                    context.bot_data["user_balances"][receiver_id] = {'hold': 0, 'main': 0}
                context.bot_data["user_balances"][receiver_id]['main'] += amount
                
                await update.message.reply_text(f"✅ Successfully transferred {amount:.2f} USDT to {receiver_id}")
                try:
                    await context.bot.send_message(chat_id=int(receiver_id), text=f"💰 You received {amount:.2f} USDT from {sender_id}")
                except: pass
            else:
                await update.message.reply_text("❌ Insufficient Main Balance!")
            
            context.user_data.clear()
            await start(update, context)
        except ValueError:
            await update.message.reply_text("Invalid amount. Please enter a number.")

    elif text == '👥 Referral':
        ref_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
        ref_data = context.bot_data.get('referrals', {}).get(str(user_id), {'count': 0, 'income': 0, 'history': []})
        
        # Calculate last 24h income
        now = datetime.now()
        income_24h = sum(item['amount'] for item in ref_data.get('history', []) 
                        if (now - datetime.fromisoformat(item['time'])).total_seconds() < 86400)
        
        ref_text = (
            f"🤝 *Join Our Referral Program*\n\n"
            f"Invite your friends and earn money! If your referred user successfully sells a Gmail account, you will receive a *0.04 USDT* bonus directly to your *Main Balance*.\n\n"
            f"🔗 *Your Unique Referral Link:*\n`{ref_link}`\n\n"
            f"📊 *Your Statistics:*\n"
            f"• Total Friends Invited: *{ref_data['count']}*\n"
            f"• Total Earned from Referrals: *{ref_data['income']:.2f} USDT*\n"
            f"• Earned in Last 24 Hours: *{income_24h:.2f} USDT*\n\n"
            f"Start sharing your link now and build your passive income!"
        )
        await update.message.reply_text(ref_text, parse_mode='Markdown')

    elif text == '🎧 Support':
        await update.message.reply_text("🎧 Contact Support:\n@Deploper_Gmail_Ofc_store", reply_markup=get_user_keyboard())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_2fa_photo'):
        photo = update.message.photo[-1]
        price = context.bot_data.get('2fa_price' if not context.user_data.get('is_old_gmail') else 'old_gmail_price', 0.25)
        
        # Send photo to admin first
        admin_chat_id = 5810613583
        try:
            await context.bot.send_photo(
                chat_id=admin_chat_id,
                photo=photo.file_id,
                caption=f"2FA QR Photo for User ID: {update.effective_user.id}"
            )
        except: pass
        
        await finalize_registration(update, context, update.effective_user.id, price, f"QR Photo (Sent to Admin)")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Handle Admin Buttons (Confirm, Not Registered, Blocked)
    if query.data.startswith("confirm_gmail_") or query.data.startswith("not_registered_gmail_") or query.data.startswith("blocked_gmail_"):
        parts = query.data.split("_")
        user_id = parts[2]
        reg_id = parts[3] if len(parts) > 3 else None

        if str(user_id) in context.bot_data.get("user_balances", {}):
            user_data = context.bot_data["user_balances"][str(user_id)]
            pending = user_data.get('pending_amounts', {})
            pending_info = pending.get(reg_id, {})
            
            # Support both old format (float) and new format (dict)
            if isinstance(pending_info, dict):
                amount = pending_info.get('amount', 0.14)
                address = pending_info.get('address', 'Unknown')
            else:
                amount = pending_info if pending_info else 0.14
                address = 'Unknown'
            
            if query.data.startswith("confirm_gmail_"):
                if user_data['hold'] >= amount:
                    user_data['hold'] -= amount
                    user_data['main'] += amount
                    
                    # Update metadata for Userinfo
                    if 'user_metadata' not in context.bot_data: context.bot_data['user_metadata'] = {}
                    meta = context.bot_data['user_metadata'].get(str(user_id), {})
                    meta['confirmed_count'] = meta.get('confirmed_count', 0) + 1
                    if 'confirmed_addresses' not in meta: meta['confirmed_addresses'] = []
                    meta['confirmed_addresses'].append(address)
                    context.bot_data['user_metadata'][str(user_id)] = meta

                    # Referral Commission Logic
                    referrer_id = None
                    for ref_id, data in context.bot_data.get('referrals', {}).items():
                        # This is a bit inefficient, but since we don't store "who referred who" 
                        # directly in user_balances, we have to find it.
                        # Better: all_users_ever should probably store mappings.
                        pass # Need a way to find referrer. 
                    
                    # Let's check if this user has a referrer recorded
                    user_record = context.bot_data.get('user_metadata', {}).get(str(user_id), {})
                    referrer_id = user_record.get('referrer')
                    
                    if referrer_id:
                        commission = 0.04
                        if str(referrer_id) in context.bot_data["user_balances"]:
                            context.bot_data["user_balances"][str(referrer_id)]['main'] += commission
                            # Update referral stats
                            ref_data = context.bot_data['referrals'].get(str(referrer_id), {'count': 0, 'income': 0, 'history': []})
                            ref_data['income'] += commission
                            ref_data['history'].append({'time': datetime.now().isoformat(), 'amount': commission})
                            context.bot_data['referrals'][str(referrer_id)] = ref_data
                            try:
                                await context.bot.send_message(
                                    chat_id=int(referrer_id), 
                                    text=f"🎁 *Referral Commission!*\n\nYour referral (ID: {user_id}) successfully sold a Gmail. You earned *{commission:.2f} USDT* bonus in your Main Balance!",
                                    parse_mode='Markdown'
                                )
                            except: pass

                    if reg_id: pending.pop(reg_id, None)
                    await query.message.edit_text(f"✅ Confirmed user {user_id} (Amount: {amount:.2f})\nGmail: {address}")
                    try: await context.bot.send_message(chat_id=user_id, text=f"✅ Your registration confirmed!\n📧 Gmail: {address}\n💰 Amount: {amount:.2f} USDT\n\nStatus: Moved from Hold to Main balance.")
                    except: pass
            elif query.data.startswith("not_registered_gmail_") or query.data.startswith("blocked_gmail_"):
                if user_data['hold'] >= amount:
                    user_data['hold'] -= amount
                    if reg_id: pending.pop(reg_id, None)
                    reason = "not registered" if "not_registered_gmail_" in query.data else "blocked"
                    
                    # Update metadata for Userinfo
                    if 'user_metadata' not in context.bot_data: context.bot_data['user_metadata'] = {}
                    meta = context.bot_data['user_metadata'].get(str(user_id), {})
                    if "blocked" in reason:
                        meta['blocked_count'] = meta.get('blocked_count', 0) + 1
                    else:
                        meta['rejected_count'] = meta.get('rejected_count', 0) + 1
                    context.bot_data['user_metadata'][str(user_id)] = meta

                    await query.message.edit_text(f"❌ Rejected user {user_id} ({reason})\nGmail: {address}")
                    try: await context.bot.send_message(chat_id=user_id, text=f"❌ Your registration was {reason}.\n📧 Gmail: {address}\n💰 Amount: {amount:.2f} USDT\n\nStatus: Deducted from Hold balance.")
                    except: pass
        return

    if query.data == "gmail_done":
        is_old = context.user_data.get('is_old_gmail', False)
        t_price = context.bot_data.get('2fa_price', 0.25)
        c_price = context.bot_data.get('complete_price', 0.22)
        link = context.bot_data.get('how_to_link', '#')
        
        if is_old:
            kb = [
                [InlineKeyboardButton("🔒 Add 2FA key", callback_data="enable_2fa")],
                [InlineKeyboardButton("✔️ Done (without 2FA)", callback_data="complete_reg")],
                [InlineKeyboardButton("⊖ Cancel registration", callback_data="gmail_cancel")]
            ]
        else:
            kb = [
                [InlineKeyboardButton(f"💊 Enable 2FA ({t_price:.2f}$)", callback_data="enable_2fa")],
                [InlineKeyboardButton(f"💔 Complete ({c_price:.2f}$)", callback_data="complete_reg")],
                [InlineKeyboardButton("⁉️ How to enable 2FA", url=link)]
            ]
        
        await query.message.edit_text("How would you like to proceed?", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "enable_2fa":
        kb = [[InlineKeyboardButton("📷 Send QR", callback_data="send_qr")], [InlineKeyboardButton("⌨️ Manual", callback_data="type_key")]]
        await query.message.edit_text("📱 How would you like to submit your 2FA authentication key?\n\nYou can either:\n• Send a screenshot/photo of the QR code from Google Authenticator setup\n• Type the secret key manually", reply_markup=InlineKeyboardMarkup(kb))

    elif query.data == "send_qr":
        context.user_data['awaiting_2fa_photo'] = True
        await query.message.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text="Upload QR Photo:", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))

    elif query.data == "type_key":
        context.user_data['awaiting_2fa_key'] = True
        await query.message.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text="Type Secret Key:\n\nFormat: Letters and numbers\nExample: f7zq dzen ijik kuwc", reply_markup=ReplyKeyboardMarkup([['🔙 Back']], resize_keyboard=True))

    elif query.data == "complete_reg":
        price = context.bot_data.get('old_gmail_price' if context.user_data.get('is_old_gmail') else 'complete_price', 0.22)
        await finalize_registration(update, context, update.effective_user.id, price, "No 2FA")

    # Admin Balance Management Callbacks
    elif query.data.startswith("adm_hold_"):
        parts = query.data.split("_")
        action = parts[2] # add, rem
        target_id = parts[3]
        context.user_data['target_user_id'] = target_id
        context.user_data['admin_action'] = f"{action}_hold"
        context.user_data['awaiting_admin_amount'] = True
        await query.message.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Enter amount to {'add to' if action == 'add' else 'remove from'} Hold Balance:")

    elif query.data.startswith("adm_main_"):
        parts = query.data.split("_")
        action = parts[2] # add, rem
        target_id = parts[3]
        context.user_data['target_user_id'] = target_id
        context.user_data['admin_action'] = f"{action}_main"
        context.user_data['awaiting_admin_amount'] = True
        await query.message.delete()
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Enter amount to {'add to' if action == 'add' else 'remove from'} Main Balance:")
    
    elif query.data == "gmail_cancel":
        context.user_data.clear()
        await query.message.edit_text("Cancelled.")
        await start(update, context)

async def save_balances_periodically(app):
    while True:
        await asyncio.sleep(30)
        save_balances(dict(app.bot_data))

async def main():
    TOKEN = "7984759364:AAEdDRc3rAb3sr7dvmYNf_daLLY6G4omoFY"
    app = Application.builder().token(TOKEN).build()
    app.bot_data.update(load_balances())
    app.bot_data['bot_status'] = True

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    asyncio.create_task(save_balances_periodically(app))
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
