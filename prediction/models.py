from django.db import models

class PredictionRecord(models.Model):
    disaster_type = models.CharField(max_length=50)
    risk_level = models.CharField(max_length=50)
    city = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    prediction_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.disaster_type} - {self.risk_level} at {self.prediction_time}"

class Disaster(models.Model):
    year = models.IntegerField()
    disaster_type = models.CharField(max_length=100)
    disaster_subtype = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    location = models.CharField(max_length=100)
    total_deaths = models.IntegerField()
    total_affected = models.IntegerField()
    cpi = models.FloatField()

    def __str__(self):
        return f"{self.disaster_type} - {self.year} - {self.country}"
