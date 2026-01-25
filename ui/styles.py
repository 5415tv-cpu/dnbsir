import streamlit as st

def load_css():
    st.markdown("""
        <style>
        /* Global Font & Reset */
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Pretendard', sans-serif;
        }

        /* 📱 Mobile Container Force (Center Layout) */
        .block-container {
            max-width: 500px !important;
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }
        
        /* Hide Streamlit Header/Footer for App-like feel */
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* 📱 Mobile Responsive Rules */
        @media only screen and (max-width: 768px) {
            /* 1. Font Scaling */
            html, body, [class*="css"] {
                font-size: 110% !important; 
            }
            
            /* 2. Button Optimization */
            /* Default (Secondary) - White Card Style */
            .stButton > button {
                min-height: 70px !important;
                height: auto !important;
                padding: 16px 20px !important;
                background: white !important;
                color: #333 !important;
                font-size: 17px !important;
                font-weight: 600 !important;
                border: 1px solid #f1f3f5 !important;
                border-left: 6px solid #1A73E8 !important; /* Premium Accent */
                border-radius: 20px !important; /* Extremely Rounded */
                margin-top: 6px !important;
                margin-bottom: 10px !important;
                white-space: pre-wrap !important;
                line-height: 1.5 !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
                transition: transform 0.2s, box-shadow 0.2s !important;
                text-align: left !important;
                display: flex !important;
                align-items: center !important;
                justify-content: flex-start !important;
            }
            
            /* Primary Button (Killer Features) - Gradient Hero Style with Glow */
            @keyframes pulse-glow {
                0% { box-shadow: 0 0 0 0 rgba(26, 115, 232, 0.4); }
                70% { box-shadow: 0 0 0 10px rgba(26, 115, 232, 0); }
                100% { box-shadow: 0 0 0 0 rgba(26, 115, 232, 0); }
            }

            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #1A73E8 0%, #0052cc 100%) !important;
                color: white !important;
                border: none !important;
                border-left: none !important;
                min-height: 100px !important; /* BIG */
                font-size: 22px !important;
                box-shadow: 0 10px 30px rgba(26, 115, 232, 0.4) !important;
                justify-content: center !important;
                text-align: center !important;
                animation: pulse-glow 2s infinite !important; /* GLOW EFFECT */
            }

            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 15px 35px rgba(26, 115, 232, 0.6) !important;
            }
            
            /* 3. Reduce Spacing */
            .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
            }
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 auto !important;
                min-width: 100% !important;
            }
            
            /* 4. Force 1-Column Layout for Columns */
            div[data-testid="column"] {
                width: 100% !important;
                display: block !important;
            }
        }

        /* 🎴 Kiosk Card Base */
        .kiosk-card {
            background: white;
            border-radius: 20px;
            padding: 18px 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08); /* Softer shadow */
            margin-bottom: 12px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: auto; /* Let content dictate height or min-height */
            min-height: 140px;
            border: 1px solid #f0f0f0;
        }
        
        .kiosk-card:hover {
            transform: translateY(-5px) scale(1.02);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        }
        
        .kiosk-card:active {
            transform: scale(0.98);
        }

        /* ✨ Gradient Variants */
        .card-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
        }
        .card-primary h3, .card-primary p { color: white !important; }

        .card-success {
            background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
            color: #1a472a;
        }
        
        .card-orange {
            background: linear-gradient(135deg, #fccb90 0%, #d57eeb 100%);
            color: white;
        }

        .card-glass {
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.6);
        }

        /* 🖼️ Typography */
        .kiosk-icon {
            font-size: 48px;
            margin-bottom: 12px;
            filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1));
        }
        
        .kiosk-title {
            font-size: 18px;
            font-weight: 800;
            margin-bottom: 4px;
            line-height: 1.3;
        }
        
        .kiosk-desc {
            font-size: 13px;
            opacity: 0.9;
            font-weight: 500;
        }

        /* 📏 Metric Styling */
        .metric-value {
            font-size: 28px;
            font-weight: 900;
            background: -webkit-linear-gradient(45deg, #0984e3, #00cec9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* 🔘 Button Override */
        .stButton > button {
            width: 100%;
            border-radius: 12px;
            height: 3.5rem;
            font-weight: 700;
            border: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        </style>
    """, unsafe_allow_html=True)

def card(icon, title, desc, variant="card-glass", key=None):
    """
    Renders a Kiosk-style card.
    Note: Standard Streamlit buttons are hard to style deeply due to iframe isolation.
    We will use a workaround or just render HTML for display.
    For clickable cards in Streamlit, buttons are safer.
    Here we return a styled container string for markdown usage.
    """
    return f"""
    <div class="kiosk-card {variant}">
        <div class="kiosk-icon">{icon}</div>
        <div class="kiosk-title">{title}</div>
        <div class="kiosk-desc">{desc}</div>
    </div>
    """
