from django import forms

# Disaster type selection form
DISASTER_CHOICES = [
    ('Drought', 'Drought'),
    ('Landslide', 'Landslide'),
    ('Avalanche', 'Avalanche'),
]

class DisasterSelectForm(forms.Form):
    disaster_type = forms.ChoiceField(choices=DISASTER_CHOICES, label="Select Disaster Type")

# Dynamic prediction form generator based on disaster type
def get_prediction_form(disaster_type, disaster_features_display, realistic_ranges):
    fields = {}
    for display_name, feature_name in disaster_features_display[disaster_type]:
        min_val, max_val = realistic_ranges[disaster_type][feature_name]
        field_label = f"{display_name} (Range: {min_val} to {max_val})"
        fields[feature_name] = forms.FloatField(label=field_label)
    DynamicPredictionForm = type('DynamicPredictionForm', (forms.Form,), fields)
    return DynamicPredictionForm
