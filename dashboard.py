import streamlit as st
import pandas as pd
import numpy as np
import requests
import tweepy
import config
from config import IEX_API_TOKEN
import datetime
import psycopg2, psycopg2.extras
import plotly.graph_objects as go

auth = tweepy.OAuthHandler(config.TWIIER_CONSUMER_KEY, config.TWIIER_CONSUMER_SECRET)
auth.set_access_token(config.TWIIER_ACCESS_TOKEN, config.TWIIER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

connection = psycopg2.connect(host=config.DB_HOST, database=config.DB_NAME, user=config.DB_USER, password=config.DB_PASS)
cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)


option = st.sidebar.selectbox('Which Dashboard', ('twitter', 'Wallstreetbets', 'stockwits', 'chart', 'News', 'pattern'), 2)

if option == 'twitter':
    try:
        st.header("Twitter dashboard")
        for username in config.TWITTER_USERNAMES:
            st.subheader(username)

            user = api.get_user(username)

            tweets = api.user_timeline(username)

            st.image(user.profile_image_url)

            for tweet in tweets:
                if '$' in tweet.text:
                    words = tweet.text.split(' ')
                    for word in words:
                        if word.startswith('$') and word[1:].isalpha():
                            symbol = word[1:]
                            st.write(symbol)
                            st.write(tweet.text)
                            st.image(f"https://charts2.finviz.com/chart.ashx?t={symbol}")
    except Exception as e:
        print(e)

if option == 'Wallstreetbets':  #Can make a graph to visyalise the number of comments change
    st.header("Wallstreetbets dashboard")
    num_days = st.sidebar.slider('Number of days', 1, 30, 3)


    cursor.execute("""
    SELECT count(*) AS num_mentions, symbol
    FROM mention JOIN stock on stock.id = mention.stock_id
    WHERE date(dt) > current_date - interval '%s day'
    GROUP BY stock_id, symbol
    HAVING COUNT(symbol) > 10
    ORDER BY num_mentions DESC
    """, (num_days,))

    counts = cursor.fetchall()
    df = pd.DataFrame(counts, columns=['Stocks', 'Counts'])
    st.subheader("Top Mentioned Stocks")
    st.table(df)   #How to rewmove index column in streamlit

    cursor.execute("""
    SELECT date(dt) as day, symbol, COUNT(symbol) as num_mentions
    FROM mention JOIN stock on stock.id = mention.stock_id
    WHERE date(dt) > current_date - interval '%s day'
    GROUP BY symbol, date(dt)
    HAVING COUNT(symbol) > 10
    """, (num_days,))

    daily_mention = cursor.fetchall()

    cursor.execute("""
    SELECT symbol, message, url, dt
    FROM mention JOIN stock on stock.id = mention.stock_id
    ORDER BY dt DESC
    Limit 100
    """)

    mentions = cursor.fetchall()

    top_stock = []
    for count in counts:
        stock_symbol = count[1]
        top_stock.append(stock_symbol)

    # print(top_stock)

    # stock_select = st.sidebar.checkbox('GME','CLOV') #Later can make a list to filter the stock that is checked
    # if stock_select == 'GME':
    #     pass

    # df_daily = pd.DataFrame(daily_mention, columns=['Date', 'Symbol', 'Count'])
    # df_daily = df_daily.T
    # st.line_chart(df_daily)
    # st.table(df_daily)

    for num_stock in range(len(top_stock)):  #Only showing the top stocks mentions
        for mention in mentions:
            if mention['symbol'] == top_stock[num_stock]:
                st.text(mention['symbol'])
                st.text(mention['dt'])
                st.text(mention['symbol'])
                st.text(mention['message'])
                st.text(mention['url'])

        rows = cursor.fetchall()
        st.write(rows)

if option == 'stockwits':
    symbol = st.sidebar.text_input("Symbol", value='AAPL', max_chars=5)

    st.header(f"Here shows stockwits comments for {symbol}")

    r = requests.get(f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json")

    data = r.json()

    for message in data['messages']:
        st.image(message['user']['avatar_url'])
        st.write(message['user']['username'])
        st.write(message['created_at'])
        st.write(message['body'])

if option == 'chart':
    st.header("chart dashboard")
    st.subheader("Currently it only support data on ARK series stocks")  #Need to expand the database to all stocks?

    symbol = st.sidebar.text_input("Symbol", value='MSFT', max_chars=None, key=None, type='default')

    data = pd.read_sql("""
        select date(dt) as day, round(open,2) as open, round(high,2) as high, round(low,2) as low, round(close,2) as close
        from stock_price
        where stock_id = (select id from stock where UPPER(symbol) = %s) 
        order by day asc""", connection, params=(symbol.upper(),))

    st.subheader(symbol.upper())

    fig = go.Figure(data=[go.Candlestick(x=data['day'],
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name=symbol)])

    fig.update_xaxes(type='category')
    fig.update_layout(height=700)

    st.plotly_chart(fig, use_container_width=True)

    st.table(data)

if option == 'News':
    symbol = st.sidebar.text_input("Symbol", value="MSFT", max_chars=5)
    last = 10 #Number of news -1 returned
    url = f"https://cloud.iexapis.com/v1/stock/{symbol}/news/last/{last}?token={IEX_API_TOKEN}"
    r = requests.get(url)
    news = r.json()

    for article in news:
        st.subheader(article['headline'])
        dt = datetime.datetime.utcfromtimestamp(article['datetime']/1000).isoformat()
        st.write(f"Posted by {article['source']} at {dt}")
        st.write(article['url'])
        st.write(article['summary'])
        st.image(article['image'])

if option == 'pattern': #Can Add datetime on the sidebar
    st.header("pattern dashboard")

    pattern = st.sidebar.selectbox(
        "Which pattern?",
        ("engulfing", "threebar")
    )

    st.write('Update later')

    # if pattern == 'engulfing':
    #     cursor.execute("""
    #     SELECT * FROM ( SELECT day, open, close, stock_id, LAG(close, 1)
    #     OVER ( PARTITION BY stock_id ORDER BY day ) previous_close, LAG(open, 1)
    #     OVER ( PARTITION BY stock_id ORDER BY day ) previous_open FROM daily_bars ) a
    #     WHERE previous_close < previous_open AND close > previous_open AND open < previous_close
    #     AND day = '2021-04-23';
    #     """)
    #
    # if pattern == 'threebar':
    #     cursor.execute("""
    #     SELECT * FROM ( SELECT day, close, volume, stock_id, LAG(close, 1) OVER ( PARTITION BY stock_id ORDER BY day )
    #     previous_close, LAG(volume, 1) OVER ( PARTITION BY stock_id ORDER BY day ) previous_volume, LAG(close, 2)
    #     OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_close, LAG(volume, 2)
    #     OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_volume, LAG(close, 3)
    #     OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_previous_close,
    #     LAG(volume, 3) OVER ( PARTITION BY stock_id ORDER BY day ) previous_previous_previous_volume FROM daily_bars ) a
    #     WHERE close > previous_previous_previous_close and previous_close < previous_previous_close and previous_close < previous_previous_previous_close
    #     AND volume > previous_volume and previous_volume < previous_previous_volume and previous_previous_volume < previous_previous_previous_volume
    #     AND day = '2021-04-23';
    #     """)
    #
    # rows = cursor.fetchall()
    #
    # for row in rows:
    #     st.image(f"https://charts2.finviz.com/chart.ashx?t={row['symbol']}")




