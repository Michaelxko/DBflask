from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

def create_bahn_guru_link(origin, destination, date, departure_after=None, arrival_before=None, duration=None, max_changes=None):
    base_url = "https://bahn.guru/day"
    origin_encoded = origin.replace(" ", "%20")
    destination_encoded = destination.replace(" ", "%20")
    url = f"{base_url}?origin={origin_encoded}&destination={destination_encoded}&class=2&bc=4&age=Y"
    if duration is not None:
        url += f"&duration={duration}"
    if max_changes is not None:
        url += f"&maxChanges={max_changes}"
    url += f"&date={date}"
    if departure_after:
        url += f"&departureAfter={departure_after}"
    if arrival_before:
        url += f"&arrivalBefore={arrival_before}"
    return url

def create_bahn_guru_links(origins, destinations, date, departure_after=None, arrival_before=None, duration=None, max_changes=None):
    links = []
    for origin in origins:
        for destination in destinations:
            url = create_bahn_guru_link(origin, destination, date, departure_after, arrival_before, duration, max_changes)
            links.append({"url": url, "origin": origin, "destination": destination})
    return links

def scrape_data_and_create_dataframe(links):
    all_rows = []
    for link_info in links:
        url = link_info["url"]
        origin = link_info["origin"]
        destination = link_info["destination"]
        print(f"Scraping URL: {url}")  # Debug statement
        response = requests.get(url).text
        soup = BeautifulSoup(response, 'html.parser')
        table = soup.find('table')
        if table is not None:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if cols:
                    col_data = [col.text.strip() for col in cols]
                    fahrzeit_index = 2
                    if len(col_data) > fahrzeit_index and len(col_data[fahrzeit_index]) > 2:
                        col_data[fahrzeit_index] = col_data[fahrzeit_index][:-2]
                    preis_index = 6
                    if len(col_data) > preis_index and len(col_data[preis_index]) > 3:
                        col_data[preis_index] = col_data[preis_index][:-3]
                    col_data.extend([origin, destination])
                    all_rows.append(col_data)
        else:
            print(f"No table found for URL: {url}")  # Debug statement
    column_names = ["Abfahrt", "Ankunft", "Fahrzeit", "Umstiege", "VIA", "Mit", "Preis", "Von", "Bis"]
    df = pd.DataFrame(all_rows, columns=column_names)
    df['Preis'] = df['Preis'].str.replace('€', '').str.replace(',', '.').astype(float)  # Clean and convert 'Preis' to numeric
    print(f"DataFrame created with {len(df)} rows")  # Debug statement
    return df

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    print("Form submitted")  # Debug statement
    traveler = request.form.get('traveler')
    predate = request.form.get('date')
    date = datetime.strptime(predate, '%Y-%m-%d').strftime('%d.%m.%Y')
    departure_after = request.form.get('departure')
    arrival_before = request.form.get('arrival')
    origins = request.form.getlist('origins')
    destinations = request.form.getlist('destinations')
    
    print(f"Traveler: {traveler}")  # Debug statement
    print(f"Date: {date}")  # Debug statement
    print(f"Departure: {departure_after}")  # Debug statement
    print(f"Arrival: {arrival_before}")  # Debug statement
    print(f"Origins: {origins}")  # Debug statement
    print(f"Destinations: {destinations}")  # Debug statement
    
    user_inputs = {
        'traveler': traveler,
        'date': predate,
        'departure': departure_after,
        'arrival': arrival_before,
        'origins': origins,
        'destinations': destinations
    }
    
    links = create_bahn_guru_links(origins, destinations, date, departure_after, arrival_before, duration=4, max_changes=1)
    print(f"Generated links: {links}")  # Debug statement
    df = scrape_data_and_create_dataframe(links)
    print("Dataframe created")  # Debug statement
    
    if df.empty:
        print("No data found for the given criteria")  # Debug statement
        return render_template('results.html', tables=[], message="No data found for the given criteria.", date=date, origins=origins, destinations=destinations)
    
    print(df.head())  # Debug statement to show the first few rows of the DataFrame

    df_price = df.sort_values(by="Preis")
    df_abfahrt = df.sort_values(by "Abfahrt")
    df_ankunft = df.sort_values(by="Ankunft")
    
    return render_template('results.html', 
                           tables=[
                               df.to_html(classes='data', header="true", index=False),
                               df_price.to_html(classes='data', header="true", index=False),
                               df_abfahrt.to_html(classes='data', header="true", index=False),
                               df_ankunft.to_html(classes='data', header="true", index=False)
                           ], 
                           titles=df.columns.values, 
                           date=date, 
                           origins=origins, 
                           destinations=destinations)

if __name__ == "__main__":
    # For deployment, port must be set dynamically for compatibility with web services
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
