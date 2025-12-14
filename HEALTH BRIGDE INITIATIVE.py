import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import hashlib

# Page configuration
st.set_page_config(
    page_title="Health Bridge Initiative",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'screening_data' not in st.session_state:
    st.session_state.screening_data = []
if 'annotation_data' not in st.session_state:
    st.session_state.annotation_data = []
if 'funding_requests' not in st.session_state:
    st.session_state.funding_requests = []


class HealthBridgeAI:
    def __init__(self):
        self.load_facilities()
        self.load_guidelines()

    def load_facilities(self):
        """Load healthcare facilities database"""
        self.facilities = {
            'Lagos': [
                {'name': 'Lagos University Teaching Hospital (LUTH)', 'type': 'Tertiary',
                 'specialty': 'Nephrology', 'location': 'Idi-Araba', 'contact': '01-3423456'},
                {'name': 'Badagry General Hospital', 'type': 'Secondary',
                 'specialty': 'General Medicine', 'location': 'Badagry', 'contact': '09012345678'},
                {'name': 'Amuwo Odofin Maternal & Child Centre', 'type': 'Secondary',
                 'specialty': 'Maternal & Child Health', 'location': 'Festac', 'contact': '01-3425678'}
            ],
            'Kano': [
                {'name': 'Aminu Kano Teaching Hospital', 'type': 'Tertiary',
                 'specialty': 'Nephrology', 'location': 'Kano', 'contact': '064-981234'}
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

        # Blood Glucose assessment - USING mg/dL
        # mmol/L to mg/dL conversion: 7.0 mmol/L = 126 mg/dL, 11.1 mmol/L = 200 mg/dL
        if data['random_glucose'] >= 200:  # Diabetes threshold in mg/dL
            score += 2
            risk_factors.append(f"High diabetes risk (Glucose: {data['random_glucose']} mg/dL)")
        elif data['random_glucose'] >= 126:  # Pre-diabetes threshold in mg/dL
            score += 1
            risk_factors.append(f"Elevated glucose (Glucose: {data['random_glucose']} mg/dL)")

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

        # BMI
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

        # Determine Risk Level
        if score >= 5:
            risk_level = "🔴 HIGH RISK"
            recommendation = "Urgent referral to specialist required"
            timeline = "Within 1 week"
        elif score >= 3:
            risk_level = "🟡 MODERATE RISK"
            recommendation = "Refer to healthcare facility for evaluation"
            timeline = "Within 1 month"
        else:
            risk_level = "🟢 LOW RISK"
            recommendation = "Lifestyle advice and monthly screening"
            timeline = "Monthly checkup"

        return {
            'risk_level': risk_level,
            'score': score,
            'risk_factors': risk_factors,
            'recommendation': recommendation,
            'timeline': timeline
        }

    def generate_referral(self, data, risk_assessment):
        """Generate referral information"""
        location = data.get('location', 'Lagos')
        available_facilities = self.facilities.get(location, self.facilities['Lagos'])

        if "HIGH RISK" in risk_assessment['risk_level']:
            facility_type = "Tertiary"
        else:
            facility_type = "Secondary"

        suitable_facilities = [
            f for f in available_facilities
            if f['type'] == facility_type or facility_type == "Tertiary"
        ][:2]

        return {
            'patient_id': hashlib.md5(f"{data['name']}{datetime.now()}".encode()).hexdigest()[:8],
            'suggested_facilities': suitable_facilities,
            'referral_date': datetime.now().strftime("%Y-%m-%d"),
            'follow_up_required': "HIGH RISK" in risk_assessment['risk_level']
        }

    def provide_health_advice(self, risk_factors):
        """Generate personalized health advice"""
        advice = []

        if any("hypertension" in factor.lower() for factor in risk_factors):
            advice.extend([
                "• Reduce salt intake to less than 5g per day",
                "• Increase consumption of fruits and vegetables",
                "• Exercise for 30 minutes most days",
                "• Limit alcohol consumption"
            ])

        if any("diabetes" in factor.lower() or "glucose" in factor.lower() for factor in risk_factors):
            advice.extend([
                "• Reduce sugar and refined carbohydrate intake",
                "• Choose whole grains over processed foods",
                "• Monitor blood sugar levels regularly",
                "• Maintain healthy body weight"
            ])

        if any("protein" in factor.lower() for factor in risk_factors):
            advice.extend([
                "• Drink adequate water (unless advised otherwise)",
                "• Avoid painkillers like ibuprofen without prescription",
                "• Control blood pressure and blood sugar strictly",
                "• Regular kidney function tests recommended"
            ])

        # General advice
        advice.extend([
            "• Avoid smoking and tobacco products",
            "• Get 7-8 hours of sleep nightly",
            "• Manage stress through relaxation techniques",
            "• Regular health check-ups are important"
        ])

        return advice


def main():
    # Initialize AI Engine
    ai_engine = HealthBridgeAI()

    # Sidebar Navigation
    st.sidebar.image("https://img.icons8.com/color/96/000000/health-book.png", width=100)
    st.sidebar.title("🩺 Health Bridge Initiative")

    menu = st.sidebar.selectbox(
        "Navigation",
        ["🏠 Home", "🔍 Health Screening", "📊 Dashboard", "🤖 AI Training",
         "💰 Funding Platform", "🏥 Facility Network", "📚 About"]
    )

    # Main Content Area
    if menu == "🏠 Home":
        show_homepage()

    elif menu == "🔍 Health Screening":
        show_screening_page(ai_engine)

    elif menu == "📊 Dashboard":
        show_dashboard(ai_engine)

    elif menu == "🤖 AI Training":
        show_ai_training_page(ai_engine)

    elif menu == "💰 Funding Platform":
        show_funding_platform()

    elif menu == "🏥 Facility Network":
        show_facility_network(ai_engine)

    elif menu == "📚 About":
        show_about_page()


def show_homepage():
    """Display homepage with mission and overview"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div style='text-align: center;'>
            <h1>🌉 Health Bridge Initiative</h1>
            <h3 style='color: #1f77b4;'>Building Nigeria's Shield Against Silent Epidemics</h3>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Mission Statement
    st.markdown("""
    ### 🎯 Our Mission
    To eradicate preventable deaths from chronic kidney and liver disease in Nigeria by building a 
    **community-driven early detection system** that bridges the gap between risk identification and 
    affordable, accessible care.
    """)

    # Three Pillars
    st.markdown("### 🌟 Our Three-Pillar Approach")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4;'>
            <h4>🔍 Community Screening</h4>
            <p>Monthly free health camps in underserved communities using simple, affordable tools:</p>
            <ul>
                <li>Blood Pressure Monitoring</li>
                <li>Urine Dipstick Tests</li>
                <li>Blood Glucose Testing</li>
                <li>BMI Calculation</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #ff7f0e;'>
            <h4>🤖 AI-Powered Navigation</h4>
            <p>Intelligent guidance system that provides:</p>
            <ul>
                <li>Instant risk assessment</li>
                <li>Local language support (Yoruba, Hausa, Igbo)</li>
                <li>Smart referrals to verified facilities</li>
                <li>Personalized health advice</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 5px solid #2ca02c;'>
            <h4>💰 Sustainable Funding</h4>
            <p>Integrated financial support system:</p>
            <ul>
                <li>Crowdfunding platform (1% fee)</li>
                <li>Health resilience bonds</li>
                <li>Partnership with health insurance</li>
                <li>Preventive care financing</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # Impact Metrics
    st.markdown("---")
    st.markdown("### 📈 Our Impact Goals")

    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)

    with metrics_col1:
        st.metric("Target Screened", "10,000", "by Dec 2026")

    with metrics_col2:
        st.metric("Early Detection Rate", "50% ↑", "vs current 20%")

    with metrics_col3:
        st.metric("Cost Savings", "₦500M", "in prevented dialysis")

    with metrics_col4:
        st.metric("Communities Reached", "25+", "across Lagos")

    # Call to Action
    st.markdown("---")
    st.markdown("""
    <div style='background-color: #e6f7ff; padding: 30px; border-radius: 10px; text-align: center;'>
        <h3>🚀 Join Our Movement</h3>
        <p>Be part of Nigeria's health revolution. Whether as a volunteer, partner, or donor, 
        your contribution builds a healthier future for all.</p>
        <button style='background-color: #1f77b4; color: white; padding: 10px 30px; 
        border: none; border-radius: 5px; font-size: 16px; cursor: pointer;'>
        Get Involved Today</button>
    </div>
    """, unsafe_allow_html=True)


def show_screening_page(ai_engine):
    """Interactive health screening interface"""
    st.title("🔍 Community Health Screening")

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Screening Form", "📊 Risk Assessment", "🏥 Referral", "💡 Health Advice"])

    with tab1:
        with st.form("screening_form"):
            st.subheader("Personal Information")

            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name*")
                age = st.number_input("Age*", min_value=1, max_value=120, value=30)
                phone = st.text_input("Phone Number*")

            with col2:
                location = st.selectbox("Location*", ["Lagos", "Kano", "Ogun", "Oyo", "Others"])
                language = st.selectbox("Preferred Language", ["English", "Yoruba", "Hausa", "Igbo", "Pidgin"])
                sex = st.selectbox("Sex*", ["Male", "Female"])

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
                weight = st.number_input("Weight (kg)", min_value=20.0, max_value=200.0, value=70.0, step=0.1)
                height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
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

            submitted = st.form_submit_button("🚀 Analyze My Health Risk")

            if submitted and name and phone:
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
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                st.session_state.screening_data.append(screening_data)
                st.success("✅ Screening data submitted successfully!")
                st.rerun()

    if st.session_state.screening_data:
        latest_data = st.session_state.screening_data[-1]

        with tab2:
            st.subheader("🎯 Risk Assessment Results")

            # Calculate risk
            risk_assessment = ai_engine.calculate_kidney_risk(latest_data)

            # Display risk level with color coding
            risk_color = {
                "🔴 HIGH RISK": "red",
                "🟡 MODERATE RISK": "orange",
                "🟢 LOW RISK": "green"
            }

            st.markdown(f"""
            <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid {risk_color.get(risk_assessment["risk_level"].split()[0], "gray")};'>
                <h2 style='color: {risk_color.get(risk_assessment["risk_level"].split()[0], "black")};'>
                    {risk_assessment["risk_level"]}
                </h2>
                <p><strong>Risk Score:</strong> {risk_assessment['score']:.1f}/10</p>
                <p><strong>Recommendation:</strong> {risk_assessment['recommendation']}</p>
                <p><strong>Timeline:</strong> {risk_assessment['timeline']}</p>
            </div>
            """, unsafe_allow_html=True)

            # Risk factors
            st.subheader("⚠️ Identified Risk Factors")
            if risk_assessment['risk_factors']:
                for factor in risk_assessment['risk_factors']:
                    st.write(f"• {factor}")
            else:
                st.write("No significant risk factors identified")

            # Visual risk chart
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=risk_assessment['score'],
                title={'text': "Risk Score"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [None, 10]},
                    'bar': {'color': risk_color.get(risk_assessment["risk_level"].split()[0], "gray")},
                    'steps': [
                        {'range': [0, 3], 'color': "lightgreen"},
                        {'range': [3, 5], 'color': "lightyellow"},
                        {'range': [5, 10], 'color': "lightcoral"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 5
                    }
                }
            ))
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("🏥 Referral Information")

            referral = ai_engine.generate_referral(latest_data, risk_assessment)

            st.markdown(f"""
            <div style='background-color: #e8f4f8; padding: 20px; border-radius: 10px;'>
                <h4>📋 Referral Slip</h4>
                <p><strong>Patient ID:</strong> {referral['patient_id']}</p>
                <p><strong>Date:</strong> {referral['referral_date']}</p>
                <p><strong>Priority:</strong> {"URGENT" if referral['follow_up_required'] else "ROUTINE"}</p>
            </div>
            """, unsafe_allow_html=True)

            st.subheader("📍 Recommended Healthcare Facilities")

            for i, facility in enumerate(referral['suggested_facilities'], 1):
                st.markdown(f"""
                <div style='background-color: #f0f8ff; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #1f77b4;'>
                    <h5>{i}. {facility['name']}</h5>
                    <p><strong>Type:</strong> {facility['type']} | <strong>Specialty:</strong> {facility['specialty']}</p>
                    <p><strong>Location:</strong> {facility['location']}</p>
                    <p><strong>Contact:</strong> {facility['contact']}</p>
                </div>
                """, unsafe_allow_html=True)

            # Generate printable referral
            if st.button("🖨️ Generate Printable Referral Slip"):
                referral_text = f"""
                HEALTH BRIDGE INITIATIVE - REFERRAL SLIP
                Patient: {latest_data['name']}
                Patient ID: {referral['patient_id']}
                Date: {referral['referral_date']}
                Risk Level: {risk_assessment['risk_level']}

                Recommended Facilities:
                """
                for facility in referral['suggested_facilities']:
                    referral_text += f"\n- {facility['name']} ({facility['type']})"
                    referral_text += f"\n  Location: {facility['location']}"
                    referral_text += f"\n  Contact: {facility['contact']}"

                st.download_button(
                    label="📥 Download Referral Slip",
                    data=referral_text,
                    file_name=f"referral_{referral['patient_id']}.txt",
                    mime="text/plain"
                )

        with tab4:
            st.subheader("💡 Personalized Health Advice")

            advice = ai_engine.provide_health_advice(risk_assessment['risk_factors'])

            st.markdown("""
            <div style='background-color: #f0fff0; padding: 20px; border-radius: 10px;'>
                <h4>Based on your screening results:</h4>
            </div>
            """, unsafe_allow_html=True)

            for item in advice:
                st.write(item)

            # Language toggle for advice
            if latest_data['language'] != 'English':
                st.info(f"💬 This advice is available in {latest_data['language']}. Switch language in settings.")

            # Additional resources
            with st.expander("📚 Additional Health Resources"):
                st.write("""
                - **Nutrition Guide:** Download our free healthy eating guide
                - **Exercise Plans:** Simple 30-minute workout routines
                - **Medication Tracker:** Keep track of your medications
                - **Support Groups:** Connect with others managing similar conditions
                """)

            # Funding eligibility check
            if "HIGH RISK" in risk_assessment['risk_level']:
                st.markdown("""
                <div style='background-color: #fffacd; padding: 15px; border-radius: 8px; margin: 10px 0;'>
                    <h5>💰 Financial Assistance Available</h5>
                    <p>You may be eligible for our health funding support program.</p>
                </div>
                """, unsafe_allow_html=True)

                if st.button("Learn About Funding Options"):
                    st.switch_page("💰 Funding Platform")


def show_dashboard(ai_engine):
    """Analytics dashboard for the initiative"""
    st.title("📊 Health Bridge Dashboard")

    if not st.session_state.screening_data:
        st.info("No screening data available yet. Start with the Health Screening page.")
        return

    df = pd.DataFrame(st.session_state.screening_data)

    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Screened", len(df))

    with col2:
        high_risk = sum(1 for data in st.session_state.screening_data
                        if ai_engine.calculate_kidney_risk(data)['score'] >= 5)
        st.metric("High Risk Cases", high_risk)

    with col3:
        avg_age = df['age'].mean()
        st.metric("Average Age", f"{avg_age:.1f}")

    with col4:
        hypertension_rate = (df['systolic_bp'] >= 140).mean() * 100
        st.metric("Hypertension Rate", f"{hypertension_rate:.1f}%")

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        # Risk Distribution
        risk_levels = []
        for data in st.session_state.screening_data:
            risk = ai_engine.calculate_kidney_risk(data)['risk_level'].split()[0]
            risk_levels.append(risk)

        risk_df = pd.DataFrame({'Risk Level': risk_levels})
        risk_counts = risk_df['Risk Level'].value_counts()

        fig1 = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title="Risk Level Distribution",
            color_discrete_sequence=['green', 'orange', 'red']
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        # Age vs Blood Pressure
        fig2 = px.scatter(
            df, x='age', y='systolic_bp',
            color=df['systolic_bp'].apply(lambda x: 'Normal' if x < 140 else 'High'),
            title="Age vs Blood Pressure",
            labels={'systolic_bp': 'Systolic BP', 'age': 'Age'},
            color_discrete_map={'Normal': 'green', 'High': 'red'}
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Data Table
    st.subheader("📋 Screening Records")
    display_df = df[['name', 'age', 'location', 'systolic_bp', 'diastolic_bp', 'urine_protein']].copy()
    display_df['Risk Level'] = [ai_engine.calculate_kidney_risk(data)['risk_level'].split()[0]
                                for data in st.session_state.screening_data]
    st.dataframe(display_df, use_container_width=True)

    # Export data
    if st.button("📥 Export Data as pdf"):
        pdf = df.to_pdf(index=False)
        st.download_button(
            label="Download pdf",
            data=pdf,
            file_name="health_screening_data.pdf",
            mime="text/pdf"
        )


def show_ai_training_page(ai_engine):
    """Interface for human annotation and AI training"""
    st.title("🤖 AI Training & Annotation Hub")

    st.markdown("""
    <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4>🧠 Sentinel Learning Hub</h4>
        <p>Help train our AI by reviewing and annotating screening cases. Your expertise makes our AI smarter and more accurate for Nigerian healthcare contexts.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📝 Annotate Cases", "📊 Annotation Progress", "🎓 Training Guide"])

    with tab1:
        if st.session_state.screening_data:
            st.subheader("Cases Needing Annotation")

            # Select a case to annotate
            case_options = [f"{i + 1}: {data['name']} ({data['age']}y)"
                            for i, data in enumerate(st.session_state.screening_data)]
            selected_case = st.selectbox("Select a case to annotate:", case_options)
            case_index = int(selected_case.split(":")[0]) - 1

            if case_index < len(st.session_state.screening_data):
                case_data = st.session_state.screening_data[case_index]

                # Display case information
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Patient Info:**
                    - Name: {case_data['name']}
                    - Age: {case_data['age']}
                    - Location: {case_data['location']}
                    """)

                with col2:
                    st.markdown(f"""
                    **Vital Signs:**
                    - BP: {case_data['systolic_bp']}/{case_data['diastolic_bp']}
                    - Urine Protein: {case_data['urine_protein']}
                    - Glucose: {case_data.get('blood_glucose', 'N/A')}
                    """)

                # AI's initial assessment
                ai_assessment = ai_engine.calculate_kidney_risk(case_data)
                st.markdown(f"""
                <div style='background-color: #fffaf0; padding: 15px; border-radius: 8px;'>
                    <h5>🤖 AI's Initial Assessment</h5>
                    <p><strong>Risk Level:</strong> {ai_assessment['risk_level']}</p>
                    <p><strong>Identified Factors:</strong> {', '.join(ai_assessment['risk_factors'])}</p>
                </div>
                """, unsafe_allow_html=True)

                # Annotation interface
                st.subheader("📝 Your Annotation")

                with st.form("annotation_form"):
                    st.markdown("**Review AI Assessment:**")

                    accuracy = st.slider(
                        "How accurate is the AI's assessment?",
                        0, 100, 80,
                        help="0 = Completely wrong, 100 = Perfectly accurate"
                    )

                    corrections = st.text_area(
                        "Corrections or additional insights:",
                        placeholder="E.g., 'Consider also checking for liver enzymes due to herbal medicine use history...'",
                        height=100
                    )

                    severity_adjustment = st.selectbox(
                        "Adjust risk severity if needed:",
                        ["No change", "Increase severity", "Decrease severity"]
                    )

                    tags = st.multiselect(
                        "Add relevant medical tags:",
                        ["Hypertension", "Diabetes", "Obesity", "Herbal Toxicity",
                         "Family History", "Elderly", "Smoking", "Alcohol Use"]
                    )

                    confidence = st.slider(
                        "Your confidence in this annotation:",
                        0, 100, 90,
                        help="How confident are you in your assessment?"
                    )

                    submitted = st.form_submit_button("✅ Submit Annotation")

                    if submitted:
                        annotation = {
                            'case_id': case_index,
                            'case_data': case_data,
                            'ai_assessment': ai_assessment,
                            'accuracy_score': accuracy,
                            'corrections': corrections,
                            'severity_adjustment': severity_adjustment,
                            'tags': tags,
                            'confidence': confidence,
                            'annotator': 'Health Professional',
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        st.session_state.annotation_data.append(annotation)
                        st.success("✅ Annotation submitted! Thank you for improving our AI.")

                        # Show next case
                        st.rerun()
        else:
            st.info("No screening cases available for annotation. Please complete some screenings first.")

    with tab2:
        st.subheader("Annotation Progress & Quality")

        if st.session_state.annotation_data:
            ann_df = pd.DataFrame(st.session_state.annotation_data)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Annotations", len(ann_df))
                avg_accuracy = ann_df['accuracy_score'].mean()
                st.metric("Average AI Accuracy", f"{avg_accuracy:.1f}%")

            with col2:
                avg_confidence = ann_df['confidence'].mean()
                st.metric("Annotator Confidence", f"{avg_confidence:.1f}%")

                corrections_count = ann_df['corrections'].str.strip().ne('').sum()
                st.metric("Cases Corrected", corrections_count)

            # Quality metrics
            st.subheader("📈 Quality Metrics")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(ann_df['timestamp']),
                y=ann_df['accuracy_score'],
                mode='lines+markers',
                name='AI Accuracy'
            ))
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(ann_df['timestamp']),
                y=ann_df['confidence'],
                mode='lines+markers',
                name='Annotator Confidence'
            ))
            fig.update_layout(
                title="Annotation Quality Over Time",
                xaxis_title="Date",
                yaxis_title="Score (%)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # Export annotations
            if st.button("📥 Export Annotations for Training"):
                export_data = []
                for ann in st.session_state.annotation_data:
                    export_data.append({
                        'case_id': ann['case_id'],
                        'ai_risk_level': ann['ai_assessment']['risk_level'],
                        'accuracy_score': ann['accuracy_score'],
                        'corrections': ann['corrections'],
                        'tags': ', '.join(ann['tags']),
                        'confidence': ann['confidence']
                    })

                export_df = pd.DataFrame(export_data)
                csv = export_df.to_csv(index=False)
                st.download_button(
                    label="Download Training Data",
                    data=csv,
                    file_name="ai_training_annotations.csv",
                    mime="text/csv"
                )
        else:
            st.info("No annotations submitted yet. Start annotating in the first tab.")

    with tab3:
        st.subheader("🎓 Annotation Guidelines")

        st.markdown("""
        ### How to Provide Quality Annotations

        **1. Review AI Assessment:**
        - Check if all risk factors are correctly identified
        - Verify the severity assessment
        - Consider cultural and contextual factors

        **2. Provide Specific Corrections:**
        - Be specific about what needs correction
        - Provide medical reasoning for changes
        - Suggest additional tests if needed

        **3. Tag Appropriately:**
        - Use relevant medical tags
        - Add new tags if common conditions are missing
        - Consider socio-economic factors

        **4. Quality Standards:**
        - Only annotate cases you're confident about
        - If unsure, mark confidence lower
        - Provide constructive feedback

        ### Why Your Annotations Matter

        Each annotation helps:
        - Improve AI accuracy for Nigerian patients
        - Reduce healthcare disparities
        - Build better tools for community health workers
        - Create a unique Nigerian medical AI dataset

        ### Micropayment Program

        High-quality annotators can earn:
        - ₦50-₦200 per verified annotation batch
        - Bonus for consistent high-quality work
        - Opportunities for advanced training
        """)

        st.info("💼 Join our Annotator Network: Contact us at annotators@healthbridge.ng")


def show_funding_platform():
    """Crowdfunding platform for health needs"""
    st.title("💰 Health Bridge Funding Platform")

    st.markdown("""
    <div style='background-color: #f0fff0; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4>🌉 Bridging the Financial Gap in Healthcare</h4>
        <p>Our platform connects patients in need with compassionate donors. With only <strong>1% platform fee</strong>, 
        we ensure maximum funds go directly to medical treatment.</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Active Campaigns", "🎗️ Start a Campaign", "📊 Funding Dashboard"])

    with tab1:
        st.subheader("Active Funding Campaigns")

        # Sample campaigns (in real app, this would come from database)
        campaigns = [
            {
                'name': 'Kidney Transplant for Mr. Ade',
                'goal': 15000000,
                'raised': 5200000,
                'days_left': 45,
                'description': 'Father of 3 needs life-saving transplant',
                'verified': True,
                'urgency': 'High'
            },
            {
                'name': 'Dialysis Support Group',
                'goal': 5000000,
                'raised': 2500000,
                'days_left': 30,
                'description': 'Monthly dialysis for 5 patients',
                'verified': True,
                'urgency': 'Medium'
            },
            {
                'name': 'Children Liver Care',
                'goal': 8000000,
                'raised': 1800000,
                'days_left': 60,
                'description': 'Liver treatment for children in Badagry',
                'verified': True,
                'urgency': 'High'
            }
        ]

        for campaign in campaigns:
            progress = (campaign['raised'] / campaign['goal']) * 100

            st.markdown(f"""
            <div style='background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px;'>
                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <h5>{campaign['name']} {"✅" if campaign['verified'] else "⏳"}</h5>
                    <span style='background-color: {'#ffcccc' if campaign['urgency'] == 'High' else '#fffacd'}; 
                    padding: 5px 10px; border-radius: 15px; font-size: 12px;'>
                    {campaign['urgency']} URGENCY</span>
                </div>
                <p>{campaign['description']}</p>

                <div style='margin: 15px 0;'>
                    <div style='background-color: #e0e0e0; height: 10px; border-radius: 5px;'>
                        <div style='background-color: #4CAF50; width: {progress}%; height: 100%; border-radius: 5px;'></div>
                    </div>
                    <div style='display: flex; justify-content: space-between; margin-top: 5px;'>
                        <span>₦{campaign['raised']:,.0f} raised</span>
                        <span>{progress:.1f}%</span>
                        <span>Goal: ₦{campaign['goal']:,.0f}</span>
                    </div>
                </div>

                <div style='display: flex; justify-content: space-between; align-items: center;'>
                    <span>⏰ {campaign['days_left']} days left</span>
                    <button style='background-color: #1f77b4; color: white; padding: 8px 20px; 
                    border: none; border-radius: 5px; cursor: pointer;'>
                    Donate Now</button>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab2:
        st.subheader("Start a New Funding Campaign")

        with st.form("campaign_form"):
            st.markdown("### Campaign Details")

            campaign_name = st.text_input("Campaign Title*")
            patient_name = st.text_input("Patient Name*")
            relationship = st.selectbox("Your Relationship to Patient",
                                        ["Self", "Family Member", "Friend", "Healthcare Provider"])

            col1, col2 = st.columns(2)
            with col1:
                treatment_type = st.selectbox("Treatment Type*",
                                              ["Kidney Transplant", "Dialysis", "Liver Treatment",
                                               "Cancer Therapy", "Surgery", "Medication"])
                goal_amount = st.number_input("Funding Goal (₦)*", min_value=100000,
                                              max_value=50000000, value=5000000, step=100000)

            with col2:
                timeline = st.number_input("Timeline (days)", min_value=7, max_value=365, value=60)
                hospital = st.text_input("Treating Hospital")

            medical_description = st.text_area("Medical Situation*", height=150,
                                               placeholder="Describe the medical condition, treatment needed, and why funding is required...")

            # Document upload (simulated)
            st.markdown("### Verification Documents")
            st.info("For security, documents will be verified offline. Our team will contact you.")

            col3, col4 = st.columns(2)
            with col3:
                st.checkbox("Medical report available")
                st.checkbox("Hospital estimate provided")

            with col4:
                st.checkbox("Patient consent obtained")
                st.checkbox("Identity verification ready")

            terms = st.checkbox("I agree to the 1% platform fee and terms of service*")

            submitted = st.form_submit_button("🚀 Launch Campaign")

            if submitted and campaign_name and patient_name and medical_description and terms:
                st.success("✅ Campaign submitted for verification!")
                st.info(
                    "Our team will review your application within 24-48 hours and contact you for document verification.")

    with tab3:
        st.subheader("Funding Platform Dashboard")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Raised", "₦9,500,000", "+12% this month")

        with col2:
            st.metric("Active Campaigns", "15", "3 new this week")

        with col3:
            st.metric("Donors", "342", "+28 this month")

        with col4:
            st.metric("Success Rate", "78%", "of campaigns fully funded")

        st.markdown("---")

        # Platform fee transparency
        st.markdown("""
        <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px;'>
            <h5>💎 Platform Fee Transparency</h5>
            <p>We charge only <strong>1% platform fee</strong> to cover:</p>
            <ul>
                <li>Payment processing costs</li>
                <li>Campaign verification</li>
                <li>Platform maintenance</li>
                <li>Customer support</li>
            </ul>
            <p><em>Compared to industry standard of 5-10%</em></p>
        </div>
        """, unsafe_allow_html=True)


def show_facility_network(ai_engine):
    """Healthcare facility directory and network"""
    st.title("🏥 Healthcare Facility Network")

    st.markdown("""
    <div style='background-color: #f0f8ff; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h4>🔗 Our Verified Healthcare Partners</h4>
        <p>We partner with healthcare facilities across Nigeria to ensure our referrals lead to quality care.</p>
    </div>
    """, unsafe_allow_html=True)

    # Search and filter
    col1, col2, col3 = st.columns(3)

    with col1:
        location_filter = st.selectbox("Filter by Location",
                                       ["All Locations", "Lagos", "Kano", "Ogun", "Oyo"])

    with col2:
        facility_type = st.selectbox("Facility Type",
                                     ["All Types", "Tertiary", "Secondary", "Primary"])

    with col3:
        specialty_filter = st.selectbox("Specialty",
                                        ["All Specialties", "Nephrology", "General Medicine",
                                         "Maternal & Child Health"])

    # Display facilities
    st.subheader("📍 Available Facilities")

    all_facilities = []
    for location, facilities in ai_engine.facilities.items():
        for facility in facilities:
            facility['state'] = location
            all_facilities.append(facility)

    # Apply filters
    filtered_facilities = all_facilities

    if location_filter != "All Locations":
        filtered_facilities = [f for f in filtered_facilities if f['state'] == location_filter]

    if facility_type != "All Types":
        filtered_facilities = [f for f in filtered_facilities if f['type'] == facility_type]

    if specialty_filter != "All Specialties":
        filtered_facilities = [f for f in filtered_facilities if f['specialty'] == specialty_filter]

    # Display facilities in cards
    for facility in filtered_facilities:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"""
            <div style='background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 15px;'>
                <h5>{facility['name']}</h5>
                <p><strong>Type:</strong> {facility['type']} | <strong>Specialty:</strong> {facility['specialty']}</p>
                <p><strong>Location:</strong> {facility['location']}, {facility['state']}</p>
                <p><strong>Contact:</strong> {facility['contact']}</p>
                <p style='color: #666; font-size: 14px;'>✅ Verified Partner | 📞 24/7 Emergency Contact Available</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button("Get Directions", key=f"dir_{facility['name']}"):
                st.info(f"Directions to {facility['name']} would open in maps app")

            if st.button("Book Appointment", key=f"book_{facility['name']}"):
                st.info(f"Appointment booking system coming soon!")

    # Partnership information
    with st.expander("🤝 Become a Partner Facility"):
        st.markdown("""
        ### Join Our Network

        **Benefits for Healthcare Facilities:**
        - Increased patient referrals
        - Quality assurance recognition
        - Access to community health data
        - Partnership with innovative health initiative

        **Requirements:**
        - Valid medical practice license
        - Quality care standards
        - Transparent pricing
        - Willingness to provide pro bono cases

        **Application Process:**
        1. Submit facility details
        2. Quality assessment visit
        3. Agreement signing
        4. Onboarding to our referral system

        [Apply here: partnerships@healthbridge.ng]
        """)


def show_about_page():
    """About page with mission, team, and contact"""
    st.title("📚 About Health Bridge Initiative")

    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Our Story", "👥 Our Team", "📞 Contact", "📰 News & Updates"])

    with tab1:
        st.markdown("""
        ### Our Origin Story

        The Health Bridge Initiative was born from personal tragedy and transformed into a mission for systemic change.

        In 2019, our founder **Alabi Ridwan Opeyemi** lost his father to kidney disease. The proposed transplant was financially out of reach—a story familiar to thousands of Nigerian families. This preventable loss revealed a systemic failure: the absence of early detection systems at the primary healthcare level.

        ### Our Vision

        We envision a Nigeria where:
        - **No family** faces catastrophic health expenditures
        - **Every Nigerian** has access to early disease detection
        - **Healthcare** is preventive, not just reactive
        - **Technology** bridges gaps in healthcare delivery

        ### Our Approach

        **1. Community-First Design:**
        We work WITH communities, not FOR them. Our model is co-created with local leaders, ensuring cultural relevance and sustainability.

        **2. Technology as an Enabler:**
        Our AI tools are designed for Nigeria—working offline, in local languages, on basic smartphones.

        **3. Sustainable Finance:**
        We're building a model that moves beyond donor dependency through innovative financing like health resilience bonds.

        ### Our Impact Goals (2025-2027)

        | Goal | Target | Progress |
        |------|--------|----------|
        | People Screened | 50,000 | 400 (Dec 2025 Pilot) |
        | Early Detection Rate | 50% increase | In progress |
        | Healthcare Cost Savings | ₦500M | Tracked |
        | Communities Reached | 25+ | 1 (Badagry) |
        | AI Training Data | 10,000 annotated cases | Collecting |

        ### Our Values

        - **Empathy:** We remember why we started
        - **Innovation:** We build solutions for our context
        - **Integrity:** We are transparent in all we do
        - **Collaboration:** We are stronger together
        - **Sustainability:** We build for the long term
        """)

    with tab2:
        st.subheader("👥 Meet Our Team")

        team_members = [
            {"name": "Alabi Ridwan Opeyemi", "role": "Founder & CEO",
             "bio": "Presidential Health Fellow, Public Health Innovator", "img": "👨‍⚕️"},
            {"name": "Salam Raheem Olatunji", "role": "CTO",
             "bio": "LEAD, UI/UX PANDAR", "img": "👨‍⚕️"},
            {"name": "Mr. Tijani Sodiq", "role": "Research & Development Lead",
             "bio": "Health Systems Strategist", "img": "🔬"},
            {"name": "Mr. Nafiu Issa", "role": "Financial & Regulatory Advisor",
             "bio": "Financial Compliance Expert", "img": "💰"},
            {"name": "Mr. Babajide Kayode", "role": "Technical & Procurement Lead",
             "bio": "Supply Chain & Technology Specialist", "img": "💻"},
            {"name": "Imam Sodiq Oloyede", "role": "Community & Religious Advisor",
             "bio": "Community Mobilization Expert", "img": "🕌"},
            {"name": "Ms. Taiwo Oni", "role": "Secretary & Social Media Manager",
             "bio": "Community Health Organizer", "img": "📋"},
            {"name": "Amotu Rahman Clinic", "role": "Medical Partner & Volunteer Coordinator",
             "bio": "Clinical Excellence & Quality Care", "img": "🏥"}
        ]

        # Display team in columns
        cols = st.columns(3)
        for i, member in enumerate(team_members):
            with cols[i % 3]:
                st.markdown(f"""
                <div style='text-align: center; padding: 15px; border-radius: 10px; background-color: #f8f9fa; margin-bottom: 20px;'>
                    <div style='font-size: 48px; margin-bottom: 10px;'>{member['img']}</div>
                    <h5>{member['name']}</h5>
                    <p style='color: #1f77b4; font-weight: bold;'>{member['role']}</p>
                    <p style='font-size: 14px; color: #666;'>{member['bio']}</p>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("### 🤝 Join Our Team")
        st.info("We're always looking for passionate individuals. Send your CV to: careers@healthbridge.ng")

    with tab3:
        st.subheader("📞 Contact Us")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### 📍 Headquarters
            **Health Bridge Initiative**  
            Badagry, Lagos State  
            Nigeria

            ### 📱 Contact Information
            **Phone:** +234 817 937 1170  
            **Email:** info@healthbridge.ng  
            **Website:** www.healthbridge.ng (Coming Soon)

            ### 🕒 Office Hours
            Monday - Friday: 9AM - 5PM  
            Saturday: 10AM - 2PM  
            Sunday: Closed
            """)

        with col2:
            st.markdown("""
            ### 📧 General Inquiries
            **Partnerships:** partnerships@healthbridge.ng  
            **Media & Press:** media@healthbridge.ng  
            **Volunteering:** volunteers@healthbridge.ng  
            **Donations:** donate@healthbridge.ng  
            **Technical Support:** support@healthbridge.ng

            ### 🔗 Follow Us
            **LinkedIn:** @healthbridgeng  
            **Twitter:** @healthbridge_ng  
            **Instagram:** @healthbridge.initiative  
            **Facebook:** Health Bridge Initiative

            ### 📬 Send a Message
            """)

            with st.form("contact_form"):
                name = st.text_input("Your Name")
                email = st.text_input("Your Email")
                subject = st.selectbox("Subject",
                                       ["General Inquiry", "Partnership", "Volunteering",
                                        "Donation", "Technical Issue", "Other"])
                message = st.text_area("Message", height=150)

                if st.form_submit_button("Send Message"):
                    st.success("Message sent! We'll respond within 48 hours.")

    with tab4:
        st.subheader("📰 Latest Updates")

        updates = [
            {"date": "Dec 19, 2025", "title": "Inaugural Screening in Oko Afo",
             "content": "Our first community health screening event launches in Badagry."},
            {"date": "Dec 2, 2025", "title": "Executive Team Formed",
             "content": "Core leadership team established with key advisors."},
            {"date": "Nov 28, 2025", "title": "₦200,000 Community Funding Raised",
             "content": "Local Muslim community raises seed funding for pilot."},
            {"date": "Nov 15, 2025", "title": "AI Development Begins",
             "content": "Work starts on our AI health navigator MVP."},
            {"date": "Oct 30, 2025", "title": "Partnership with Local Leaders",
             "content": "Agreements signed with community and religious leaders."},
        ]

        for update in updates:
            with st.expander(f"{update['date']}: {update['title']}"):
                st.write(update['content'])

        st.markdown("---")
        st.subheader("📅 Upcoming Events")

        events = [
            {"date": "Dec 19, 2025", "event": "Community Health Screening", "location": "Oko Afo, Badagry"},
            {"date": "Jan 15, 2026", "event": "AI Training Workshop", "location": "Virtual"},
            {"date": "Feb 10, 2026", "event": "Partnership Summit", "location": "Lagos"},
            {"date": "Mar 5, 2026", "event": "Volunteer Training", "location": "Badagry"},
        ]

        for event in events:
            st.write(f"**{event['date']}:** {event['event']} - *{event['location']}*")


# Run the app
if __name__ == "__main__":
    main()

