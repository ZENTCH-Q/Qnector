# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Strategy(db.Model):
    __tablename__ = 'strategy'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    risk_percentage = db.Column(db.Float, nullable=False)
    mt5_id = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    server = db.Column(db.String(100), nullable=False)
    directory = db.Column(db.String(200), nullable=False)
    websocket_url = db.Column(db.String(200), nullable=False)
    commission = db.Column(db.Float, nullable=False)
    created_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Inactive')

    trades = db.relationship('Trade', backref='strategy', lazy=True)

class Trade(db.Model):
    __tablename__ = 'trade'

    id = db.Column(db.Integer, primary_key=True)
    strategy_id = db.Column(db.Integer, db.ForeignKey('strategy.id'), nullable=False)
    trade_id = db.Column(db.Integer, nullable=False)  # MT5 Trade ID
    symbol = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(4), nullable=False)  # 'BUY' or 'SELL'
    volume = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    sl = db.Column(db.Float, nullable=True)
    tp = db.Column(db.Float, nullable=True)
    profit = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
