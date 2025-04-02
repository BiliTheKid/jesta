# app.py
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
from services.whatsapp import send_message

API_URL = "http://localhost:8000"

def main():
    st.title("מערכת ניהול - אנשי מקצוע")

    page = st.sidebar.selectbox(
        "Choose operation",
        ["Send Message", "Professionals", "Service Calls", "Display Message", "Csv Uploader"]
    )

    if page == "Send Message":
        message_sender_page()
    elif page == "Professionals":
        professional_page()
    elif page == "Display Message":
        dispaly_messages()
    elif page == "Csv Uploader":
        csv_upload_page()
    else:
        service_call_page()

def message_sender_page():
    st.header("Message Sender")
    
    st.write("""
        Send WhatsApp messages to professionals or clients.
        Enter the recipient's phone number and the message you want to send.
    """)

    phone_number = st.text_input("Recipient Phone Number", placeholder="Enter phone number here")
    message_body = st.text_area("Message Body", placeholder="Write your message here")

    message_template = st.selectbox(
        "Use Message Template",
        ["Custom Message", "Job Offer", "Confirmation Request", "Job Complete"]
    )

    if message_template != "Custom Message":
        if message_template == "Job Offer":
            message_body = st.text_area(
                "Edit Template",
                """We have a new job that matches your skills:
                Location: [Location]
                Date: [Date]
                Description: [Description]
                
                Reply ACCEPT to take this job."""
            )
        elif message_template == "Confirmation Request":
            message_body = st.text_area(
                "Edit Template",
                """Please confirm your availability for:
                Job: [Job Title]
                Date: [Date]
                
                Reply CONFIRM to accept."""
            )
        elif message_template == "Job Complete":
            message_body = st.text_area(
                "Edit Template",
                """Job completed:
                [Job Title]
                
                Thank you for your service!"""
            )

    if st.button("Send Message"):
        if phone_number and message_body:
            if send_message(phone_number, message_body):
                st.success("Message sent successfully!")
                try:
                    requests.post(
                        f"{API_URL}/messages/log",
                        json={
                            "phone_number": phone_number,
                            "message": message_body,
                            "sent_at": datetime.now().isoformat()
                        }
                    )
                except Exception as e:
                    st.warning(f"Message sent but logging failed: {e}")
            else:
                st.error("Failed to send message.")
        else:
            st.error("Please provide both recipient's phone number and message.")

def professional_page():
    st.header("ניהול בעלי מלאכה")

    # קבלת רשימת מקצועות קיימת מה-API
    professions_response = requests.get(f"{API_URL}/professions/")
    if professions_response.status_code == 200:
        professions = [p['name'] for p in professions_response.json()]
    else:
        professions = ["חשמלאי", "אינסטלטור", "נגר", "Electrician"]

    # הוספת מקצוע חדש
    with st.expander("הוספת מקצוע חדש"):
        new_profession = st.text_input("שם מקצוע חדש")
        if st.button("הוסף מקצוע"):
            if new_profession:
                response = requests.post(f"{API_URL}/professions/", json={"name": new_profession})
                if response.status_code == 200:
                    st.success("מקצוע נוסף בהצלחה!")
                    professions.append(new_profession)
                else:
                    st.error("שגיאה בהוספת מקצוע")

    # יצירת בעל מלאכה חדש
    with st.expander("הוספת בעל מלאכה חדש"):
        with st.form("new_professional"):
            name = st.text_input("שם")
            phone = st.text_input("טלפון")
            profession = st.selectbox("מקצוע", professions)
            location = st.text_input("מיקום")  # ✅ Added location input
            available = st.checkbox("זמין", value=True)

            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("הוסף בעל מלאכה")
            with col2:
                send_welcome = st.checkbox("שלח הודעת ברוכים הבאים")

            if submit and name and phone and profession:
                response = requests.post(
                    f"{API_URL}/professionals/",
                    json={
                        "name": name,
                        "phone": phone,
                        "profession": profession,
                        "available": available,
                        "location": location  # ✅ Pass location to backend
                    }
                )
                if response.status_code == 200:
                    st.success("בעל מלאכה נוסף בהצלחה!")

                    if send_welcome:
                        welcome_msg = f"""ברוכים הבאים {name}!\nנרשמת כמ {profession} במערכת השירות שלנו.\n\nהשב עם:\nACCEPT - כדי לקבל עבודה\nCONFIRM - כדי לאשר את זמינותך\nCOMPLETE - כאשר העבודה הסתיימה\n\nתודה שהצטרפת לפלטפורמה שלנו!"""

                        if send_message(phone, welcome_msg):
                            st.success("הודעת ברוכים הבאים נשלחה!")
                        else:
                            st.warning("בעל מלאכה נוסף, אך הודעת ברוכים הבאים לא נשלחה.")
                else:
                    st.error("שגיאה בהוספת בעל מלאכה")

        # רשימה וניהול בעלי מלאכה קיימים
    st.subheader("בעלי מלאכה קיימים")

    col1, col2 = st.columns(2)
    with col1:
        profession_filter = st.selectbox(
            "סנן לפי מקצוע",
            ["הכל"] + professions
        )
    with col2:
        availability_filter = st.selectbox(
            "סנן לפי זמינות",
            ["הכל", "זמין", "לא זמין"]
        )

    if st.button("רענן רשימה"):
        params = {}
        if profession_filter != "הכל":
            params["profession"] = profession_filter
        if availability_filter != "הכל":
            params["available"] = availability_filter == "זמין"

        try:
            st.session_state.professionals = requests.get(
                f"{API_URL}/professionals/",
                params=params
            ).json()
        except requests.exceptions.RequestException as e:
            st.error(f"שגיאת תקשורת עם ה-API: {e}")
            return

    if 'professionals' not in st.session_state:
        try:
            st.session_state.professionals = requests.get(f"{API_URL}/professionals/").json()
        except requests.exceptions.RequestException as e:
            st.error(f"שגיאת תקשורת עם ה-API: {e}")
            return

    if st.session_state.professionals:
        df = pd.DataFrame(st.session_state.professionals)

        for _, row in df.iterrows():
            with st.expander(f"{row['name']} - {row['profession']}"):
                with st.form(f"edit_professional_{row['id']}"):
                    col1, col2 = st.columns([3, 1])

                    with col1:
                        edit_name = st.text_input("שם", row['name'])
                        edit_phone = st.text_input("טלפון", row['phone'])
                        edit_profession = st.selectbox(
                            "מקצוע",
                            professions,
                            index=professions.index(row['profession'])
                        )
                        edit_available = st.checkbox("זמין", row['available'])

                    with col2:
                        st.write("פעולות:")
                        update_button = st.form_submit_button("עדכן")
                        delete_button = st.form_submit_button("מחק")
                        send_msg_button = st.form_submit_button("שלח הודעה")

                    if update_button:
                        response = requests.put(
                            f"{API_URL}/professionals/{row['id']}",
                            json={
                                "name": edit_name,
                                "phone": edit_phone,
                                "profession": edit_profession,
                                "available": edit_available
                            }
                        )
                        if response.status_code == 200:
                            st.success("עודכן בהצלחה!")
                            st.session_state.professionals = requests.get(f"{API_URL}/professionals/").json()
                            st.experimental_rerun()
                        else:
                            st.error("שגיאה בעדכון בעל מלאכה")

                    if delete_button:
                        if st.checkbox("אשר מחיקה"):
                            response = requests.delete(f"{API_URL}/professionals/{row['id']}")
                            if response.status_code == 200:
                                st.success("נמחק בהצלחה!")
                                st.session_state.professionals = requests.get(f"{API_URL}/professionals/").json()
                                st.experimental_rerun()
                            else:
                                st.error("שגיאה במחיקת בעל מלאכה")

                    if send_msg_button:
                        message = st.text_area("הודעה", key=f"msg_{row['id']}")
                        if message and st.button("שלח", key=f"send_{row['id']}"):
                            if send_message(edit_phone, message):
                                st.success("הודעה נשלחה!")
                            else:
                                st.error("שליחת ההודעה נכשלה")


def csv_upload_page():
    API_URL = "http://localhost:8000/professionals/upload-csv/"
    st.header("העלאת CSV וייבוא בעלי מלאכה")

    uploaded_file = st.file_uploader("בחר קובץ CSV", type="csv")

    if uploaded_file is not None:
        st.write("קובץ CSV הועלה בהצלחה.")
        
        if st.button("ייבא נתונים"):
            files = {'file': uploaded_file}
            response = requests.post(API_URL, files=files)

            if response.status_code == 200:
                st.success("בעלי המלאכה יובאו בהצלחה.")
                st.write(response.json()) # הצגת תגובת ה-API
            else:
                st.error(f"שגיאה ביבוא: {response.status_code} - {response.text}")

# Fetch messages from API
def fetch_messages():
    API_URL_MESSAGE = "http://localhost:8000/messages/"  # Update with your actual FastAPI URL
    response = requests.get(API_URL_MESSAGE)
    if response.status_code == 200:
        return response.json()  # Expecting a list of messages
    else:
        st.error("Failed to fetch messages")
        return []

# Filter messages from the last 24 hours
# Display messages as cards
def display_messages_page(messages):
    if not messages:
        st.info("אין הודעות להצגה.")
        return

    for msg in messages:
        with st.container():
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #ddd; 
                    padding: 10px; 
                    border-radius: 10px; 
                    margin-bottom: 10px; 
                    background-color: #f9f9f9;">
                    <b>{msg['fromName']}</b> <span style="color: gray;">({msg['timestamp']})</span>
                    <p>{msg['body']}</p>
                    <p><b>Intent:</b> <span style="color:blue;">{msg['intent'] or 'לא זוהה כוונה'}</span></p>
                </div>
                """,
                unsafe_allow_html=True
            )

def dispaly_messages():
    st.title("📩 הודעות אחרונות - 24 שעות")
    messages = fetch_messages()
    display_messages_page(messages)


def service_call_page():
    st.header("Service Calls Management")
    
    # Create new service call
    with st.expander("Create New Service Call"):
        with st.form("new_service_call"):
            title = st.text_input("Title")
            description = st.text_area("Description")
            date = st.date_input("Date")
            time = st.time_input("Time")
            location = st.text_input("Location")
            profession = st.selectbox(
                "Required Profession",
                ["Electrician", "Plumber", "Carpenter"]
            )
            urgency = st.select_slider(
                "Urgency",
                options=["LOW", "NORMAL", "HIGH", "URGENT"]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("Create Service Call")
            with col2:
                notify_professionals = st.checkbox("Notify available professionals", value=True)
            
            if submit and title and description and location:
                datetime_str = f"{date} {time}"
                datetime_obj = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                
                response = requests.post(
                    f"{API_URL}/service-calls/",
                    json={
                        "title": title,
                        "description": description,
                        "date": datetime_obj.isoformat(),
                        "location": location,
                        "profession": profession,
                        "urgency": urgency
                    }
                )
                
                if response.status_code == 200:
                    st.success("Service call created successfully!")
                    
                    if notify_professionals:
                        professionals = requests.get(
                            f"{API_URL}/professionals/by-profession/{profession}"
                        ).json()
                        
                        notification_msg = f"""New Service Call:
                        Title: {title}
                        Location: {location}
                        Date: {date}
                        Urgency: {urgency}
                        
                        Reply ACCEPT to take this job."""
                        
                        sent_count = 0
                        for prof in professionals:
                            if send_message(prof['phone'], notification_msg):
                                sent_count += 1
                        
                        if sent_count > 0:
                            st.success(f"Notifications sent to {sent_count} professionals")
                        else:
                            st.warning("Service call created but notifications failed to send")
                else:
                    st.error("Error creating service call")

    st.subheader("Existing Service Calls")
    
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "OPEN", "ASSIGNED", "CONFIRMED", "COMPLETED"]
    )
    
    if st.button("Refresh Service Calls"):
        if status_filter == "All":
            st.session_state.service_calls = requests.get(f"{API_URL}/service-calls/").json()
        else:
            st.session_state.service_calls = requests.get(
                f"{API_URL}/service-calls/by-status/{status_filter}"
            ).json()
    
    if 'service_calls' not in st.session_state:
        st.session_state.service_calls = requests.get(f"{API_URL}/service-calls/").json()
    
    if st.session_state.service_calls:
        df = pd.DataFrame(st.session_state.service_calls)
        for _, row in df.iterrows():
            with st.expander(f"{row['title']} - {row['profession']} - {row['status']}"):
                with st.form(f"edit_service_call_{row['id']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        edit_title = st.text_input("Title", row['title'])
                        edit_description = st.text_area("Description", row['description'])
                        edit_location = st.text_input("Location", row['location'])
                        edit_status = st.selectbox(
                            "Status",
                            ["OPEN", "ASSIGNED", "CONFIRMED", "COMPLETED"],
                            index=["OPEN", "ASSIGNED", "CONFIRMED", "COMPLETED"].index(row['status'])
                        )
                    
                    with col2:
                        st.write("Actions:")
                        update_button = st.form_submit_button("Update")
                        delete_button = st.form_submit_button("Delete")
                        notify_button = st.form_submit_button("Send Notifications")
                    
                    if update_button:
                        response = requests.put(
                            f"{API_URL}/service-calls/{row['id']}",
                            json={
                                "title": edit_title,
                                "description": edit_description,
                                "location": edit_location,
                                "status": edit_status
                            }
                        )
                        if response.status_code == 200:
                            st.success("Updated successfully!")
                            st.session_state.service_calls = requests.get(f"{API_URL}/service-calls/").json()
                            st.experimental_rerun()
                        else:
                            st.error("Error updating service call")
                    
                    if delete_button:
                        if st.checkbox("Confirm deletion", key=f"confirm_sc_{row['id']}"):
                            response = requests.delete(f"{API_URL}/service-calls/{row['id']}")
                            if response.status_code == 200:
                                st.success("Deleted successfully!")
                                st.session_state.service_calls = requests.get(f"{API_URL}/service-calls/").json()
                                st.experimental_rerun()
                            else:
                                st.error("Error deleting service call")
                    
                    if notify_button:
                        # Get professionals of matching profession
                        professionals = requests.get(
                            f"{API_URL}/professionals/by-profession/{row['profession']}"
                        ).json()
                        
                        notification_msg = f"""Service Call:
                        Title: {row['title']}
                        Location: {row['location']}
                        Date: {row['date']}
                        Description: {row['description']}
                        Urgency: {row['urgency']}
                        
                        Reply ACCEPT to take this job."""
                        
                        sent_count = 0
                        for prof in professionals:
                            if send_message(prof['phone'], notification_msg):
                                sent_count += 1
                        
                        if sent_count > 0:
                            st.success(f"Notifications sent to {sent_count} professionals")
                        else:
                            st.warning("No notifications sent. No available professionals found.")

if __name__ == "__main__":
    main()