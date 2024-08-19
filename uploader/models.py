from django.db import models

class ProcessedData(models.Model):
    year = models.IntegerField()
    month = models.CharField(max_length=10)
    category = models.CharField(max_length=255)
    clubbed_name = models.CharField(max_length=255)
    product = models.CharField(max_length=255)
    value = models.FloatField()

    def __str__(self):
        return f"{self.year} {self.month} {self.category} {self.clubbed_name} {self.product}"
