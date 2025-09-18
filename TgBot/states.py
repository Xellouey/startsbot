from aiogram.fsm.state import StatesGroup, State

class DepositState(StatesGroup):
    enter_amount = State()

class StarsState(StatesGroup):
    wait_amount = State()
    wait_login = State()

class NewsletterState(StatesGroup):
    waiting_for_title = State()
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_buttons = State()
    
class AdminStates(StatesGroup):
    main_menu = State()
    broadcast_start = State()
    broadcast_confirm = State()