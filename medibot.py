import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests
import google.generativeai as genai



# Configure Gemini (add this near your imports)
genai.configure(api_key='AIzaSyDDjCutEZobboVnlAqOjSLXQANWihZFBhI')
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
    # Add this function near the top of your file, after your imports but before any other functions
    

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

    def get_user_location():
        try:
            response = requests.get('https://ipapi.co/json/')
            data = response.json()
            return data['latitude'], data['longitude'], data['city']
        except Exception as e:
            st.error(f"Error getting location: {e}")
            return None, None, None

    def parse_hospital_details(raw_details, hospital_name):
        prompt = f"""
        Parse these hospital details and create a properly formatted response:
        Hospital Name: {hospital_name}
        Raw Details: {raw_details}
        
        Return only a dictionary in this exact format:
        {{
            'address': 'full address here',
            'phone': 'phone number here',
            'distance': 'distance here',
            'directions': 'https://www.google.com/maps/dir/?api=1&destination=hospital+address+here'
        }}
        """
        
        try:
            response = model.generate_content(prompt)
            # Clean and format the response
            response_text = response.text.strip()
            # Remove any markdown formatting if present
            if response_text.startswith('```') and response_text.endswith('```'):
                response_text = response_text[3:-3]
            if response_text.startswith('python'):
                response_text = response_text[6:]
            
            # Safely evaluate the dictionary string
            import ast
            result = ast.literal_eval(response_text)
            
            # Verify the required keys are present
            required_keys = {'address', 'phone', 'distance', 'directions'}
            if not all(key in result for key in required_keys):
                raise ValueError("Missing required keys in response")
                
            return result
        except Exception as e:
            st.error(f"Error parsing details: {e}")
            # Return default values if parsing fails
            return {
                'address': raw_details,
                'phone': "Phone not available",
                'distance': "Distance not available",
                'directions': f"https://www.google.com/maps/search/?api=1&query={hospital_name.replace(' ', '+')}"
            }

    # Cache to store user location
    user_location_cache = {}
    cache_duration = 3600  # Cache duration in seconds (1 hour)

    def get_user_ip():
        try:
            ip_response = requests.get('https://api.ipify.org?format=json')
            if ip_response.status_code == 200:
                ip = ip_response.json()['ip']
                st.write(f"User IP: {ip}")  # Debug: Show the user's IP
                return ip
            else:
                st.error("Could not retrieve IP address.")
                return None
        except Exception as e:
            st.error(f"Error getting IP address: {str(e)}")
            return None

    def get_location_from_ip(ip):
        try:
            location_response = requests.get(f'https://ipinfo.io/{ip}/json/')
            if location_response.status_code == 200:
                location_data = location_response.json()
                # Extract latitude and longitude from the 'loc' field
                loc = location_data.get('loc')
                if loc:
                    lat, lng = map(float, loc.split(','))
                    # Add latitude and longitude to the location data
                    location_data['latitude'] = lat
                    location_data['longitude'] = lng
                return location_data
            else:
                st.error(f"Could not retrieve location from IP. Status code: {location_response.status_code}")
                return None
        except Exception as e:
            st.error(f"Error getting location: {str(e)}")
            return None

    def search_and_format_hospitals():
        user_ip = get_user_ip()  # Get the user's IP address
        if not user_ip:
            st.error("Could not determine your IP address.")
            return None

        location_data = get_location_from_ip(user_ip)  # Get location data from IP
        if not location_data:
            st.error("Could not retrieve location from IP.")
            return None

        # Extract latitude and longitude
        lat = location_data.get('latitude')
        lng = location_data.get('longitude')

        if lat is not None and lng is not None:
            search_query = f"hospitals near me : {lat}°N {lng}°E"
            
            # Use Selenium to search Google with the search_query
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.get("https://www.google.com")

                # Search for hospitals using the constructed query
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                search_box.send_keys(search_query)
                search_box.send_keys(Keys.RETURN)

                # Wait for results and extract hospital details
                places = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.VkpGBb"))
                )

                # Process and return hospital details
                hospitals = []
                for place in places[:5]:  # Limit to top 5 results
                    name = place.find_element(By.CSS_SELECTOR, "div.dbg0pd").text
                    details = place.find_element(By.CSS_SELECTOR, "div.rllt__details").text
                    
                    # Initialize raw details
                    raw_details = {
                        "name": name,
                        "details": details  # Keep raw details for formatting
                    }

                    hospitals.append(raw_details)

                # Pass raw details to Gemini for formatting
                formatted_hospitals = []
                for hospital in hospitals:
                    # Construct the directions link
                    directions = f"https://www.google.com/maps/search/?api=1&query={hospital['name'].replace(' ', '+')}"

                    prompt = f"""
                    Clean and format the following hospital details:
                    Name: {hospital['name']}
                    Details: {hospital['details']}
                    
                    Return the information in the following format:
                    Address: [address]
                    Distance: [distance]
                    Phone: [phone]
                    Directions: {directions}
                    """

                    # Call Gemini to process the details
                    try:
                        gemini_response = model.generate_content(prompt)
                        if not gemini_response or not hasattr(gemini_response, 'text'):
                            raise ValueError("No valid response from Gemini.")
                        
                        formatted_details = gemini_response.text.strip().split('\n')
                        
                        # Parse the formatted details
                        formatted_hospital = {
                            "name": hospital['name'],
                            "address": "Not provided",
                            "distance": "Not provided",
                            "phone": "Not provided",
                            "directions": directions  # Use the constructed directions link
                        }
                        
                        for line in formatted_details:
                            if line.startswith("Address:"):
                                formatted_hospital["address"] = line.split("Address:")[1].strip()
                            elif line.startswith("Distance:"):
                                formatted_hospital["distance"] = line.split("Distance:")[1].strip()
                            elif line.startswith("Phone:"):
                                formatted_hospital["phone"] = line.split("Phone:")[1].strip()

                        formatted_hospitals.append(formatted_hospital)
                    except Exception as e:
                        st.error(f"Error retrieving formatted details from Gemini: {str(e)}")

                driver.quit()

                return formatted_hospitals

            except Exception as e:
                if 'driver' in locals():
                    driver.quit()
                st.error(f"Error searching for hospitals: {str(e)}")
                return None
        else:
            st.error("Could not determine location from IP.")
            return None

    def display_hospitals(formatted_hospitals):
        if not formatted_hospitals:
            st.write("No hospitals found.")
            return
        
        for hospital in formatted_hospitals:
            with st.expander(f"🏥 {hospital['name']}"):
                st.markdown(f"📍 **Address:** {hospital['address']}")
                st.markdown(f"📏 **Distance:** {hospital['distance']}")
                st.markdown(f"📞 **Phone:** {hospital['phone']}")
                st.markdown(f"🗺️ **Directions:** [link]({hospital['directions']})")
                

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
        user_ip = get_user_ip()  # Get the user's IP address
        if not user_ip:
            return None  # Suppress error message

        location_data = get_location_from_ip(user_ip)  # Get location data from IP
        if not location_data:
            return None  # Suppress error message

        # Extract latitude and longitude
        lat = location_data.get('latitude')
        lng = location_data.get('longitude')

        if lat is not None and lng is not None:
            search_query = f"medical shops near me : {lat}°N {lng}°E"
            
            # Use Selenium to search Google with the search_query
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')

            try:
                driver = webdriver.Chrome(options=chrome_options)
                driver.get("https://www.google.com")

                # Search for medical shops using the constructed query
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "q"))
                )
                search_box.send_keys(search_query)
                search_box.send_keys(Keys.RETURN)

                # Wait for results and extract medical shop details
                places = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.VkpGBb"))
                )

                # Process and return medical shop details
                shops = []
                for place in places[:5]:  # Limit to top 5 results
                    name = place.find_element(By.CSS_SELECTOR, "div.dbg0pd").text
                    details = place.find_element(By.CSS_SELECTOR, "div.rllt__details").text
                    
                    # Initialize raw details
                    raw_details = {
                        "name": name,
                        "details": details  # Keep raw details for formatting
                    }

                    # Print the raw details for debugging
                 

                    shops.append(raw_details)

                driver.quit()

                # Pass raw details to Gemini for formatting
                formatted_shops = []
                for shop in shops:
                    # Construct the directions link
                    directions = f"https://www.google.com/maps/search/?api=1&query={shop['name'].replace(' ', '+')}"

                    prompt = f"""
                    Clean and format the following medical shop details:
                    Name: {shop['name']}
                    Details: {shop['details']}
                    
                    Return the information in the following format:
                    Address: [address]
                    Distance: [distance]
                    Phone: [phone]
                    Directions: [link]
                    """

                    # Log the prompt for debugging
                   

                    # Call Gemini to process the details
                    formatted_details = []  # Initialize formatted_details
                    for attempt in range(3):  # Retry mechanism
                        try:
                            gemini_response = model.generate_content(prompt)
                            if not gemini_response or not hasattr(gemini_response, 'text'):
                                raise ValueError("No valid response from Gemini.")
                            
                            response_text = getattr(gemini_response, 'text', None)
                            if not response_text:
                                raise ValueError("Response text is empty.")
                            
                            formatted_details = response_text.strip().split('\n')
                            break  # Exit retry loop if successful
                        except Exception:
                            continue  # Skip to the next shop if an error occurs

                    # Check if formatted_details was successfully populated
                    if formatted_details:
                        # Parse the formatted details if successful
                        formatted_shop = {
                            "name": shop['name'],
                            "address": "Not provided",
                            "distance": "Not provided",
                            "phone": "Not provided",
                            "directions": directions  # Use the constructed directions link
                        }
                        
                        for line in formatted_details:
                            if line.startswith("Address:"):
                                formatted_shop["address"] = line.split("Address:")[1].strip()
                            elif line.startswith("Distance:"):
                                formatted_shop["distance"] = line.split("Distance:")[1].strip()
                            elif line.startswith("Phone:"):
                                formatted_shop["phone"] = line.split("Phone:")[1].strip()

                        formatted_shops.append(formatted_shop)

                return formatted_shops

            except Exception:
                if 'driver' in locals():
                    driver.quit()
                return None  # Suppress error message
        else:
            return None  # Suppress error message

    def display_medical_shops(formatted_shops):
        if not formatted_shops:
            st.write("No medical shops found.")
            return
        
        for shop in formatted_shops:
            with st.expander(f"💊 {shop['name']}"):
                st.markdown(f"📍 **Address:** {shop['address']}")
                st.markdown(f"📏 **Distance:** {shop['distance']}")
                st.markdown(f"📞 **Phone:** {shop['phone']}")
                st.markdown(f"🗺️ **Directions:** [Link]({shop['directions']})")

    # Initialize session states
    if 'show_hospitals' not in st.session_state:
        st.session_state.show_hospitals = False
    if 'selected_hospital' not in st.session_state:
        st.session_state.selected_hospital = None
    if 'show_medical_shops' not in st.session_state:
        st.session_state.show_medical_shops = False

    # In your main content area
    if st.session_state.show_hospitals:
        formatted_hospitals = search_and_format_hospitals()
        if formatted_hospitals:
            display_hospitals(formatted_hospitals)
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
                    - 🚑 Seek emergency care if needed
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


# Add this new function near your other helper functions


# Modify your existing get_nearby_places function


if __name__ == "__main__":
    create_emergency_sidebar()
