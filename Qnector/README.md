Overview
This Flask MT5 Trading Application is a robust platform designed to manage and execute trading strategies using MetaTrader 5 (MT5). It integrates WebSocket communication to receive trade alerts, executes trades based on predefined strategies, logs all activities, and provides a user-friendly web interface for managing strategies and monitoring performance.

Features
Strategy Management: Create, edit, delete, activate, and deactivate trading strategies.
WebSocket Integration: Listen to real-time alerts (e.g., from TradingView) via WebSocket to trigger trade executions.
Trade Execution: Connects to MT5 accounts to execute trades based on received alerts.
Performance Tracking: Logs all trades and calculates performance metrics such as total profit, win rate, drawdown, Sharpe Ratio, and Sortino Ratio.
Web Interface: Intuitive dashboard for managing strategies and viewing performance data.
Logging: Comprehensive logging for monitoring application behavior and troubleshooting.
Prerequisites
Before setting up the application, ensure you have the following:

Python 3.8+ installed on your system.
MetaTrader 5 (MT5): Installed and configured on the machine where the application will run.
Access to a WebSocket Source: Such as TradingView alerts to send trade signals.
Basic Knowledge of Flask and SQLAlchemy: Helpful but not mandatory.
Installation
Follow these steps to set up and run the application:

1. Clone the Repository
First, clone the repository containing the application code. Replace yourusername and your-repo-name with your GitHub username and repository name.

bash
Copy code
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
2. Create and Activate a Virtual Environment
It's best practice to use a virtual environment to manage dependencies.

bash
Copy code
# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On Unix or MacOS:
source venv/bin/activate
3. Install Dependencies
Install all necessary Python packages using pip.

bash
Copy code
pip install -r requirements.txt
Note: If you don't have a requirements.txt, create one with the following content based on your app.py imports:

plaintext
Copy code
Flask
Flask_SQLAlchemy
Flask_WTF
WTForms
Flask-Migrate
python-dotenv
MetaTrader5
websocket-client
numpy
scipy
Then install them:

bash
Copy code
pip install Flask Flask_SQLAlchemy Flask_WTF WTForms Flask-Migrate python-dotenv MetaTrader5 websocket-client numpy scipy
4. Configure Environment Variables
Create a .env file in the root directory to store sensitive information like SECRET_KEY.

a. Generate a Secret Key
Use the provided secretkey_gen.py script to generate a secure secret key.

bash
Copy code
python secretkey_gen.py
This will output a secure key, e.g., e5f6c2d9a1b4...

b. Create .env
Create a file named .env and add the following content:

dotenv
Copy code
SECRET_KEY=your_generated_secret_key_here
Replace your_generated_secret_key_here with the key generated from secretkey_gen.py.

5. Configure config.ini
The application uses a config.ini file for additional configurations.

a. Default Configuration
If config.ini does not exist, the application will create one with default values. However, you should verify and update it as needed.

b. Contents of config.ini
ini
Copy code
[DEFAULT]
WebSocket_URL = wss://your.websocket.url
Ping_Interval = 30
Risk_Percentage = 1
Commission = 4
WebSocket_URL: The URL of your WebSocket server (e.g., TradingView WebSocket endpoint).
Ping_Interval: Interval in seconds to send ping messages to keep the WebSocket connection alive.
Risk_Percentage: The percentage of account balance to risk per trade.
Commission: The commission per trade (could be in account currency).
Update config.ini with your specific configurations.

6. Initialize the Database
The application uses SQLite by default. Ensure that the database file (strategies.db) is created.

bash
Copy code
# Within a Python shell or using a script

from app import db, app
with app.app_context():
    db.create_all()
7. Run Database Migrations
Flask-Migrate handles database migrations. Initialize and apply migrations as follows:

bash
Copy code
# Initialize migrations (only needed once)
flask db init

# Generate migration script
flask db migrate -m "Initial migration."

# Apply migrations
flask db upgrade
Note: Ensure that the FLASK_APP environment variable is set to app.py:

bash
Copy code
export FLASK_APP=app.py  # On Unix or MacOS
set FLASK_APP=app.py     # On Windows
8. Generate a Secret Key (If Not Done)
If you haven't generated a secret key using secretkey_gen.py, do so now and add it to your .env file as described in step 4.

9. Start the Application
Run the Flask application.

bash
Copy code
python app.py
By default, Flask runs on http://127.0.0.1:5000/. Navigate to this URL in your web browser to access the dashboard.

Usage
Once the application is running, you can interact with it through the web interface. Below are detailed steps for using each feature of the application.

1. Accessing the Dashboard
Open Your Web Browser:

Launch your preferred web browser (e.g., Chrome, Firefox, Edge).
Navigate to the Dashboard:

Enter http://127.0.0.1:5000/ in the address bar and press Enter.
You should see the Dashboard page, which lists all available trading strategies along with their performance metrics.


Dashboard Overview:

Strategy List: Displays all strategies with details such as name, status, total profit, total trades, win rate, etc.
Actions: Options to run, stop, edit, or delete each strategy.
Performance Metrics: Quick glance at key performance indicators for each strategy.
2. Creating a Strategy
To execute trades automatically, you need to create a trading strategy. Here's how to do it:

Navigate to Create Strategy:

On the Dashboard, locate and click the "Create Strategy" button.
Alternatively, go directly to http://127.0.0.1:5000/create.


Fill Out the Strategy Form:

Strategy Name: Enter a unique name for your strategy (e.g., "ScalpingStrategy1").
Risk %: Specify the percentage of your account balance you wish to risk per trade (e.g., 1 for 1%).
MT5 ID: Input your MT5 account ID.
Password: Enter your MT5 account password.
Server: Provide the MT5 server name.
Directory: Specify the path to your MT5 installation directory (e.g., C:\Program Files\MetaTrader 5).
WebSocket URL: Enter the URL for receiving WebSocket alerts (e.g., TradingView's WebSocket endpoint).
Commission: Input the commission per trade (e.g., 4).


Save the Strategy:

After filling out all fields, click the "Save" button at the bottom of the form.
If the strategy name is unique and all fields are correctly filled, you will see a success message: "Strategy created successfully!"


Note: If the strategy name already exists, you will receive an error message prompting you to choose a different name.

3. Managing Strategies
Once strategies are created, you can manage them through various actions such as editing, deleting, running, or stopping.

a. Editing a Strategy
Locate the Strategy:

On the Dashboard, find the strategy you wish to edit in the strategy list.
Click the "Edit" Button:

Next to the strategy, click the "Edit" button.


Modify Strategy Details:

Update any of the strategy's details as needed (e.g., change risk percentage, update WebSocket URL).
Ensure that the Strategy Name remains unique.


Save Changes:

Click the "Save" button to apply the changes.
A success message will confirm the update: "Strategy updated successfully!"
b. Deleting a Strategy
Locate the Strategy:

On the Dashboard, find the strategy you wish to delete.
Click the "Delete" Button:

Next to the strategy, click the "Delete" button.


Confirm Deletion:

A confirmation prompt will appear asking if you're sure you want to delete the strategy.
Confirm the action to proceed.
Deletion Confirmation:

Upon successful deletion, a message will appear: "Strategy deleted successfully!"
Note: Deleting a strategy will also stop any running WebSocket handlers associated with it.

c. Running a Strategy
Activating a strategy allows it to start listening for WebSocket alerts and executing trades accordingly.

Locate the Strategy:

On the Dashboard, find the strategy you wish to run.
Click the "Run" Button:

Next to the strategy, click the "Run" button.


Activation Confirmation:

A success message will confirm that the strategy has started: "Strategy 'StrategyName' started successfully."
The strategy's status will change to "Active".


WebSocket Handler Activation:

Once activated, the application will start the WebSocket handler for the strategy, allowing it to receive alerts and execute trades.
d. Stopping a Strategy
Deactivating a strategy stops it from listening to alerts and executing trades.

Locate the Strategy:

On the Dashboard, find the active strategy you wish to stop.
Click the "Stop" Button:

Next to the strategy, click the "Stop" button.


Deactivation Confirmation:

A success message will confirm that the strategy has stopped: "Strategy 'StrategyName' stopped successfully."
The strategy's status will change to "Inactive".


WebSocket Handler Deactivation:

The WebSocket handler associated with the strategy will stop, preventing it from receiving further alerts.
4. Viewing Performance
Monitoring the performance of your strategies is crucial for evaluating their effectiveness. The application provides detailed performance metrics and visualizations.

a. Strategy Performance
Navigate to Strategy Performance:

On the Dashboard, click on the strategy's name or the "View Performance" button next to it.
Alternatively, go to http://127.0.0.1:5000/performance/<strategy_id>, replacing <strategy_id> with the actual ID of the strategy.


Review Performance Metrics:

The Strategy Performance page displays comprehensive metrics, including:

Total Profit: Cumulative profit from all trades.
Total Trades: Number of trades executed.
Win Rate: Percentage of profitable trades.
Average Profit per Trade: Mean profit across all trades.
Drawdown Percentage: Maximum loss from a peak in the equity curve.
Sharpe Ratio: Measure of risk-adjusted return.
Sortino Ratio: Measure of downside risk-adjusted return.
Equity Curve Chart: Visual representation of equity over time.


Analyze Trades:

Trades Table: Below the metrics, a table lists all individual trades with details like symbol, action (BUY/SELL), volume, price, SL, TP, profit, and timestamp.
Filtering: Use filters or search to find specific trades based on criteria.
Interpret the Equity Curve:

The Equity Curve Chart helps visualize the growth or decline of your strategy's equity over time.
Analyze trends, identify drawdowns, and assess overall performance.
b. Portfolio Performance
Managing multiple strategies? The Portfolio Performance page aggregates data across all active strategies for a holistic view.

Navigate to Portfolio Performance:

On the Dashboard, locate and click the "Portfolio" link or go directly to http://127.0.0.1:5000/portfolio.


Review Aggregated Metrics:

The Portfolio Performance page provides combined metrics from all strategies, including:

Total Profit: Combined profit from all trades across strategies.
Total Trades: Total number of trades executed.
Win Rate: Overall win rate across all strategies.
Average Profit per Trade: Mean profit across all trades.
Drawdown Percentage: Maximum combined drawdown.
Sharpe Ratio: Combined risk-adjusted return.
Sortino Ratio: Combined downside risk-adjusted return.
Equity Curve Chart: Aggregated equity growth over time.


Analyze Combined Trades:

Trades Table: A comprehensive table lists all trades from every strategy, providing a unified view of trading activities.
Filtering: Apply filters to view trades from specific strategies or timeframes.
Interpret the Combined Equity Curve:

Assess the overall health and performance of your entire trading portfolio.
Identify overarching trends, drawdowns, and growth patterns.
Configuration
Proper configuration is crucial for the seamless operation of the application. Below are details on configuring environment variables and the config.ini file.

.env File
The .env file stores sensitive information and configuration variables. Ensure this file is never committed to version control.

Example .env File:

dotenv
Copy code
SECRET_KEY=your_generated_secret_key_here
SECRET_KEY: A secure secret key for Flask sessions. Generate using secretkey_gen.py.
config.ini File
The config.ini file contains additional configurations for the application.

Example config.ini File:

ini
Copy code
[DEFAULT]
WebSocket_URL = wss://your.websocket.url
Ping_Interval = 30
Risk_Percentage = 1
Commission = 4
WebSocket_URL: The URL of your WebSocket server (e.g., TradingView WebSocket endpoint).
Ping_Interval: Interval in seconds to send ping messages to keep the WebSocket connection alive.
Risk_Percentage: The percentage of account balance to risk per trade.
Commission: The commission per trade (could be in account currency).
Note: If config.ini does not exist, the application will create one with default values. However, you should verify and update it as needed.

Logging
The application is configured to log activities and errors for monitoring and troubleshooting purposes.

Log File: tradingview_ws.log
Log Level: DEBUG
Log Format: Includes timestamp, log level, and message.
Logging Configuration:

python
Copy code
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("tradingview_ws.log"),
        logging.StreamHandler()
    ]
)
Custom Filters:

Suppresses specific error messages related to WebSocket callbacks and errors to reduce noise in logs.
Best Practices:

Monitor Logs: Regularly check tradingview_ws.log for any issues or unexpected behavior.
Log Rotation: Implement log rotation to prevent log files from growing indefinitely.
Sensitive Information: Avoid logging sensitive information like passwords or secret keys.
Security Considerations
Ensuring the security of your application is paramount, especially when dealing with financial transactions and sensitive data.

Protect Sensitive Data:

Ensure your .env file is never committed to version control.
Use environment variables or secret management services in production.
Secure SECRET_KEY:

Always use a strong, randomly generated SECRET_KEY.
Rotate keys periodically and handle key changes carefully.
MT5 Credentials:

Store MT5 passwords securely.
Consider encrypting sensitive fields in the database.
WebSocket Security:

Use secure WebSocket URLs (wss://) to encrypt data in transit.
Implement authentication if your WebSocket server supports it.
Database Security:

If using a production-grade database (e.g., PostgreSQL), ensure proper authentication and authorization mechanisms are in place.
Regularly back up your database to prevent data loss.
Application Security:

Keep all dependencies up to date to benefit from security patches.
Regularly review and update your code to fix potential vulnerabilities.
Troubleshooting
Encountering issues is common during setup and operation. Below are common problems and their solutions:

WebSocket Connection Issues:

Symptom: Unable to receive alerts or execute trades.
Solution:
Verify the WebSocket_URL in config.ini.
Ensure the WebSocket server is operational.
Check network connectivity and firewall settings.
MT5 Connection Errors:

Symptom: Failed to initialize or connect to MT5.
Solution:
Verify MT5 installation directory in the strategy configuration.
Ensure MT5 is running and accessible.
Check MT5 account credentials and server details.
Database Errors:

Symptom: Issues with creating or accessing the database.
Solution:
Ensure the database file (strategies.db) has proper permissions.
Verify that migrations have been applied successfully.
Application Crashes or Freezes:

Solution:
Check tradingview_ws.log for detailed error messages.
Ensure all dependencies are installed correctly.
Verify that MT5 is functioning as expected.
Secret Key Issues:

Symptom: Flask session errors or unexpected behavior.
Solution:
Ensure SECRET_KEY is set correctly in the .env file.
Restart the application after updating .env.
Port Conflicts:

Symptom: Unable to start the Flask application on the default port.
Solution:
Specify a different port when running the application:

bash
Copy code
python app.py --port 5001
WebSocket Ping Failures:

Symptom: WebSocket connection drops frequently.
Solution:
Increase the Ping_Interval in config.ini.
Ensure the network is stable.
Trade Execution Failures:

Symptom: Trades are not being executed or logged.
Solution:
Check MT5 connection details.
Verify that the strategy is active and correctly configured.
Review tradingview_ws.log for error messages related to trade execution.