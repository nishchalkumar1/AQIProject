
import math

def calculate_sub_index(concentration, breakpoints):
    """
    Calculates the sub-index for a single pollutant based on CPCB breakpoints.
    Formula: I = [(IHi - ILo) / (BPHi - BPLo)] * (Cp - BPLo) + ILo
    """
    if concentration is None or math.isnan(concentration):
        return None
        
    cp = concentration
    
    for (bCk_low, bCk_high, i_low, i_high) in breakpoints:
        if bCk_low <= cp <= bCk_high:
            return ((i_high - i_low) / (bCk_high - bCk_low)) * (cp - bCk_low) + i_low
            
    # If out of range (usually very high), extrapolate or cap? 
    # CPCB caps at 500+ usually. We'll return max or extrapolate linear from last bucket.
    if cp > breakpoints[-1][1]:
        # Extrapolate using the last bucket's slope
        (bCk_low, bCk_high, i_low, i_high) = breakpoints[-1]
        return ((i_high - i_low) / (bCk_high - bCk_low)) * (cp - bCk_low) + i_low
        
    return 0

def calculate_aqi_pm25(pm25_concentration):
    """
    Calculates AQI for PM2.5 based on Indian CPCB standards.
    Input: PM2.5 concentration in µg/m³
    """
    # Breakpoints (Concentration Low, Concentration High, AQI Low, AQI High)
    # Source: CPCB
    # 0-30 -> 0-50
    # 31-60 -> 51-100
    # 61-90 -> 101-200
    # 91-120 -> 201-300
    # 121-250 -> 301-400
    # 250+ -> 401-500
    
    pm25_breakpoints = [
        (0, 30, 0, 50),
        (30.1, 60, 51, 100),
        (60.1, 90, 101, 200),
        (90.1, 120, 201, 300),
        (120.1, 250, 301, 400),
        (250.1, 1000, 401, 500) # Cap at 500+ effectively
    ]
    
    aqi = calculate_sub_index(pm25_concentration, pm25_breakpoints)
    if aqi is None:
        return None
    return round(aqi)

def get_aqi_category(aqi):
    if aqi is None:
        return "Unknown"
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"

def get_health_advisory(aqi):
    category = get_aqi_category(aqi)
    
    advisories = {
        "Good": {
            "effect": "Minimal Impact.",
            "precaution": "Enjoy your outdoor activities.",
            "health_risks": [
                "Air quality is satisfactory",
                "No health implications",
                "Safe for outdoor activities"
            ],
            "vulnerable_groups": []
        },
        "Satisfactory": {
            "effect": "May cause minor breathing discomfort to sensitive people.",
            "precaution": "Sensitive people should consider reducing prolonged outdoor exertion.",
            "health_risks": [
                "Minor breathing discomfort for sensitive individuals",
                "Slight irritation in eyes and throat",
                "Mild coughing in people with asthma"
            ],
            "vulnerable_groups": ["People with asthma", "Young children", "Elderly"]
        },
        "Moderate": {
            "effect": "Breathing discomfort to people with lung disease, heart disease, children and older adults.",
            "precaution": "People with respiratory or heart disease should limit outdoor exertion.",
            "health_risks": [
                "Breathing discomfort during prolonged exposure",
                "Increased respiratory symptoms (coughing, wheezing)",
                "Aggravation of heart and lung diseases",
                "Reduced lung function in children",
                "Eye, nose, and throat irritation"
            ],
            "vulnerable_groups": ["Heart disease patients", "Lung disease patients", "Children", "Older adults"]
        },
        "Poor": {
            "effect": "Breathing discomfort to people on prolonged exposure and discomfort to people with heart disease.",
            "precaution": "Limit prolonged outdoor exertion. Wear masks if stepping out.",
            "health_risks": [
                "Increased respiratory symptoms in general population",
                "Difficulty breathing and chest tightness",
                "Aggravated asthma and COPD symptoms",
                "Increased risk of heart attacks",
                "Reduced stamina and fatigue",
                "Headaches and dizziness",
                "Skin irritation and rashes"
            ],
            "vulnerable_groups": ["Everyone (especially vulnerable groups)", "Pregnant women", "People with diabetes"]
        },
        "Very Poor": {
            "effect": "Respiratory illness to the people on prolonged exposure. Effect may be more pronounced in people with lung and heart diseases.",
            "precaution": "Avoid outdoor activities. Use air purifiers indoors if possible. Wear N95 masks.",
            "health_risks": [
                "Severe respiratory illness on prolonged exposure",
                "Chronic bronchitis and reduced lung function",
                "Increased hospital admissions for respiratory issues",
                "Cardiovascular complications and arrhythmia",
                "Premature death in people with heart/lung disease",
                "Severe asthma attacks requiring emergency care",
                "Weakened immune system",
                "Long-term lung damage"
            ],
            "vulnerable_groups": ["Entire population at risk", "Immediate danger to vulnerable groups"]
        },
        "Severe": {
            "effect": "Respiratory effects even on healthy people and serious health impacts on people with existing diseases.",
            "precaution": "Avoid all outdoor activities. Close windows. Consult a doctor if you feel breathless.",
            "health_risks": [
                "Serious respiratory effects even in healthy individuals",
                "Acute respiratory distress syndrome (ARDS)",
                "Severe cardiovascular complications",
                "Stroke and heart attack risk significantly elevated",
                "Permanent lung damage with prolonged exposure",
                "Premature mortality in vulnerable populations",
                "Neurological effects and cognitive impairment",
                "Increased cancer risk with long-term exposure",
                "Emergency medical attention may be required"
            ],
            "vulnerable_groups": ["EVERYONE - Emergency health alert"]
        },
        "Unknown": {
             "effect": "Data unavailable.",
             "precaution": "-",
             "health_risks": [],
             "vulnerable_groups": []
        }
    }
    
    return advisories.get(category, advisories["Unknown"])

