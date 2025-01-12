# app.py
import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, PasswordField
from wtforms.validators import DataRequired, NumberRange, ValidationError
from models import db, Strategy, Trade
from datetime import datetime, timedelta
import logging
import configparser
import atexit
import websocket
import json
import threading
import time
import ssl
import MetaTrader5 as mt5
from flask_migrate import Migrate
from dotenv import load_dotenv  # Import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
from scipy import stats  # For statistical tests
import numpy as np

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secure_secret_key')  # Replace with a secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///strategies.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

# =======================
# Logging Configuration
# =======================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("tradingview_ws.log"),
        logging.StreamHandler()
    ]
)

# Custom filter to suppress specific error messages
class SuppressErrorsFilter(logging.Filter):
    def filter(self, record):
        if 'error from callback' in record.getMessage() or 'WebSocket Error' in record.getMessage():
            return False  # Suppress the log message
        return True  # Allow other messages

for handler in logging.getLogger().handlers:
    handler.addFilter(SuppressErrorsFilter())

# =======================
# Configuration
# =======================
CONFIG_FILE = 'config.ini'

config = configparser.ConfigParser()

if not os.path.exists(CONFIG_FILE):
    logging.error(f"Configuration file {CONFIG_FILE} not found.")
    # Create a default config file or handle appropriately
    config['DEFAULT'] = {
        'WebSocket_URL': 'wss://your.websocket.url',
        'Ping_Interval': '30',
        'Risk_Percentage': '1',
        'Commission': '4'
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    logging.info(f"Default configuration file {CONFIG_FILE} created.")
else:
    config.read(CONFIG_FILE)

# =======================
# WebSocket and MT5 Handling
# =======================

class MT5Connection:
    def __init__(self, strategy):
        self.strategy = strategy
        self.initialize_mt5()

    def initialize_mt5(self):
        try:
            if not mt5.initialize(path=self.strategy.directory):
                logging.error(f"Failed to initialize MT5. Error code: {mt5.last_error()}")
                return False

            authorized = mt5.login(int(self.strategy.mt5_id), password=self.strategy.password, server=self.strategy.server)
            if authorized:
                logging.info(f"Connected to MT5 account {self.strategy.mt5_id} on server {self.strategy.server}.")
                return True
            else:
                logging.error(f"Failed to connect to MT5 account {self.strategy.mt5_id}. Error code: {mt5.last_error()}")
                return False
        except Exception as e:
            logging.error(f"Exception during MT5 initialization: {e}")
            return False

    def shutdown_mt5(self):
        mt5.shutdown()
        logging.info("MT5 connection closed.")

    def calculate_volume(self, symbol, sl_pips):
        # Implement the calculate_volume function as per your original script
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logging.error("Failed to retrieve account information.")
                return None

            balance = account_info.balance
            if balance <= 0:
                logging.error("Account balance is zero or negative.")
                return None

            risk_amount = balance * (self.strategy.risk_percentage / 100)
            logging.debug(f"Account Balance: {balance}, Risk Percentage: {self.strategy.risk_percentage}%, Risk Amount: {risk_amount}")

            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logging.error(f"Symbol {symbol} not found in MT5.")
                return None

            if not mt5.symbol_select(symbol, True):
                logging.error(f"Failed to select symbol {symbol}.")
                return None

            account_currency = account_info.currency
            quote_currency = symbol[-3:]
            logging.debug(f"Account Currency: {account_currency}, Quote Currency: {quote_currency}")

            if account_currency != quote_currency:
                exchange_symbol = account_currency + quote_currency
                exchange_info = mt5.symbol_info(exchange_symbol)
                if exchange_info is None:
                    reverse_exchange_symbol = quote_currency + account_currency
                    exchange_info = mt5.symbol_info(reverse_exchange_symbol)
                    if exchange_info is None:
                        logging.error(f"Neither {exchange_symbol} nor {reverse_exchange_symbol} found in MT5.")
                        return None
                    else:
                        tick = mt5.symbol_info_tick(reverse_exchange_symbol)
                        if tick is None:
                            logging.error(f"Failed to get tick information for {reverse_exchange_symbol}.")
                            return None
                        exchange_rate = 1 / tick.bid
                        logging.debug(f"Using reverse exchange rate from {reverse_exchange_symbol}: {exchange_rate}")
                else:
                    tick = mt5.symbol_info_tick(exchange_symbol)
                    if tick is None:
                        logging.error(f"Failed to get tick information for {exchange_symbol}.")
                        return None
                    exchange_rate = tick.ask
                    logging.debug(f"Using direct exchange rate from {exchange_symbol}: {exchange_rate}")

                pip_value = (10 ** -symbol_info.digits) * 100000 / exchange_rate
                logging.debug(f"Calculated pip value (adjusted for exchange rate): {pip_value}")
            else:
                pip_value = (10 ** -symbol_info.digits) * 100000
                logging.debug(f"Pip Value (per lot): {pip_value}")

            half_commission = self.strategy.commission / 2
            denominator = (sl_pips * pip_value) + half_commission
            logging.debug(f"Denominator for volume calculation: (SL Pips * Pip Value) + Half Commission = ({sl_pips} * {pip_value}) + {half_commission} = {denominator}")

            if denominator <= 0:
                logging.error("Invalid denominator for volume calculation.")
                return None

            volume = risk_amount / denominator
            volume = round(volume, 2)

            if volume < symbol_info.volume_min:
                logging.warning(f"Calculated volume {volume} is below the minimum {symbol_info.volume_min}. Adjusting to minimum.")
                volume = symbol_info.volume_min
            elif volume > symbol_info.volume_max:
                logging.warning(f"Calculated volume {volume} is above the maximum {symbol_info.volume_max}. Adjusting to maximum.")
                volume = symbol_info.volume_max

            logging.info(f"Calculated volume: {volume} lots based on risk management (including commission).")
            return volume

        except Exception as e:
            logging.error(f"An error occurred while calculating volume: {e}")
            return None

    def process_alert(self, description, name):
        # Validate that the alert's strategy name matches the strategy's name
        if name != self.strategy.name:
            logging.warning(f"Alert name '{name}' does not match strategy name '{self.strategy.name}'. Ignoring this alert.")
            return  # Ignore the alert if names do not match

        # Existing processing code
        try:
            parts = description.strip().lower().split()
            if len(parts) != 4:
                logging.warning("Alert description does not have exactly 4 parts. Skipping.")
                return

            action, symbol, sl_pips, tp_pips = parts

            if action not in ["buy", "sell"]:
                logging.warning(f"Unknown action '{action}'. Skipping.")
                return

            try:
                sl_pips = float(sl_pips)
                tp_pips = float(tp_pips)
            except ValueError:
                logging.error("SL and TP pips must be numeric values.")
                return

            volume = self.calculate_volume(symbol.upper(), sl_pips)
            if volume is None:
                logging.error("Failed to calculate trade volume. Skipping trade.")
                return

            symbol_info = mt5.symbol_info(symbol.upper())
            if symbol_info is None:
                logging.error(f"Failed to get symbol info for {symbol}.")
                return

            digits = symbol_info.digits
            pip = 10 ** -digits
            tick = mt5.symbol_info_tick(symbol.upper())
            if tick is None:
                logging.error(f"Failed to get tick information for {symbol}.")
                return

            if action == "buy":
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
                sl_price = price - (sl_pips * pip)
                tp_price = price + (tp_pips * pip)
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
                sl_price = price + (sl_pips * pip)
                tp_price = price - (tp_pips * pip)

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol.upper(),
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"TradingView Alert: {name}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"Trade executed successfully: {action.upper()} {volume} {symbol.upper()} at {price}. SL: {sl_price}, TP: {tp_price}. Alert Name: {name}")

                # Log the trade in the database
                trade = Trade(
                    strategy_id=self.strategy.id,
                    trade_id=result.order,
                    symbol=symbol.upper(),
                    action=action.upper(),
                    volume=volume,
                    price=price,
                    sl=sl_price,
                    tp=tp_price,
                    profit=result.profit,
                    timestamp=datetime.utcnow()
                )
                db.session.add(trade)
                db.session.commit()
                logging.info(f"Trade logged successfully: Trade ID {trade.id}")
            else:
                logging.error(f"Failed to execute trade: {result.retcode} - {result.comment}")

        except Exception as e:
            logging.error(f"An error occurred while processing the alert for MT5: {e}")

class WebSocketHandler(threading.Thread):
    def __init__(self, strategy):
        super().__init__()
        self.strategy = strategy
        self.ws = None
        self.daemon = True
        self.mt5_conn = MT5Connection(strategy)
        self.stop_event = threading.Event()

    def run(self):
        def on_message(ws, message):
            try:
                data = json.loads(message)
                content = data.get("text", {}).get("content", {}).get("p", {})
                alert_message = content.get("message")
                alert_name = content.get("name")

                if alert_message and alert_name:
                    logging.info(f"Alert Name: {alert_name}")
                    logging.info(f"Alert Message: {alert_message}")
                    self.mt5_conn.process_alert(alert_message, alert_name)
            except json.JSONDecodeError:
                logging.warning("Received non-JSON message. Ignoring.")

        def on_error(ws, error):
            logging.error(f"WebSocket Error: {error}")

        def on_close(ws, close_status_code, close_msg):
            logging.debug("WebSocket connection closed")
            logging.debug(f"Close Status Code: {close_status_code}")
            logging.debug(f"Close Message    : {close_msg}")

        def on_open(ws):
            logging.info("WebSocket connection opened")

            def run_ping():
                while not self.stop_event.is_set():
                    time.sleep(int(config['DEFAULT'].get('Ping_Interval', 30)))
                    try:
                        ping_message = {"type": "ping"}
                        ws.send(json.dumps(ping_message))
                    except Exception as e:
                        logging.error(f"Failed to send ping: {e}")
                        break

            threading.Thread(target=run_ping, daemon=True).start()

        self.ws = websocket.WebSocketApp(
            self.strategy.websocket_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )

        while not self.stop_event.is_set():
            try:
                self.ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                logging.info("Attempting to reconnect in 5 seconds...")
                time.sleep(5)

    def stop(self):
        self.stop_event.set()
        if self.ws:
            self.ws.close()
        self.mt5_conn.shutdown_mt5()
        logging.info(f"WebSocket handler for strategy '{self.strategy.name}' stopped.")

# Dictionary to hold WebSocket handlers for each strategy
websocket_handlers = {}

# Initialize WebSocket handlers for existing strategies
with app.app_context():
    db.create_all()  # Ensures tables are created
    strategies = Strategy.query.all()
    for strategy in strategies:
        if strategy.status == 'Active':
            handler = WebSocketHandler(strategy)
            handler.start()
            websocket_handlers[strategy.id] = handler

# Ensure MT5 is shutdown gracefully on program exit
def shutdown():
    for handler in websocket_handlers.values():
        if handler.ws:
            handler.ws.close()
        handler.mt5_conn.shutdown_mt5()

atexit.register(shutdown)

# =======================
# Flask Routes
# =======================

class StrategyForm(FlaskForm):
    name = StringField('Strategy Name', validators=[DataRequired()])
    risk_percentage = FloatField('Risk %', validators=[DataRequired(), NumberRange(min=0.1, max=100)])
    mt5_id = StringField('MT5 ID', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    server = StringField('Server', validators=[DataRequired()])
    directory = StringField('Directory', validators=[DataRequired()])
    websocket_url = StringField('WebSocket URL', validators=[DataRequired()])
    commission = FloatField('Commission', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save')

    def validate_name(self, field):
        # Check if a strategy with the same name already exists (excluding current strategy if editing)
        existing_strategy = Strategy.query.filter_by(name=field.data).first()
        if existing_strategy and (not hasattr(self, 'strategy_id') or existing_strategy.id != self.strategy_id):
            raise ValidationError('Strategy name already exists. Please choose a different name.')

@app.route('/')
def dashboard():
    strategies = Strategy.query.all()
    performance_data = []
    for strategy in strategies:
        trades = Trade.query.filter_by(strategy_id=strategy.id).order_by(Trade.timestamp).all()
        profits = [trade.profit for trade in trades]
        total_profit = sum(profits)
        total_trades = len(trades)
        wins = len([p for p in profits if p > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        average_profit = (total_profit / total_trades) if total_trades > 0 else 0

        # Calculate Drawdown %
        equity_curve = []
        current_equity = 0
        max_equity = 0
        for trade in trades:
            current_equity += trade.profit
            equity_curve.append(current_equity)
            if current_equity > max_equity:
                max_equity = current_equity
        drawdown = 0
        if equity_curve:
            drawdown = max([max_equity - equity for equity in equity_curve])
            drawdown_percentage = (drawdown / max_equity * 100) if max_equity > 0 else 0
        else:
            drawdown_percentage = 0

        # Sharpe Ratio (Assuming risk-free rate = 0)
        if total_trades > 1 and np.std(profits) != 0:
            sharpe_ratio = (np.mean(profits) / np.std(profits)) * np.sqrt(total_trades)
        else:
            sharpe_ratio = 0

        # Sortino Ratio (Assuming risk-free rate = 0)
        negative_returns = [p for p in profits if p < 0]
        if len(negative_returns) > 0 and np.std(negative_returns) != 0:
            sortino_ratio = (np.mean(profits) / np.std(negative_returns)) * np.sqrt(total_trades)
        else:
            sortino_ratio = 0

        performance = {
            'strategy': strategy,
            'total_profit': total_profit,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'average_profit': average_profit,
            'drawdown_percentage': drawdown_percentage,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio
        }
        performance_data.append(performance)

    return render_template('dashboard.html', strategies=strategies, performance_data=performance_data)

@app.route('/create', methods=['GET', 'POST'])
def create_strategy():
    form = StrategyForm()
    if form.validate_on_submit():
        strategy = Strategy(
            name=form.name.data,
            risk_percentage=form.risk_percentage.data,
            mt5_id=form.mt5_id.data,
            password=form.password.data,
            server=form.server.data,
            directory=form.directory.data,
            websocket_url=form.websocket_url.data,
            commission=form.commission.data,
            created_date=datetime.utcnow(),
            updated_date=datetime.utcnow(),
            status='Inactive'  # Default status is 'Inactive'
        )
        db.session.add(strategy)
        try:
            db.session.commit()
            flash('Strategy created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except IntegrityError:
            db.session.rollback()
            flash('Strategy name already exists. Please choose a different name.', 'danger')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating strategy: {e}")
            flash('An error occurred while creating the strategy.', 'danger')
    return render_template('edit_strategy.html', form=form, action='Create')

@app.route('/edit/<int:strategy_id>', methods=['GET', 'POST'])
def edit_strategy(strategy_id):
    strategy = Strategy.query.get_or_404(strategy_id)
    form = StrategyForm(obj=strategy)
    form.strategy_id = strategy_id  # Pass strategy_id to the form for validation

    if form.validate_on_submit():
        strategy.name = form.name.data
        strategy.risk_percentage = form.risk_percentage.data
        strategy.mt5_id = form.mt5_id.data
        strategy.password = form.password.data
        strategy.server = form.server.data
        strategy.directory = form.directory.data
        strategy.websocket_url = form.websocket_url.data
        strategy.commission = form.commission.data
        strategy.updated_date = datetime.utcnow()

        try:
            db.session.commit()
            # If strategy is active, restart the WebSocket handler
            if strategy.status == 'Active':
                handler = websocket_handlers.get(strategy.id)
                if handler:
                    handler.stop()
                    websocket_handlers.pop(strategy.id, None)
                new_handler = WebSocketHandler(strategy)
                new_handler.start()
                websocket_handlers[strategy.id] = new_handler

            flash('Strategy updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except IntegrityError:
            db.session.rollback()
            flash('Strategy name already exists. Please choose a different name.', 'danger')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating strategy: {e}")
            flash('An error occurred while updating the strategy.', 'danger')

    return render_template('edit_strategy.html', form=form, action='Edit')

@app.route('/delete/<int:strategy_id>', methods=['POST'])
def delete_strategy(strategy_id):
    strategy = Strategy.query.get_or_404(strategy_id)
    handler = websocket_handlers.pop(strategy.id, None)
    if handler:
        handler.stop()
    db.session.delete(strategy)
    db.session.commit()
    flash('Strategy deleted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/run/<int:strategy_id>', methods=['POST'])
def run_strategy(strategy_id):
    strategy = Strategy.query.get_or_404(strategy_id)
    if strategy.status == 'Active':
        flash('Strategy is already running.', 'warning')
        return redirect(url_for('dashboard'))
    
    handler = WebSocketHandler(strategy)
    handler.start()
    websocket_handlers[strategy.id] = handler

    # Update strategy status
    strategy.status = 'Active'
    strategy.updated_date = datetime.utcnow()
    db.session.commit()

    flash(f"Strategy '{strategy.name}' started successfully.", 'success')
    return redirect(url_for('dashboard'))

@app.route('/stop/<int:strategy_id>', methods=['POST'])
def stop_strategy(strategy_id):
    strategy = Strategy.query.get_or_404(strategy_id)
    if strategy.status == 'Inactive':
        flash('Strategy is already stopped.', 'warning')
        return redirect(url_for('dashboard'))
    
    handler = websocket_handlers.get(strategy.id)
    if handler:
        handler.stop()
        websocket_handlers.pop(strategy.id, None)
    
    # Update strategy status
    strategy.status = 'Inactive'
    strategy.updated_date = datetime.utcnow()
    db.session.commit()

    flash(f"Strategy '{strategy.name}' stopped successfully.", 'success')
    return redirect(url_for('dashboard'))

@app.route('/performance/<int:strategy_id>')
def strategy_performance(strategy_id):
    # Fetch the strategy by ID
    strategy = Strategy.query.get_or_404(strategy_id)
    
    # Retrieve all trades associated with this strategy, ordered by timestamp
    trades = Trade.query.filter_by(strategy_id=strategy.id).order_by(Trade.timestamp).all()
    
    # Calculate Total Profit
    total_profit = sum(trade.profit for trade in trades)
    
    # Calculate Total Trades
    total_trades = len(trades)
    
    # Calculate Win Rate
    wins = len([trade for trade in trades if trade.profit > 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate Average Profit per Trade
    average_profit = (total_profit / total_trades) if total_trades > 0 else 0
    
    # Calculate Drawdown %
    equity_curve = []
    current_equity = 0
    max_equity = 0
    for trade in trades:
        current_equity += trade.profit
        equity_curve.append(current_equity)
        if current_equity > max_equity:
            max_equity = current_equity
    drawdown = 0
    if equity_curve:
        drawdown = max([max_equity - equity for equity in equity_curve])
        drawdown_percentage = (drawdown / max_equity * 100) if max_equity > 0 else 0
    else:
        drawdown_percentage = 0

    # Sharpe Ratio (Assuming risk-free rate = 0)
    if total_trades > 1 and np.std([trade.profit for trade in trades]) != 0:
        sharpe_ratio = (np.mean([trade.profit for trade in trades]) / np.std([trade.profit for trade in trades])) * np.sqrt(total_trades)
    else:
        sharpe_ratio = 0

    # Sortino Ratio (Assuming risk-free rate = 0)
    negative_returns = [trade.profit for trade in trades if trade.profit < 0]
    if len(negative_returns) > 0 and np.std(negative_returns) != 0:
        sortino_ratio = (np.mean([trade.profit for trade in trades]) / np.std(negative_returns)) * np.sqrt(total_trades)
    else:
        sortino_ratio = 0

    # Prepare data for the equity curve chart
    equity_values = equity_curve
    equity_timestamps = [trade.timestamp.strftime('%Y-%m-%d %H:%M') for trade in trades]

    return render_template(
        'strategy_performance.html',
        strategy=strategy,
        total_profit=total_profit,
        total_trades=total_trades,
        win_rate=win_rate,
        average_profit=average_profit,
        drawdown_percentage=drawdown_percentage,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        equity_values=equity_values,
        equity_timestamps=equity_timestamps,
        trades=trades
    )

@app.route('/portfolio')
def portfolio_performance():
    strategies = Strategy.query.all()
    strategy_ids = [s.id for s in strategies]
    portfolio_trades = Trade.query.filter(Trade.strategy_id.in_(strategy_ids)).order_by(Trade.timestamp).all()
    
    profits = [trade.profit for trade in portfolio_trades]
    total_profit = sum(profits)
    total_trades = len(portfolio_trades)
    wins = len([p for p in profits if p > 0])
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    average_profit = (total_profit / total_trades) if total_trades > 0 else 0

    # Calculate Drawdown %
    equity_curve = []
    current_equity = 0
    max_equity = 0
    for trade in portfolio_trades:
        current_equity += trade.profit
        equity_curve.append(current_equity)
        if current_equity > max_equity:
            max_equity = current_equity
    drawdown = 0
    if equity_curve:
        drawdown = max([max_equity - equity for equity in equity_curve])
        drawdown_percentage = (drawdown / max_equity * 100) if max_equity > 0 else 0
    else:
        drawdown_percentage = 0

    # Sharpe Ratio (Assuming risk-free rate = 0)
    if total_trades > 1 and np.std(profits) != 0:
        sharpe_ratio = (np.mean(profits) / np.std(profits)) * np.sqrt(total_trades)
    else:
        sharpe_ratio = 0

    # Sortino Ratio (Assuming risk-free rate = 0)
    negative_returns = [p for p in profits if p < 0]
    if len(negative_returns) > 0 and np.std(negative_returns) != 0:
        sortino_ratio = (np.mean(profits) / np.std(negative_returns)) * np.sqrt(total_trades)
    else:
        sortino_ratio = 0

    # Prepare data for the equity curve chart
    equity_values = equity_curve
    equity_timestamps = [trade.timestamp.strftime('%Y-%m-%d %H:%M') for trade in portfolio_trades]

    return render_template(
        'portfolio_performance.html',
        strategies=strategies,
        total_profit=total_profit,
        total_trades=total_trades,
        win_rate=win_rate,
        average_profit=average_profit,
        drawdown_percentage=drawdown_percentage,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        equity_values=equity_values,
        equity_timestamps=equity_timestamps,
        trades=portfolio_trades
    )

if __name__ == "__main__":
    app.run(debug=True)
