# Input
# - dfs = array of dataframes [df[0], df[1], ...]
# - Each df has time index, of time type.
# - Value of dataframe is of string type!!! You are responsible for coverting to the right data type
# - The whole processing needs to fit into ~15 seconds
# + another 5 seconds for overhear
# + another 20 seconds for cold start of the container.
# Total response max ~30 seconds.

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
from PIL import Image
import base64
from matplotlib.dates import MO, TU, WE, TH, FR, SA, SU


#######################################################
# Here is the data set: Historical Hourly Weather Data 2012-2017
# https://www.kaggle.com/datasets/selfishgene/historical-hourly-weather-data

def load_dataset():
    dfs = []
    dfs.append(pd.read_csv('./data/Historical Hourly Weather Data 2012-2017/temperature.csv', \
                           usecols=["datetime", "Chicago", "New York", "Boston"], index_col="datetime"))
    dfs[0].index.name = "time"
    dfs[0].index = pd.to_datetime(dfs[0].index, format='ISO8601')

    dfs.append(pd.read_csv('./data/Historical Hourly Weather Data 2012-2017/pressure.csv', \
                           usecols=["datetime", "Chicago", "New York", "Boston"], index_col="datetime"))
    dfs[1].index.name = "time"
    dfs[1].index = pd.to_datetime(dfs[1].index, format="%d.%m.%Y %H:%M")

    # The data set does not end the same day for all cities. Let's cut it off.
    dfs[0] = dfs[0][~(dfs[0].index >= '2017-10-01')]
    dfs[0] = dfs[0][~(dfs[0].index < '2017-08-01')]
    dfs[1] = dfs[1][~(dfs[1].index >= '2017-10-01')]
    dfs[1] = dfs[1][~(dfs[1].index < '2017-08-01')]
    return dfs


def save_data_to_2minlog(dfs, temperature_secret, pressure_secret ):
    import requests

    for t, row in dfs[0].iterrows():
        print(t, row)
        # https://www.w3schools.com/tags/ref_urlencode.ASP
        url = f"https://h9kkg3e1md.execute-api.us-east-1.amazonaws.com/log?" + \
              f"project_secret={temperature_secret}&" + \
              f"Chicago={row['Chicago']}&New%20York={row['New York']}&Boston={row['Boston']}" + \
              f"&time={t.isoformat()}"
        print(url)
        r = requests.get(url)
        print(r.status_code, r.headers)
        if (r.status_code != 200):
            print("Error!")
            print(r)
            exit(1)
        print('***********************')

    for t, row in dfs[1].iterrows():
        print(t, row)
        # https://www.w3schools.com/tags/ref_urlencode.ASP
        url = f"https://h9kkg3e1md.execute-api.us-east-1.amazonaws.com/log?" + \
              f"project_secret={pressure_secret}&" + \
              f"Chicago={row['Chicago']}&New%20York={row['New York']}&Boston={row['Boston']}" + \
              f"&time={t.isoformat()}"
        print(url)
        r = requests.get(url)
        print(r.status_code, r.headers)
        if (r.status_code != 200):
            print("Error!")
            print(r)
            exit(1)
        print('***********************')




def generate_image(dfs, output_type):
    #######################################################
    # Here it starts - input is array of data frames: dfs = [df[0], df[1]]; output_type = "jpg"
    # Out

    dfs[0] = dfs[0].astype(float)
    dfs[1] = dfs[1].astype(float)

    # Recalculate from Kelvin to Fahrenheit
    dfs[0] = (dfs[0] - 273.15) * 9 / 5 + 32

    points = 24 * 15  # Show 15 days back

    sns.set_theme()
    sns.set(style="white")
    dpi = 90
    plt.figure(figsize=(800 / dpi, 600 / dpi), dpi=dpi)  # 800 x 600 pixels

    for col in dfs[0].columns:
        last_value = dfs[0].iloc[-1:][col].values[0]  # Last value of the dataframe from column COL
        ax1 = sns.lineplot(data=dfs[0].iloc[-points:][col],
                           linestyle="-",
                           label=f"T: {col}: {last_value:.1f} °F",
                           legend=False)  # Does not go to separate legend, only to joint one

    yshift1 = 40  # Prevent overlap of the two graphs
    ax1.set_ylim(bottom=ax1.get_ylim()[0], top=ax1.get_ylim()[1] + yshift1)
    ax1.set_ylabel('Temperature (°F)')
    ax1.set(xlabel=None)  # We do not want a title for time

    ax2 = plt.twinx()  # Second Y axis, sharing ne X axis.
    for col in dfs[0].columns:
        last_value = dfs[0].iloc[-1:][col].values[0]
        ax2 = sns.lineplot(data=dfs[1].iloc[-points:][col], ax=ax2,
                           linestyle="--", label=f"P: {col}: {last_value:.1f} hPa")

    yshift2 = yshift1  # Prevent overlap of the two graphs
    yshift2top = 10  # Prevent overlap of the two graphs
    ax2.set_ylim(bottom=ax2.get_ylim()[0] - yshift2, top=ax2.get_ylim()[1] + yshift2top)
    ax2.set_ylabel('Pressure (hPa)')

    # https://seaborn.pydata.org/tutorial/aesthetics.html#removing-axes-spines
    sns.despine(offset=10, trim=True, right=False);

    # Format and ticks at X axes
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())  # byweekday=MO))
    plt.gcf().autofmt_xdate(rotation=90)

    # Combine legends
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lab = labels + labels2
    lin = lines + lines2

    # Change position in label - to have it logically: fist row temperatures, second row pressure.
    lab = [lab[i] for i in [0, 3, 1, 4, 2, 5]]
    lin = [lin[i] for i in [0, 3, 1, 4, 2, 5]]

    ax2.legend(lin, lab, loc="best", frameon=True, ncol=3)  # title='Now'

    buf = io.BytesIO()
    plt.savefig(buf, format=output_type)  # .jpg, .png...
    buf.seek(0)
    buf.flush()
    img = buf.read()
    return img


if __name__ == "__main__": # If run outside of AWS Lambda
    print("Main")
    dfs = load_dataset()
    # temperature_secret = "SEC-XXX"
    # pressure_secret = "SEC-XXX"
    ## save_data_to_2minlog(dfs, temperature_secret, pressure_secret ) ## do not run, unless you want to save the data to cloud
    img = generate_image(dfs, 'jpg')
    image = Image.open(io.BytesIO(img))
    image.show()
else:
    print("Lambda")
    # Global variables - input:
    # - dfs
    # - queryStringParameters
    # Global variables - output:
    # - response - http type response
    print("queryStringParameters", queryStringParameters)
    img = generate_image(dfs, 'jpg')

    response = {
        'headers': {"Content-Type": "image/png"},
        'statusCode': 200,
        'body': base64.b64encode(img).decode('utf-8'),
        'isBase64Encoded': True
    }

