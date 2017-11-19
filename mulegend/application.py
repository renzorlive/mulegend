from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # update database with current prices every time index is visited


    try:
        # User's users database entry
        user_users_data = db.execute("SELECT * FROM users WHERE id = :id",
                                      id=session["user_id"])

        # User's portfolio database entries
        user_portfolio_data = db.execute("SELECT * FROM portfolio WHERE username = :username",
                                          username=user_users_data[0]["username"])
        # user's cash ballance
        cash_ballance = float(user_users_data[0]["cash"])
        cash_ballance_usd = usd(cash_ballance)
        # total ballance stocks+cash
        total_ballance = usd(0.0 + cash_ballance)
    except:
        return apology("Could not query database", 403)

    # Retrieve quote data
    if user_portfolio_data:
        quote = lookup(user_portfolio_data[0]["stockname"] )
        # Current stock price
        share_price = float(quote["price"])

        # user's total stocks value
        stocks_value = 0.0
        for entry in user_portfolio_data:
            stocks_value += entry["totalprice"]

        # total ballance stocks+cash
        total_ballance = usd(stocks_value + cash_ballance)

        return render_template("index.html", stocks=user_portfolio_data,
                                share_price=share_price, cash_ballance=cash_ballance_usd, total_ballance=total_ballance)
    else:
        return render_template("index.html", cash_ballance=cash_ballance_usd, total_ballance=total_ballance )

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # User submited the form via POST
    if request.method == "POST":
        # Ensure Symbol was provided
        if not request.form.get("symbol"):
            return apology("must provide symbol", 403)
        # ensures number of shares were provided
        elif not request.form.get("numshares"):
            return apology("must enter number of shares", 403)
        # ensures a number was provided
        elif not request.form.get("numshares").isnumeric():
            return apology("must enter a whole number", 403)
        elif int(request.form.get("numshares")) == 0:
            return apology("number cannot be 0", 403)

        # Retrieve quote data
        quote = lookup(request.form.get("symbol"))
        if not quote:
            return apology("Could not retrieve quote data", 403)

        # load data
        try:
            # price of share
            price_share = float(quote["price"])
            # number of shares
            shares_amount = int(request.form.get("numshares"))

            # amount to pay
            total_price = price_share * shares_amount

            # user data
            userdata = db.execute("SELECT * FROM users WHERE id = :id",
                                   id=session["user_id"])
            # logged in user's cash
            cash = int(userdata[0]["cash"])

            # query database to check if user has shares in this stock
            has_shares = False
            shares_qry = db.execute("SELECT * FROM portfolio WHERE username = :username AND stockname = :stockname",
                                    username=userdata[0]["username"], stockname=request.form.get("symbol") )
            if shares_qry:
                has_shares = True

        except ZeroDivisionError: # TODO delete zero division to catch all errors
            return apology("An error has occured while loading data", 403)

        # buy stock
        if cash >= total_price:
            # if user has no database entry for this stock...
            if not has_shares:
                # insert new entry
                db.execute("INSERT INTO portfolio (username, stockname, totalprice, amount) VALUES(:username, :stockname, :totalprice, :amount)",
                            username=userdata[0]["username"], stockname=quote["symbol"], totalprice=float(price_share), amount=int(shares_amount) )
            # is user has a database entry for this stock...
            elif has_shares:
                # update entry
                db.execute("UPDATE portfolio SET totalprice = :totalprice, amount = amount + :amount WHERE username = :username AND stockname = :stockname",
                            totalprice=float(price_share), amount=int(shares_amount), username=userdata[0]["username"], stockname=request.form.get("symbol"))

            # subtract from user's cash
            db.execute("UPDATE users SET cash = cash - :total_price WHERE id = :id",
                        total_price=total_price, id=session["user_id"])
        else:
            return apology("You don't have enough money", 403)

        # insert transaction into history database
        transaction = "Brought"
        history_updated = db.execute("INSERT INTO history ('transaction', username, stockname, transactionprice, amount) VALUES(:transaction, :username, :stockname, :transactionprice, :amount)",
                                      transaction=transaction, username=userdata[0]["username"],
                                      stockname=quote["symbol"], transactionprice=usd(float(total_price)),
                                      amount=int(shares_amount))
        if not history_updated:
            return apology("history database could not be updated", 403)

        # Flash message
        if int(shares_amount) == 1:
            flash('Brought {} share from stock {}!'.format(int(shares_amount), quote["name"]))
        else:
            flash('Brought {} shares from stock {}!'.format(int(shares_amount), quote["name"]))

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET, display buy form
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # user data
    userdata = db.execute("SELECT * FROM users WHERE id = :id",
                           id=session["user_id"])
    if not userdata:
        apology("Could not retrieve user data", 403)

    # query history database
    history_database = db.execute("SELECT * FROM history WHERE username = :username",
                                   username=userdata[0]["username"])
    if not history_database:
        return apology("History is empty or database error", 403)

    return render_template("history.html", history=history_database, username=userdata[0]["username"])


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Flash message
    flash('You were successfully logged in')

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submiting a form via POST)
    if request.method == "POST":
        # Retrieve stock quote
        quote = lookup(request.form.get("symbol"))
        if not quote:
            return apology("Could not retrieve quote data", 403)

        # Render second template, displaying the stock quote
        return render_template("quoted.html", name=quote["name"],
                                price=usd(quote["price"]), symbol=quote["symbol"])

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Render first template containing the lookup form
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via Post)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure samepassword was submitted
        elif not request.form.get("samepassword"):
            return apology("please retype the password", 403)

        # Ensure passwords match
        elif not (request.form.get("password") == request.form.get("samepassword")):
            return apology("passwords did not match", 403)

        # Generate password hash
        hash = generate_password_hash(request.form.get("password"))

        # Insert user into database
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                            username=request.form.get("username"), hash=hash )
        if not result:
            return apology("Username already exists or database error", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Automatically log in the user
        session["user_id"] = rows[0]["id"]

        # Flash message
        flash('Registered!')

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # If submitted form via post...
    if request.method == "POST":
        # Ensure stock name was provided
        if not request.form.get("symbol"):
            return apology("must provide share's symbol's e.g. NFLX", 403)
        # Ensure amount of shares to sellwas provided
        elif not request.form.get("numshares"):
            return apology("must specify the amount of shares to sell", 403)
        # Ensures a number was provided as the amount of shares to sell
        elif not request.form.get("numshares").isnumeric():
            return apology("number of shares must be a whole, positive number", 403)
        elif int(request.form.get("numshares")) == 0:
            return apology("number of shares cannot be 0", 403)

        # Retrieve quote data
        quote = lookup(request.form.get("symbol"))
        if not quote:
            return apology("Could not retrieve quote data", 403)

        # load data
        # user data
        userdata = db.execute("SELECT * FROM users WHERE id = :id",
                               id=session["user_id"])
        if not userdata:
            return apology("Could not retrieve user data", 403)
        username = userdata[0]["username"]

        # number of share requested to be sold
        shares_amount_to_sell = int(request.form.get("numshares"))

        # portfolio query for the logged-in user's requested stock
        shares_qry = db.execute("SELECT * FROM portfolio WHERE username = :username AND stockname = :stockname",
                                 username=username, stockname=request.form.get("symbol"))
        if not shares_qry:
            return apology("Not enough shares to sell or database error", 403)

        # total shares in this stock
        shares_amount_in_stock = int(shares_qry[0]["amount"])

        # if user requested more shares than has in stock, apology
        if shares_amount_to_sell > shares_amount_in_stock:
            return apology("Not enough shares in stock", 403)

        # calculate total price of shares sold
        total_price_sold = shares_amount_to_sell * float(quote["price"])

        # update database totalprice, note, totalprice is actually the price of a share
        portfolio_updated = db.execute("UPDATE portfolio SET totalprice = :share_price, amount = amount - :amount WHERE username = :username AND stockname = :stockname",
                                          username=username, stockname=request.form.get("symbol"),
                                          share_price=float(quote["price"]), amount=shares_amount_to_sell)
        if not portfolio_updated:
            return apology("Could not refresh user's database entry", 403)

        # portfolio query for the logged-in user's requested stock
        shares_qry_2 = db.execute("SELECT * FROM portfolio WHERE username = :username AND stockname = :stockname",
                                 username=username, stockname=request.form.get("symbol") )
        if not shares_qry_2:
            return apology("Error: no stock entry or database error", 403)
        # if stock has 0 or less shares, delete entry
        if int(shares_qry_2[0]["amount"]) <= 0:
            entry_delete = db.execute("DELETE FROM portfolio WHERE username = :username AND stockname = :stockname",
                                       username=username, stockname=request.form.get("symbol"))
            if not entry_delete:
                return apology("Could not delete database entry", 403)

        # fund user
        funded = db.execute("UPDATE users SET cash = cash + :cash WHERE username = :username",
                            cash=total_price_sold, username=username)
        if not funded:
            return apology("Could not fund user", 403)


        # insert transaction into history database
        transaction = "Sold"
        history_updated = db.execute("INSERT INTO history ('transaction', username, stockname, transactionprice, amount) VALUES(:transaction, :username, :stockname, :transactionprice, :amount)",
                                      transaction=transaction, username=userdata[0]["username"],
                                      stockname=quote["symbol"], transactionprice=usd(float(total_price_sold)),
                                      amount=int(shares_amount_to_sell))
        if not history_updated:
            return apology("history database could not be updated", 403)

        # Flash message
        if int(shares_amount_to_sell) == 1:
            flash('Sold {} share from stock {}!'.format(int(shares_amount_to_sell), quote["name"]))
        else:
            flash('Sold {} shares from stock {}!'.format(int(shares_amount_to_sell), quote["name"]))

        # Redirect user to home page
        return redirect("/")

    # If reached page via GET, render html
    else:
        return render_template("sell.html")

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Deposit cash into user account"""
    # User submited the form via POST
    if request.method == "POST":
        # Ensure input was provided
        if not request.form.get("DepositAmount"):
            return apology("must specify the amount of money to deposit", 403)

        # username of logged in user
        userdata = db.execute("SELECT * FROM users WHERE id = :id",
                               id=session["user_id"])
        if not userdata:
            return apology("could not retrieve user data", 403)
        username = userdata[0]["username"]

        # amount to deposit, if not a floating point value, apology
        try:
            deposit_amount = float(request.form.get("DepositAmount"))
            if deposit_amount <= 0.0:
                return apology("must enter a positive number", 403)
        except:
            return apology("Please enter a floating point value representing amount to deposit in dollars", 403)

        # update user's cash
        deposited_cash = db.execute("UPDATE users SET cash = cash + :cash WHERE username = :username",
                                     cash=deposit_amount, username=username)
        if not deposited_cash:
            return apology("could not deposit cash", 403)

        # Flash message
        flash('Deposited ${} !'.format(deposit_amount))

        # Redirect user to home page on success
        return redirect("/")

    # User reached route via GET, display deposit form
    else:
        return render_template("deposit.html")

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)