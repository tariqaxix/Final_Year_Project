import os
import json
import joblib
import pandas as pd
import numpy as np
import requests
import pytz
import plotly.express as px
from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Sum
from .models import PredictionRecord, Disaster

import xgboost
xgboost.XGBClassifier.use_label_encoder = False

if not hasattr(xgboost.XGBModel, 'gpu_id'):
    xgboost.XGBModel.gpu_id = property(lambda self: 0)

if not hasattr(xgboost.XGBModel, 'predictor'):
    xgboost.XGBModel.predictor = property(lambda self: "cpu_predictor")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'prediction', 'ml_models')

drought_model = joblib.load(os.path.join(MODEL_DIR, "stacking_ensemble_model.pkl"))
landslide_model = joblib.load(os.path.join(MODEL_DIR, "landslide_lr_model.pkl"))
landslide_scaler = joblib.load(os.path.join(MODEL_DIR, "landslide_scaler.pkl"))
avalanche_model = joblib.load(os.path.join(MODEL_DIR, "avalanch_rf_model.pkl"))
avalanche_scaler = joblib.load(os.path.join(MODEL_DIR, "avalanch_scaler.pkl"))

models = {
    "Drought": (drought_model, None),
    "Landslide": (landslide_model, landslide_scaler),
    "Avalanche": (avalanche_model, avalanche_scaler)
}

disaster_features_display = {
    "Drought": [
        ("Total Precipitation", "PRECTOT"),
        ("Surface Pressure", "PS"),
        ("2m Specific Humidity", "QV2M"),
        ("2m Temperature", "T2M"),
        ("2m Dew Point Temperature", "T2MDEW"),
        ("2m Wet Bulb Temperature", "T2MWET"),
        ("2m Maximum Temperature", "T2M_MAX"),
        ("2m Minimum Temperature", "T2M_MIN"),
        ("2m Temperature Range", "T2M_RANGE"),
        ("Surface Temperature", "TS"),
        ("10m Wind Speed", "WS10M"),
        ("10m Maximum Wind Speed", "WS10M_MAX"),
        ("10m Minimum Wind Speed", "WS10M_MIN"),
        ("10m Wind Speed Range", "WS10M_RANGE"),
        ("50m Wind Speed", "WS50M"),
        ("50m Maximum Wind Speed", "WS50M_MAX"),
        ("50m Minimum Wind Speed", "WS50M_MIN"),
        ("50m Wind Speed Range", "WS50M_RANGE")
    ],
    "Landslide": [
        ("Temperature (°C)", "Temperature (°C)"),
        ("Humidity (%)", "Humidity (%)"),
        ("Precipitation (mm)", "Precipitation (mm)"),
        ("Soil Moisture (%)", "Soil Moisture (%)"),
        ("Elevation (m)", "Elevation (m)")
    ],
    "Avalanche": [
        ("Elevation (m)", "elevation"),
        ("Temperature (°C)", "temperature"),
        ("Wind Speed (m/s)", "wind_speed"),
        ("Humidity (%)", "humidity"),
        ("Snow Depth (cm)", "snow_depth")
    ]
}

realistic_ranges = {
    "Drought": {
        "PRECTOT": (0, 300), "PS": (900, 1100), "QV2M": (0.0, 0.03),
        "T2M": (-50, 50), "T2MDEW": (-50, 50), "T2MWET": (-50, 50),
        "T2M_MAX": (-50, 60), "T2M_MIN": (-60, 50), "T2M_RANGE": (0, 30),
        "TS": (-50, 60), "WS10M": (0, 40), "WS10M_MAX": (0, 50),
        "WS10M_MIN": (0, 20), "WS10M_RANGE": (0, 30), "WS50M": (0, 40),
        "WS50M_MAX": (0, 50), "WS50M_MIN": (0, 20), "WS50M_RANGE": (0, 30)
    },
    "Landslide": {
        "Temperature (°C)": (-50, 50), "Humidity (%)": (0, 100),
        "Precipitation (mm)": (0, 300), "Soil Moisture (%)": (0, 100),
        "Elevation (m)": (0, 9000)
    },
    "Avalanche": {
        "elevation": (0, 9000), "temperature": (-50, 20),
        "wind_speed": (0, 50), "humidity": (0, 100), "snow_depth": (0, 500)
    }
}

labels_mapping = {
    "Drought": {0: "Low", 1: "Medium", 2: "Extreme"},
    "Landslide": {0: "Low", 1: "Medium", 2: "High"},
    "Avalanche": {0: "Low", 1: "High"}
}

API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "a280db6006e0874eb83bbc0af8b047b9")

def dashboard_page(request):
    # Existing functionalities
    prediction_records = PredictionRecord.objects.order_by('-prediction_time')[:5]
    recent_predictions = [{
        "prediction_time": rec.prediction_time.strftime("%Y-%m-%d %H:%M"),
        "city": rec.city,
        "disaster_type": rec.disaster_type,
        "risk_level": rec.risk_level,
        "lat": rec.latitude,
        "lon": rec.longitude
    } for rec in prediction_records]

    deaths_by_region = Disaster.objects.values('region').annotate(total_deaths=Sum('total_deaths'))
    fig_deaths_region = px.bar(deaths_by_region, x='region', y='total_deaths', title='Total Deaths by Region')
    chart_deaths_region_html = fig_deaths_region.to_html(full_html=False)

    df_grouped = Disaster.objects.values('country', 'disaster_type').annotate(total_deaths=Sum('total_deaths'))
    df_grouped = pd.DataFrame(df_grouped)
    df_grouped['Log Total Deaths'] = np.log1p(df_grouped['total_deaths'])

    fig_disaster_type_animation = px.choropleth(df_grouped,
        locations='country',
        locationmode='country names',
        color='Log Total Deaths',
        hover_name='country',
        animation_frame='disaster_type',
        color_continuous_scale=px.colors.diverging.RdBu,
        range_color=[df_grouped['Log Total Deaths'].min(), df_grouped['Log Total Deaths'].max()],
        projection='natural earth'
    )

    chart_disaster_type_animation_html = fig_disaster_type_animation.to_html(full_html=False)

    df_grouped_robinson = Disaster.objects.values('country').annotate(total_deaths=Sum('total_deaths'))
    df_grouped_robinson = pd.DataFrame(df_grouped_robinson)
    df_grouped_robinson['Log Total Deaths'] = np.log1p(df_grouped_robinson['total_deaths'])

    fig_disaster_type_animation_robinson = px.choropleth(df_grouped_robinson,
        locations='country',
        locationmode='country names',
        color='Log Total Deaths',
        hover_name='country',
        color_continuous_scale=px.colors.diverging.RdBu,
        range_color=[df_grouped_robinson['Log Total Deaths'].min(), df_grouped_robinson['Log Total Deaths'].max()],
        projection='robinson'
    )

    chart_disaster_type_animation_robinson_html = fig_disaster_type_animation_robinson.to_html(full_html=False)

    # **Newly added yearly trend chart**
    disaster_yearly = Disaster.objects.values('year', 'disaster_type').annotate(total=Count('disaster_type'))
    df_disaster_yearly = pd.DataFrame(disaster_yearly)
    fig_yearly_trend = px.line(df_disaster_yearly, x='year', y='total', color='disaster_type', 
                               title="Yearly Trend of Disasters")
    chart_yearly_trend_html = fig_yearly_trend.to_html(full_html=False)

    return render(request, 'prediction/dashboard.html', {
        'recent_predictions': recent_predictions,
        'chart_deaths_region_html': chart_deaths_region_html,
        'chart_disaster_type_animation_html': chart_disaster_type_animation_html,
        'chart_disaster_type_animation_robinson_html': chart_disaster_type_animation_robinson_html,
        'chart_yearly_trend_html': chart_yearly_trend_html,  # **Include the yearly trend**
    })

def interactive_page(request):
    return render(request, 'prediction/interactive.html')

def ml_page(request):
    return render(request, 'prediction/ml_page.html')

def fetch_weather(request):
    city = request.GET.get('city')
    if not city:
        return JsonResponse({"error": "Missing city parameter"}, status=400)
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={API_KEY}"
        res = requests.get(url)
        data = res.json()

        if res.status_code != 200 or 'main' not in data:
            return JsonResponse({"error": "Weather data not found or API error"}, status=400)
        
        return JsonResponse({
            "temperature": data["main"].get("temp", None),
            "humidity": data["main"].get("humidity", None),
            "pressure": data["main"].get("pressure", None),
            "wind_speed": data["wind"].get("speed", None),
            "lat": data["coord"].get("lat", None),
            "lon": data["coord"].get("lon", None)
        })
    except Exception as e:
        return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

def get_fields(request):
    dtype = request.GET.get('disaster_type')
    if not dtype or dtype not in disaster_features_display:
        return JsonResponse({"error": "Invalid disaster type"}, status=400)
    fields = [({
        "display_name": d, "feature_name": f,
        "min_val": realistic_ranges[dtype][f][0],
        "max_val": realistic_ranges[dtype][f][1]
    }) for d, f in disaster_features_display[dtype]]
    return JsonResponse({"fields": fields})

@csrf_exempt
def ajax_predict(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST supported"}, status=400)
    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    dtype = data.get("disaster_type")
    if dtype not in disaster_features_display:
        return JsonResponse({"error": "Invalid disaster type"}, status=400)
    
    form_values = data.get("form_values", {})
    values = []
    warnings = []

    for label, fname in disaster_features_display[dtype]:
        val = form_values.get(fname)
        if val is None:
            return JsonResponse({"error": f"Missing: {fname}"}, status=400)
        try:
            val = float(val)
        except:
            return JsonResponse({"error": f"{fname} must be numeric"}, status=400)
        min_v, max_v = realistic_ranges[dtype][fname]
        if not (min_v <= val <= max_v):
            warnings.append(f"{label} ({val}) is out of range ({min_v}-{max_v})")
        values.append(val)
    
    model, scaler = models[dtype]
    df = pd.DataFrame([values], columns=[f for _, f in disaster_features_display[dtype]])
    if scaler:
        df = scaler.transform(df)
    
    pred = model.predict(df)
    pred_val = int(float(pred[0])) if not isinstance(pred[0], str) else pred[0]
    label = labels_mapping[dtype].get(pred_val, str(pred_val))

    safety_tips = {
        "Drought": "🌟 Tips to stay safe in drought-prone regions: Save water, grow drought-resistant crops, avoid excessive water usage.",
        "Landslide": "⛷️ Landslide risk high? Avoid unstable slopes, stay clear of mountain foothills during rainfall.",
        "Avalanche": "❄️ Avalanche risk high? Avoid high-altitude snowy areas, be cautious during heavy snowstorms."
    }

    safety_tip = safety_tips.get(dtype, "Stay safe and prepare in advance!")

    PredictionRecord.objects.create(
        disaster_type=dtype,
        risk_level=label,
        city=data.get("city", ""),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        prediction_time=timezone.now()
    )

    return JsonResponse({
        "result": label,
        "warnings": warnings,
        "safety_tip": safety_tip
    })

def get_predictions(request):
    gmt6 = pytz.timezone("Asia/Almaty")
    records = PredictionRecord.objects.order_by('-prediction_time')[:5]
    data = [{
        "prediction_time": rec.prediction_time.astimezone(gmt6).strftime("%Y-%m-%d %H:%M"),
        "city": rec.city, "disaster_type": rec.disaster_type,
        "risk_level": rec.risk_level, "lat": rec.latitude, "lon": rec.longitude
    } for rec in records]
    return JsonResponse({"predictions": data})
