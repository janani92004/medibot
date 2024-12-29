import streamlit as st
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import folium_static
import requests
import google.generativeai as genai
import ast
from streamlit_geolocation import streamlit_geolocation 
import time
import os
# Access the Google API key from the secrets
# Configure Gemini (add this near your imports)
api_key = os.getenv('api_key')

# Configure the API with the key
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Load datasets
dataset1_path = 'medical_records.csv'
dataset2_path = 'dosage_records.csv'
first_aid_dataset_path = 'first_aid.csv'

dataset1 = pd.read_csv(dataset1_path)
dataset2 = pd.read_csv(dataset2_path, encoding='latin-1')
first_aid_dataset = pd.read_csv(first_aid_dataset_path, encoding='latin-1')

# Initialize global DataFrames
df_first_aid = pd.DataFrame(columns=['Date', 'Time', 'Emergency'])
df_diagnosis = pd.DataFrame(columns=['Date', 'Time', 'Name', 'Age', 'Diagnosis', 'Recommendation'])

# At the start of your file, after imports
st.set_page_config(layout="wide")  # Makes the page use full width

# Update the title styling
st.markdown("""
    <h1 style='text-align: left;'>Medi-bot: Your Personal Medical Chat-bot</h1>
    """, unsafe_allow_html=True)

# Wrap main content in columns for better spacing
col1, col2, col3 = st.columns([2,1,1])  # Makes the first column wider

# At the start of your main code, add these session state initializations
if 'current_task' not in st.session_state:
    st.session_state.current_task = None
if 'show_hospitals' not in st.session_state:
    st.session_state.show_hospitals = False
if 'show_medical_shops' not in st.session_state:
    st.session_state.show_medical_shops = False

with col1:  # Put main content in left column
    # User choice
    user_choice = st.selectbox(
        "What help do you need?",
        ["First Aid", "Diagnosis", "Medicine Recommendation"]
    )

    # Clear previous results when task changes
    if 'previous_task' not in st.session_state:
        st.session_state.previous_task = user_choice
    if st.session_state.previous_task != user_choice:
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False
        st.session_state.previous_task = user_choice

    # Function to provide emergency advice
    def provide_emergency_advice(user_emergency, dataset):
        for _, row in dataset.iterrows():
            if pd.notna(row['Emergency']):
                if any(keyword in user_emergency.lower() for keyword in row['Emergency'].lower().split()):
                    return row.to_dict()  # Convert the row to a dictionary
        return None

    # Function to recommend drug
    def recommend_drug(symptoms, age, dataset1, dataset2):
        symptoms_list = [symptom.strip().lower() for symptom in symptoms.split(',')]
        disease = None
        matched_row = None

        # Custom logic for specific symptom combinations
        if set(['fever', 'headache', 'fatigue']).issubset(symptoms_list):
            disease = 'Influenza'
        elif 'headache' in symptoms_list and len(symptoms_list) == 1:
            disease = 'Migraine'
        elif set(['fever', 'cough', 'fatigue']).issubset(symptoms_list):
            disease = 'Common Cold'
        elif set(['fever', 'sore throat', 'fatigue']).issubset(symptoms_list):
            disease = 'Strep Throat'
        elif set(['fever', 'nausea', 'fatigue']).issubset(symptoms_list):
            disease = 'Food Poisoning'
        else:
            for index, row in dataset1.iterrows():
                if any(symptom in row['Symptoms'].lower() for symptom in symptoms_list):
                    disease = row['Preliminary_Disease_Diagnosis']
                    matched_row = row
                    break

        if matched_row is not None or disease:
            if matched_row is None:
                for index, row in dataset1.iterrows():
                    if row['Preliminary_Disease_Diagnosis'].lower() == disease.lower():
                        matched_row = row
                        break

            recommended_medicine = matched_row['Recommended_Medicine']
            recommended_dosage = None

            for index, row in dataset2.iterrows():
                if row['Preliminary_Disease_Diagnosis'].lower() == disease.lower():
                    if age <= 12:
                        recommended_dosage = row['Child']
                    elif age > 12 and age <= 65:
                        recommended_dosage = row['Adult']
                    else:
                        recommended_dosage = row['Senior']
                    break

            if recommended_dosage is not None:
                return {
                    'Diagnosis': disease,
                    'Medicine': recommended_medicine,
                    'Dosage': recommended_dosage,
                    'Advice': matched_row['Recommended_Advice']
                }
        return None

    def search_youtube(query):
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode (no GUI)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://www.youtube.com")
            
            # Accept cookies if present
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Accept all']"))
                )
                cookie_button.click()
            except:
                pass
            
            # Modified search query
            search_query = f"how to treat a {query}"
            
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "search_query"))
            )
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            
            first_video = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a#video-title"))
            )
            video_url = first_video.get_attribute('href')
            
            driver.quit()
            return video_url
        except Exception as e:
            if 'driver' in locals():
                driver.quit()
            return None

    def get_doctors_advice(diagnosis):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://www.google.com")
            
            # Accept cookies if present
            try:
                cookie_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept all')]"))
                )
                cookie_button.click()
            except:
                pass
            
            # Modified search query to focus on advice keywords
            search_query = f"{diagnosis} treatment tips home remedies self care advice"
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.send_keys(search_query)
            search_box.send_keys(Keys.RETURN)
            
            # Wait for and extract the AI Overview content
            ai_overview = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='VwiC3b']"))  # This targets Gemini's overview box
            )
            
            advice_text = []
            if ai_overview:
                text = ai_overview.text
                # Extract key points from the AI overview
                advice_text.append(text)
            
            driver.quit()
            
            # Format the output
            if advice_text:
                formatted_advice = "### AI Overview:\n" + "\n".join(advice_text)
                return formatted_advice
            return None
            
        except Exception as e:
            if 'driver' in locals():
                driver.quit()
            return None


    def parse_hospital_details(raw_details):
        try:
            # Assuming raw_details is a string representation of a dictionary
            print("Raw details to parse:", raw_details)  # Debugging line
            result = ast.literal_eval(raw_details)  # Ensure this is a valid Python literal
            
            # Verify the required keys are present
            required_keys = {'address', 'phone', 'distance', 'directions'}
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in response")
            
            return result
        except Exception as e:
            st.error(f"Error parsing details: {e}")
            return {
                'address': "Address not available",
                'phone': "Phone not available",
                'distance': "Distance not available",
                'directions': "Directions not available"
            }

    
 # Importing the correct geolocation method

    def search_and_format_hospitals():
        # Get the uses's location (latitude and longitude) using streamlit_geolocation
        location = streamlit_geolocation() 
        time.sleep(10)  # This function should return latitude and longitude
        if location:
            latitude = location['latitude']
            longitude = location['longitude']
                
                # Get the maximum decimal precision
           

            st.write(f"Latitude: {latitude}, Longitude: {longitude}") 

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.get("https://www.google.com")

                st.write("Searching for hospitals...")

                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                # Modify the search query to include lat and lon
                search_query = f"hospitals nearby this location less than 4km: {latitude},{longitude}"
                search_box.send_keys(search_query)
                search_box.submit()

                st.write("Waiting for results...")

                places = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.VkpGBb"))
                )

                st.write(f"Found {len(places)} places")

                raw_hospitals = []
                for place in places[:5]:
                    try:
                        name = place.find_element(By.CSS_SELECTOR, "div.dbg0pd").text
                        details = place.find_element(By.CSS_SELECTOR, "div.rllt__details").text
                        raw_hospitals.append({"name": name, "details": details})
                    except Exception as e:
                        continue

                driver.quit()

                if not raw_hospitals:
                    st.error("No hospital data found")
                    return None

                # Format data and create prompt for Gemini
                hospitals_data = "Here are the hospitals found:\n\n"
                for idx, hospital in enumerate(raw_hospitals, 1):
                    hospitals_data += f"Hospital {idx}:\nName: {hospital['name']}\nDetails: {hospital['details']}\n\n"

                prompt = f"""
                Parse these hospital details into a structured format. For each hospital, extract:
                1. Name
                2. Distance (the value ending with 'm' or 'km')
                3. Address (the part with road/street name)
                4. Phone number (the 10-digit or landline number)

                Format as a list of dictionaries like this:
                [
                    {{
                        "name": "Hospital Name",
                        "distance": "X.X m",
                        "address": "Street address",
                        "phone": "Phone number",
                        "directions": "https://www.google.com/maps/search/?api=1&query=Hospital+Name+Street+Address"
                    }} 
                ]

                Here are the details to parse:
                {hospitals_data}

                Return ONLY the Python list, no other text.
                """

                response = model.generate_content(prompt)
                hospitals = ast.literal_eval(response.text)
                return hospitals

            except Exception as e:
                st.warning("Please click the 'Get My Location' button to allow geolocation access.")
                return None


    def display_hospital_details(hospital, user_lat, user_lon):
        st.subheader(f"🏥 {hospital['name']}")
        st.write(f"📍 **Address:** {hospital['address']}")
        st.write(f"📞 **Phone:** {hospital['phone']}")
        st.write(f"🚗 **Distance:** {hospital['distance']}")
        
        # Create map
        m = folium.Map(location=[user_lat, user_lon], zoom_start=13)
        
        # Add user location marker
        folium.Marker(
            [user_lat, user_lon],
            popup="Your Location",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        # Add hospital location marker
        hospital_lat, hospital_lon = get_coordinates_from_address(hospital['address'])
        if hospital_lat and hospital_lon:
            folium.Marker(
                [hospital_lat, hospital_lon],
                popup=hospital['name'],
                icon=folium.Icon(color='green', icon='plus')
            ).add_to(m)
        
        # Display map
        folium_static(m)
        
        # Add directions button
        directions_url = f"https://www.google.com/maps/dir/{user_lat},{user_lon}/{hospital_lat},{hospital_lon}"
        st.markdown(f"[🚗 Get Directions]({directions_url})")

    def create_emergency_sidebar():
        with st.sidebar:
            st.title("🚨 Emergency Contacts")
            
            # Read emergency contacts from CSV with latin-1 encoding
            emergency_df = pd.read_csv('Emergency_Services_Worldwide.csv', encoding='latin-1')
            
            # Get unique countries for selector
            countries = emergency_df['Country'].unique()
            
            # Country selector
            country = st.selectbox(
                "Select your country",
                countries
            )
            
            st.markdown("---")
            
            # Display contacts for selected country
            if country:
                # Filter contacts for selected country
                country_contacts = emergency_df[emergency_df['Country'] == country]
                
                # Display country name
                st.markdown(f"### {country}")
                
                # Display all emergency services for the country
                for _, row in country_contacts.iterrows():
                    st.markdown(f"- **{row['Service']}**: {row['Number']}")
            
            # Disclaimer
            st.markdown("---")
            st.caption("""
                ⚠️ **Disclaimer**: In case of emergency, immediately dial your 
                country's emergency services number.
            """)
            
            st.markdown("---")
            
            # Initialize session states if they don't exist
            if 'show_hospitals' not in st.session_state:
                st.session_state.show_hospitals = False
            if 'show_medical_shops' not in st.session_state:
                st.session_state.show_medical_shops = False
            
            # Modified buttons with callbacks
            if st.button("🏥 Search For Hospitals Nearby", type="primary"):
                st.session_state.show_hospitals = True
                st.session_state.show_medical_shops = False
                st.rerun()
            
            if st.button("💊 Search For Medical Shops Nearby"):
                st.session_state.show_medical_shops = True
                st.session_state.show_hospitals = False
                st.rerun()

    def search_and_format_medical_shops():
        location = streamlit_geolocation()
        time.sleep(10)  # This function should return latitude and longitude
        if location:
            latitude = location['latitude']
            longitude = location['longitude']
                
                # Get the maximum decimal precision
           

            st.write(f"Latitude: {latitude}, Longitude: {longitude}") 

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("https://www.google.com")
            
            st.write("Searching for medical shops...")
            
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_query = f"medical shops nearby this location less than 4km: {latitude},{longitude}"
            search_box.send_keys(search_query)
            search_box.submit()
            
            st.write("Waiting for results...")
            
            places = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.VkpGBb"))
            )
            
            st.write(f"Found {len(places)} places")
            
            raw_shops = []
            for place in places[:5]:
                try:
                    name = place.find_element(By.CSS_SELECTOR, "div.dbg0pd").text
                    details = place.find_element(By.CSS_SELECTOR, "div.rllt__details").text
                    raw_shops.append({"name": name, "details": details})
                except Exception as e:
                    continue
            
            driver.quit()

            if not raw_shops:
                st.error("No medical shops found")
                return None

            # Format data and create prompt for Gemini
            shops_data = "Here are the medical shops found:\n\n"
            for idx, shop in enumerate(raw_shops, 1):
                shops_data += f"Shop {idx}:\nName: {shop['name']}\nDetails: {shop['details']}\n\n"

            prompt = f"""
            Parse these medical shop details into a structured format. For each shop, extract:
            1. Name
            2. Distance (the value ending with 'm' or 'km')
            3. Address (the part with road/street name)
            4. Phone number (the 10-digit or landline number)

            Format as a list of dictionaries like this:
            [
                {{
                    "name": "Shop Name",
                    "distance": "X.X m",
                    "address": "Street address",
                    "phone": "Phone number",
                    "directions": "https://www.google.com/maps/search/?api=1&query=Shop+Name+Street+Address"
                }},
            ]

            Here are the details to parse:
            {shops_data}

            Return ONLY the Python list, no other text.
            """

            response = model.generate_content(prompt)
            shops = ast.literal_eval(response.text)
            return shops

        except Exception as e:
            st.warning("Please click the 'Get My Location' button to allow geolocation access.")
            return None
            

    # Initialize session states
    if 'show_hospitals' not in st.session_state:
        st.session_state.show_hospitals = False
    if 'selected_hospital' not in st.session_state:
        st.session_state.selected_hospital = None
    if 'show_medical_shops' not in st.session_state:
        st.session_state.show_medical_shops = False

    # In your main content area
    if st.session_state.show_hospitals:
        hospitals = search_and_format_hospitals()
        if hospitals:
            st.success("Found nearby hospitals!")
            for hospital in hospitals:
                with st.expander(f"🏥 {hospital['name']}"):
                    st.write(f"📍 **Address:** {hospital['address']}")
                    st.write(f"🚗 **Distance:** {hospital['distance']}")
                    st.write(f"📞 **Phone:** {hospital['phone']}")
                    st.markdown(f"[🗺️ Get Directions]({hospital['directions']})")
        else:
            st.error("No hospitals found nearby")

    if 'show_medical_shops' not in st.session_state:
        st.session_state.show_medical_shops = False

    if st.session_state.show_medical_shops:
        shops = search_and_format_medical_shops()
        if shops:
            st.success("Found nearby medical shops!")
            for shop in shops:
                with st.expander(f"💊 {shop['name']}"):
                    st.write(f"📍 **Address:** {shop['address']}")
                    st.write(f"🚗 **Distance:** {shop['distance']}")
                    st.write(f"📞 **Phone:** {shop['phone']}")
                    st.markdown(f"[🗺️ Get Directions]({shop['directions']})")
        else:
            st.error("No medical shops found nearby")

    if user_choice == "First Aid":
        # Clear any hospital or medical shop results
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False
        
        user_emergency = st.text_input("Please describe your emergency:")
        if st.button("Get Advice"):
            if user_emergency:
                advice_found = provide_emergency_advice(user_emergency, first_aid_dataset)
                if advice_found:
                    st.success("Here is the advice for your emergency:")
                    st.write(advice_found['Emergency_Advice'])
                    if pd.notna(advice_found['Emergency_Image']):
                        st.image(advice_found['Emergency_Image'])
                    if pd.notna(advice_found['Emergency_Video']):
                        video_url = f"https://youtu.be/{advice_found['Emergency_Video']}"
                        st.video(video_url)
                else:
                    st.warning("No matching advice found in our database. Searching YouTube for relevant first aid videos...")
                    video_url = search_youtube(user_emergency)
                    if video_url:
                        st.info("Here's a relevant first aid video from YouTube:")
                        st.video(video_url)
                    else:
                        st.error("Sorry, couldn't find any relevant videos.")
            else:
                st.warning("Please enter an emergency description.")

    elif user_choice == "Diagnosis":
        # Clear any hospital or medical shop results
        st.session_state.show_hospitals = False
        st.session_state.show_medical_shops = False
        
        # Arrange form fields in a cleaner layout
        col_left, col_right = st.columns(2)
        with col_left:
            patient_name = st.text_input("What is your name?")
        with col_right:
            patient_age = st.number_input("What is your age?", min_value=0)
        symptoms = st.text_area("What symptoms are you experiencing (comma-separated)?", height=100)
        
        if st.button("Get Diagnosis"):
            if patient_name and patient_age and symptoms:
                recommended_info = recommend_drug(symptoms, patient_age, dataset1, dataset2)
                if recommended_info:
                    st.success(f"Preliminary diagnosis based on symptoms: {recommended_info['Diagnosis']}")
                    st.write(f"Recommended medicine: {recommended_info['Medicine']}")
                    st.write(f"Recommended dosage according to age: {recommended_info['Dosage']}")
                    st.write(f"Recommended advice related to symptoms: {recommended_info['Advice']}")
                    
                    prompt = f"""
                    Based on this diagnosis: {recommended_info['Diagnosis']}
                    And these symptoms: {symptoms}
                    
                    Provide exactly 5 important points of advice. Format as a simple list with one emoji per point.
                    Return ONLY the list items without any other text.
                    Example format:
                    - 🏥 Visit your doctor regularly
                    - 💊 Take prescribed medicines as directed
                    - 🏠 Get adequate rest
                    - 🥗 Stay hydrated
                    - ⚠️ Seek emergency care if needed
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        st.markdown("---")
                        st.subheader("📋 Quick Health Tips")
                        
                        # Split the response into lines and create bullet points
                        advice_points = [line.strip() for line in response.text.split('\n') if line.strip()]
                        for point in advice_points:
                            # Remove any existing bullet points or dashes
                            clean_point = point.lstrip('- •').strip()
                            st.write(f"• {clean_point}")
                            
                    except Exception as e:
                        st.error("Could not generate additional advice.")
                    
                else:
                    st.warning("Sorry, no match found for the provided symptoms.")
            else:
                st.warning("Please fill in all fields.")

def get_coordinates_from_address(address):
    try:
        geolocator = Nominatim(user_agent="medibot")
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        st.error(f"Error getting coordinates: {e}")
        return None, None

if __name__ == "__main__":
    create_emergency_sidebar()
