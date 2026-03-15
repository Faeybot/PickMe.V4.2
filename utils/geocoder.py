from geopy.geocoders import Nominatim

def get_city_name(lat, lon):
    try:
        geolocator = Nominatim(user_agent="pickme_bot")
        location = geolocator.reverse((lat, lon), timeout=10)
        if location and 'address' in location.raw:
            address = location.raw['address']
            # Ambil kota atau kabupaten
            city = address.get('city') or address.get('town') or address.get('city_district')
            return city if city else "Unknown"
    except:
        return "Unknown"

def create_hashtag(city_name):
    if city_name and city_name != "Unknown":
        # Menghapus spasi dan menambah #
        return f"#{city_name.replace(' ', '')}"
    return "#LuarKota"
  
