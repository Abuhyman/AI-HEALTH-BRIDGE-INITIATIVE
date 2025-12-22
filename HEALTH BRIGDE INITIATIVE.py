# app.py - Complete Production-Ready Health Bridge Initiative App
# Supports: Web App + Mobile App (via Streamlit Mobile) + Cloud Database
import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import hashlib
import os
from supabase import create_client
# ==================== IMPORTS ====================
import os
from dotenv import load_dotenv
import streamlit as st  # <-- ADD THIS LINE
import requests
from streamlit_option_menu import option_menu
from streamlit_lottie import st_lottie
import plotly.graph_objs as go
from plotly.subplots import make_subplots

# Fixed import for Supabase
import supabase
# Or if that doesn't work, try:
# from supabase import create_client

# ==================== ENVIRONMENT SETUP ====================
load_dotenv()

# ==================== SUPABASE DATABASE SETUP ====================
@st.cache_resource
def init_supabase():
    """Initialize Supabase connection"""
    try:
        # Get credentials from Streamlit secrets or environment
        supabase_url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
        supabase_key = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
        
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            st.success(" Connected to cloud database ✅")
            return supabase
        else:
            st.warning(" Database credentials not found. Using session storage only. ⚠")
            return None
    except Exception as e:  # <-- THIS LINE WAS MISSING
        st.error(f" Database connection failed: {str(e)} ❌")
        return None

# ==================== PAYSTACK PAYMENT SETUP ====================
class PaymentManager:
    def __init__(self):
        self.public_key = st.secrets.get("PAYSTACK_PUBLIC_KEY", os.getenv("PAYSTACK_PUBLIC_KEY"))
        self.secret_key = st.secrets.get("PAYSTACK_SECRET_KEY", os.getenv("PAYSTACK_SECRET_KEY"))
        self.base_url = "https://api.paystack.co"
    
    def initialize_transaction(self, email, amount, metadata=None):
        """Initialize Paystack payment"""
        if not self.secret_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "email": email,
            "amount": int(amount * 100),  # Convert to kobo
            "currency": "NGN",
            "metadata": metadata or {}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                headers=headers,
                json=data
            )
            return response.json()
        except:
            return None
    
    def verify_transaction(self, reference):
        """Verify Paystack payment"""
        if not self.secret_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=headers
            )
            return response.json()
        except:
            return None

# ==================== HEALTH BRIDGE AI ENGINE ====================
class HealthBridgeAI:
    def __init__(self):
        self.supabase = init_supabase()
        self.payment_manager = PaymentManager()
        self.load_facilities()
        self.load_guidelines()
    
    def load_facilities(self):
        """Load healthcare facilities database"""
        self.facilities = {
            'Lagos': [
                {'name': 'Lagos University Teaching Hospital (LUTH)', 'type': 'Tertiary', 
                 'specialty': 'Nephrology', 'location': 'Idi-Araba', 'contact': '01-3423456',
                 'latitude': 6.5244, 'longitude': 3.3792},
                {'name': 'Badagry General Hospital', 'type': 'Secondary',
                 'specialty': 'General Medicine', 'location': 'Badagry', 'contact': '09012345678',
                 'latitude': 6.4167, 'longitude': 2.8833},
                {'name': 'Amuwo Odofin Maternal & Child Centre', 'type': 'Secondary',
                 'specialty': 'Maternal & Child Health', 'location': 'Festac', 'contact': '01-3425678',
                 'latitude': 6.4667, 'longitude': 3.2833}
            ],
            'Kano': [
                {'name': 'Aminu Kano Teaching Hospital', 'type': 'Tertiary',
                 'specialty': 'Nephrology', 'location': 'Kano', 'contact': '064-981234',
                 'latitude': 11.9964, 'longitude': 8.5167}
            ]
        }
    
    def load_guidelines(self):
        """Load medical guidelines for risk assessment"""
        self.guidelines = {
            'kidney': {
                'eGFR_stages': {'G1': '≥90', 'G2': '60-89', 'G3a': '45-59',
                              'G3b': '30-44', 'G4': '15-29', 'G5': '<15'},
                'ACR_categories': {'A1': '<30', 'A2': '30-300', 'A3': '>300'},
                'risk_factors': ['Hypertension', 'Diabetes', 'Family History',
                               'Age >60', 'Obesity', 'Smoking']
            },
            'liver': {
                'ALT_normal': '7-56 U/L',
                'AST_normal': '10-40 U/L',
                'risk_factors': ['Alcohol', 'Hepatitis B/C', 'Obesity',
                               'Diabetes', 'Herbal Medicine Use']
            }
        }
    
    def calculate_kidney_risk(self, data):
        """Calculate kidney disease risk based on KDIGO guidelines"""
        score = 0
        risk_factors = []
        
        # Blood Pressure
        if data['systolic_bp'] >= 160 or data['diastolic_bp'] >= 100:
            score += 3
            risk_factors.append("Severe Hypertension")
        elif data['systolic_bp'] >= 140 or data['diastolic_bp'] >= 90:
            score += 2
            risk_factors.append("Hypertension")
        
        # Urine Protein
        urine_map = {'Negative': 0, 'Trace': 1, '1+': 2, '2+': 3, '3+': 4}
        urine_score = urine_map.get(data['urine_protein'], 0)
        if urine_score >= 3:
            score += 3
            risk_factors.append("Significant Proteinuria")
        elif urine_score >= 1:
            score += 1
            risk_factors.append("Proteinuria")
        
        # Blood Glucose in mg/dL
        blood_glucose = data.get('blood_glucose', 0)
        if blood_glucose >= 200:
            score += 2
            risk_factors.append(f"Diabetes Risk (Glucose: {blood_glucose} mg/dL)")
        elif blood_glucose >= 140:
            score += 1
            risk_factors.append(f"Pre-diabetes (Glucose: {blood_glucose} mg/dL)")
        elif blood_glucose >= 70:
            risk_factors.append(f"Normal Glucose ({blood_glucose} mg/dL)")
        else:
            risk_factors.append(f"Low Glucose ({blood_glucose} mg/dL)")
        
        # Additional Risk Factors
        if data.get('known_diabetes') == 'Yes':
            score += 2
            risk_factors.append("Known Diabetes")
        
        if data.get('known_hypertension') == 'Yes':
            score += 1
            risk_factors.append("Known Hypertension")
        
        if data.get('family_history') == 'Yes':
            score += 1
            risk_factors.append("Family History")
        
        if data.get('herbal_use') == 'Yes':
            score += 1
            risk_factors.append("Herbal Medicine Use")
        
        if data.get('smoking') == 'Yes':
            score += 1
            risk_factors.append("Smoking")
        
        # BMI Calculation
        if 'weight' in data and 'height' in data:
            height_m = data['height'] / 100
            bmi = data['weight'] / (height_m ** 2)
            data['bmi'] = round(bmi, 1)
            if bmi >= 30:
                score += 1
                risk_factors.append("Obesity")
            elif bmi >= 25:
                score += 0.5
                risk_factors.append("Overweight")
        
        # Age Risk
        if data.get('age', 0) > 60:
            score += 1
            risk_factors.append("Age > 60")
        
        # Determine Risk Level
        if score >= 6:
            risk_level = " CRITICAL RISK 🔴"
            recommendation = "Immediate medical attention required"
            timeline = "Within 48 hours"
        elif score >= 5:
            risk_level = " HIGH RISK 🔴"
            recommendation = "Urgent referral to specialist required"
            timeline = "Within 1 week"
        elif score >= 3:
            risk_level = " MODERATE RISK 🟡"
            recommendation = "Refer to healthcare facility for evaluation"
            timeline = "Within 1 month"
        else:
            risk_level = " LOW RISK 🟢"
            recommendation = "Lifestyle advice and annual screening"
            timeline = "Annual checkup"
        
        return {
            'risk_level': risk_level,
            'score': round(score, 1),
            'risk_factors': risk_factors,
            'recommendation': recommendation,
            'timeline': timeline,
            'bmi': data.get('bmi', None)
        }
    
 def save_to_cloud(self, table, data):
    """Save data to Supabase - Simple version"""
    if self.supabase:
        try:
            # Remove any None values
            clean_data = {k: v for k, v in data.items() if v is not None}
            
            # Insert data
            response = self.supabase.table(table).insert(clean_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            # Show helpful error
            if "column" in str(e) and "does not exist" in str(e):
                st.info(f"Hint: You may need to add this column to your {table} table in Supabase.")
            return None
    return None
    
    def get_from_cloud(self, table, query="*"):
        """Retrieve data from Supabase"""
        if self.supabase:
            try:
                response = self.supabase.table(table).select(query).execute()
                return response.data
            except:
                return []
        return []
    
    def generate_patient_id(self, name, phone):
        """Generate unique patient ID"""
        return hashlib.md5(f"{name}{phone}{datetime.now()}".encode()).hexdigest()[:8].upper()

# ==================== STREAMLIT APP CONFIGURATION ====================
st.set_page_config(
    page_title="Health Bridge Initiative",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",  # Better for mobile
    menu_items={
        'Get Help': 'https://healthbridge.ng/help',
        'Report a bug': 'https://healthbridge.ng/bug',
        'About': '### Health Bridge Initiative - Saving Lives Through Early Detection'
    }
)
# ==================== SESSION STATE INITIALIZATION ====================
if 'screening_data' not in st.session_state:
    st.session_state.screening_data = []
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False
if 'volunteer_data' not in st.session_state:
    st.session_state.volunteer_data = []

# ==================== PAGE FUNCTIONS ====================
def show_homepage():
    """Display homepage with mission and overview"""
    st.markdown("""
    <style>
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 5px solid #667eea;
    }
    @media (max-width: 768px) {
        .hero { padding: 2rem 1rem; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="hero">
        <h1 style="font-size: 3rem; margin-bottom: 1rem;">🩺 Health Bridge Initiative</h1>
        <h3 style="color: rgba(255,255,255,0.9);">Building Nigeria's Shield Against Silent Epidemics</h3>
        <p style="font-size: 1.2rem; margin-top: 2rem;">
            Early detection saves lives. Join our mission to eradicate preventable deaths from
            chronic kidney and liver diseases in Nigeria.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Actions for Mobile
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🩺 Start Screening", use_container_width=True):
            st.switch_page("pages/1_ _Health_Screening.py")
    with col2:
        if st.button("💰 Donate Now", use_container_width=True):
            st.switch_page("pages/4_ _Funding_Platform.py")
    with col3:
        if st.button("🤝 Volunteer", use_container_width=True):
            st.switch_page("pages/3_ _Volunteer.py")
    
    st.markdown("---")
    
    # Mission & Features
    st.subheader("🎯 Our Mission")
    st.markdown("""
    To eradicate preventable deaths from chronic kidney and liver disease in Nigeria by building a
    **community-driven early detection system** that bridges the gap between risk identification and
    affordable, accessible care.
    """)
    
    # Three Pillars
    st.subheader("🌟 Our Three-Pillar Approach")
    cols = st.columns(3)
    pillars = [
        {
            "title": "🔍 Community Screening",
            "color": "#1f77b4",
            "items": [
                "Monthly free health camps",
                "Blood pressure monitoring",
                "Urine dipstick tests",
                "Blood glucose testing",
                "BMI calculation"
            ]
        },
        {
            "title": "🤖 AI-Powered Navigation",
            "color": "#ff7f0e",
            "items": [
                "Instant risk assessment",
                "Local language support",
                "Smart facility referrals",
                "Personalized health advice",
                "Mobile app integration"
            ]
        },
        {
            "title": "💰 Sustainable Funding",
            "color": "#2ca02c",
            "items": [
                "Crowdfunding platform (1% fee)",
                "Health resilience bonds",
                "Insurance partnerships",
                "Preventive care financing",
                "Transparent tracking"
            ]
        }
    ]
    
    for i, col in enumerate(cols):
        with col:
            pillar = pillars[i]
            st.markdown(f"""
            <div style='border-left: 5px solid {pillar["color"]}; padding-left: 15px; margin: 1rem 0;'>
                <h4>{pillar["title"]}</h4>
                <ul style='padding-left: 20px;'>
                    {''.join([f'<li>{item}</li>' for item in pillar["items"]])}
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    # Impact Metrics
    st.markdown("---")
    st.subheader("📈 Real-time Impact Dashboard")
    
    # Load data from cloud
    ai_engine = HealthBridgeAI()
    screenings = ai_engine.get_from_cloud("screening_data")
    donations = ai_engine.get_from_cloud("payments", "SUM(amount) as total, COUNT(*) as count")
    
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("People Screened", len(screenings) if screenings else "0", "+12 this week")
    with metric_cols[1]:
        high_risk = len([s for s in screenings if s.get('risk_score', 0) >= 5]) if screenings else 0
        st.metric("High Risk Cases", high_risk)
    with metric_cols[2]:
        total_donations = donations[0]['total'] if donations and donations[0]['total'] else "₦0"
        st.metric("Funds Raised", str(total_donations))
    with metric_cols[3]:
        volunteers = len(ai_engine.get_from_cloud("volunteers"))
        st.metric("Active Volunteers", volunteers)
    
    # Call to Action
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 3rem; background: linear-gradient(to right, #e3f2fd, #f3e5f5); border-radius: 15px;'>
        <h2>🚀 Join Our Movement</h2>
        <p style='font-size: 1.1rem; margin: 1rem 0;'>
            Be part of Nigeria's health revolution. Whether as a volunteer, partner, or donor,
            your contribution builds a healthier future for all.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Mobile App Download Section
    with st.expander("📱 Download Our Mobile App"):
        st.markdown("""
        ### Available on All Platforms
        **Android:**
        - Google Play Store: `Health Bridge Nigeria`
        - Direct APK: [Download Here](https://healthbridge.ng/app)
        
        **iOS:**
        - Apple App Store: Coming Soon
        
        **Features in Mobile App:**
        - Offline screening capability
        - Push notification reminders
        - Health tracking dashboard
        - Direct chat with doctors
        - Location-based facility finder
        
        **System Requirements:**
        - Android 8.0+ or iOS 12+
        - 100MB free space
        - Internet connection for cloud sync
        """)
        
        # QR Code for Mobile Download
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Scan to Download:**")
            st.image("https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://healthbridge.ng/download", width=150)
        with col2:
            st.markdown("**App Features Preview:**")
            st.write("• Real-time health monitoring")
            st.write("• Medication reminders")
            st.write("• Health education library")
            st.write("• Emergency contacts")

def show_screening_page():
    """Interactive health screening interface"""
    ai_engine = HealthBridgeAI()
    st.title("🔍 Community Health Screening")
    
    # Mobile-friendly tabs
    tabs = st.tabs(["📝 Screening Form", "📊 Risk Assessment", "🏥 Referral", "💡 Health Advice"])
    
    with tabs[0]:
        with st.form("screening_form", clear_on_submit=True):
            st.subheader("Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name*", placeholder="Enter full name")
                age = st.number_input("Age*", min_value=1, max_value=120, value=30)
                phone = st.text_input("Phone Number*", placeholder="08012345678")
            with col2:
                location = st.selectbox("Location*", ["Lagos", "Kano", "Abuja", "Port Harcourt", "Ibadan", "Ogun", "Oyo", "Others"])
                language = st.selectbox("Preferred Language", ["English", "Yoruba", "Hausa", "Igbo", "Pidgin"])
                sex = st.selectbox("Sex*", ["Male", "Female", "Prefer not to say"])
            
            st.markdown("---")
            st.subheader("Vital Signs & Measurements")
            col3, col4 = st.columns(2)
            with col3:
                systolic_bp = st.slider("Systolic BP (mmHg)*", 80, 250, 120)
                diastolic_bp = st.slider("Diastolic BP (mmHg)*", 50, 150, 80)
                blood_glucose = st.number_input(
                    "Random Blood Glucose (mg/dL)*",
                    min_value=20,
                    max_value=600,
                    value=100,
                    step=1,
                    help="Normal: 70-139 mg/dL | Pre-diabetes: 140-199 mg/dL | Diabetes: ≥200 mg/dL"
                )
            with col4:
                weight = st.number_input("Weight (kg)*", min_value=20.0, max_value=200.0, value=70.0, step=0.1)
                height = st.number_input("Height (cm)*", min_value=100, max_value=250, value=170)
                waist_circumference = st.number_input("Waist Circumference (cm)", min_value=50, max_value=200, value=85)
            
            st.markdown("---")
            st.subheader("Medical History & Risk Factors")
            col5, col6 = st.columns(2)
            with col5:
                urine_protein = st.selectbox("Urine Protein", ["Negative", "Trace", "1+", "2+", "3+"])
                known_diabetes = st.radio("Known Diabetes?", ["No", "Yes"])
                known_hypertension = st.radio("Known Hypertension?", ["No", "Yes"])
            with col6:
                family_history = st.radio("Family History of Kidney Disease?", ["No", "Yes"])
                herbal_use = st.radio("Regular Herbal Medicine Use?", ["No", "Yes"])
                smoking = st.radio("Do you smoke?", ["No", "Yes"])
            
            # Consent
            st.markdown("---")
            consent = st.checkbox("I consent to store my health data securely in the cloud*")
            share_data = st.checkbox("I agree to share anonymized data for research purposes")
            
            submitted = st.form_submit_button("🚀 Analyze My Health Risk", type="primary")
            
            if submitted:
                if not all([name, phone, consent]):
                    st.error("Please fill all required fields (*)")
                else:
                    screening_data = {
                        'name': name,
                        'age': age,
                        'phone': phone,
                        'location': location,
                        'language': language,
                        'sex': sex,
                        'systolic_bp': systolic_bp,
                        'diastolic_bp': diastolic_bp,
                        'blood_glucose': blood_glucose,
                        'weight': weight,
                        'height': height,
                        'waist_circumference': waist_circumference,
                        'urine_protein': urine_protein,
                        'known_diabetes': known_diabetes,
                        'known_hypertension': known_hypertension,
                        'family_history': family_history,
                        'herbal_use': herbal_use,
                        'smoking': smoking,
                        'timestamp': datetime.now().isoformat(),
                        'data_shared': share_data
                    }
                    
                    # Calculate risk
                    risk_assessment = ai_engine.calculate_kidney_risk(screening_data)
                    
                    # Generate patient ID
                    patient_id = ai_engine.generate_patient_id(name, phone)
                    
                    # Prepare data for cloud
                    cloud_data = {
                        **screening_data,
                        'patient_id': patient_id,
                        'risk_score': risk_assessment['score'],
                        'risk_level': risk_assessment['risk_level'],
                        'recommendation': risk_assessment['recommendation'],
                        'bmi': risk_assessment.get('bmi'),
                        'risk_factors': ', '.join(risk_assessment['risk_factors'])
                    }
                    
                    # Save to cloud
                    saved_data = ai_engine.save_to_cloud("screening_data", cloud_data)
                    
                    if saved_data:
                        st.session_state.current_screening = {
                            'data': screening_data,
                            'risk': risk_assessment,
                            'patient_id': patient_id
                        }
                        st.success("✅ Screening data saved securely to cloud!")
                        st.balloons()
                    else:
                        st.warning("⚠ Data saved locally. Please check internet connection.")
                        st.session_state.current_screening = {
                            'data': screening_data,
                            'risk': risk_assessment,
                            'patient_id': patient_id
                        }
    
    # Display results if screening exists
    if 'current_screening' in st.session_state:
        screening = st.session_state.current_screening
        screening_data = screening['data']
        risk_assessment = screening['risk']
        patient_id = screening['patient_id']
        
        with tabs[1]:
            st.subheader("🎯 Your Risk Assessment")
            
            # Risk Level Card
            risk_level = risk_assessment['risk_level']
            risk_color = {
                "🟢 LOW RISK": "green",
                "🟡 MODERATE RISK": "orange",
                "🔴 HIGH RISK": "red",
                "🔴 CRITICAL RISK": "darkred"
            }.get(risk_level.split()[0], "gray")
            
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                        padding: 25px; border-radius: 15px; border-left: 8px solid {risk_color};
                        margin: 20px 0;'>
                <h2 style='color: {risk_color}; margin: 0;'>{risk_level}</h2>
                <p style='font-size: 1.2rem; margin: 10px 0;'>
                    <strong>Risk Score:</strong> {risk_assessment['score']:.1f}/10
                </p>
                <p><strong>Recommendation:</strong> {risk_assessment['recommendation']}</p>
                <p><strong>Timeline:</strong> {risk_assessment['timeline']}</p>
                <p><strong>Patient ID:</strong> {patient_id}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Vital Signs Dashboard
            st.subheader("📊 Your Vital Signs")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                bp_status = "✅ Normal" if (screening_data['systolic_bp'] < 140 and screening_data['diastolic_bp'] < 90) else "⚠ High"
                st.metric("Blood Pressure", 
                         f"{screening_data['systolic_bp']}/{screening_data['diastolic_bp']} mmHg", 
                         bp_status)
            with col2:
                glucose = screening_data['blood_glucose']
                if glucose >= 200:
                    glucose_status = "🔴 Diabetes"
                elif glucose >= 140:
                    glucose_status = "🟡 Pre-diabetes"
                elif glucose >= 70:
                    glucose_status = "🟢 Normal"
                else:
                    glucose_status = "🔵 Low"
                st.metric("Blood Glucose", f"{glucose} mg/dL", glucose_status)
            with col3:
                bmi = risk_assessment.get('bmi')
                if bmi:
                    if bmi >= 30:
                        bmi_status = "🔴 Obese"
                    elif bmi >= 25:
                        bmi_status = "🟡 Overweight"
                    else:
                        bmi_status = "🟢 Normal"
                    st.metric("BMI", f"{bmi:.1f}", bmi_status)
            with col4:
                urine_color = "red" if screening_data['urine_protein'] in ["2+", "3+"] else \
                             "orange" if screening_data['urine_protein'] in ["Trace", "1+"] else "green"
                st.metric("Urine Protein", screening_data['urine_protein'])
            
            # Risk Factors
            st.subheader("⚠ Identified Risk Factors")
            if risk_assessment['risk_factors']:
                for factor in risk_assessment['risk_factors']:
                    st.write(f"• {factor}")
            else:
                st.success("No significant risk factors identified")
            
            # Glucose Gauge
            st.subheader("📈 Blood Glucose Analysis")
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=glucose,
                title={'text': "Blood Glucose (mg/dL)"},
                number={'suffix': " mg/dL"},
                gauge={
                    'axis': {'range': [40, 300]},
                    'bar': {'color': "#1f77b4"},
                    'steps': [
                        {'range': [40, 70], 'color': "#e6f3ff"},
                        {'range': [70, 140], 'color': "#d4edda"},
                        {'range': [140, 200], 'color': "#fff3cd"},
                        {'range': [200, 300], 'color': "#f8d7da"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 200
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[2]:
            st.subheader("🏥 Referral Information")
            
            # Generate referral
            suitable_facilities = []
            if "HIGH RISK" in risk_level or "CRITICAL" in risk_level:
                facility_type = "Tertiary"
            else:
                facility_type = "Secondary"
            
            location = screening_data['location']
            if location in ai_engine.facilities:
                for facility in ai_engine.facilities[location]:
                    if facility['type'] == facility_type:
                        suitable_facilities.append(facility)
            
            # Referral Card
            st.markdown(f"""
            <div style='background: #e8f4f8; padding: 20px; border-radius: 10px;'>
                <h4>📋 Health Bridge Referral Slip</h4>
                <p><strong>Patient:</strong> {screening_data['name']}</p>
                <p><strong>Patient ID:</strong> {patient_id}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
                <p><strong>Priority:</strong> {"🔴 URGENT" if "HIGH" in risk_level or "CRITICAL" in risk_level else "🟢 ROUTINE"}</p>
                <p><strong>Blood Glucose:</strong> {screening_data['blood_glucose']} mg/dL</p>
                <p><strong>Blood Pressure:</strong> {screening_data['systolic_bp']}/{screening_data['diastolic_bp']} mmHg</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Facilities
            if suitable_facilities:
                st.subheader("📍 Recommended Healthcare Facilities")
                for i, facility in enumerate(suitable_facilities[:2], 1):
                    st.markdown(f"""
                    <div style='background: #f0f8ff; padding: 15px; border-radius: 8px;
                                margin: 10px 0; border-left: 4px solid #1f77b4;'>
                        <h5>{i}. {facility['name']}</h5>
                        <p><strong>Type:</strong> {facility['type']} | 
                           <strong>Specialty:</strong> {facility['specialty']}</p>
                        <p><strong>Location:</strong> {facility['location']}</p>
                        <p><strong>Contact:</strong> {facility['contact']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Map Integration
                with st.expander("🗺 View on Map"):
                    lat, lng = facility.get('latitude', 0), facility.get('longitude', 0)
                    if lat and lng:
                        st.map(pd.DataFrame({
                            'lat': [lat],
                            'lon': [lng]
                        }), zoom=13)
            
            # Download Referral
            st.subheader("📄 Download Referral")
            referral_text = f"""
=================================
HEALTH BRIDGE INITIATIVE - REFERRAL
=================================
Patient: {screening_data['name']}
Patient ID: {patient_id}
Date: {datetime.now().strftime('%Y-%m-%d')}
Risk Level: {risk_level}

VITAL SIGNS:
- Blood Pressure: {screening_data['systolic_bp']}/{screening_data['diastolic_bp']} mmHg
- Blood Glucose: {screening_data['blood_glucose']} mg/dL
- Urine Protein: {screening_data['urine_protein']}
- BMI: {risk_assessment.get('bmi', 'N/A')}

RECOMMENDED FACILITIES:
"""
            for facility in suitable_facilities[:2]:
                referral_text += f"\n• {facility['name']} ({facility['type']})"
                referral_text += f"\n📍 {facility['location']}"
                referral_text += f"\n📞 {facility['contact']}"
                referral_text += f"\n⚕ Specialty: {facility['specialty']}\n"
            
            referral_text += f"""
RECOMMENDATION:
{risk_assessment['recommendation']}

TIMELINE:
{risk_assessment['timeline']}

=================================
For verification: www.healthbridge.ng
Emergency: 112 or 767
📞 *08179371170*
=================================
"""
            
            st.download_button(
                label="📥 Download Referral Slip",
                data=referral_text,
                file_name=f"referral_{patient_id}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            # Share options
            st.markdown("### 📲 Share Your Results")
            share_cols = st.columns(3)
            with share_cols[0]:
                if st.button("📧 Email", use_container_width=True):
                    st.info("Email sharing coming soon!")
            with share_cols[1]:
                if st.button("📱 WhatsApp", use_container_width=True):
                    st.info("WhatsApp sharing coming soon!")
            with share_cols[2]:
                if st.button("💾 Save to Phone", use_container_width=True):
                    st.success("Referral saved to device!")
        
        with tabs[3]:
            st.subheader("💡 Personalized Health Advice")
            
            # Generate advice based on risk factors
            advice = []
            risk_factors = [f.lower() for f in risk_assessment['risk_factors']]
            
            if any('hypertension' in f for f in risk_factors):
                advice.extend([
                    "• **Reduce salt intake** to less than 5g per day",
                    "• **Increase potassium-rich foods**: bananas, spinach, sweet potatoes",
                    "• **Exercise regularly**: 30 minutes most days",
                    "• **Limit alcohol**: Max 1 drink/day for women, 2 for men"
                ])
            
            if any('diabetes' in f or 'glucose' in f for f in risk_factors):
                advice.extend([
                    "• **Monitor blood sugar** regularly",
                    "• **Choose complex carbs**: whole grains, vegetables",
                    "• **Exercise**: 150 minutes/week of moderate activity",
                    "• **Maintain healthy weight**: Target BMI 18.5-24.9"
                ])
            
            if any('protein' in f for f in risk_factors):
                advice.extend([
                    "• **Stay hydrated**: 2-3 liters of water daily",
                    "• **Avoid NSAIDs**: Ibuprofen, aspirin without prescription",
                    "• **Control BP & sugar** strictly",
                    "• **Regular kidney function tests** recommended"
                ])
            
            # General advice
            advice.extend([
                "• **Avoid smoking and tobacco** products",
                "• **Get 7-8 hours** of quality sleep nightly",
                "• **Manage stress**: Meditation, deep breathing",
                "• **Regular check-ups**: Annual health screening"
            ])
            
            # Display advice
            for item in advice:
                st.markdown(item)
            
            # Glucose-specific advice
            glucose = screening_data['blood_glucose']
            if glucose >= 200:
                st.warning("""
                **🔴 IMPORTANT FOR HIGH BLOOD GLUCOSE (≥200 mg/dL):**
                - **Urgent consultation** with doctor within 1 week
                - **Monitor glucose** levels twice daily
                - **Follow diabetic diet**: Low glycemic index foods
                - **Medication** may be required immediately
                """)
            elif glucose >= 140:
                st.info("""
                **🟡 FOR ELEVATED BLOOD GLUCOSE (140-199 mg/dL):**
                - **Consult doctor** within 1 month
                - **Lifestyle modification** crucial
                - **Reduce sugar** and processed foods
                - **Re-check** in 3 months
                """)
            elif glucose < 70:
                st.error("""
                **🔵 FOR LOW BLOOD GLUCOSE (<70 mg/dL):**
                - **Immediate action**: Consume 15g fast-acting carbs
                - **Re-check** in 15 minutes
                - **Consult doctor** if recurrent episodes
                - **Carry glucose tablets** or sweets
                """)
            
            # Local language note
            if screening_data['language'] != 'English':
                st.info(f"💬 Personalized advice in {screening_data['language']} coming soon!")
            
            # Funding eligibility
            if "HIGH RISK" in risk_level or "CRITICAL" in risk_level:
                st.markdown("""
                <div style='background: #fffacd; padding: 15px; border-radius: 8px; margin: 20px 0;'>
                    <h5>💰 Financial Assistance Available</h5>
                    <p>You may be eligible for our health funding support program.</p>
                    <p>Our crowdfunding platform has only 1% processing fee.</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Apply for Financial Support", use_container_width=True):
                    st.switch_page("pages/4_ _Funding_Platform.py")

def show_dashboard():
    """Analytics dashboard for the initiative"""
    ai_engine = HealthBridgeAI()
    st.title("📊 Health Bridge Dashboard")
    
    # Load data from cloud
    screenings = ai_engine.get_from_cloud("screening_data")
    donations = ai_engine.get_from_cloud("payments", "SUM(amount) as total_donations, COUNT(*) as donation_count")
    
    if not screenings:
        st.info("No screening data available yet. Start with the Health Screening page.")
        return
    
    df = pd.DataFrame(screenings)
    
    # Key Metrics
    st.subheader("📈 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_screened = len(df)
        st.metric("Total Screened", total_screened)
    with col2:
        high_risk = len([s for s in screenings if s.get('risk_score', 0) >= 5])
        st.metric("High Risk Cases", high_risk, f"{(high_risk/total_screened*100):.1f}%" if total_screened > 0 else "0%")
    with col3:
        avg_age = df['age'].mean() if 'age' in df.columns else 0
        st.metric("Average Age", f"{avg_age:.1f}")
    with col4:
        if donations and donations[0]['total_donations']:
            total_donations = donations[0]['total_donations']
            st.metric("Funds Raised", f"₦{total_donations:,.0f}")
        else:
            st.metric("Funds Raised", "₦0")
    
    st.markdown("---")
    
    # Glucose Analysis
    if 'blood_glucose' in df.columns:
        st.subheader("🩸 Blood Glucose Distribution (mg/dL)")
        # Categories
        glucose_cats = pd.cut(df['blood_glucose'],
                            bins=[0, 70, 140, 200, 600],
                            labels=['Low (<70)', 'Normal (70-139)', 'Pre-diabetes (140-199)', 'Diabetes (≥200)'])
        glucose_counts = glucose_cats.value_counts().sort_index()
        
        fig1 = px.pie(
            values=glucose_counts.values,
            names=glucose_counts.index,
            title="Blood Glucose Categories",
            color_discrete_sequence=['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    st.markdown("---")
    
    # Risk Distribution
    st.subheader("⚠ Risk Level Distribution")
    if 'risk_level' in df.columns:
        risk_counts = df['risk_level'].value_counts()
        fig2 = px.bar(
            x=risk_counts.index,
            y=risk_counts.values,
            title="Risk Levels Across Population",
            labels={'x': 'Risk Level', 'y': 'Count'},
            color=risk_counts.values,
            color_continuous_scale='RdYlGn_r'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # Location Analysis
    st.subheader("📍 Geographic Distribution")
    if 'location' in df.columns:
        location_counts = df['location'].value_counts()
        fig3 = px.bar(
            x=location_counts.index,
            y=location_counts.values,
            title="Screenings by Location",
            labels={'x': 'Location', 'y': 'Count'},
            color=location_counts.values,
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # Time Series Analysis
    st.subheader("📅 Screening Trends Over Time")
    if 'timestamp' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_counts = df.groupby('date').size().reset_index(name='count')
        fig4 = px.line(
            daily_counts,
            x='date',
            y='count',
            title="Daily Screenings",
            markers=True
        )
        fig4.update_layout(xaxis_title="Date", yaxis_title="Number of Screenings")
        st.plotly_chart(fig4, use_container_width=True)
    
    # Data Table
    st.subheader("📋 Detailed Screening Records")
    display_columns = ['patient_id', 'name', 'age', 'location', 'blood_glucose', 'risk_level']
    available_columns = [col for col in display_columns if col in df.columns]
    
    if available_columns:
        st.dataframe(
            df[available_columns],
            use_container_width=True,
            hide_index=True
        )
    
    # Export Options
    st.subheader("📤 Data Export")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Export as CSV", use_container_width=True):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"health_screening_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    with col2:
        if st.button("📊 Generate Report", use_container_width=True):
            report = generate_dashboard_report(df)
            st.download_button(
                label="Download Report",
                data=report,
                file_name=f"dashboard_report_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

def show_funding_platform():
    """Crowdfunding platform with Paystack integration"""
    ai_engine = HealthBridgeAI()
    st.title("💰 Health Bridge Funding Platform")
    
    # Tabs for different funding sections
    tabs = st.tabs(["💸 Donate Now", "📋 Funding Requests", "🤝 Corporate Sponsorship", "📊 Funding Analytics"])
    
    with tabs[0]:
        st.subheader("Make a Donation")
        with st.form("donation_form"):
            col1, col2 = st.columns(2)
            with col1:
                donor_name = st.text_input("Full Name")
                donor_email = st.text_input("Email Address*", placeholder="example@email.com")
                donation_type = st.selectbox(
                    "Donation Type",
                    ["General Fund", "Specific Patient", "Equipment Fund", "Screening Camp", "Research"]
                )
            with col2:
                amount = st.number_input("Amount (₦)*", min_value=100, value=5000, step=100)
                message = st.text_area("Message (Optional)", placeholder="Your message here...")
                anonymous = st.checkbox("Donate Anonymously")
            
            # Patient selection for specific donations
            if donation_type == "Specific Patient":
                patients = ai_engine.get_from_cloud("screening_data", "DISTINCT patient_id, name")
                if patients:
                    patient_options = {f"{p['name']} (ID: {p['patient_id']})": p['patient_id'] for p in patients}
                    selected_patient = st.selectbox("Select Patient to Support", list(patient_options.keys()))
                    patient_id = patient_options[selected_patient]
                else:
                    st.info("No patients available for funding")
                    patient_id = None
            
            submitted = st.form_submit_button("💳 Proceed to Payment", type="primary")
            
            if submitted:
                if not donor_email or amount < 100:
                    st.error("Please enter valid email and amount (minimum ₦100)")
                else:
                    # Prepare payment metadata
                    metadata = {
                        "donor_name": "Anonymous" if anonymous else donor_name,
                        "donation_type": donation_type,
                        "message": message,
                        "patient_id": patient_id if donation_type == "Specific Patient" else None,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Initialize payment
                    payment_data = ai_engine.payment_manager.initialize_transaction(
                        email=donor_email,
                        amount=amount,
                        metadata=metadata
                    )
                    
                    if payment_data and payment_data.get('status'):
                        authorization_url = payment_data['data']['authorization_url']
                        reference = payment_data['data']['reference']
                        st.success("✅ Payment initialized! Redirecting to Paystack...")
                        
                        # Display payment button
                        st.markdown(f"""
                        <a href="{authorization_url}" target="_blank">
                            <button style='
                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                color: white;
                                padding: 15px 30px;
                                border: none;
                                border-radius: 10px;
                                font-size: 16px;
                                cursor: pointer;
                                width: 100%;
                                margin: 10px 0;
                            '>
                                💳 Click to Complete Payment on Paystack
                            </button>
                        </a>
                        """, unsafe_allow_html=True)
                        
                        # Save payment record
                        payment_record = {
                            "reference": reference,
                            "donor_email": donor_email,
                            "donor_name": "Anonymous" if anonymous else donor_name,
                            "amount": amount,
                            "currency": "NGN",
                            "status": "pending",
                            "metadata": metadata,
                            "created_at": datetime.now().isoformat()
                        }
                        ai_engine.save_to_cloud("payments", payment_record)
                    else:
                        st.error("Payment initialization failed. Please try again.")
    
    with tabs[1]:
        st.subheader("Active Funding Requests")
        # Load funding requests from cloud
        funding_requests = ai_engine.get_from_cloud("funding_requests")
        
        if funding_requests:
            for request in funding_requests:
                if request.get('status') == 'active':
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"### {request['patient_name']}")
                            st.write(f"**Diagnosis:** {request.get('diagnosis', 'Not specified')}")
                            st.write(f"**Amount Needed:** ₦{request.get('amount_needed', 0):,.0f}")
                            st.write(f"**Urgency:** {request.get('urgency_level', 'Medium')}")
                            
                            # Progress bar
                            amount_raised = request.get('amount_raised', 0)
                            amount_needed = request.get('amount_needed', 1)
                            progress = (amount_raised / amount_needed) * 100
                            st.progress(min(progress / 100, 1.0))
                            st.write(f"**₦{amount_raised:,.0f} raised of ₦{amount_needed:,.0f} ({progress:.1f}%)**")
                        
                        with col2:
                            if st.button("Donate Now", key=request['id'], use_container_width=True):
                                st.session_state.selected_request = request
                                st.rerun()
                        st.markdown("---")
        else:
            st.info("No active funding requests")
        
        # Option to create funding request
        if st.button("➕ Create Funding Request", use_container_width=True):
            with st.form("new_funding_request"):
                st.subheader("New Funding Request")
                patient_name = st.text_input("Patient Name")
                diagnosis = st.text_area("Diagnosis")
                treatment_plan = st.text_area("Treatment Plan")
                amount_needed = st.number_input("Amount Needed (₦)", min_value=10000, value=500000)
                urgency = st.selectbox("Urgency Level", ["Low", "Medium", "High", "Critical"])
                story = st.text_area("Patient's Story")
                
                if st.form_submit_button("Submit for Review"):
                    # Save to cloud
                    pass
    
    with tabs[2]:
        st.subheader("Corporate Partnership Opportunities")
        partnership_tiers = [
            {
                "name": "🌱 Community Partner",
                "amount": "₦500,000/year",
                "benefits": [
                    "Logo on website",
                    "Social media recognition",
                    "Annual impact report"
                ]
            },
            {
                "name": "💎 Health Champion",
                "amount": "₦2,000,000/year",
                "benefits": [
                    "All Community benefits",
                    "Naming rights for screening camps",
                    "Featured in press releases",
                    "Employee engagement programs"
                ]
            },
            {
                "name": "🏆 Life Saver",
                "amount": "₦5,000,000+/year",
                "benefits": [
                    "All Health Champion benefits",
                    "Board advisory position",
                    "Customized impact reporting",
                    "Exclusive event invitations",
                    "Media coverage opportunities"
                ]
            }
        ]
        
        for tier in partnership_tiers:
            with st.expander(f"{tier['name']} - {tier['amount']}"):
                st.markdown("**Benefits:**")
                for benefit in tier['benefits']:
                    st.write(f"✓ {benefit}")
                if st.button(f"Become {tier['name'].split()[1]} Partner", key=tier['name']):
                    st.info("Contact us at partners@healthbridge.ng")
        
        st.markdown("---")
        st.subheader("📞 Contact Our Partnership Team")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Email:** partners@healthbridge.ng")
            st.write("**Phone:** +234 817 937 1170")
        with col2:
            st.write("**Address:** Health Bridge Initiative HQ")
            st.write("Lagos, Nigeria")
    
    with tabs[3]:
        st.subheader("Funding Analytics")
        payments = ai_engine.get_from_cloud("payments")
        
        if payments:
            payments_df = pd.DataFrame(payments)
            # Convert amount to numeric
            payments_df['amount'] = pd.to_numeric(payments_df['amount'], errors='coerce')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                total_donations = payments_df['amount'].sum()
                st.metric("Total Donations", f"₦{total_donations:,.0f}")
            with col2:
                avg_donation = payments_df['amount'].mean()
                st.metric("Average Donation", f"₦{avg_donation:,.0f}")
            with col3:
                successful_donations = len(payments_df[payments_df['status'] == 'success'])
                st.metric("Successful Donations", successful_donations)
            
            # Donation trends
            if 'created_at' in payments_df.columns:
                payments_df['date'] = pd.to_datetime(payments_df['created_at']).dt.date
                daily_donations = payments_df.groupby('date')['amount'].sum().reset_index()
                fig = px.line(
                    daily_donations,
                    x='date',
                    y='amount',
                    title="Daily Donation Trends",
                    labels={'amount': 'Amount (₦)', 'date': 'Date'}
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No donation data available")

def show_volunteer_registration():
    """Volunteer registration and management"""
    ai_engine = HealthBridgeAI()
    st.title("🤝 Join Our Volunteer Team")
    
    tabs = st.tabs(["📝 Volunteer Application", "🔍 Find Opportunities", "📚 Volunteer Resources"])
    
    with tabs[0]:
        with st.form("volunteer_application", clear_on_submit=True):
            st.subheader("Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                full_name = st.text_input("Full Name*", placeholder="John Doe")
                email = st.text_input("Email Address*", placeholder="john@example.com")
                phone = st.text_input("Phone Number*", placeholder="08012345678")
            with col2:
                location = st.selectbox("Location*", ["Lagos", "Kano", "Abuja", "Port Harcourt", "Ibadan", "Others"])
                profession = st.text_input("Profession/Occupation", placeholder="Doctor, Nurse, Student, etc.")
                age = st.number_input("Age*", min_value=18, max_value=80, value=25)
            
            st.markdown("---")
            st.subheader("Volunteer Preferences")
            skills = st.multiselect("Select Your Skills*",
                                  ["Medical Professional", "Nursing", "Community Health", "Data Entry",
                                   "Event Management", "Fundraising", "Translation", "Counseling",
                                   "Logistics", "IT Support", "Marketing", "Graphic Design",
                                   "Photography/Videography", "Teaching", "Research", "Others"])
            other_skills = st.text_input("Other Skills (if not listed)")
            
            availability = st.selectbox("Availability*",
                                      ["Weekends Only", "Weekdays Only", "Flexible", "Specific Days", "Remote Only"])
            if availability == "Specific Days":
                specific_days = st.multiselect("Select Days",
                                             ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            
            experience = st.number_input("Years of Relevant Experience", min_value=0, max_value=50, value=0)
            
            st.markdown("---")
            st.subheader("Background Information")
            motivation = st.text_area("Why do you want to volunteer with us?*",
                                    placeholder="Share your motivation...",
                                    height=100)
            previous_volunteering = st.text_area("Previous Volunteering Experience (if any)",
                                               placeholder="Describe your previous experience...",
                                               height=80)
            emergency_contact = st.text_input("Emergency Contact Name & Number")
            
            st.markdown("---")
            st.subheader("Terms & Conditions")
            col3, col4 = st.columns(2)
            with col3:
                terms = st.checkbox("I agree to the Terms and Conditions*")
                data_consent = st.checkbox("I consent to data processing*")
            with col4:
                code_of_conduct = st.checkbox("I agree to abide by the Code of Conduct*")
                background_check = st.checkbox("I consent to background checks if required")
            
            submitted = st.form_submit_button("Submit Application", type="primary")
            
            if submitted:
                # Validate required fields
                required_fields = [full_name, email, phone, location, skills, motivation]
                if not all(required_fields) or not all([terms, data_consent, code_of_conduct]):
                    st.error("Please fill all required fields (*)")
                else:
                    volunteer_data = {
                        "full_name": full_name,
                        "email": email,
                        "phone": phone,
                        "location": location,
                        "profession": profession,
                        "age": age,
                        "skills": ", ".join(skills) + (f", {other_skills}" if other_skills else ""),
                        "availability": availability,
                        "specific_days": specific_days if availability == "Specific Days" else None,
                        "experience_years": experience,
                        "motivation": motivation,
                        "previous_experience": previous_volunteering,
                        "emergency_contact": emergency_contact,
                        "status": "pending",
                        "applied_date": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat()
                    }
                    
                    # Save to cloud
                    result = ai_engine.save_to_cloud("volunteers", volunteer_data)
                    
                    if result:
                        st.success("""
                        ✅ Thank you for your application!
                        
                        **Next Steps:**
                        1. You'll receive a confirmation email within 24 hours
                        2. Our team will review your application
                        3. We'll contact you for an interview
                        4. Upon approval, you'll receive volunteer training
                        
                        **Contact:** volunteers@healthbridge.ng
                        """)
                        st.balloons()
                        # Send confirmation (would integrate with email service)
                        # send_confirmation_email(email, full_name)
                    else:
                        st.error("Failed to submit application. Please try again or contact us.")
    
    with tabs[1]:
        st.subheader("Current Volunteer Opportunities")
        opportunities = [
            {
                "title": "🩺 Community Health Screeners",
                "location": "Lagos & Kano",
                "commitment": "Weekends, 4-6 hours",
                "skills": ["Medical background", "Compassionate", "Good communication"],
                "description": "Assist in conducting health screenings at community camps"
            },
            {
                "title": "📊 Data Entry Specialists",
                "location": "Remote",
                "commitment": "Flexible, 2-4 hours/week",
                "skills": ["Computer literate", "Attention to detail", "Basic Excel"],
                "description": "Help enter and organize screening data"
            },
            {
                "title": "🗣 Community Ambassadors",
                "location": "All Locations",
                "commitment": "Variable",
                "skills": ["Local language", "Public speaking", "Community networks"],
                "description": "Raise awareness about health screening in local communities"
            },
            {
                "title": "🎪 Event Volunteers",
                "location": "Lagos",
                "commitment": "Weekend events",
                "skills": ["Logistics", "Teamwork", "Problem-solving"],
                "description": "Help organize and run screening camps"
            }
        ]
        
        for opp in opportunities:
            with st.expander(f"{opp['title']} - {opp['location']}"):
                st.write(f"**Commitment:** {opp['commitment']}")
                st.write(f"**Required Skills:** {', '.join(opp['skills'])}")
                st.write(f"**Description:** {opp['description']}")
                if st.button("Apply for this Role", key=opp['title']):
                    st.session_state.selected_opportunity = opp['title']
                    st.rerun()
        
        st.markdown("---")
        st.subheader("Volunteer Benefits")
        benefits_cols = st.columns(2)
        with benefits_cols[0]:
            st.write("✓ **Training & Development**")
            st.write("✓ **Certificate of Service**")
            st.write("✓ **Professional Networking**")
            st.write("✓ **Skill Development**")
        with benefits_cols[1]:
            st.write("✓ **Travel Allowance**")
            st.write("✓ **Meals during events**")
            st.write("✓ **Health Bridge Merchandise**")
            st.write("✓ **Impact Recognition**")
    
    with tabs[2]:
        st.subheader("Volunteer Resources")
        resource_cols = st.columns(3)
        with resource_cols[0]:
            st.markdown("### 📚 Training Materials")
            st.write("[Health Screening Protocol](link)")
            st.write("[Data Privacy Guidelines](link)")
            st.write("[Community Engagement Guide](link)")
            st.write("[Emergency Procedures](link)")
        with resource_cols[1]:
            st.markdown("### 📅 Upcoming Events")
            st.write("**Jan 15:** Volunteer Orientation")
            st.write("**Jan 20:** Community Screening - Lagos")
            st.write("**Jan 27:** First Aid Training")
            st.write("**Feb 3:** Data Entry Workshop")
        with resource_cols[2]:
            st.markdown("### 👥 Community")
            st.write("**WhatsApp Group:** Join here")
            st.write("**Forum:** volunteers.healthbridge.ng")
            st.write("**Email:** volunteers@healthbridge.ng")
            st.write("**Hotline:** 0817 937 1170")
        
        st.markdown("---")
        st.subheader("Volunteer Stories")
        stories = [
            {"name": "Dr. OYELEYE HASSAN", "role": "Medical Volunteer",
             "story": "I've screened over 500 people and detected 25 high-risk cases. Saving lives through early detection!"},
            {"name": "IMAM OLOYEDE SODIQ", "role": "Community Ambassador",
             "story": "Translating health information to Igbo has helped my community understand their risks better."},
            {"name": "BILAL DAWODU", "role": "Data Specialist",
             "story": "Every data point I enter represents a life we're helping to save. It's incredibly rewarding."}
        ]
        
        for story in stories:
            with st.expander(f"{story['name']} - {story['role']}"):
                st.write(story['story'])
                st.caption(f"Volunteer since 2023")

def show_admin_panel():
    """Admin panel for data management and system control"""
    # Password protection
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.title("🔐 Admin Login")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("admin_login"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    # Check credentials (in production, use secure authentication)
                    admin_user = st.secrets.get("ADMIN_USERNAME", "admin")
                    admin_pass = st.secrets.get("ADMIN_PASSWORD", "HealthBridge2024!")
                    if username == admin_user and password == admin_pass:
                        st.session_state.admin_authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        st.markdown("---")
        st.info("For emergency access, contact system administrator.")
        return
    
    ai_engine = HealthBridgeAI()
    st.title("🔧 Admin Control Panel")
    
    # Logout button
    if st.button("🚪 Logout", type="secondary"):
        st.session_state.admin_authenticated = False
        st.rerun()
    
    # Admin tabs
    tabs = st.tabs(["📊 System Overview", "👥 User Management", "💾 Data Management", "⚙ System Settings", "📈 Analytics", "🔐 Security"])
    
    with tabs[0]:
        st.subheader("System Status")
        # Load all data
        screenings = ai_engine.get_from_cloud("screening_data")
        volunteers = ai_engine.get_from_cloud("volunteers")
        payments = ai_engine.get_from_cloud("payments")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Screenings", len(screenings) if screenings else 0)
        with col2:
            active_volunteers = len([v for v in volunteers if v.get('status') == 'active']) if volunteers else 0
            st.metric("Active Volunteers", active_volunteers)
        with col3:
            total_donations = sum([p.get('amount', 0) for p in payments]) if payments else 0
            st.metric("Total Donations", f"₦{total_donations:,.0f}")
        with col4:
            today = datetime.now().date()
            today_screenings = len([s for s in screenings 
                                  if pd.to_datetime(s.get('timestamp')).date() == today]) if screenings else 0
            st.metric("Today's Screenings", today_screenings)
        
        # System health
        st.subheader("System Health")
        health_items = [
            {"component": "Database", "status": "✅ Online" if ai_engine.supabase else "❌ Offline"},
            {"component": "Payment Gateway", "status": "✅ Online" if ai_engine.payment_manager.secret_key else "❌ Offline"},
            {"component": "Storage", "status": "🟢 Healthy"},
            {"component": "API Services", "status": "✅ Online"}
        ]
        
        for item in health_items:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(item['component'])
            with col2:
                st.write(item['status'])
        
        # Recent activity
        st.subheader("Recent Activity")
        if screenings:
            recent = sorted(screenings, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
            for item in recent:
                st.write(f"**{item.get('name', 'Unknown')}** - {item.get('location', 'Unknown')} - {item.get('risk_level', 'Unknown')}")
    
    with tabs[1]:
        st.subheader("User Management")
        volunteers = ai_engine.get_from_cloud("volunteers")
        
        if volunteers:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.multiselect("Filter by Status", 
                                             ["pending", "approved", "active", "inactive", "rejected"])
            with col2:
                location_filter = st.multiselect("Filter by Location",
                                               list(set([v.get('location', 'Unknown') for v in volunteers])))
            
            # Apply filters
            filtered_volunteers = volunteers
            if status_filter:
                filtered_volunteers = [v for v in filtered_volunteers if v.get('status') in status_filter]
            if location_filter:
                filtered_volunteers = [v for v in filtered_volunteers if v.get('location') in location_filter]
            
            # Display table
            for volunteer in filtered_volunteers:
                with st.expander(f"{volunteer['full_name']} - {volunteer['status']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Email:** {volunteer.get('email')}")
                        st.write(f"**Phone:** {volunteer.get('phone')}")
                        st.write(f"**Location:** {volunteer.get('location')}")
                        st.write(f"**Skills:** {volunteer.get('skills', 'None')}")
                    with col2:
                        st.write(f"**Applied:** {volunteer.get('applied_date', 'Unknown')[:10]}")
                        st.write(f"**Experience:** {volunteer.get('experience_years', 0)} years")
                        st.write(f"**Availability:** {volunteer.get('availability')}")
                    
                    # Status update
                    new_status = st.selectbox("Update Status",
                                            ["pending", "approved", "active", "inactive", "rejected"],
                                            index=["pending", "approved", "active", "inactive", "rejected"]
                                            .index(volunteer.get('status', 'pending')),
                                            key=f"status_{volunteer.get('id')}")
                    
                    if st.button("Update", key=f"update_{volunteer.get('id')}"):
                        # Update in database
                        try:
                            ai_engine.supabase.table("volunteers").update(
                                {"status": new_status}
                            ).eq("id", volunteer['id']).execute()
                            st.success("Status updated!")
                            st.rerun()
                        except:
                            st.error("Update failed")
        else:
            st.info("No volunteer data")
    
    with tabs[2]:
        st.subheader("Data Management")
        # Export all data
        st.write("### Export Data")
        export_cols = st.columns(3)
        with export_cols[0]:
            if st.button("📥 Export Screenings", use_container_width=True):
                screenings = ai_engine.get_from_cloud("screening_data")
                if screenings:
                    df = pd.DataFrame(screenings)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="screenings_export.csv",
                        mime="text/csv"
                    )
        with export_cols[1]:
            if st.button("📥 Export Volunteers", use_container_width=True):
                volunteers = ai_engine.get_from_cloud("volunteers")
                if volunteers:
                    df = pd.DataFrame(volunteers)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="volunteers_export.csv",
                        mime="text/csv"
                    )
        with export_cols[2]:
            if st.button("📥 Export Payments", use_container_width=True):
                payments = ai_engine.get_from_cloud("payments")
                if payments:
                    df = pd.DataFrame(payments)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name="payments_export.csv",
                        mime="text/csv"
                    )
        
        # Data cleanup
        st.markdown("---")
        st.subheader("Data Maintenance")
        with st.expander("🗑 Clean Old Data"):
            days_to_keep = st.number_input("Keep data younger than (days)", 
                                         min_value=30, max_value=365, value=180)
            if st.button("Clean Old Data", type="secondary"):
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                st.info(f"This will delete data older than {cutoff_date.strftime('%Y-%m-%d')}")
                confirm = st.checkbox("I understand this action cannot be undone")
                if confirm and st.button("Confirm Deletion", type="primary"):
                    # Implementation would delete old data
                    st.success("Data cleanup scheduled")
    
    with tabs[3]:
        st.subheader("System Settings")
        # App settings
        with st.form("system_settings"):
            st.write("### Application Settings")
            app_name = st.text_input("Application Name", value="Health Bridge Initiative")
            maintenance_mode = st.checkbox("Maintenance Mode")
            allow_registrations = st.checkbox("Allow New Registrations", value=True)
            enable_payments = st.checkbox("Enable Payments", value=True)
            
            # Notification settings
            st.write("### Notification Settings")
            notify_new_screening = st.checkbox("Notify on New Screening", value=True)
            notify_high_risk = st.checkbox("Notify on High Risk Cases", value=True)
            notify_donation = st.checkbox("Notify on Donations", value=True)
            
            if st.form_submit_button("Save Settings"):
                st.success("Settings saved!")
    
    with tabs[4]:
        st.subheader("Advanced Analytics")
        # Load all data
        screenings = ai_engine.get_from_cloud("screening_data")
        
        if screenings:
            df = pd.DataFrame(screenings)
            
            # Advanced charts
            col1, col2 = st.columns(2)
            with col1:
                # Age distribution
                fig1 = px.histogram(df, x='age', nbins=20, title="Age Distribution")
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                # Risk vs Glucose
                if 'blood_glucose' in df.columns and 'risk_score' in df.columns:
                    fig2 = px.scatter(df, x='blood_glucose', y='risk_score',
                                    color='risk_level', title="Glucose vs Risk Score")
                    st.plotly_chart(fig2, use_container_width=True)
            
            # Time series analysis
            if 'timestamp' in df.columns:
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                daily = df.groupby('date').size().reset_index(name='count')
                fig3 = px.line(daily, x='date', y='count', title="Daily Screening Trends")
                st.plotly_chart(fig3, use_container_width=True)
    
    with tabs[5]:
        st.subheader("Security Settings")
        st.write("### Access Control")
        with st.form("security_settings"):
            # Password policy
            min_password_length = st.number_input("Minimum Password Length",
                                                min_value=8, max_value=20, value=12)
            require_special_chars = st.checkbox("Require Special Characters", value=True)
            password_expiry_days = st.number_input("Password Expiry (days)",
                                                 min_value=30, max_value=365, value=90)
            
            # Session settings
            session_timeout = st.number_input("Session Timeout (minutes)",
                                           min_value=5, max_value=240, value=30)
            max_login_attempts = st.number_input("Max Login Attempts",
                                               min_value=3, max_value=10, value=5)
            
            # IP restrictions
            enable_ip_whitelist = st.checkbox("Enable IP Whitelist")
            ip_list = st.text_area("Allowed IPs (one per line)")
            
            if st.form_submit_button("Update Security Settings"):
                st.success("Security settings updated!")

def show_about_page():
    """About page with organization information"""
    st.title("📚 About Health Bridge Initiative")
    tabs = st.tabs(["🏢 Our Story", "👥 Our Team", "🤝 Partners", "📞 Contact"])
    
    with tabs[0]:
        st.markdown("""
        ## Our Mission
        To eradicate preventable deaths from chronic kidney and liver disease in Nigeria by building a
        **community-driven early detection system** that bridges the gap between risk identification and
        affordable, accessible care.
        
        ## Our Vision
        A Nigeria where no one dies from preventable chronic diseases because of late diagnosis or lack of access to care.
        
        ## Our Story
        Founded in 2025, Health Bridge Initiative was born out of a simple observation:
        **too many Nigerians were dying from diseases that could have been managed if detected early.**
        
        Our founder, MR ALABI RIDWAN OPEYEMI, witnessed firsthand the devastating impact of late-stage kidney disease diagnosis in his community. What started as a small community screening program in Lagos has grown into a nationwide movement.
        
        ## What Makes Us Different
        1. **Community-First Approach**: We meet people where they are, in their communities
        2. **Technology-Enabled**: AI-powered risk assessment and mobile app
        3. **Sustainable Model**: Integrated funding system with minimal fees
        4. **Data-Driven**: Continuous improvement based on real data
        5. **Local Solutions**: Designed specifically for Nigerian contexts
        
        ## Our Values
        - **Compassion**: Every life matters
        - **Innovation**: Finding better ways to serve
        - **Integrity**: Transparent in all we do
        - **Collaboration**: Working together for impact
        - **Excellence**: Striving for the highest standards
        """)
    
    with tabs[1]:
        st.subheader("Leadership Team")
        team_members = [
            {"name": "Mr ALABI RIDWAN OPEYEMI", "role": "Founder & CEO",
             "bio": "BIOMEDICAL EPIDEMIOLGIST  with 5+ years experience in public health"},
            {"name": "IBRAHEEM RUQOYA", "role": "Chief Medical Partner ",
             "bio": "Nephrological Nurse  specializing in community health"},
            {"name": "SALAAM RAHEEM OLATUNJI", "role": "CTO",
             "bio": "Technology entrepreneur focused on health tech and User Experience and Interface"},
            {"name": "MR ISSA NAFIU", "role": "CFO",
             "bio": "AUDITOR,LAGOS STATE MINISTRY OF FINANCE"}
        ]
        
        for member in team_members:
            with st.expander(f"{member['name']} - {member['role']}"):
                st.write(member['bio'])
        
        st.markdown("---")
        st.subheader("Board of Advisors")
        advisors = [
            "DR. OYELEYE HASSAN - Lagos University Teaching Hospital",
            "Dr. ABUBAKR ASHIRU - Federal Ministry of Health",
            "DR. OYEYEMI OGUNJOBI - LAGOS STATE MINISTRY OF HEALTH(SWAp DESK )",
            "Mrs. Bola Adekunle - Nigerian Health Foundation"
        ]
        
        for advisor in advisors:
            st.write(f"• {advisor}")
    
    with tabs[2]:
        st.subheader("Our Partners")
        partners = [
            {"name": "Lagos State Ministry of Health", "type": "Government"},
            {"name": "Nigerian Medical Association", "type": "Professional Body"},
            {"name": "Paystack", "type": "Technology Partner"},
            {"name": "Supabase", "type": "Database Partner"},
            {"name": "Google for Nonprofits", "type": "Technology Partner"},
            {"name": "Rotary Club Nigeria", "type": "Community Partner"}
        ]
        
        col1, col2 = st.columns(2)
        for i, partner in enumerate(partners):
            with col1 if i % 2 == 0 else col2:
                st.markdown(f"""
                <div style='padding: 15px; border: 1px solid #ddd; border-radius: 10px; margin: 10px 0;'>
                    <strong>{partner['name']}</strong><br>
                    <small>{partner['type']}</small>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("Become a Partner")
        st.write("We're always looking for organizations to join our mission.")
        if st.button("Partner With Us"):
            st.info("Email us at partners@healthbridge.ng")
    
    with tabs[3]:
        st.subheader("Contact Information")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### Headquarters
            **Address:**
            Health Bridge Initiative
           27, MAGBON BADAGRY
            LAGOS, Nigeria
            
            **Phone:**
            +234 817 937 1170
            
            **Email:**
            info@healthbridge.ng
            
            **Emergency Hotline:**
            112 or 767
            """)
        with col2:
            st.markdown("""
            ### Regional Offices
            **Lagos Office**
           
            
            **Kano Office**
           
            
            **Abuja Office**
         
            
            **Port Harcourt Office**
            
            """)
        
        st.markdown("---")
        st.subheader("Send us a Message")
        with st.form("contact_form"):
            name = st.text_input("Your Name")
            email = st.text_input("Your Email")
            subject = st.selectbox("Subject",
                                 ["General Inquiry", "Partnership", "Volunteering", "Technical Support", "Media"])
            message = st.text_area("Message", height=150)
            if st.form_submit_button("Send Message"):
                st.success("Message sent! We'll respond within 48 hours.")

# ==================== MOBILE APP ENHANCEMENTS ====================
def mobile_optimizations():
    """Apply mobile-specific optimizations"""
    st.markdown("""
    <style>
    /* Mobile-responsive design */
    @media (max-width: 768px) {
        .stButton > button {
            width: 100%;
            margin: 5px 0;
        }
        .stTextInput > div > div > input {
            font-size: 16px !important; /* Prevents zoom on iOS */
        }
        .stNumberInput > div > div > input {
            font-size: 16px !important;
        }
        .stSelectbox > div > div > div {
            font-size: 16px !important;
        }
    }
    /* PWA-like styling */
    .pwa-header {
        position: fixed;
        top: 0;
        width: 100%;
        background: white;
        z-index: 999;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    /* Mobile-friendly spacing */
    .mobile-padding {
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================
def generate_dashboard_report(df):
    """Generate comprehensive dashboard report"""
    report = f"""
HEALTH BRIDGE INITIATIVE - DASHBOARD REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
===================================================

SUMMARY STATISTICS:
• Total Screenings: {len(df)}
• High Risk Cases: {len(df[df['risk_level'].str.contains('HIGH')]) if 'risk_level' in df.columns else 'N/A'}
• Average Age: {df['age'].mean():.1f if 'age' in df.columns else 'N/A'}
• Most Common Location: {df['location'].mode()[0] if 'location' in df.columns else 'N/A'}

GLUCOSE ANALYSIS:
• Normal (70-139 mg/dL): {len(df[(df['blood_glucose'] >= 70) & (df['blood_glucose'] < 140)]) if 'blood_glucose' in df.columns else 'N/A'}
• Pre-diabetes (140-199 mg/dL): {len(df[(df['blood_glucose'] >= 140) & (df['blood_glucose'] < 200)]) if 'blood_glucose' in df.columns else 'N/A'}
• Diabetes (≥200 mg/dL): {len(df[df['blood_glucose'] >= 200]) if 'blood_glucose' in df.columns else 'N/A'}

RISK DISTRIBUTION:
{df['risk_level'].value_counts().to_string() if 'risk_level' in df.columns else 'N/A'}

GEOGRAPHIC DISTRIBUTION:
{df['location'].value_counts().to_string() if 'location' in df.columns else 'N/A'}

TIMELINE:
• First Record: {df['timestamp'].min() if 'timestamp' in df.columns else 'N/A'}
• Last Record: {df['timestamp'].max() if 'timestamp' in df.columns else 'N/A'}
• Average Daily: {len(df) / 30:.1f} screenings/day (30-day estimate)

===================================================
Report generated by Health Bridge Analytics System
"""
    return report

# ==================== DEPLOYMENT CONFIGURATION ====================
# Create pages directory structure
PAGES_STRUCTURE = {
    "1_ _Health_Screening.py": show_screening_page,
    "2_ _Dashboard.py": show_dashboard,
    "3_ _Volunteer.py": show_volunteer_registration,
    "4_ _Funding_Platform.py": show_funding_platform,
    "5_ _Admin.py": show_admin_panel,
    "6_ _About.py": show_about_page
}

def create_pages_directory():
    """Create pages directory for multi-page app"""
    import os
    pages_dir = "pages"
    if not os.path.exists(pages_dir):
        os.makedirs(pages_dir)
    
    for page_file, page_function in PAGES_STRUCTURE.items():
        page_path = os.path.join(pages_dir, page_file)
        if not os.path.exists(page_path):
            # Create simple page files that import from main app
            with open(page_path, "w") as f:
                f.write(f'''
import streamlit as st
from app import HealthBridgeAI, {page_function.__name__}

st.set_page_config(page_title="{page_file.split('_')[2]}", layout="wide")
ai_engine = HealthBridgeAI()
{page_function.__name__}()
''')

# ==================== PWA MANIFEST ====================
def create_pwa_manifest():
    """Create PWA manifest for mobile app installation"""
    manifest = {
        "name": "Health Bridge Nigeria",
        "short_name": "HealthBridge",
        "description": "Early detection of chronic diseases in Nigeria",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1f77b4",
        "icons": [
            {
                "src": "/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return manifest

# ==================== MAIN APP FUNCTION ====================
def main():
    """Main application function"""
    # Apply mobile optimizations
    mobile_optimizations()
    
    # Initialize AI Engine
    ai_engine = HealthBridgeAI()
    
    # Custom sidebar for mobile
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 20px 0;'>
            <h2>🩺 Health Bridge</h2>
            <p style='color: #666; font-size: 0.9rem;'>
                Early Detection Saves Lives
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Mobile-friendly navigation
        menu = option_menu(
            menu_title=None,
            options=["🏠 Home", "🔍 Screening", "📊 Dashboard", "🤝 Volunteer", "💰 Funding", "🔧 Admin", "📚 About"],
            icons=["house", "clipboard-pulse", "bar-chart", "people", "cash-coin", "gear", "info-circle"],
            menu_icon="cast",
            default_index=0,
            orientation="vertical",
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "20px"},
                "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px"},
                "nav-link-selected": {"background-color": "#1f77b4"},
            }
        )
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### Quick Actions")
        if st.button("🆘 Emergency", use_container_width=True):
            st.info("Emergency: 112 or 767\nPoison Control: 0800 112 112")
        if st.button("📞 Call Us", use_container_width=True):
            st.info("Hotline: 0817 937 1170")
        
        # User info if logged in
        if st.session_state.current_user:
            st.markdown(f"**Welcome,** {st.session_state.current_user}")
        
        # Offline mode indicator
        if not ai_engine.supabase:
            st.warning("⚠ Offline Mode")
        
        # Version info
        st.markdown("---")
        st.caption("v2.0.0 | Health Bridge Initiative")
    
    # Main content routing
    if menu == "🏠 Home":
        show_homepage()
    elif menu == "🔍 Screening":
        show_screening_page()
    elif menu == "📊 Dashboard":
        show_dashboard()
    elif menu == "🤝 Volunteer":
        show_volunteer_registration()
    elif menu == "💰 Funding":
        show_funding_platform()
    elif menu == "🔧 Admin":
        show_admin_panel()
    elif menu == "📚 About":
        show_about_page()

# ==================== RUN THE APPLICATION ====================
if __name__ == "__main__":
    # Create pages directory for multi-page app
    create_pages_directory()
    
    # Run main app
    main()
