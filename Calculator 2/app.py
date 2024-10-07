from flask import Flask, render_template, request, url_for, jsonify
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # To prevent the need for a display
import matplotlib.pyplot as plt
import io
import base64
import json
import plotly.express as px
import plotly

app = Flask(__name__)

# Tax brackets for Trump and Harris for different filing statuses
# For simplicity, defining brackets for 'single' and 'married' statuses
trump_brackets = {
    'single': [
        {'min': 0, 'max': 11000, 'rate': 0.10},
        {'min': 11001, 'max': 44725, 'rate': 0.12},
        {'min': 44726, 'max': 95375, 'rate': 0.22},
        {'min': 95376, 'max': 182100, 'rate': 0.24},
        {'min': 182101, 'max': 231250, 'rate': 0.32},
        {'min': 231251, 'max': 578125, 'rate': 0.35},
        {'min': 578126, 'max': float('inf'), 'rate': 0.37},
],
    'married': [
        {'min': 0, 'max': 19750, 'rate': 0.10},
        {'min': 19751, 'max': 80250, 'rate': 0.12},
        {'min': 80251, 'max': 171050, 'rate': 0.22},
        {'min': 171051, 'max': 326600, 'rate': 0.24},
        {'min': 326601, 'max': 414700, 'rate': 0.32},
        {'min': 414701, 'max': 622050, 'rate': 0.35},
        {'min': 622051, 'max': float('inf'), 'rate': 0.37},
    ],
    # Additional filing statuses can be added here
}

harris_brackets = {
    'single': [
        {'min': 0, 'max': 9275, 'rate': 0.10},
        {'min': 9275, 'max': 37650, 'rate': 0.15},
        {'min': 37651, 'max': 91150, 'rate': 0.25},
        {'min': 91151, 'max': 190150, 'rate': 0.28},
        {'min': 190151, 'max': 413350, 'rate': 0.33},
        {'min': 413350, 'max': 415050, 'rate': 0.35},
        {'min': 415050, 'max': float('inf'), 'rate': 0.396},
],
    'married': [
        {'min': 0, 'max': 19900, 'rate': 0.12},
        {'min': 19901, 'max': 81050, 'rate': 0.15},
        {'min': 81051, 'max': 172750, 'rate': 0.25},
        {'min': 172751, 'max': 329850, 'rate': 0.28},
        {'min': 329851, 'max': 418850, 'rate': 0.35},
        {'min': 418851, 'max': 628300, 'rate': 0.38},
        {'min': 628301, 'max': float('inf'), 'rate': 0.40},
    ],
    # Additional filing statuses can be added here
}

# Convert to pandas DataFrame for each filing status
trump_dfs = {status: pd.DataFrame(brackets) for status, brackets in trump_brackets.items()}
harris_dfs = {status: pd.DataFrame(brackets) for status, brackets in harris_brackets.items()}

# Sample median income data by state (simplified for example)
state_income_data = {
    'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California'],
    'MedianIncome': [49881, 77640, 58745, 45869, 75577],
    'StateCode': ['AL', 'AK', 'AZ', 'AR', 'CA']
}
state_income_df = pd.DataFrame(state_income_data)

# Sample county-level data (simplified for example)
county_income_data = {
    'State': ['Alabama', 'Alabama', 'Alabama', 'California', 'California'],
    'County': ['Autauga County', 'Baldwin County', 'Barbour County', 'Alameda County', 'Alpine County'],
    'MedianIncome': [60000, 65000, 40000, 80000, 70000],
    'CountyCode': ['01001', '01003', '01005', '06001', '06003']  # FIPS codes
}
county_income_df = pd.DataFrame(county_income_data)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        income = float(request.form['income'])
        num_kids = int(request.form['num_kids'])
        filing_status = request.form['filing_status']
        kids_ages = []
        for i in range(1, num_kids+1):
            age = int(request.form.get(f'kid_{i}_age', 0))
            kids_ages.append(age)
        # Calculate the effective tax rates using the selected filing status
        trump_tax = calculate_tax(income, trump_dfs[filing_status], kids_ages, 'trump')
        harris_tax = calculate_tax(income, harris_dfs[filing_status], kids_ages, 'harris')
        trump_effective_rate = round(trump_tax / income * 100, 2) if income > 0 else 0
        harris_effective_rate = round(harris_tax / income * 100, 2) if income > 0 else 0
        return render_template('results.html', income=income, num_kids=num_kids, kids_ages=kids_ages,
                               trump_tax=trump_tax, harris_tax=harris_tax,
                               trump_rate=trump_effective_rate, harris_rate=harris_effective_rate,
                               filing_status=filing_status)
    else:
        return render_template('index.html')

@app.route('/income_vs_tax')
def income_vs_tax():
    # For demonstration, using 'single' filing status
    filing_status = 'single'
    # Generate income levels
    income_levels = list(range(10000, 200001, 5000))
    trump_rates = []
    harris_rates = []

    for income in income_levels:
        trump_tax = calculate_tax(income, trump_dfs[filing_status], [17,17], 'trump')
        harris_tax = calculate_tax(income, harris_dfs[filing_status], [17,17], 'harris')
        trump_rate = trump_tax / income * 100
        harris_rate = harris_tax / income * 100
        trump_rates.append(trump_rate)
        harris_rates.append(harris_rate)

    # Plotting the bar chart using matplotlib
    fig, ax = plt.subplots(figsize=(12.8, 6.4))
    index = range(len(income_levels))
    bar_width = 0.35
    ax.bar(index, trump_rates, bar_width, label="Trump's Plan")
    ax.bar([i + bar_width for i in index], harris_rates, bar_width, label="Harris's Plan")
    ax.set_xlabel('Income Level (Thousands of $)')
    ax.set_ylabel('Effective Tax Rate (%)')
    ax.set_title('Income Level vs Effective Tax Rate')
    ax.set_xticks([i + bar_width / 2 for i in index])
    ax.set_xticklabels([f'${i // 1000}k' for i in income_levels], rotation=45)
    ax.legend()

    # Save the plot to a PNG image in memory
    img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    plt.close(fig)  # Close the figure to free memory

    return render_template('income_vs_tax.html', plot_url=plot_url)

@app.route('/map')
def map():
    # For demonstration, using 'single' filing status
    filing_status = 'single'
    # Calculate effective tax rates for median incomes at the state level
    trump_rates = []
    harris_rates = []
    for income in state_income_df['MedianIncome']:
        trump_tax = calculate_tax(income, trump_dfs[filing_status], [], 'trump')
        harris_tax = calculate_tax(income, harris_dfs[filing_status], [], 'harris')
        trump_rate = trump_tax / income * 100
        harris_rate = harris_tax / income * 100
        trump_rates.append(trump_rate)
        harris_rates.append(harris_rate)
    state_income_df['TrumpRate'] = trump_rates
    state_income_df['HarrisRate'] = harris_rates

    # Create initial map at the state level
    fig = px.choropleth(
        state_income_df,
        locations='StateCode',
        locationmode='USA-states',
        color='MedianIncome',
        hover_data=['State', 'MedianIncome', 'TrumpRate', 'HarrisRate'],
        scope='usa',
        labels={'MedianIncome': 'Median Income'},
        title='Median Income and Effective Tax Rates by State'
    )

    # Update hover template
    fig.update_traces(
        hovertemplate='<b>%{customdata[0]}</b><br>' +
                      'Median Income: $%{customdata[1]}<br>' +
                      "Trump's Effective Rate: %{customdata[2]:.2f}%<br>" +
                      "Harris's Effective Rate: %{customdata[3]:.2f}%<extra></extra>"
    )

    graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('map.html', graphJSON=graph_json)

@app.route('/get_county_data/<state_code>')
def get_county_data(state_code):
    # For demonstration, using 'single' filing status
    filing_status = 'single'
    # Filter counties for the selected state
    state_name = state_income_df[state_income_df['StateCode'] == state_code]['State'].values[0]
    counties_in_state = county_income_df[county_income_df['State'] == state_name]

    # Calculate effective tax rates for counties
    trump_rates = []
    harris_rates = []
    for income in counties_in_state['MedianIncome']:
        trump_tax = calculate_tax(income, trump_dfs[filing_status], [], 'trump')
        harris_tax = calculate_tax(income, harris_dfs[filing_status], [], 'harris')
        trump_rate = trump_tax / income * 100
        harris_rate = harris_tax / income * 100
        trump_rates.append(trump_rate)
        harris_rates.append(harris_rate)
    counties_in_state['TrumpRate'] = trump_rates
    counties_in_state['HarrisRate'] = harris_rates

    # Create county-level map
    fig = px.choropleth(
        counties_in_state,
        geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
        locations='CountyCode',
        color='MedianIncome',
        hover_data=['County', 'MedianIncome', 'TrumpRate', 'HarrisRate'],
        scope='usa',
        labels={'MedianIncome': 'Median Income'},
        title=f'Median Income and Effective Tax Rates by County in {state_name}'
    )

    # Update hover template
    fig.update_traces(
        hovertemplate='<b>%{customdata[0]}</b><br>' +
                      'Median Income: $%{customdata[1]}<br>' +
                      "Trump's Effective Rate: %{customdata[2]:.2f}%<br>" +
                      "Harris's Effective Rate: %{customdata[3]:.2f}%<extra></extra>"
    )

    fig.update_geos(fitbounds="locations", visible=False)

    county_graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return county_graph_json

def calculate_tax(income, brackets_df, kids_ages, plan):
    tax = 0
    for index, row in brackets_df.iterrows():
        min_income = row['min']
        max_income = row['max']
        rate = row['rate']
        if income > min_income:
            taxable_income = min(income, max_income) - min_income
            tax += taxable_income * rate
        else:
            break
    # Calculate tax credits
    if plan == 'trump':
        # $2000 per child under age 17
        tax_credit = sum(2000 for age in kids_ages if age < 17)
    elif plan == 'harris':

        tax_credit = 0
        for _ in kids_ages:
            if _ <= 1:
                tax_credit += 6000
            elif _ <= 5:
                tax_credit += 3600        
            elif _ < 18:
                tax_credit += 3000
    else:
        tax_credit = 0
    # Subtract tax credit from tax liability
    tax -= tax_credit
    if tax < 0:
        tax = 0
    return round(tax, 2)

if __name__ == '__main__':
    app.run(debug=True)
