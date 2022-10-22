import urllib.parse, urllib.request, urllib.error, json, math

from flask import Flask, render_template, request
import logging
app = Flask(__name__)

# this is going to take a holiday, a year, and a location, and tell the sun up and sun down times of that holiday
# that year for the given location

# PTV Geocoding and Places API
# https://developer.myptv.com/Home.htm
geo_api_key = "ODQxMTE0MjE5ZTBiNDg4ZmI5ZmVmMjQyZDg1NGM4NzE6ZmFkODVjNTItYTlmYS00YWM4LTgzYmUtNzIwMWQ0YmE3ZTk0"
geo_base_url = "https://api.myptv.com/geocoding/v1/locations/by-address?"

# Calenderific Holiday API
# https://calendarific.com/api-documentation
holiday_api_key = "7b1985fb18e3d5cc330b9218734ffc0d3606f7ae"
holiday_base_url = "https://calendarific.com/api/v2/holidays?"

# Sunrise Sunset API
# https://sunrise-sunset.org/api
sunrise_base_url = "https://api.sunrise-sunset.org/json?"

# Abstract Timezone API
# https://www.abstractapi.com/time-date-timezone-api
timezone_api_key = "5f25f3c74bac48a2bf7f6231cc68da40"
timezone_base_url = "https://timezone.abstractapi.com/v1/convert_time?"

# handler for project_home.html
@app.route("/")
def main_handler():
    app.logger.info("In MainHandler")
    return render_template("project_home.html", page_title="Holiday Sun - Home")

# handler for project_contact.html
@app.route("/contact")
def contact_handler():
    app.logger.info("In ContactHandler")
    return render_template("project_contact.html", page_title="Holiday Sun - Contact")

# handler for project_results.html
@app.route("/results")
def results_handler():
    app.logger.info("In RouteHandler")
    holiday = request.args.get('holiday')
    h_country = request.args.get('h_country')
    postal = request.args.get('postal')
    p_country = request.args.get('p_country')
    try:
        year = int(request.args.get('year'))
    except ValueError:
        return render_template("project_result.html", page_title="Holiday Sun - Results", results=
        "Please give a valid year (integer between 0 and 9999, do not include BC/AD/CE).")
    # preparing input data
    if p_country == None and h_country == None:
        return render_template("project_result.html", page_title="Holiday Sun - Results", results=
        "Please give at least 1 country. If a second country is not given, the 1 country will be used for both"
        " the country of the holiday and the country of the postal code.")
    if p_country == None:
        p_country = h_country
    if h_country == None:
        h_country = p_country
    if holiday == None:
        return render_template("project_result.html", page_title="Holiday Sun - Results", results=
        "Please enter a holiday.")
    if postal == None:
        return render_template("project_result.html", page_title="Holiday Sun - Results", results=
        "Please enter a postal code.")
    # input data
    results = holiday_processor(holiday=holiday, h_country=h_country, postal=postal, p_country=p_country, year=year)
    # sending data to templates
    return render_template("project_result.html", page_title="Holiday Sun - Results", results=
    "{results}".format(results=results))

# stripping punctuation, removing spaces and putting in lowercase
def strip_(string):
    punctuation = [".", ",", "'", ".", "(", ")", "<", ">", "\\", "`", "~", "?", "!", ";", '"', "*", ":", "[", "]",
                   "-", "+", "/", "&", "—", " ", "@", "#", "$", "%", "^", "_", "{", "}"]
    string = string.lower()
    for char in punctuation:
        string = string.replace(char, "")
    return(string)

# API request
def apirequest(url, params):
    header = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '
                            'AppleWebKit/537.11 (KHTML, like Gecko) '
                            'Chrome/23.0.1271.64 Safari/537.11',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
              'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
              'Accept-Encoding': 'none',
              'Accept-Language': 'en-US,en;q=0.8',
              'Connection': 'keep-alive'}
    apirequest = "{url}{params}".format(url=url, params=params)
    req = urllib.request.Request(url=apirequest, headers=header)
    requeststr = urllib.request.urlopen(req).read()
    return json.loads(requeststr)

# geo API and sunrise API parameters
def parameters(tuple):
    params = {}
    for pair in tuple:
        params[pair[0]] = pair[1]
    return urllib.parse.urlencode(params)

# holiday API parameters
def holiday_parameters(h_country, year):
    return "{y}/{h}".format(y=year, h=h_country)

# extracting necessary information from geo API
def geo_getinfo(geo_data):
    city = geo_data["locations"][0]["address"]["city"]
    latitude = geo_data["locations"][0]["referencePosition"]["latitude"]
    longitude = geo_data["locations"][0]["referencePosition"]["longitude"]
    return [city, latitude, longitude]

# find specific holiday from the holiday API request
def find_holiday(holiday_data, holiday):
    try:
        for data in holiday_data['response']['holidays']:
            if strip_(data['name']) == strip_(holiday) or strip_(data['name']) == strip_(holiday + "day"):
                return data
    except TypeError:
        return "error"

# extract necessary information from holiday API
def holiday_getinfo(holiday_data):
    info = [holiday_data['date']['iso'], holiday_data['description']]
    return info

# extracting sun rise/set times
def sunrise_getinfo(sunrise_data):
    sunrise = sunrise_data["results"]["sunrise"]
    sunset = sunrise_data["results"]["sunset"]
    return [sunrise, sunset]

# turns the given military time into am or pm time
def am_pm(time):
    t = int(time[0:2])
    if t > 12:
        return str(t-12) + time[2:-3] + " PM"
    if t == 12:
        return time[:-3] + " PM"
    if t == 0:
        return "12" + time[2:-3] + " AM"
    else:
        if t < 10:
            return time[1:-3] + " AM"
        else:
            return time[0:-3] + " AM"

# main method
def holiday_processor(holiday=None, h_country=None, postal=None, p_country=None, year=None):
    # accessing API and giving output
    geo_paramstr = parameters((['postalCode', postal], ['country', p_country], ['apiKey', geo_api_key]))
    geo_data = apirequest(geo_base_url, geo_paramstr)
    if len(geo_data['locations']) == 0 or len(geo_data['locations']) > 1:
        return("There was an issue with the given country and/or postal code. Please review both.")
    geo_info = geo_getinfo(geo_data)
    h_params = parameters((['api_key', holiday_api_key], ['country', h_country], ['year', year]))
    holidays = apirequest(holiday_base_url, h_params)
    holiday_data = find_holiday(holidays, holiday)
    if holiday_data == 'error':
        return "There seems to be an issue with the year you chose. Try picking one between 1800 and 2400."
    if holiday_data == None:
        return("We could not find that holiday. Please check that the holiday and country of celebration are"
               " spelled correctly.")
    holiday = holiday_data['name']
    holiday_info = holiday_getinfo(holiday_data)
    s_params = parameters((['lat', geo_info[1]], ['lng', geo_info[2]], ['date', holiday_info[0]], ['formatted', 0]))
    try:
        sunrise_data = apirequest(sunrise_base_url, s_params)
    except urllib.error.HTTPError:
        return("There was an error, please try again.")
    sunrise_info = sunrise_getinfo(sunrise_data)
    sunrise_info[0] = sunrise_info[0][:-6]
    sunrise_info[1] = sunrise_info[1][:-6]
    sunrise_timezone_paramstr = parameters((['api_key', timezone_api_key], ['base_location', "London, United Kingdom"],
        ['base_datetime', sunrise_info[0]], ['target_location', "{lat},{long}".format(lat=geo_info[1], long=geo_info[2])]))
    sunrise_timezone_data = apirequest(timezone_base_url, sunrise_timezone_paramstr)
    sunrise_time_mt = (sunrise_timezone_data["target_location"]["datetime"])[11:]
    sunrise_time = am_pm(sunrise_time_mt)
    sunset_timezone_paramstr = parameters((['api_key', timezone_api_key], ['base_location', "London, United Kingdom"],
        ['base_datetime', sunrise_info[1]], ['target_location', "{lat},{long}".format(lat=geo_info[1], long=geo_info[2])]))
    sunset_timezone_data = apirequest(timezone_base_url, sunset_timezone_paramstr)
    sunset_time_mt = (sunset_timezone_data["target_location"]["datetime"])[11:]
    sunset_time = am_pm(sunset_time_mt)
    return ("On {holiday} ({date}) in {city}, the sun will rise at {sunrise} and will set at {sunset}. FUN FACT: {description}"
            .format(holiday=holiday, date=holiday_info[0], city=geo_info[0], sunrise=sunrise_time, sunset=sunset_time,
                    description=holiday_info[1]))

if __name__ == "__main__":
    app.run(host="localhost", port=8080, debug=True)
