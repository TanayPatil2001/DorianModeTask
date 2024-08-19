# from django import forms
# from .models import ProcessedData
# class UploadFileForm(forms.ModelForm):
#     class Meta:
#         model = ProcessedData
#         fields = ['file']

from django import forms
from .models import ProcessedData

class UploadFileForm(forms.Form):
    file = forms.FileField()

