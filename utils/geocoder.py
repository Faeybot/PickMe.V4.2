from geopy.geocoders import Nominatim
import logging

def get_city_name(lat, lon):
    try:
        # User_agent bebas, tapi unik agar tidak di-block
        geolocator = Nominatim(user_agent="pickme_bot_v3")
        location = geolocator.reverse((lat, lon), timeout=10)
        
        if location and 'address' in location.raw:
            address = location.raw['address']
            # Mencoba mengambil data kota, kota kecil, atau distrik
            city = address.get('city') or address.get('town') or address.get('city_district') or address.get('county')
            return city if city else "Unknown City"
    except Exception as e:
        logging.error(f"Geocoder error: {e}")
        return "Unknown City"
    return "Unknown City"

def create_hashtag(city_name):
    if city_name and city_name != "Unknown City":
        # Menghapus spasi dan karakter aneh agar jadi hashtag yang valid
        clean_name = "".join(e for e in city_name if e.isalnum())
        return f"#{clean_name}"
    return "#LuarKota"
    
